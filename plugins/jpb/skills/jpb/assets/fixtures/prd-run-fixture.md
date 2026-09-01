---
status: open
run_date: 2026-08-11
roster:
  - GPT — gpt-5.6-sol — filled
  - Fable — claude-fable-5 — filled
  - Gemini — gemini-3.1-pro-high — DROPPED: fixture drop
parity:
  - GPT — web_search: disabled
  - Fable — toolCalls: 0
cost:
  - GPT — $0 — subscription
  - Fable — $0 — subscription
  - OpenRouter total — $0.032051
---

# JPB run — prd renderer fixture

Renderer regression fixture: a PRD-length brief carrying its own H2 headings
and fenced code blocks. Step 11 contract: this must render as ONE Brief
panel and ONE Brief tab, never one panel per brief H2.

## The scrubbed brief

The product is a multiplayer thing. This brief deliberately has internal
structure that must NOT become page sections.

## 1. Vision

Something visionary about the product.

## 2. Platforms

Desktop and mobile.

```js
// a fenced block with fake headings and template-literal hazards
## not a heading
## Reconciliation
## GPT box — gpt-5.6-sol
const x = `${dangerous}`
```

## 3. Economy and pricing

Free tier, paid tier. Inline `code with a backtick` too.

### 3.1 A nested heading

Deeper structure inside the brief.

## GPT box — gpt-5.6-sol

## Front

Product name candidates.

## Back

How it works.

## Side

Specs.

## Bottom

Assumptions.

## Fable box — claude-fable-5

## Front

Names.

## Back

Mechanism.

## Side

Specs.

## Bottom

Assumptions.

## Dropped — Gemini (gemini-3.1-pro-high)

Fixture drop reason.

## Judge K tally

### Clusters

#### Cluster one

Both boxes agree on the thing.

## Judge G tally

### Clusters

#### Cluster one

Same agreement.

## Reconciliation

| Cluster | K | G | Support |
|---|---|---|---|
| One | yes | yes | 2/2 |

## Debate card

1. A fixture question?
