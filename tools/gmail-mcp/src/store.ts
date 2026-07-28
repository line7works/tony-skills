import { promises as fs } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

/**
 * Everything sensitive lives under ~/.gmail-mcp, never in the repo.
 *   credentials.json   the Google Cloud OAuth client (client_id + client_secret)
 *   accounts/<alias>.json   one refresh token per Gmail account
 */
export const CONFIG_DIR = path.join(homedir(), ".gmail-mcp");
export const CREDENTIALS_PATH = path.join(CONFIG_DIR, "credentials.json");
export const ACCOUNTS_DIR = path.join(CONFIG_DIR, "accounts");

/**
 * gmail.modify covers read, compose, send, label, archive and trash.
 * It deliberately stops short of permanent deletion, which would need the
 * full https://mail.google.com/ scope.
 */
export const SCOPES = ["https://www.googleapis.com/auth/gmail.modify"];

export interface OAuthClientConfig {
  client_id: string;
  client_secret: string;
}

export interface StoredAccount {
  alias: string;
  email: string;
  tokens: {
    access_token?: string | null;
    refresh_token?: string | null;
    scope?: string;
    token_type?: string | null;
    expiry_date?: number | null;
  };
  authorizedAt: string;
}

export class ConfigError extends Error {}

async function ensureDirs(): Promise<void> {
  await fs.mkdir(ACCOUNTS_DIR, { recursive: true, mode: 0o700 });
  await fs.chmod(CONFIG_DIR, 0o700).catch(() => {});
  await fs.chmod(ACCOUNTS_DIR, 0o700).catch(() => {});
}

/**
 * Reads the OAuth client. Accepts either a bare {client_id, client_secret}
 * object or the credentials file Google Cloud hands you, which wraps the same
 * fields under an "installed" or "web" key.
 */
export async function loadOAuthClientConfig(): Promise<OAuthClientConfig> {
  let raw: string;
  try {
    raw = await fs.readFile(CREDENTIALS_PATH, "utf8");
  } catch {
    throw new ConfigError(
      `No OAuth client found at ${CREDENTIALS_PATH}.\n` +
        `Create a Desktop app OAuth client in Google Cloud, download the JSON, ` +
        `and save it to that path.`,
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new ConfigError(`${CREDENTIALS_PATH} is not valid JSON.`);
  }

  const obj = parsed as Record<string, any>;
  const node = obj.installed ?? obj.web ?? obj;
  const client_id = node?.client_id;
  const client_secret = node?.client_secret;

  if (typeof client_id !== "string" || typeof client_secret !== "string") {
    throw new ConfigError(
      `${CREDENTIALS_PATH} is missing client_id or client_secret. ` +
        `Expected the JSON downloaded from the Google Cloud credentials page.`,
    );
  }
  return { client_id, client_secret };
}

/** Aliases are used as filenames and as tool arguments, so keep them tame. */
export function assertValidAlias(alias: string): void {
  if (!/^[a-z0-9][a-z0-9-]{0,31}$/.test(alias)) {
    throw new ConfigError(
      `Invalid alias "${alias}". Use lowercase letters, digits and hyphens, ` +
        `starting with a letter or digit, max 32 characters.`,
    );
  }
}

export async function listAccounts(): Promise<StoredAccount[]> {
  let names: string[];
  try {
    names = await fs.readdir(ACCOUNTS_DIR);
  } catch {
    return [];
  }
  const accounts: StoredAccount[] = [];
  for (const name of names.filter((n) => n.endsWith(".json")).sort()) {
    try {
      accounts.push(JSON.parse(await fs.readFile(path.join(ACCOUNTS_DIR, name), "utf8")));
    } catch {
      // A corrupt token file shouldn't take down every other account.
    }
  }
  return accounts;
}

export async function loadAccount(alias: string): Promise<StoredAccount> {
  assertValidAlias(alias);
  try {
    const raw = await fs.readFile(path.join(ACCOUNTS_DIR, `${alias}.json`), "utf8");
    return JSON.parse(raw) as StoredAccount;
  } catch {
    const known = (await listAccounts()).map((a) => a.alias);
    throw new ConfigError(
      `No account authorized under alias "${alias}".` +
        (known.length ? ` Known aliases: ${known.join(", ")}.` : ` No accounts authorized yet.`),
    );
  }
}

export async function saveAccount(account: StoredAccount): Promise<string> {
  assertValidAlias(account.alias);
  await ensureDirs();
  const file = path.join(ACCOUNTS_DIR, `${account.alias}.json`);
  await fs.writeFile(file, JSON.stringify(account, null, 2) + "\n", { mode: 0o600 });
  await fs.chmod(file, 0o600).catch(() => {});
  return file;
}

export async function removeAccount(alias: string): Promise<boolean> {
  assertValidAlias(alias);
  try {
    await fs.unlink(path.join(ACCOUNTS_DIR, `${alias}.json`));
    return true;
  } catch {
    return false;
  }
}
