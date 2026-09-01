#!/usr/bin/env bash
# Fetch the real billed cost of an OpenRouter call from its .raw response.
#
# Usage: openrouter-cost.sh <response.raw>
# Prints: <generation-id> <prompt_tokens> <completion_tokens> <usd-cost>
# Requires OPENROUTER_API_KEY. Exit 1 with a reason on any failure.
set -u
RAW="$1"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not set}"

GEN_ID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('id',''))" "$RAW")
[ -n "$GEN_ID" ] || { echo "FAILED: no generation id in $RAW"; exit 1; }

# The generation record is written asynchronously; retry briefly.
for i in 1 2 3 4 5; do
  if curl -s --max-time 30 "https://openrouter.ai/api/v1/generation?id=$GEN_ID" \
      -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    | python3 -c '
import json, sys
gen_id = sys.argv[1]
try:
    d = json.load(sys.stdin).get("data") or {}
except Exception:
    sys.exit(1)
cost = d.get("total_cost")
if not d or cost is None:
    sys.exit(1)
print(gen_id, d.get("tokens_prompt"), d.get("tokens_completion"), cost)
' "$GEN_ID"; then
    exit 0
  fi
  sleep 2
done
echo "FAILED: generation record for $GEN_ID not available"
exit 1
