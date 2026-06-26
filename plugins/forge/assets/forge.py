#!/usr/bin/env python3
"""
forge - Claude-driven, model-agnostic AI image generation on Fal.ai.

The deterministic spine behind the /forge skill. Python standard library only:
no pip installs. Talks to Fal's REST queue directly (submit -> poll -> fetch ->
download), writes an auditable run manifest, and guards spend with a cost cap.

M1 commands: gen, estimate, models.
Later milestones add: batch, compare, edit, finish, export, style, resume, init.

Usage:
    python3 forge.py models
    python3 forge.py estimate "a trophy" --model gpt --size 1024 --quality high
    python3 forge.py gen "a trophy on an orange podium" --model nano --size 1024
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

QUEUE_HOST = "https://queue.fal.run"   # verified host + "Authorization: Key <FAL_KEY>" auth
HTTP_TIMEOUT = 180
POLL_TIMEOUT = 240
SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR / "models.json"


# ---------- output helpers ----------

def die(msg, code=1):
    print(f"forge: error: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"forge: {msg}", file=sys.stderr)


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
        return (int(m.group(1)), int(m.group(2)))
    if s.isdigit():
        return (int(s), int(s))
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
        if dims and max(dims) >= 4096 and (q + "@4k") in price:
            return float(price[q + "@4k"])
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
    waited, interval = 0, 2
    while True:
        code, raw = _request(status_url, "GET", None, auth(key), timeout=60)
        if code in (200, 202):                 # Fal returns 202 while IN_QUEUE / IN_PROGRESS
            status = json.loads(raw).get("status")
            if status == "COMPLETED":
                return
            if status in ("FAILED", "ERROR"):
                raise RuntimeError(f"Fal job failed: {raw[:300].decode('utf-8', 'replace')}")
            interval = 2
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
    """Minimal brand-profile read (full auto-detect + `forge init` land in M3)."""
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
    dims = parse_dims(size)
    per = estimate_per_image(cfg, dims, args.quality)
    total = per * args.num
    if args.json:
        print(json.dumps({
            "model": cfg["alias"], "fal_id": cfg["id"], "size": size,
            "quality": args.quality, "num_images": args.num,
            "per_image_usd": round(per, 4), "estimated_total_usd": round(total, 4),
            "basis": "conservative upper bound",
        }, indent=2))
    else:
        print(f"~${total:.3f} for {args.num} image(s) on '{cfg['alias']}' "
              f"(~${per:.3f} each, conservative upper bound)")


def cmd_gen(args, reg):
    brand = load_brand_profile(args.brand)
    cfg = resolve_model(args.model or brand.get("default_model"), reg)
    size = args.size or brand.get("default_size")
    dims = parse_dims(size)
    per = estimate_per_image(cfg, dims, args.quality)
    total = per * args.num

    if args.cap is not None and total > args.cap:
        die(f"estimate ${total:.3f} exceeds --cap ${args.cap:.2f}. "
            f"Raise the cap or lower --num/--size/--quality.")

    inp = build_input(cfg, args.prompt, dims, args.quality, args.num, args.seed, args.negative)

    if args.dry_run:
        plan = {
            "command": "gen", "dry_run": True, "model": cfg["alias"], "fal_id": cfg["id"],
            "size": size, "quality": args.quality, "num_images": args.num,
            "estimated_total_usd": round(total, 4), "input": inp,
        }
        print(json.dumps(plan, indent=2) if args.json
              else f"[dry run] '{cfg['alias']}' x{args.num} ~${total:.3f}, no spend.\n"
                   f"input: {json.dumps(inp)}")
        return

    key = os.environ.get("FAL_KEY")
    if not key:
        die("FAL_KEY is not set. Get a key at fal.ai and `export FAL_KEY=...` in "
            "your shell (see IMPLEMENTATION.md section 10).")

    out_root = Path(args.out) if args.out else (Path.cwd() / "generated-assets")
    run_id = new_run_id(args.prompt)
    run_dir = out_root / run_id
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ensure_gitignore(Path.cwd())
    manifest_path = run_dir / "manifest.json"

    item = {
        "id": "img-01", "status": "pending", "prompt": args.prompt,
        "model": cfg["alias"], "fal_id": cfg["id"], "size": size,
        "quality": args.quality, "seed": args.seed, "num_images": args.num,
        "request_id": None, "submitted_at": None, "completed_at": None,
        "attempts": 0, "cost_usd": round(total, 4), "cost_basis": "estimate",
        "outputs": [], "error": None,
    }
    manifest = {
        "schema_version": 1, "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "command": "gen", "cap_usd": args.cap, "spent_usd": 0.0, "items": [item],
    }
    write_atomic(manifest_path, manifest)

    try:
        item["attempts"] = 1
        sub = submit_job(cfg["id"], inp, key)
        item["request_id"] = sub.get("request_id")
        item["status"] = "submitted"
        item["submitted_at"] = datetime.now().isoformat(timespec="seconds")
        write_atomic(manifest_path, manifest)

        poll_job(sub["status_url"], key)
        result = fetch_result(sub["response_url"], key)
        images = result.get("images", [])
        if not images:
            raise RuntimeError("Fal returned no images")
        for i, img in enumerate(images, 1):
            dest = raw_dir / f"img-{i:02d}.png"
            download(img["url"], dest)
            item["outputs"].append(str(dest.relative_to(run_dir)))
        item["status"] = "completed"
        item["completed_at"] = datetime.now().isoformat(timespec="seconds")
        manifest["spent_usd"] = round(total, 4)
        write_atomic(manifest_path, manifest)
    except Exception as e:
        item["status"] = "failed"
        item["error"] = str(e)
        write_atomic(manifest_path, manifest)
        die(f"generation failed: {e}\nmanifest: {manifest_path}")

    out = {
        "run_id": run_id, "model": cfg["alias"],
        "outputs": [str(run_dir / o) for o in item["outputs"]],
        "estimated_cost_usd": round(total, 4), "manifest": str(manifest_path),
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"done. {len(item['outputs'])} image(s) on '{cfg['alias']}', ~${total:.3f}")
        for o in out["outputs"]:
            print(f"  {o}")
        print(f"manifest: {manifest_path}")


# ---------- arg parsing ----------

def _add_common(sp):
    sp.add_argument("--model", help="model alias (nano, nano-pro, gpt, flux)")
    sp.add_argument("--size", help="WxH, a number, or a preset (1k/2k/4k)")
    sp.add_argument("--quality", choices=["auto", "low", "medium", "high"],
                    help="for models priced by quality (gpt)")
    sp.add_argument("-n", "--num", type=int, default=1, help="images per prompt")
    sp.add_argument("--seed", type=int, help="fixed seed (models that support it)")
    sp.add_argument("--negative", help="negative prompt (models that support it)")
    sp.add_argument("--brand", help="path to a brand profile (.forge/brand.json)")
    sp.add_argument("--cap", type=float, help="spend ceiling in USD")
    sp.add_argument("--out", help="output dir (default ./generated-assets)")
    sp.add_argument("--json", action="store_true", help="machine-readable output")


def build_parser():
    p = argparse.ArgumentParser(prog="forge", description="Claude-driven image generation on Fal.ai.")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("gen", help="generate images from a prompt")
    g.add_argument("prompt")
    g.add_argument("--dry-run", action="store_true", help="plan + estimate only, no spend")
    _add_common(g)

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
    {"models": cmd_models, "estimate": cmd_estimate, "gen": cmd_gen}[args.command](args, reg)


if __name__ == "__main__":
    main()
