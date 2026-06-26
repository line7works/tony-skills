#!/usr/bin/env python3
"""
forge - Claude-driven, model-agnostic AI image generation on Fal.ai.

The deterministic spine behind the /forge skill. Python standard library only:
no pip installs. Talks to Fal's REST queue directly (submit -> poll -> fetch ->
download), writes an auditable run manifest, guards spend with a running cost
cap, and renders an HTML contact sheet you can open in a browser.

Commands: gen, batch, compare, resume, estimate, models.
(edit, style, finish, export, init arrive in later milestones.)

Usage:
    python3 forge.py models
    python3 forge.py estimate "a trophy" --model gpt --size 1024 --quality high
    python3 forge.py gen "a trophy on an orange podium" --model nano --size 1024
    python3 forge.py batch shots.md --refs ./brand --cap 3 --concurrency 4
    python3 forge.py compare "a mascot" --models nano,gpt,flux
    python3 forge.py resume 20260626-072444-a-clean-flat-mod
"""

import argparse
import csv
import html
import io
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

QUEUE_HOST = "https://queue.fal.run"   # verified host + "Authorization: Key <FAL_KEY>" auth
HTTP_TIMEOUT = 180
POLL_TIMEOUT = 240
DEFAULT_CONCURRENCY = 4
MAX_ATTEMPTS = 3
SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR / "models.json"


# ---------- output helpers ----------

def die(msg, code=1):
    print(f"forge: error: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"forge: {msg}", file=sys.stderr)


def require_key():
    key = os.environ.get("FAL_KEY")
    if not key:
        die("FAL_KEY is not set. Get a key at fal.ai and `export FAL_KEY=...` in "
            "your shell (see IMPLEMENTATION.md section 10).")
    return key


# ---------- registry ----------

def load_registry():
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except FileNotFoundError:
        die(f"model registry not found at {REGISTRY_PATH}")
    except json.JSONDecodeError as e:
        die(f"model registry is not valid JSON: {e}")


def resolve_model(alias, reg):
    models = reg.get("models", {})
    alias = alias or reg.get("default_model")
    if alias not in models:
        die(f"unknown model '{alias}'. Known: {', '.join(sorted(models))}")
    cfg = dict(models[alias])
    cfg["alias"] = alias
    return cfg


# ---------- size / input building ----------

PRESETS = {
    "0.5k": (512, 512), "1k": (1024, 1024), "2k": (2048, 2048),
    "4k": (4096, 4096), "square": (1024, 1024), "hd": (1280, 720),
}
ASPECTS = {
    "1:1": 1.0, "16:9": 16 / 9, "9:16": 9 / 16, "4:3": 4 / 3, "3:4": 3 / 4,
    "3:2": 3 / 2, "2:3": 2 / 3, "21:9": 21 / 9, "4:5": 0.8, "5:4": 1.25,
}


def parse_dims(size):
    """Return (w, h) ints from '1024', '1024x768', or a preset; else None."""
    if not size:
        return None
    s = str(size).strip().lower()
    if s in PRESETS:
        return PRESETS[s]
    m = re.match(r"^(\d+)\s*[x×]\s*(\d+)$", s)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        return (w, h) if w > 0 and h > 0 else None
    if s.isdigit():
        n = int(s)
        return (n, n) if n > 0 else None
    return None


def nearest_aspect(w, h):
    r = w / h
    return min(ASPECTS, key=lambda k: abs(ASPECTS[k] - r))


def res_bucket(maxdim):
    if maxdim <= 512:
        return "0.5K"
    if maxdim <= 1024:
        return "1K"
    if maxdim <= 2048:
        return "2K"
    return "4K"


def build_input(cfg, prompt, dims, quality, num, seed, negative, image_urls=None):
    """Assemble the model-specific Fal input body from generic args."""
    inp = {"prompt": prompt, "num_images": num, "output_format": "png"}
    style = cfg.get("size_style")
    if style == "image_size":
        if dims:
            inp["image_size"] = {"width": dims[0], "height": dims[1]}
        if cfg.get("supports_quality") and quality:
            inp["quality"] = quality
    elif style == "aspect_resolution":
        if dims:
            inp["aspect_ratio"] = nearest_aspect(*dims)
            inp["resolution"] = res_bucket(max(dims))
        else:
            inp["resolution"] = "1K"
    if cfg.get("supports_seed") and seed is not None:
        inp["seed"] = seed
    if cfg.get("supports_negative") and negative:
        inp["negative_prompt"] = negative
    if image_urls:
        inp["image_urls"] = image_urls
    return inp


# ---------- cost ----------

def estimate_per_image(cfg, dims, quality):
    """Conservative upper-bound per-image price in USD from the registry."""
    by = cfg.get("price_by")
    price = cfg.get("price_usd")
    default = float(cfg.get("price_default", 0.15))
    if by == "flat":
        return float(price)
    if by == "resolution":
        bucket = res_bucket(max(dims)) if dims else "1K"
        return float(price.get(bucket, default))
    if by == "quality":
        q = quality or "high"
        if dims and max(dims) >= 4096:
            for k in (q + "@4k", "high@4k"):   # conservative 4K ceiling for any quality
                if k in price:
                    return float(price[k])
        return float(price.get(q, default))
    return default


# ---------- http ----------

_SSL_CTX = None


def _ca_bundle():
    """Find a CA bundle. macOS Python builds often ship an empty default trust
    store, which is the usual cause of CERTIFICATE_VERIFY_FAILED."""
    candidates = [os.environ.get("SSL_CERT_FILE")]
    try:
        import certifi
        candidates.append(certifi.where())
    except Exception:
        pass
    candidates += [
        "/etc/ssl/cert.pem",
        "/private/etc/ssl/cert.pem",
        "/opt/homebrew/etc/openssl@3/cert.pem",
        "/usr/local/etc/openssl@3/cert.pem",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def ssl_context():
    """Verified TLS context, loading an explicit CA bundle if the default store
    is empty. Verification stays on so FAL_KEY never crosses an unverified link."""
    global _SSL_CTX
    if _SSL_CTX is None:
        ctx = ssl.create_default_context()
        if not ctx.get_ca_certs():
            bundle = _ca_bundle()
            if bundle:
                try:
                    ctx.load_verify_locations(bundle)
                except Exception:
                    pass
        _SSL_CTX = ctx
    return _SSL_CTX


def _request(url, method="GET", body=None, headers=None, timeout=HTTP_TIMEOUT):
    hdr = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error reaching {url}: {e.reason}")


def auth(key):
    return {"Authorization": f"Key {key}"}


def submit_job(model_id, inp, key):
    code, raw = _request(f"{QUEUE_HOST}/{model_id}", "POST", inp, auth(key))
    if code not in (200, 201):
        raise RuntimeError(f"Fal submit failed ({code}): {raw[:300].decode('utf-8', 'replace')}")
    return json.loads(raw)


def poll_job(status_url, key, timeout=POLL_TIMEOUT):
    waited, interval, not_found = 0, 2, 0
    while True:
        code, raw = _request(status_url, "GET", None, auth(key), timeout=60)
        if code in (200, 202):                 # Fal returns 202 while IN_QUEUE / IN_PROGRESS
            status = json.loads(raw).get("status")
            if status == "COMPLETED":
                return
            if status in ("FAILED", "ERROR"):
                raise RuntimeError(f"Fal job failed: {raw[:300].decode('utf-8', 'replace')}")
            interval, not_found = 2, 0
        elif code == 404 and not_found < 5:    # queue eventual-consistency right after submit
            not_found += 1
            interval = 3
        elif code == 429 or code >= 500:
            interval = min(interval * 2, 15)   # back off on throttle / server error
        else:
            raise RuntimeError(f"Fal status error ({code}): {raw[:200].decode('utf-8', 'replace')}")
        if waited >= timeout:
            raise RuntimeError(f"timed out after {timeout}s waiting for Fal result")
        time.sleep(interval)
        waited += interval


def fetch_result(response_url, key):
    code, raw = _request(response_url, "GET", None, auth(key), timeout=60)
    if code != 200:
        raise RuntimeError(f"Fal result fetch failed ({code}): {raw[:200].decode('utf-8', 'replace')}")
    return json.loads(raw)


def download(url, dest):
    code, raw = _request(url, "GET", timeout=120)   # CDN URL, no auth needed
    if code != 200:
        raise RuntimeError(f"image download failed ({code}) from {url}")
    dest.write_bytes(raw)


# ---------- manifest / fs ----------

def slugify(text, n=16):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "gen").lower()).strip("-")
    return s[:n] or "gen"


def new_run_id(label):
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + slugify(label)


def write_atomic(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def find_git_root(start):
    for d in [Path(start).resolve(), *Path(start).resolve().parents]:
        if (d / ".git").exists():
            return d
    return None


def ensure_gitignore(start):
    """Keep generated assets and any local key out of the host repo."""
    root = find_git_root(start)
    if not root:
        return
    gi = root / ".gitignore"
    existing = gi.read_text().splitlines() if gi.exists() else []
    missing = [x for x in ("generated-assets/", ".env") if x not in existing]
    if missing:
        with gi.open("a") as f:
            if existing and existing[-1].strip():
                f.write("\n")
            f.write("# forge\n" + "\n".join(missing) + "\n")


def load_brand_profile(explicit=None):
    """Read the nearest .forge/brand.json (full auto-detect + init land in M3)."""
    path = Path(explicit) if explicit else None
    if path is None:
        for d in [Path.cwd(), *Path.cwd().parents]:
            cand = d / ".forge" / "brand.json"
            if cand.exists():
                path = cand
                break
    if path and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            warn(f"brand profile at {path} is not valid JSON; ignoring")
    return {}


# ---------- shot lists ----------

def _norm_shot(row, i):
    prompt = (row.get("prompt") or row.get("brief") or "").strip()
    sid = str(row.get("id") or f"shot-{i:02d}")
    out = {"id": slugify(sid, 24), "prompt": prompt}
    for k in ("model", "size"):
        if row.get(k):
            out[k] = str(row[k]).strip()
    if row.get("negative"):
        out["negative"] = str(row["negative"]).strip()
    if row.get("seed") not in (None, ""):
        out["seed"] = int(row["seed"])
    if row.get("num") not in (None, ""):
        out["num"] = max(1, int(row["num"]))
    return out


def _dedup_ids(items):
    """Suffix colliding shot ids so each writes a distinct file. Non-ASCII ids all
    slugify to 'gen', which would otherwise overwrite one another on disk."""
    seen = {}
    for i, it in enumerate(items, 1):
        base = it.get("id") or f"shot-{i:02d}"
        seen[base] = seen.get(base, 0) + 1
        it["id"] = base if seen[base] == 1 else f"{base}-{seen[base]}"
    return items


def parse_shotlist(path):
    """One shot per row. Markdown/text lines, or .json array, or .csv rows."""
    p = Path(path)
    if not p.exists():
        die(f"shot list not found: {path}")
    text = p.read_text()
    if p.suffix == ".json":
        items = [_norm_shot(r if isinstance(r, dict) else {"prompt": r}, i)
                 for i, r in enumerate(json.loads(text), 1)]
        return _dedup_ids(items)
    if p.suffix == ".csv":
        items = [_norm_shot(r, i) for i, r in enumerate(csv.DictReader(io.StringIO(text)), 1)]
        return _dedup_ids(items)
    items, i = [], 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        i += 1
        line = re.sub(r"^[-*]\s+", "", line)
        if ":" in line:
            label, brief = line.split(":", 1)
            items.append({"id": slugify(label, 24), "prompt": brief.strip()})
        else:
            items.append({"id": f"shot-{i:02d}", "prompt": line})
    return _dedup_ids(items)


# ---------- run engine ----------

def _is_transient(err):
    """Retryable failures: timeouts, network blips, Fal 429/5xx, and the spurious
    403 balance-lock Fal can throw when several paid jobs submit in the same burst
    (observed live against a healthy balance). Matches the parenthesized HTTP code
    the raisers actually emit, e.g. 'submit failed (500):'."""
    s = str(err).lower()
    if "timed out" in s or "network error" in s:
        return True
    if "(403)" in s and ("locked" in s or "exhausted" in s):
        return True
    return any(f"({code})" in s for code in ("429", "500", "502", "503", "504"))


def _new_item(idx, shot, cfg, size, dims, quality, seed, per, negative=None):
    return {
        "id": shot.get("id") or f"shot-{idx:02d}", "status": "pending",
        "prompt": shot["prompt"], "model": cfg["alias"], "fal_id": cfg["id"],
        "size": size, "quality": quality, "seed": seed, "negative": negative,
        "num_images": max(1, int(shot.get("num", 1) or 1)),
        "request_id": None, "status_url": None, "response_url": None,
        "submitted_at": None, "completed_at": None, "attempts": 0,
        "cost_usd": round(per, 4), "cost_basis": "estimate", "outputs": [], "error": None,
    }


def process_item(item, cfg, inp, run_dir, key, persist):
    """Submit -> poll -> download one item, with retry/backoff. Never raises."""
    delay = 2
    for attempt in range(1, MAX_ATTEMPTS + 1):
        item["attempts"] = attempt
        try:
            sub = submit_job(cfg["id"], inp, key)
            item["request_id"] = sub.get("request_id")
            item["status_url"] = sub.get("status_url")
            item["response_url"] = sub.get("response_url")
            item["status"] = "submitted"
            item["submitted_at"] = datetime.now().isoformat(timespec="seconds")
            persist()
            poll_job(item["status_url"], key)
            result = fetch_result(item["response_url"], key)
            _save_images(item, result, run_dir)
            item["status"] = "completed"
            item["completed_at"] = datetime.now().isoformat(timespec="seconds")
            item["error"] = None
            persist()
            return
        except Exception as e:
            item["error"] = str(e)
            if attempt < MAX_ATTEMPTS and _is_transient(e):
                time.sleep(delay)
                delay = min(delay * 2, 15)
                continue
            item["status"] = "failed"
            persist()
            return


def _save_images(item, result, run_dir):
    images = result.get("images", [])
    if not images:
        raise RuntimeError("Fal returned no images")
    raw_dir = run_dir / "raw"
    item["outputs"] = []
    for i, img in enumerate(images, 1):
        suffix = f"-{i}" if len(images) > 1 else ""
        dest = raw_dir / f"{item['id']}{suffix}.png"
        download(img["url"], dest)
        item["outputs"].append(str(dest.relative_to(run_dir)))


def run_batch(shots, defaults, reg, run_dir, command, cap, concurrency, key, brand):
    """Core engine for gen/batch/compare. Concurrent, cost-capped, atomic manifest."""
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    ensure_gitignore(Path.cwd())
    manifest_path = run_dir / "manifest.json"
    lock = threading.Lock()
    committed = {"usd": 0.0}

    jobs, manifest_items = [], []
    for idx, shot in enumerate(shots, 1):
        cfg = resolve_model(shot.get("model") or defaults.get("model") or brand.get("default_model"), reg)
        size = shot.get("size") or defaults.get("size") or brand.get("default_size")
        dims = parse_dims(size)
        quality = defaults.get("quality")
        seed = shot.get("seed") if shot.get("seed") is not None else defaults.get("seed")
        negative = shot.get("negative") or defaults.get("negative")
        num = max(1, int(shot.get("num", 1) or 1))
        per = estimate_per_image(cfg, dims, quality) * num          # reserve all N images
        item = _new_item(idx, shot, cfg, size, dims, quality, seed, per, negative)
        manifest_items.append(item)
        jobs.append((item, cfg, dims, quality, seed, negative, per))

    manifest = {
        "schema_version": 1, "run_id": run_dir.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "command": command, "cap_usd": cap, "spent_usd": 0.0, "items": manifest_items,
    }
    write_atomic(manifest_path, manifest)

    def persist():
        with lock:
            manifest["spent_usd"] = round(
                sum(it["cost_usd"] for it in manifest_items if it["status"] == "completed"), 4)
            write_atomic(manifest_path, manifest)

    def reserve(per):
        with lock:
            if cap is not None and committed["usd"] + per > cap + 1e-9:
                return False
            committed["usd"] += per
            return True

    def worker(job):
        item, cfg, dims, quality, seed, negative, per = job
        try:
            if not reserve(per):
                item["status"], item["error"] = "skipped", "cap reached"
                persist()
                return
            inp = build_input(cfg, item["prompt"], dims, quality, item["num_images"],
                              seed, negative)
            process_item(item, cfg, inp, run_dir, key, persist)
        except Exception as e:
            item["status"], item["error"] = "failed", str(e)
            persist()

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        list(ex.map(worker, jobs))
    persist()
    return manifest, manifest_path


# ---------- contact sheet ----------

def write_contact_sheet(run_dir, manifest):
    items = manifest["items"]
    cells = []
    for it in items:
        imgs = "".join(f'<img src="{html.escape(o)}" loading="lazy">' for o in it.get("outputs", [])) \
            or '<div class="ph">no image</div>'
        cells.append(
            f'<figure class="cell {it["status"]}">{imgs}'
            f'<figcaption><b>{html.escape(it["id"])}</b> &middot; {html.escape(it["model"])} '
            f'&middot; ${it["cost_usd"]:.3f} &middot; {it["status"]}'
            f'<span class="prompt">{html.escape(it["prompt"])}</span></figcaption></figure>')
    spent = manifest.get("spent_usd", 0)
    doc = (
        '<!doctype html><meta charset="utf-8">'
        f'<title>forge &middot; {html.escape(manifest["run_id"])}</title>'
        '<style>'
        'body{font:14px -apple-system,system-ui,sans-serif;margin:24px;background:#faf9fb;color:#1e1b20}'
        'h1{font-size:15px;font-weight:600}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}'
        '.cell{margin:0;background:#fff;border:1px solid #e5e3e8;border-radius:10px;overflow:hidden}'
        '.cell img{width:100%;display:block;aspect-ratio:1;object-fit:contain;background:#fff}'
        '.cell.failed,.cell.skipped{opacity:.45}'
        'figcaption{padding:8px 10px;font-size:12px;line-height:1.4}'
        '.prompt{display:block;color:#6b6770;margin-top:4px}'
        '.ph{aspect-ratio:1;display:grid;place-items:center;color:#bbb}'
        '</style>'
        f'<h1>forge &middot; {html.escape(manifest["run_id"])} &middot; '
        f'{len(items)} shots &middot; ${spent:.2f}</h1>'
        f'<div class="grid">{"".join(cells)}</div>')
    path = run_dir / "contact-sheet.html"
    path.write_text(doc)
    return path


# ---------- shared command helpers ----------

def _defaults_from_args(args):
    return {"model": args.model, "size": args.size, "quality": args.quality,
            "seed": args.seed, "negative": getattr(args, "negative", None)}


def _out_root(args):
    return Path(args.out) if args.out else (Path.cwd() / "generated-assets")


def _estimate_shots(shots, defaults, reg, brand):
    total, rows = 0.0, []
    for idx, shot in enumerate(shots, 1):
        cfg = resolve_model(shot.get("model") or defaults.get("model") or brand.get("default_model"), reg)
        dims = parse_dims(shot.get("size") or defaults.get("size") or brand.get("default_size"))
        num = max(1, int(shot.get("num", 1) or 1))
        per = estimate_per_image(cfg, dims, defaults.get("quality")) * num
        total += per
        rows.append((shot.get("id") or f"shot-{idx:02d}", cfg["alias"], per))
    return total, rows


def _summary(manifest, sheet):
    items = manifest["items"]
    by = {}
    for it in items:
        by[it["status"]] = by.get(it["status"], 0) + 1
    parts = ", ".join(f"{n} {s}" for s, n in by.items())
    print(f"done. {parts}. spent ~${manifest['spent_usd']:.3f}")
    for it in items:
        if it["status"] == "completed":
            print(f"  [{it['id']}] {it['outputs'][0] if it['outputs'] else ''}")
        elif it["status"] != "pending":
            print(f"  [{it['id']}] {it['status']}: {it.get('error') or ''}")
    if sheet:
        print(f"contact sheet: {sheet}")
        print(f"  open {sheet}")


# ---------- commands ----------

def cmd_models(args, reg):
    models = reg.get("models", {})
    print(f"{'alias':<10} {'fal id':<28} {'preset':<8} price (USD/image)")
    print("-" * 72)
    for alias, cfg in models.items():
        price = cfg.get("price_usd")
        hint = (f"${price}" if not isinstance(price, dict)
                else " ".join(f"{k}=${v}" for k, v in price.items()))
        print(f"{alias:<10} {cfg.get('id', ''):<28} {cfg.get('preset', ''):<8} {hint}")
    print(f"\ndefault model: {reg.get('default_model')}")
    if reg.get("note"):
        print(f"note: {reg['note']}")


def cmd_estimate(args, reg):
    brand = load_brand_profile(args.brand)
    cfg = resolve_model(args.model or brand.get("default_model"), reg)
    size = args.size or brand.get("default_size")
    per = estimate_per_image(cfg, parse_dims(size), args.quality)
    total = per * args.num
    if args.json:
        print(json.dumps({"model": cfg["alias"], "fal_id": cfg["id"], "size": size,
                          "quality": args.quality, "num_images": args.num,
                          "per_image_usd": round(per, 4), "estimated_total_usd": round(total, 4),
                          "basis": "conservative upper bound"}, indent=2))
    else:
        print(f"~${total:.3f} for {args.num} image(s) on '{cfg['alias']}' "
              f"(~${per:.3f} each, conservative upper bound)")


def cmd_gen(args, reg):
    brand = load_brand_profile(args.brand)
    defaults = _defaults_from_args(args)
    shots = [{"id": "img-01", "prompt": args.prompt, "num": args.num}]
    cfg = resolve_model(args.model or brand.get("default_model"), reg)
    per = estimate_per_image(cfg, parse_dims(args.size or brand.get("default_size")), args.quality)
    total = per * args.num
    if args.cap is not None and total > args.cap:
        die(f"estimate ${total:.3f} exceeds --cap ${args.cap:.2f}. "
            f"Raise the cap or lower --num/--size/--quality.")
    if args.dry_run:
        inp = build_input(cfg, args.prompt, parse_dims(args.size or brand.get("default_size")),
                          args.quality, args.num, args.seed, args.negative)
        plan = {"command": "gen", "dry_run": True, "model": cfg["alias"], "fal_id": cfg["id"],
                "size": args.size or brand.get("default_size"), "num_images": args.num,
                "estimated_total_usd": round(total, 4), "input": inp}
        print(json.dumps(plan, indent=2) if args.json
              else f"[dry run] '{cfg['alias']}' x{args.num} ~${total:.3f}, no spend.\ninput: {json.dumps(inp)}")
        return
    key = require_key()
    run_dir = _out_root(args) / new_run_id(args.prompt)
    manifest, mpath = run_batch(shots, defaults, reg, run_dir, "gen", args.cap, 1, key, brand)
    if args.json:
        it = manifest["items"][0]
        print(json.dumps({"run_id": manifest["run_id"], "model": it["model"], "status": it["status"],
                          "outputs": [str(run_dir / o) for o in it["outputs"]],
                          "estimated_cost_usd": manifest["spent_usd"], "manifest": str(mpath)}, indent=2))
    else:
        _summary(manifest, None)
        print(f"manifest: {mpath}")


def cmd_batch(args, reg):
    brand = load_brand_profile(args.brand)
    shots = parse_shotlist(args.shotlist)
    if not shots:
        die(f"no shots found in {args.shotlist}")
    defaults = _defaults_from_args(args)
    total, rows = _estimate_shots(shots, defaults, reg, brand)
    if args.dry_run:
        print(f"[dry run] {len(shots)} shots, estimated total ~${total:.3f} "
              f"(cap {'$'+format(args.cap, '.2f') if args.cap else 'none'}):")
        for sid, model, per in rows:
            print(f"  [{sid}] {model} ~${per:.3f}")
        return
    if args.cap is not None and total > args.cap:
        warn(f"total estimate ~${total:.3f} exceeds cap ${args.cap:.2f}; "
             f"forge will run as many shots as fit and skip the rest.")
    key = require_key()
    run_dir = _out_root(args) / new_run_id(Path(args.shotlist).stem)
    manifest, mpath = run_batch(shots, defaults, reg, run_dir, "batch", args.cap,
                                args.concurrency or DEFAULT_CONCURRENCY, key, brand)
    sheet = write_contact_sheet(run_dir, manifest)
    if args.json:
        print(json.dumps({"run_id": manifest["run_id"], "spent_usd": manifest["spent_usd"],
                          "manifest": str(mpath), "contact_sheet": str(sheet),
                          "items": manifest["items"]}, indent=2))
    else:
        _summary(manifest, sheet)


def cmd_compare(args, reg):
    brand = load_brand_profile(args.brand)
    models = [m.strip() for m in (args.models or "nano,gpt,flux").split(",") if m.strip()]
    shots = [{"id": m, "prompt": args.prompt, "model": m} for m in models]
    defaults = _defaults_from_args(args)
    defaults["model"] = None  # per-shot model wins
    total, rows = _estimate_shots(shots, defaults, reg, brand)
    if args.dry_run:
        print(f"[dry run] compare across {len(models)} models, ~${total:.3f}:")
        for sid, model, per in rows:
            print(f"  [{sid}] ~${per:.3f}")
        return
    key = require_key()
    run_dir = _out_root(args) / new_run_id("compare-" + slugify(args.prompt, 12))
    manifest, mpath = run_batch(shots, defaults, reg, run_dir, "compare", args.cap,
                                args.concurrency or DEFAULT_CONCURRENCY, key, brand)
    sheet = write_contact_sheet(run_dir, manifest)
    if args.json:
        print(json.dumps({"run_id": manifest["run_id"], "spent_usd": manifest["spent_usd"],
                          "manifest": str(mpath), "contact_sheet": str(sheet),
                          "items": manifest["items"]}, indent=2))
    else:
        _summary(manifest, sheet)


def _resume_terminal(err):
    """True when a re-poll error means the prior Fal request is genuinely gone or
    failed, so a fresh (paid) submit is safe. False for transient errors (timeout,
    network, 5xx, download blip) where the job may still be live and re-submitting
    would pay twice."""
    s = str(err).lower()
    return "(404)" in s or "not found" in s or "fal job failed" in s


def cmd_resume(args, reg):
    out_root = _out_root(args)
    run_dir = out_root / args.run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        die(f"no manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    items = manifest["items"]
    # re-do anything not cleanly completed, including a "completed" item left with
    # no files by a crash mid-save (re-polling re-fetches it without paying again).
    todo = [it for it in items if it["status"] != "completed" or not it.get("outputs")]
    if not todo:
        print("nothing to resume; all items already completed.")
        return
    key = require_key()
    lock = threading.Lock()
    cap = getattr(args, "cap", None)
    # seed the breaker with money already spent so --cap is a whole-run ceiling
    committed = {"usd": round(sum(it["cost_usd"] for it in items
                                  if it["status"] == "completed" and it.get("outputs")), 4)}

    def persist():
        with lock:
            manifest["spent_usd"] = round(
                sum(it["cost_usd"] for it in items if it["status"] == "completed"), 4)
            write_atomic(manifest_path, manifest)

    def reserve(per):
        with lock:
            if cap is not None and committed["usd"] + per > cap + 1e-9:
                return False
            committed["usd"] += per
            return True

    def worker(it):
        cfg = resolve_model(it["model"], reg)
        # an already-submitted job: re-poll its result instead of paying again
        if it.get("response_url") and it.get("status_url"):
            try:
                poll_job(it["status_url"], key)
                _save_images(it, fetch_result(it["response_url"], key), run_dir)
                it["status"] = "completed"
                it["completed_at"] = datetime.now().isoformat(timespec="seconds")
                it["error"] = None
                persist()
                return
            except RuntimeError as e:
                if not _resume_terminal(e):
                    it["status"] = "submitted"        # may still be in flight; never re-pay
                    it["error"] = f"resume deferred, run again later: {e}"
                    persist()
                    return
                # else: genuinely gone/failed -> fall through to a fresh, reserved submit
        if not reserve(it.get("cost_usd") or 0.0):
            it["status"], it["error"] = "skipped", "cap reached"
            persist()
            return
        dims = parse_dims(it.get("size"))
        inp = build_input(cfg, it["prompt"], dims, it.get("quality"),
                          it.get("num_images", 1), it.get("seed"), it.get("negative"))
        process_item(it, cfg, inp, run_dir, key, persist)

    with ThreadPoolExecutor(max_workers=args.concurrency or DEFAULT_CONCURRENCY) as ex:
        list(ex.map(worker, todo))
    persist()
    sheet = write_contact_sheet(run_dir, manifest)
    _summary(manifest, sheet)


# ---------- arg parsing ----------

def _add_common(sp):
    sp.add_argument("--model", help="model alias (nano, nano-pro, gpt, flux)")
    sp.add_argument("--size", help="WxH, a number, or a preset (1k/2k/4k)")
    sp.add_argument("--quality", choices=["auto", "low", "medium", "high"],
                    help="for models priced by quality (gpt)")
    sp.add_argument("-n", "--num", type=int, default=1, help="images per prompt")
    sp.add_argument("--seed", type=int, help="fixed seed (models that support it)")
    sp.add_argument("--negative", help="negative prompt (models that support it)")
    sp.add_argument("--refs", help="reference image folder (used in later milestones)")
    sp.add_argument("--brand", help="path to a brand profile (.forge/brand.json)")
    sp.add_argument("--cap", type=float, help="spend ceiling in USD (circuit-breaker)")
    sp.add_argument("--concurrency", type=int, help=f"parallel jobs (default {DEFAULT_CONCURRENCY})")
    sp.add_argument("--out", help="output dir (default ./generated-assets)")
    sp.add_argument("--dry-run", action="store_true", help="plan + estimate only, no spend")
    sp.add_argument("--json", action="store_true", help="machine-readable output")


def build_parser():
    p = argparse.ArgumentParser(prog="forge", description="Claude-driven image generation on Fal.ai.")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("gen", help="generate images from a prompt")
    g.add_argument("prompt")
    _add_common(g)

    b = sub.add_parser("batch", help="generate a shot list (md/json/csv)")
    b.add_argument("shotlist")
    _add_common(b)

    c = sub.add_parser("compare", help="race one prompt across models")
    c.add_argument("prompt")
    c.add_argument("--models", help="comma list, e.g. nano,gpt,flux")
    _add_common(c)

    r = sub.add_parser("resume", help="re-run failed/missing items of a run")
    r.add_argument("run_id")
    r.add_argument("--out", help="output dir the run lives under (default ./generated-assets)")
    r.add_argument("--concurrency", type=int)
    r.add_argument("--cap", type=float, help="whole-run spend ceiling in USD (counts prior spend)")

    e = sub.add_parser("estimate", help="estimate cost, no API calls")
    e.add_argument("prompt", nargs="?", default="")
    _add_common(e)

    m = sub.add_parser("models", help="list the model registry")
    m.add_argument("--json", action="store_true")

    return p


def main():
    if sys.version_info < (3, 8):
        die(f"forge needs Python 3.8+, found {sys.version.split()[0]}")
    args = build_parser().parse_args()
    reg = load_registry()
    {"models": cmd_models, "estimate": cmd_estimate, "gen": cmd_gen,
     "batch": cmd_batch, "compare": cmd_compare, "resume": cmd_resume}[args.command](args, reg)


if __name__ == "__main__":
    main()
