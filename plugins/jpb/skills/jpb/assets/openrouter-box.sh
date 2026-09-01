#!/usr/bin/env bash
# Run one OpenRouter box with the mandatory failure guard.
#
# Usage: openrouter-box.sh <model-id> <prompt-file> <output-file>
# Requires OPENROUTER_API_KEY in the environment.
#
# Guard (all four or FAILED): HTTP 200, no top-level "error" key,
# choices[0].finish_reason == "stop", non-empty choices[0].message.content.
# Exit 0 = PASSED (box content written to output-file).
# Exit 1 = FAILED (reason on stdout, raw response saved to <output-file>.raw).
set -u
MODEL="$1"; PROMPT_FILE="$2"; OUT="$3"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not set}"

BODY=$(python3 - "$MODEL" "$PROMPT_FILE" <<'EOF'
import json, sys
print(json.dumps({
    "model": sys.argv[1],
    "messages": [{"role": "user", "content": open(sys.argv[2]).read()}],
    "max_tokens": 8000,
}))
EOF
)

HTTP=$(curl -s -o "$OUT.raw" -w '%{http_code}' \
  https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BODY")

python3 - "$HTTP" "$OUT" <<'EOF'
import json, sys
http, out = sys.argv[1], sys.argv[2]
if http != "200":
    print(f"FAILED: HTTP {http}"); sys.exit(1)
try:
    r = json.load(open(out + ".raw"))
except Exception as e:
    print(f"FAILED: unparseable response ({e})"); sys.exit(1)
if "error" in r:
    print(f"FAILED: top-level error: {r['error']}"); sys.exit(1)
choice = (r.get("choices") or [{}])[0]
if choice.get("finish_reason") != "stop":
    print(f"FAILED: finish_reason={choice.get('finish_reason')!r}"); sys.exit(1)
content = (choice.get("message") or {}).get("content")
if not content or not content.strip():
    print("FAILED: empty content"); sys.exit(1)
open(out, "w").write(content)
print("PASSED")
EOF
