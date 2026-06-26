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
import base64
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


# ---------- references / local-image upload ----------

MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}
REF_EXTS = (".png", ".jpg", ".jpeg", ".webp")
MAX_INLINE_MB = 8        # ceiling for inline base64; resize larger files first


def _data_uri(path):
    """Encode a local image as an inline base64 data URI (Fal accepts these in
    image_url / image_urls). Raises RuntimeError so worker threads can fail the
    item instead of killing the whole run."""
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"image not found: {path}")
    mime = MIME_BY_EXT.get(p.suffix.lower())
    if not mime:
        raise RuntimeError(f"unsupported image type '{p.suffix}' ({path}); use png/jpg/webp")
    mb = p.stat().st_size / (1024 * 1024)
    if mb > MAX_INLINE_MB:
        raise RuntimeError(f"{path} is {mb:.0f}MB; too large to send inline "
                           f"(limit {MAX_INLINE_MB}MB). Resize it first.")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def _load_ref_paths(folder):
    d = Path(folder)
    if not d.is_dir():
        die(f"refs folder not found: {folder}")
    paths = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in REF_EXTS)
    if not paths:
        die(f"no images ({', '.join(REF_EXTS)}) found in {folder}")
    return paths


def build_op_input(cfg, op, image_uris, prompt, dims, quality, num, seed):
    """Assemble the Fal input body for an edit/style op. Routes the reference
    images to the endpoint's image field (single image_url vs an image_urls array)
    and applies size params only where the op endpoint honors them."""
    if not image_uris:
        raise RuntimeError("edit/style needs at least one reference image")
    field = cfg.get(op + "_image_field", "image_urls")
    inp = {"prompt": prompt, "num_images": num, "output_format": "png"}
    if field == "image_url":
        inp["image_url"] = image_uris[0]
    else:
        inp["image_urls"] = image_uris
    osize = cfg.get("op_size_style", cfg.get("size_style"))
    if osize == "aspect_resolution":
        inp["resolution"] = res_bucket(max(dims)) if dims else "1K"
    elif osize == "image_size":
        if cfg.get("supports_quality") and quality:
            inp["quality"] = quality
        if dims:
            inp["image_size"] = {"width": dims[0], "height": dims[1]}
    if cfg.get("supports_seed") and seed is not None:
        inp["seed"] = seed
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


def process_item(item, inp, run_dir, key, persist):
    """Submit -> poll -> download one item, with retry/backoff. Never raises.
    Submits to item['fal_id'] (the gen, edit, or style endpoint)."""
    delay = 2
    for attempt in range(1, MAX_ATTEMPTS + 1):
        item["attempts"] = attempt
        try:
            sub = submit_job(item["fal_id"], inp, key)
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


def run_batch(shots, defaults, reg, run_dir, command, cap, concurrency, key, brand, op="gen"):
    """Core engine for gen/batch/compare/finish/edit/style. Concurrent, cost-capped,
    atomic manifest. op selects the endpoint family ('gen' | 'edit' | 'style')."""
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
        item["op"] = op
        if op == "gen":
            item["fal_id"] = cfg["id"]
        else:
            endpoint = cfg.get(op)
            if not endpoint:                       # fail loud, never mis-route to text-to-image
                die(f"model '{cfg['alias']}' has no {op} endpoint")
            item["fal_id"] = endpoint
        if shot.get("sources"):
            item["sources"] = shot["sources"]
        manifest_items.append(item)
        jobs.append((item, cfg, dims, quality, seed, negative, per, shot.get("images")))

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
        item, cfg, dims, quality, seed, negative, per, images = job
        try:
            if op == "gen":                        # build first so a build failure never holds a reservation
                inp = build_input(cfg, item["prompt"], dims, quality, item["num_images"],
                                  seed, negative)
            else:
                inp = build_op_input(cfg, op, images, item["prompt"], dims, quality,
                                     item["num_images"], seed)
            if not reserve(per):
                item["status"], item["error"] = "skipped", "cap reached"
                persist()
                return
            process_item(item, inp, run_dir, key, persist)
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


def cmd_edit(args, reg):
    brand = load_brand_profile(args.brand)
    cfg = resolve_model(args.model or "nano", reg)
    if not cfg.get("edit"):
        die(f"model '{cfg['alias']}' has no edit endpoint; try --model nano, gpt, or flux")
    if not Path(args.image).is_file():
        die(f"image not found: {args.image}")
    size = args.size or brand.get("default_size")
    dims = parse_dims(size)
    per = estimate_per_image(cfg, dims, args.quality) * args.num
    if args.cap is not None and per > args.cap:
        die(f"estimate ${per:.3f} exceeds --cap ${args.cap:.2f}. Raise the cap or lower --num.")
    if args.dry_run:
        msg = (f"[dry run] edit '{Path(args.image).name}' on '{cfg['alias']}' x{args.num} "
               f"~${per:.3f}, no spend.")
        print(json.dumps({"command": "edit", "dry_run": True, "model": cfg["alias"],
                          "edit_id": cfg["edit"], "image": args.image,
                          "instruction": args.instruction,
                          "estimated_total_usd": round(per, 4)}, indent=2) if args.json else msg)
        return
    try:
        uri = _data_uri(args.image)
    except RuntimeError as e:
        die(str(e))
    key = require_key()
    shots = [{"id": "edit-01", "prompt": args.instruction, "model": cfg["alias"], "num": args.num,
              "images": [uri], "sources": [str(Path(args.image).resolve())]}]
    defaults = {"model": cfg["alias"], "size": size, "quality": args.quality,
                "seed": args.seed, "negative": None}
    run_dir = _out_root(args) / new_run_id("edit-" + slugify(args.instruction, 12))
    manifest, mp = run_batch(shots, defaults, reg, run_dir, "edit", args.cap, 1, key, brand, op="edit")
    sheet = write_contact_sheet(run_dir, manifest)
    if args.json:
        it = manifest["items"][0]
        print(json.dumps({"run_id": manifest["run_id"], "status": it["status"],
                          "outputs": [str(run_dir / o) for o in it["outputs"]],
                          "spent_usd": manifest["spent_usd"], "manifest": str(mp),
                          "contact_sheet": str(sheet)}, indent=2))
    else:
        _summary(manifest, sheet)


def cmd_style(args, reg):
    brand = load_brand_profile(args.brand)
    cfg = resolve_model(args.model or "nano", reg)
    if not cfg.get("style"):
        die(f"model '{cfg['alias']}' has no style/multi-ref endpoint; use --model nano or gpt "
            f"(flux style needs the pro Kontext endpoint, not wired in v1)")
    refs = args.refs or brand.get("refs")
    if not refs:
        die("style needs --refs <folder> (or a 'refs' path in the brand profile)")
    paths = _load_ref_paths(refs)
    maxr = cfg.get("max_refs", 8)
    if len(paths) > maxr:
        warn(f"{len(paths)} refs found; '{cfg['alias']}' takes {maxr}, using the first {maxr}")
        paths = paths[:maxr]
    size = args.size or brand.get("default_size")
    dims = parse_dims(size)
    per = estimate_per_image(cfg, dims, args.quality) * args.num
    if args.cap is not None and per > args.cap:
        die(f"estimate ${per:.3f} exceeds --cap ${args.cap:.2f}. Raise the cap or lower --num.")
    if args.dry_run:
        msg = (f"[dry run] style on '{cfg['alias']}' with {len(paths)} ref(s) x{args.num} "
               f"~${per:.3f}, no spend.")
        print(json.dumps({"command": "style", "dry_run": True, "model": cfg["alias"],
                          "style_id": cfg["style"], "refs": [str(p) for p in paths],
                          "estimated_total_usd": round(per, 4)}, indent=2) if args.json else msg)
        return
    try:
        uris = [_data_uri(p) for p in paths]
    except RuntimeError as e:
        die(str(e))
    key = require_key()
    shots = [{"id": "style-01", "prompt": args.prompt, "model": cfg["alias"], "num": args.num,
              "images": uris, "sources": [str(p.resolve()) for p in paths]}]
    defaults = {"model": cfg["alias"], "size": size, "quality": args.quality,
                "seed": args.seed, "negative": None}
    run_dir = _out_root(args) / new_run_id("style-" + slugify(args.prompt, 12))
    manifest, mp = run_batch(shots, defaults, reg, run_dir, "style", args.cap, 1, key, brand, op="style")
    sheet = write_contact_sheet(run_dir, manifest)
    if args.json:
        it = manifest["items"][0]
        print(json.dumps({"run_id": manifest["run_id"], "status": it["status"],
                          "outputs": [str(run_dir / o) for o in it["outputs"]],
                          "spent_usd": manifest["spent_usd"], "manifest": str(mp),
                          "contact_sheet": str(sheet)}, indent=2))
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
        op = it.get("op", "gen")
        it.setdefault("fal_id", cfg["id"])         # heal pre-M4 manifests with no endpoint
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
        try:
            if op == "gen":
                inp = build_input(cfg, it["prompt"], dims, it.get("quality"),
                                  it.get("num_images", 1), it.get("seed"), it.get("negative"))
            else:
                images = [_data_uri(s) for s in (it.get("sources") or [])]
                inp = build_op_input(cfg, op, images, it["prompt"], dims, it.get("quality"),
                                     it.get("num_images", 1), it.get("seed"))
        except Exception as e:
            it["status"], it["error"] = "failed", f"resume could not rebuild input: {e}"
            persist()
            return
        process_item(it, inp, run_dir, key, persist)

    with ThreadPoolExecutor(max_workers=args.concurrency or DEFAULT_CONCURRENCY) as ex:
        list(ex.map(worker, todo))
    persist()
    sheet = write_contact_sheet(run_dir, manifest)
    _summary(manifest, sheet)


def cmd_finish(args, reg):
    """Re-render chosen keepers from a prior run at finish quality into a new run."""
    brand = load_brand_profile(args.brand)
    src_dir = _out_root(args) / args.run_id
    mpath = src_dir / "manifest.json"
    if not mpath.exists():
        die(f"no manifest at {mpath} (check the run id, and run from the project dir)")
    src = json.loads(mpath.read_text())
    by_id = {it["id"]: it for it in src["items"]}
    if args.ids:
        missing = [i for i in args.ids if i not in by_id]
        if missing:
            die(f"id(s) not in run {args.run_id}: {', '.join(missing)}. Have: {', '.join(by_id)}")
        not_done = [i for i in args.ids if by_id[i]["status"] != "completed"]
        if not_done:
            die(f"can only finish completed keepers; these did not complete: {', '.join(not_done)}")
        picks = [by_id[i] for i in args.ids]
    else:
        picks = [it for it in src["items"] if it["status"] == "completed"]
    if not picks:
        die("no keepers to finish (nothing completed, or no ids matched)")
    model = args.model or brand.get("finish_model") or "gpt"
    cfg = resolve_model(model, reg)                      # validate the alias up front
    quality = args.quality or ("high" if cfg.get("supports_quality") else None)
    size = args.size or brand.get("default_size") or "2048"
    shots = [{"id": it["id"], "prompt": it["prompt"], "model": model} for it in picks]
    defaults = {"model": model, "size": size, "quality": quality, "seed": None, "negative": None}
    total, rows = _estimate_shots(shots, defaults, reg, brand)
    if args.dry_run:
        if args.json:
            print(json.dumps({"command": "finish", "dry_run": True, "source_run": args.run_id,
                              "model": model, "quality": quality, "size": size,
                              "ids": [s["id"] for s in shots],
                              "estimated_total_usd": round(total, 4)}, indent=2))
        else:
            print(f"[dry run] finish {len(shots)} keeper(s) on '{model}'"
                  f"{(' ' + quality) if quality else ''} @ {size}, ~${total:.3f}:")
            for sid, _m, per in rows:
                print(f"  [{sid}] ~${per:.3f}")
        return
    if args.cap is not None and total > args.cap:
        warn(f"finish estimate ~${total:.3f} exceeds cap ${args.cap:.2f}; "
             f"running as many as fit and skipping the rest.")
    key = require_key()
    run_dir = _out_root(args) / new_run_id("finish")
    manifest, mp = run_batch(shots, defaults, reg, run_dir, "finish", args.cap,
                             args.concurrency or DEFAULT_CONCURRENCY, key, brand)
    manifest["source_run"] = args.run_id
    write_atomic(mp, manifest)
    sheet = write_contact_sheet(run_dir, manifest)
    if args.json:
        print(json.dumps({"run_id": manifest["run_id"], "source_run": args.run_id,
                          "spent_usd": manifest["spent_usd"], "manifest": str(mp),
                          "contact_sheet": str(sheet), "items": manifest["items"]}, indent=2))
    else:
        _summary(manifest, sheet)


# ---------- brand profile scaffolding (forge init) ----------

NEUTRAL_TOL = 24
BRAND_HINT_GLOBS = ("theme.css", "globals.css", "colors.css", "tailwind.config.*")


def _is_neutral(hexstr):
    """True for greys, near-black, and near-white, so brand-color detection skips them."""
    r, g, b = (int(hexstr[i:i + 2], 16) for i in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    return (mx - mn) < NEUTRAL_TOL or mx < NEUTRAL_TOL or mn > (255 - NEUTRAL_TOL)


def _expand_hex(h):
    """Normalize #rgb / #rrggbb / #rrggbbaa to a 6-digit #rrggbb (alpha dropped)."""
    h = h.lower()
    if len(h) == 4:                                  # #rgb -> #rrggbb
        return "#" + "".join(c * 2 for c in h[1:])
    return "#" + h[1:7]                              # 6- or 8-digit -> first 6


def _scan_palette(root):
    """Best-effort brand colors: most-frequent non-neutral hex codes in the project's
    design/style files (DESIGN.md, theme.css, globals.css, tailwind config)."""
    files = []
    for rel in ("DESIGN.md", "README.md", "brand.md", "STYLE.md"):
        p = root / rel
        if p.is_file():
            files.append(p)
    for pat in BRAND_HINT_GLOBS:
        for depth in ("", "*/", "*/*/", "*/*/*/"):
            if len(files) >= 16:                     # bound the walk on big trees
                break
            files += [p for p in root.glob(depth + pat) if p.is_file()]
    text = ""
    for p in files[:16]:
        try:
            text += "\n" + p.read_text(errors="ignore")[:20000]
        except Exception:
            pass
    counts = {}
    for raw in re.findall(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text):
        h = _expand_hex(raw)
        if not _is_neutral(h):
            counts[h] = counts.get(h, 0) + 1
    return [h for h, _ in sorted(counts.items(), key=lambda kv: -kv[1])][:3]


def _detect_brand(root, default_model):
    name = root.resolve().name or "project"
    return {
        "name": name[:1].upper() + name[1:],
        "palette": _scan_palette(root) or ["#000000"],
        "style": "flat modern vector, clean, friendly, no baked-in text",
        "avoid": "photorealism, stock-photo look, watermarks, gibberish text",
        "refs": "./brand",
        "default_model": default_model,
        "default_size": "1024x1024",
    }


def cmd_init(args, reg):
    target = Path(args.dir).resolve() if args.dir else Path.cwd()
    if not target.is_dir():
        die(f"not a directory: {target}")
    forge_dir = target / ".forge"
    dest = forge_dir / "brand.json"
    if forge_dir.exists() and not forge_dir.is_dir():
        die(f"{forge_dir} exists but is not a directory; move it aside first.")
    if dest.exists():
        if dest.is_dir():
            die(f"{dest} is a directory, not a file; remove it first.")
        if not args.force:
            die(f"{dest} already exists. Pass --force to overwrite.")
    profile = _detect_brand(target, reg.get("default_model", "nano"))
    try:
        forge_dir.mkdir(parents=True, exist_ok=True)
        write_atomic(dest, profile)
    except OSError as e:
        die(f"cannot write {dest}: {e}")
    print(f"wrote {dest}")
    if profile["palette"] != ["#000000"]:
        print(f"  detected palette: {', '.join(profile['palette'])}")
    else:
        print("  no brand colors auto-detected; set 'palette' by hand")
    print("  edit name/style/avoid to taste; forge auto-loads this for runs in this project.")


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

    ed = sub.add_parser("edit", help="edit an existing image with a text instruction")
    ed.add_argument("image", help="path to the image to edit")
    ed.add_argument("instruction", help="what to change, in natural language")
    _add_common(ed)

    st = sub.add_parser("style", help="generate conditioned on a folder of reference images")
    st.add_argument("prompt")
    _add_common(st)

    r = sub.add_parser("resume", help="re-run failed/missing items of a run")
    r.add_argument("run_id")
    r.add_argument("--out", help="output dir the run lives under (default ./generated-assets)")
    r.add_argument("--concurrency", type=int)
    r.add_argument("--cap", type=float, help="whole-run spend ceiling in USD (counts prior spend)")

    f = sub.add_parser("finish", help="re-render keepers from a run at finish quality")
    f.add_argument("run_id")
    f.add_argument("ids", nargs="*", help="keeper ids to finish (default: all completed)")
    _add_common(f)

    i = sub.add_parser("init", help="scaffold a .forge/brand.json brand profile")
    i.add_argument("dir", nargs="?", help="project dir to scaffold (default: current)")
    i.add_argument("--force", action="store_true", help="overwrite an existing profile")

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
     "batch": cmd_batch, "compare": cmd_compare, "resume": cmd_resume,
     "finish": cmd_finish, "init": cmd_init,
     "edit": cmd_edit, "style": cmd_style}[args.command](args, reg)


if __name__ == "__main__":
    main()
