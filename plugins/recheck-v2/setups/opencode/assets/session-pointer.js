// recheck-v2 pilot setup (E9 lane Q). Writes the harness's own session pointer so a tool
// shell inside the session can find the session record it belongs to.
//
// Measured on opencode 1.18.31: the tool shell receives OPENCODE=1 and OPENCODE_PID=<the
// opencode process id> and no session id of any kind. This plugin runs inside that same
// process, so process.pid is the value the shell reads as $OPENCODE_PID.
//
// Every value written here comes from the harness's own chat.message payload, never from the
// model. The file holds ids only: no prompt text, no credential.
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

const dir = path.join(process.env.TMPDIR || "/tmp", "recheck-v2", "opencode")

export default (async () => {
  return {
    "chat.message": async (input, output) => {
      try {
        fs.mkdirSync(dir, { recursive: true })
        const message = (output && output.message) || {}
        const record = {
          session_id: input && input.sessionID ? input.sessionID : message.sessionID,
          message_id: message.id,
          role: message.role,
          agent: message.agent,
          opencode_pid: process.pid,
          written_at: new Date().toISOString(),
        }
        const tmp = path.join(dir, process.pid + ".json.tmp")
        fs.writeFileSync(tmp, JSON.stringify(record) + "\n", { mode: 0o600 })
        fs.renameSync(tmp, path.join(dir, process.pid + ".json"))
      } catch (e) {
        // A pointer that cannot be written is not fatal: turns.py falls back to the
        // newest session in the store whose directory is the workspace.
      }
    },
  }
})
