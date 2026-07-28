import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { AddressInfo } from "node:net";
import { google } from "googleapis";

import {
  ConfigError,
  SCOPES,
  StoredAccount,
  assertValidAlias,
  listAccounts,
  loadAccount,
  loadOAuthClientConfig,
  removeAccount,
  saveAccount,
} from "./store.js";

const HTML_OK = `<!doctype html><meta charset="utf-8">
<title>Authorized</title>
<body style="font:16px system-ui;padding:3rem;max-width:32rem">
<h2>Account authorized</h2>
<p>You can close this tab and go back to the terminal.</p>`;

const HTML_FAIL = (msg: string) => `<!doctype html><meta charset="utf-8">
<title>Authorization failed</title>
<body style="font:16px system-ui;padding:3rem;max-width:32rem">
<h2>Authorization failed</h2><p>${msg}</p>`;

/**
 * Runs the OAuth dance against a loopback redirect. Google's "Desktop app"
 * client type permits 127.0.0.1 on an arbitrary port, so nothing has to be
 * registered ahead of time.
 */
async function authorize(alias: string): Promise<StoredAccount> {
  assertValidAlias(alias);
  const { client_id, client_secret } = await loadOAuthClientConfig();

  // Preserve an existing refresh token: Google only re-issues one when it
  // feels like it, and losing it silently would break the account later.
  const existing = await loadAccount(alias).catch(() => null);

  const { server, port } = await new Promise<{ server: ReturnType<typeof createServer>; port: number }>(
    (resolve, reject) => {
      const s = createServer();
      s.on("error", reject);
      s.listen(0, "127.0.0.1", () => resolve({ server: s, port: (s.address() as AddressInfo).port }));
    },
  );

  const redirectUri = `http://127.0.0.1:${port}`;
  const oauth2 = new google.auth.OAuth2(client_id, client_secret, redirectUri);

  const url = oauth2.generateAuthUrl({
    access_type: "offline",
    prompt: "consent", // forces a refresh_token even on re-authorization
    scope: SCOPES,
  });

  const codePromise = new Promise<string>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Timed out after 5 minutes waiting for authorization.")), 300_000);
    server.on("request", (req, res) => {
      const requested = new URL(req.url ?? "/", redirectUri);
      if (requested.pathname !== "/") {
        res.writeHead(404).end();
        return;
      }
      const code = requested.searchParams.get("code");
      const error = requested.searchParams.get("error");
      if (code) {
        res.writeHead(200, { "content-type": "text/html" }).end(HTML_OK);
        clearTimeout(timer);
        resolve(code);
      } else {
        const msg = error ?? "No authorization code was returned.";
        res.writeHead(400, { "content-type": "text/html" }).end(HTML_FAIL(msg));
        clearTimeout(timer);
        reject(new Error(msg));
      }
    });
  });

  console.log(`\nOpening your browser to authorize "${alias}".`);
  console.log(`If it doesn't open, paste this into your browser:\n\n${url}\n`);
  spawn("open", [url], { stdio: "ignore", detached: true }).unref();

  let code: string;
  try {
    code = await codePromise;
  } finally {
    server.close();
  }

  const { tokens } = await oauth2.getToken(code);
  if (!tokens.refresh_token && !existing?.tokens.refresh_token) {
    throw new Error(
      "Google did not return a refresh token. Revoke this app at " +
        "https://myaccount.google.com/permissions and run the command again.",
    );
  }
  const merged = { ...tokens, refresh_token: tokens.refresh_token ?? existing!.tokens.refresh_token };
  oauth2.setCredentials(merged);

  const profile = await google.gmail({ version: "v1", auth: oauth2 }).users.getProfile({ userId: "me" });
  const email = profile.data.emailAddress;
  if (!email) throw new Error("Authorized, but Gmail did not report an email address for the account.");

  // Guard against pointing two aliases at the same inbox by accident.
  for (const other of await listAccounts()) {
    if (other.email === email && other.alias !== alias) {
      console.warn(`\n  Warning: alias "${other.alias}" is already authorized for ${email}.`);
    }
  }

  const account: StoredAccount = {
    alias,
    email,
    tokens: merged,
    authorizedAt: new Date().toISOString(),
  };
  const file = await saveAccount(account);
  console.log(`\nAuthorized ${email} as "${alias}".`);
  console.log(`Token saved to ${file} (owner-only permissions).`);
  return account;
}

async function main(): Promise<void> {
  const [command, ...rest] = process.argv.slice(2);

  if (!command || command === "--help" || command === "-h") {
    console.log(
      [
        "Usage:",
        "  npm run auth -- <alias>        authorize a Gmail account under <alias>",
        "  npm run auth -- --list         list authorized accounts",
        "  npm run auth -- --remove <a>   forget an account's stored token",
        "  npm run auth -- --rename <a> <b>  rename an alias, keeping its token",
        "",
        "Aliases are how you refer to each inbox, e.g. personal, bars, golf.",
      ].join("\n"),
    );
    return;
  }

  if (command === "--list") {
    const accounts = await listAccounts();
    if (!accounts.length) {
      console.log("No accounts authorized yet. Run: npm run auth -- <alias>");
      return;
    }
    for (const a of accounts) {
      console.log(`  ${a.alias.padEnd(14)} ${a.email.padEnd(32)} authorized ${a.authorizedAt.slice(0, 10)}`);
    }
    return;
  }

  if (command === "--rename") {
    const [from, to] = rest;
    if (!from || !to) throw new ConfigError("Usage: npm run auth -- --rename <old-alias> <new-alias>");
    assertValidAlias(to);
    const account = await loadAccount(from);
    if (await loadAccount(to).catch(() => null)) {
      throw new ConfigError(`Alias "${to}" is already in use. Remove it first, or pick another name.`);
    }
    account.alias = to;
    await saveAccount(account);
    await removeAccount(from);
    console.log(`Renamed "${from}" to "${to}" (${account.email}). No re-authorization needed.`);
    return;
  }

  if (command === "--remove") {
    const alias = rest[0];
    if (!alias) throw new ConfigError("Usage: npm run auth -- --remove <alias>");
    const removed = await removeAccount(alias);
    console.log(
      removed
        ? `Removed local token for "${alias}". Also revoke it at https://myaccount.google.com/permissions if you're done with it.`
        : `No stored account under "${alias}".`,
    );
    return;
  }

  if (rest.length) {
    throw new ConfigError(
      `Expected a single alias but got: ${[command, ...rest].join(" ")}\n` +
        `An alias is one word. Use hyphens instead of spaces, e.g. "${[command, ...rest].join("-").toLowerCase()}".`,
    );
  }

  await authorize(command);
}

main().catch((err: unknown) => {
  const message = err instanceof Error ? err.message : String(err);
  console.error(`\n${message}\n`);
  process.exit(1);
});
