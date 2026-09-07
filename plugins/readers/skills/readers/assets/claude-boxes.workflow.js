// readers — the Claude lane's Workflow script, executed via the Workflow tool.
// Copied from jpb's assets/claude-boxes.workflow.js (the committed pattern) and
// reduced to one reader. TEMPLATE: `readers compose` fills the two placeholders,
// never a hand: the backtick-delimited literal on the `const prompt = ` line
// receives the composed prompt (escaped: backslashes, backticks, dollar-brace,
// in that order), and the options placeholder receives the agent options resolved from
// the request and the roster (label; the row's harness model name unless the
// row inherits the session; the pinned effort; worktree isolation when asked).
// Never pass the prompt via Workflow `args` — verified 2026-08-09: args can
// arrive as a JSON string, leaving the reader prompt-less.
// Guard: a null/empty result is a FAILED read (readers record maps it).
// Parity: under starved and packet-only the run record's tool_uses count (one
// reader per script) must be 0; the body passes it to `readers record --tool-calls`.
// The Workflow tool reads this script only from the session's working directory,
// so compose writes the copy it hands over under <cwd>/.readers/ and record removes it.
export const meta = {
  name: 'readers-claude-lane',
  description: 'One cold read by a fresh Claude reader with the model and effort the roster resolved',
  phases: [{ title: 'Read' }],
}
phase('Read')
const prompt = `__COMPOSED_PROMPT__`
const capture = await agent(prompt, __AGENT_OPTS__)
return { capture }
