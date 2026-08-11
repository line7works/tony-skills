import test from "node:test";
import assert from "node:assert/strict";

// Importing the server module must be side-effect free (no MCP transport on
// this process's stdio) — the import itself is part of what this asserts.
import { composeArgs, extractEnvelope, resolveAgyBin, runAgy } from "../src/server.js";

test("server module exports its internals and imports without side effects", () => {
  assert.equal(typeof runAgy, "function");
  assert.equal(typeof resolveAgyBin, "function");
  assert.deepEqual(extractEnvelope('noise line\n{"status":"SUCCESS","response":"hi"}'), {
    status: "SUCCESS",
    response: "hi",
  });
  const { args } = composeArgs({ prompt: "hello", cwd: "/tmp/w" });
  assert.ok(args.includes("--add-dir") && args.includes("/tmp/w"));
  assert.equal(resolveAgyBin({ AGY_BIN: "/tmp/fake-agy" }), "/tmp/fake-agy");
});
