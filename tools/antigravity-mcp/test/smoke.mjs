/**
 * End-to-end smoke test: starts the MCP server over stdio, lists its tools, and
 * makes one real (cheap, Flash-tier) round trip through the agy CLI.
 *
 *   node test/smoke.mjs
 *
 * Requires agy to be installed and already authenticated.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const here = dirname(fileURLToPath(import.meta.url));
const serverPath = join(here, "..", "src", "server.js");

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverPath],
  cwd: process.argv[2] ?? process.cwd(),
});

const client = new Client({ name: "smoke", version: "1.0.0" });
await client.connect(transport);

const { tools } = await client.listTools();
console.log("tools:", tools.map((t) => t.name).join(", "));

const res = await client.callTool({
  name: "ask_gemini",
  arguments: {
    prompt: "Reply with exactly: MCP BRIDGE OK",
    model: "gemini-3.6-flash-low",
    timeout_ms: 180_000,
  },
});

console.log("isError:", res.isError ?? false);
for (const c of res.content) console.log(c.text);

await client.close();

if (res.isError) process.exit(1);
