// recheck-v2 pilot setup (E9 lane Q). Writes the harness's own session pointer so a tool
// shell inside the session can find the session record it belongs to, and records the two
// facts about the harness process that no session-store column carries: which CLI command
// started it (ruling E9-33: `opencode run` is headless, the TUI interactive) and the process
// id the tool shell reads as $OPENCODE_PID.
//
// Measured on opencode 1.18.31: the tool shell receives OPENCODE=1 and OPENCODE_PID=<the
// opencode process id> and no session id of any kind. This plugin runs inside that same
// process, so process.pid is the value the shell reads as $OPENCODE_PID and process.argv is
// that process's own argv.
//
// Every value written here comes from the harness's own chat.message payload or the harness's
// own process, never from the model. The file holds ids and one allowlisted command word: no
// prompt text, no path, no credential. A first argument that is not one of the harness's own
// subcommands is written as "other" rather than copied, so a positional prompt or project
// path can never reach this file.
import fs from "node:fs"
import path from "node:path"

const dir = path.join(process.env.TMPDIR || "/tmp", "recheck-v2", "opencode")

// The subcommands `opencode --help` lists on 1.18.31, plus the bare TUI launch.
const COMMANDS = [
  "run", "tui", "serve", "auth", "agent", "upgrade", "models", "providers",
  "debug", "mcp", "plugin", "skill", "session", "export", "stats", "github",
]

function cliCommand() {
  try {
    // argv[0] is the runtime, argv[1] the binary; the first later token that is not a flag is
    // the subcommand. Only an allowlisted word is written down.
    const rest = (process.argv || []).slice(2)
    for (const token of rest) {
      if (typeof token !== "string" || token.startsWith("-")) continue
      return COMMANDS.indexOf(token) >= 0 ? token : "other"
    }
    return "tui"
  } catch (e) {
    return "unknown"
  }
}

export default (async () => {
  return {
    "chat.message": async (input, output) => {
      try {
        fs.mkdirSync(dir, { recursive: true })
        const message = (output && output.message) || {}
        const command = cliCommand()
        const record = {
          session_id: input && input.sessionID ? input.sessionID : message.sessionID,
          message_id: message.id,
          role: message.role,
          agent: message.agent,
          opencode_pid: process.pid,
          cli_command: command,
          // Ruling E9-33: the interaction mode is a harness fact, not the executor's word.
          mode: command === "run" ? "headless" : command === "tui" ? "interactive" : "unknown",
          written_at: new Date().toISOString(),
        }
        const tmp = path.join(dir, process.pid + ".json.tmp")
        fs.writeFileSync(tmp, JSON.stringify(record) + "\n", { mode: 0o600 })
        fs.renameSync(tmp, path.join(dir, process.pid + ".json"))
      } catch (e) {
        // A pointer that cannot be written is not worked around: turns.py, invocation.py and
        // verifier.py all stop with exit 3 naming this file (ruling E9-32). Nothing here
        // falls back to another session.
      }
    },
  }
})
