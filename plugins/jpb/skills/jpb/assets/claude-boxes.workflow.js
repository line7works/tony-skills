// Fable + Opus box runner — executed via the Workflow tool.
// TEMPLATE: substitute the backtick-delimited placeholder literal on the
// `const prompt = ` line (the ONLY backticked placeholder in this file)
// with the fully composed prompt (mandate with [TEMPLATE] expanded +
// brief) before invoking. Substitution + escaping rules live in
// box-runners.md — replace the delimited literal including its backticks,
// assert exactly one occurrence, and escape backslashes, backticks, and
// dollar-brace in the prompt first. Never pass the prompt via Workflow
// `args` — verified 2026-08-09: args can arrive as a JSON string, leaving
// args.prompt undefined and the boxes prompt-less.
// Guard: a null/empty result for either box is a FAILED run for that box.
// Parity: the run record's per-agent toolCalls must be 0 for each box.
export const meta = {
  name: 'jpb-claude-boxes',
  description: 'Run the Fable and Opus product boxes with pinned model and effort',
  phases: [{ title: 'Boxes' }],
}
phase('Boxes')
const prompt = `__COMPOSED_PROMPT__`
const [fable, opus] = await parallel([
  () => agent(prompt, { label: 'box:fable', model: 'fable', effort: 'high' }),
  () => agent(prompt, { label: 'box:opus', model: 'opus', effort: 'high' }),
])
return { fable, opus }
