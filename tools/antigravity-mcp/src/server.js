#!/usr/bin/env node
/**
 * antigravity-mcp
 *
 * Exposes Google Antigravity's `agy` CLI as an MCP server, so Claude Code can
 * consult Gemini Pro the same way it consults Codex.
 *
 * `agy` consumes MCP servers but does not serve as one, so there is nothing to
 * proxy. This wrapper shells out to `agy --print --output-format json` and
 * reshapes the envelope into an MCP tool result.
 */

import { spawn } from "node:child_process";
import { accessSync, constants } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const DEFAULT_MODEL = "gemini-3.1-pro-high";
const DEFAULT_MODE = "plan";
const DEFAULT_TIMEOUT_MS = 600_000;

/** Locate the agy binary: explicit override, then the installer's target, then PATH. */
function resolveAgyBin() {
  if (process.env.AGY_BIN) return process.env.AGY_BIN;
  const installed = join(homedir(), ".local", "bin", "agy");
  try {
    accessSync(installed, constants.X_OK);
    return installed;
  } catch {
    return "agy";
  }
}

const AGY_BIN = resolveAgyBin();

/**
 * Run agy headlessly and resolve with its parsed JSON envelope.
 *
 * The child's stdio is fully detached from ours: this process's stdin/stdout is
 * the MCP transport, and a single stray byte from the child would corrupt it.
 */
function runAgy(args, { cwd, timeoutMs }) {
  return new Promise((resolve, reject) => {
    const child = spawn(AGY_BIN, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);

    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));

    child.on("error", (err) => {
      clearTimeout(timer);
      if (err.code === "ENOENT") {
        reject(
          new Error(
            `Could not find the agy binary at "${AGY_BIN}". Install it with ` +
              `curl -fsSL https://antigravity.google/cli/install.sh | bash, ` +
              `or set AGY_BIN to its path.`,
          ),
        );
        return;
      }
      reject(err);
    });

    child.on("close", (code) => {
      clearTimeout(timer);

      if (timedOut) {
        reject(
          new Error(
            `agy exceeded the ${Math.round(timeoutMs / 1000)}s timeout and was killed. ` +
              `Raise timeout_ms, or lower --effort, for long jobs.`,
          ),
        );
        return;
      }

      if (code !== 0) {
        reject(new Error(`agy exited with code ${code}.\n${stderr.trim() || stdout.trim()}`));
        return;
      }

      resolve({ stdout, stderr });
    });
  });
}

/**
 * agy emits glog preamble lines ("ERROR: logging before google.Init: ...") on
 * both streams. They are noise, not failures. Pull the JSON envelope out by
 * taking the last line that parses as an object.
 */
function extractEnvelope(stdout) {
  const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].startsWith("{")) continue;
    try {
      return JSON.parse(lines[i]);
    } catch {
      // keep scanning upward
    }
  }
  return null;
}

const server = new McpServer({
  name: "antigravity",
  version: "1.0.0",
});

server.registerTool(
  "ask_gemini",
  {
    title: "Ask Gemini (via Antigravity)",
    description:
      "Send a prompt to Google Antigravity's agent (`agy`) and return its answer. " +
      "Defaults to Gemini 3.1 Pro. Good for second opinions, code review, and " +
      "architecture questions against the current repo. Returns a conversation_id; " +
      "pass it back as conversation_id to continue the same thread. Note that the " +
      "agent reads whatever is in its workspace and sends it to Google, so scope cwd " +
      "to the project you mean.",
    inputSchema: {
      prompt: z.string().min(1).describe("The prompt to send to the Antigravity agent."),
      model: z
        .string()
        .optional()
        .describe(
          `Model id, e.g. gemini-3.1-pro-high (default), gemini-3.1-pro-low, ` +
            `gemini-3.6-flash-medium. Run list_models for the current roster.`,
        ),
      mode: z
        .enum(["plan", "accept-edits"])
        .optional()
        .describe(
          "plan (default) biases the agent toward analysis rather than editing. It is " +
            "NOT a write guard — verified 2026-08-07: in plan mode with permissions " +
            "bypassed the agent still created a file. The real guard is leaving " +
            "skip_permissions off.",
        ),
      effort: z
        .enum(["low", "medium", "high"])
        .optional()
        .describe("Reasoning effort. Omit to use the model's own default."),
      cwd: z
        .string()
        .optional()
        .describe(
          "Working directory the agent reads as its workspace. Defaults to this " +
            "server's cwd, which is normally the current project.",
        ),
      add_dirs: z
        .array(z.string())
        .optional()
        .describe("Extra directories to add to the agent's workspace."),
      conversation_id: z
        .string()
        .optional()
        .describe("Resume a previous conversation by id, to keep context across calls."),
      timeout_ms: z
        .number()
        .int()
        .positive()
        .optional()
        .describe(`Hard timeout in milliseconds. Default ${DEFAULT_TIMEOUT_MS}.`),
      skip_permissions: z
        .boolean()
        .optional()
        .describe(
          "Auto-approve every tool the agent asks for, bypassing the settings.json " +
            "allow-list. Off by default. Only pass true when the user has explicitly " +
            "asked for it for this task.",
        ),
    },
  },
  async ({
    prompt,
    model,
    mode,
    effort,
    cwd,
    add_dirs,
    conversation_id,
    timeout_ms,
    skip_permissions,
  }) => {
    const timeoutMs = timeout_ms ?? DEFAULT_TIMEOUT_MS;
    const workdir = cwd ?? process.cwd();

    const args = [
      "--print",
      prompt,
      "--model",
      model ?? DEFAULT_MODEL,
      "--mode",
      mode ?? DEFAULT_MODE,
      "--output-format",
      "json",
      // Keep agy's own deadline just inside ours so it gets the chance to fail
      // cleanly with an envelope rather than being SIGKILLed mid-write.
      "--print-timeout",
      `${Math.max(1, Math.floor((timeoutMs / 1000) * 0.9))}s`,
      // agy does NOT treat its spawn cwd as the agent's workspace. Without an
      // explicit --add-dir it reports "you did not have an active workspace",
      // fails to read the project, and returns an empty response anyway.
      "--add-dir",
      workdir,
    ];

    if (effort) args.push("--effort", effort);
    if (skip_permissions) args.push("--dangerously-skip-permissions");
    if (conversation_id) args.push("--conversation", conversation_id);
    for (const dir of add_dirs ?? []) args.push("--add-dir", dir);

    let result;
    try {
      result = await runAgy(args, { cwd: workdir, timeoutMs });
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: err.message }],
      };
    }

    const envelope = extractEnvelope(result.stdout);

    if (!envelope) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text:
              "Could not parse a JSON envelope from agy's output.\n\n" +
              `stdout:\n${result.stdout.trim()}\n\nstderr:\n${result.stderr.trim()}`,
          },
        ],
      };
    }

    if (envelope.status && envelope.status !== "SUCCESS") {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `agy returned status ${envelope.status}.\n\n${envelope.response ?? ""}`.trim(),
          },
        ],
      };
    }

    // agy reports status SUCCESS even when every tool call was auto-denied,
    // handing back an empty response and burning the tokens. Surface that as a
    // failure with the CLI's own diagnostic rather than returning silence.
    if (!(envelope.response ?? "").trim()) {
      const diagnostic = [result.stderr, result.stdout]
        .join("\n")
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l && !l.startsWith("{") && !l.startsWith("ERROR: logging before"));

      return {
        isError: true,
        content: [
          {
            type: "text",
            text:
              "agy returned an empty response.\n\n" +
              (diagnostic ? `${diagnostic}\n\n` : "") +
              "This usually means the agent tried to use a tool that headless mode " +
              "cannot prompt for, so it was auto-denied. Add an allow-rule to " +
              "~/.gemini/antigravity-cli/settings.json, or retry this call with " +
              "skip_permissions: true if the user has authorized that.",
          },
        ],
      };
    }

    const usage = envelope.usage ?? {};
    const footer = [
      `conversation_id: ${envelope.conversation_id ?? "unknown"}`,
      `model: ${model ?? DEFAULT_MODEL}`,
      `mode: ${mode ?? DEFAULT_MODE}`,
      envelope.duration_seconds != null ? `${envelope.duration_seconds.toFixed(1)}s` : null,
      usage.total_tokens != null ? `${usage.total_tokens} tokens` : null,
    ]
      .filter(Boolean)
      .join(" | ");

    return {
      content: [
        { type: "text", text: (envelope.response ?? "").trim() },
        { type: "text", text: `\n---\n${footer}` },
      ],
    };
  },
);

server.registerTool(
  "list_models",
  {
    title: "List Antigravity models",
    description:
      "List the model ids currently available to the Antigravity CLI, for use as " +
      "the `model` argument to ask_gemini.",
    inputSchema: {},
  },
  async () => {
    try {
      const { stdout } = await runAgy(["models"], {
        cwd: process.cwd(),
        timeoutMs: 60_000,
      });
      return { content: [{ type: "text", text: stdout.trim() }] };
    } catch (err) {
      return { isError: true, content: [{ type: "text", text: err.message }] };
    }
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
