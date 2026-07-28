import { gmail_v1, google } from "googleapis";

import { loadAccount, loadOAuthClientConfig, saveAccount } from "./store.js";

export interface AccountClient {
  alias: string;
  email: string;
  gmail: gmail_v1.Gmail;
}

const clients = new Map<string, AccountClient>();

/**
 * Builds (and caches) an authorized Gmail client for an alias. Refreshed
 * tokens are written back to disk so a long-lived session doesn't have to
 * re-authorize every hour.
 */
export async function getClient(alias: string): Promise<AccountClient> {
  const cached = clients.get(alias);
  if (cached) return cached;

  const account = await loadAccount(alias);
  const { client_id, client_secret } = await loadOAuthClientConfig();

  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(account.tokens);

  auth.on("tokens", (tokens) => {
    const merged = {
      ...account.tokens,
      ...tokens,
      // A refresh response usually omits refresh_token; never overwrite ours with undefined.
      refresh_token: tokens.refresh_token ?? account.tokens.refresh_token,
    };
    account.tokens = merged;
    void saveAccount(account).catch(() => {
      // Persisting is an optimization. Failing to write shouldn't kill the call.
    });
  });

  const client: AccountClient = {
    alias,
    email: account.email,
    gmail: google.gmail({ version: "v1", auth }),
  };
  clients.set(alias, client);
  return client;
}

export function header(message: gmail_v1.Schema$Message, name: string): string {
  const headers = message.payload?.headers ?? [];
  const found = headers.find((h) => h.name?.toLowerCase() === name.toLowerCase());
  return found?.value ?? "";
}

/** Walks the MIME tree and returns the best plain-text rendering of a message. */
export function extractBody(message: gmail_v1.Schema$Message): string {
  const decode = (data?: string | null): string =>
    data ? Buffer.from(data, "base64url").toString("utf8") : "";

  const collect = (part: gmail_v1.Schema$MessagePart | undefined, want: string): string => {
    if (!part) return "";
    if (part.mimeType === want && part.body?.data) return decode(part.body.data);
    for (const child of part.parts ?? []) {
      const hit = collect(child, want);
      if (hit) return hit;
    }
    return "";
  };

  const plain = collect(message.payload, "text/plain");
  if (plain) return plain.trim();

  const html = collect(message.payload, "text/html");
  if (html) {
    return html
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(p|div|tr|li|h[1-6])>/gi, "\n")
      .replace(/<[^>]+>/g, "")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  if (message.payload?.body?.data) return decode(message.payload.body.data).trim();
  return message.snippet ?? "";
}

/** RFC 2047 encoding, so non-ASCII subjects and names survive the trip. */
function encodeHeaderValue(value: string): string {
  // eslint-disable-next-line no-control-regex
  return /^[\x00-\x7F]*$/.test(value)
    ? value
    : `=?UTF-8?B?${Buffer.from(value, "utf8").toString("base64")}?=`;
}

export interface OutgoingMessage {
  from: string;
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  inReplyTo?: string;
  references?: string;
}

/** Assembles an RFC 5322 message and returns it base64url encoded for the API. */
export function buildRawMessage(msg: OutgoingMessage): string {
  const lines = [
    `From: ${msg.from}`,
    `To: ${msg.to.join(", ")}`,
    ...(msg.cc?.length ? [`Cc: ${msg.cc.join(", ")}`] : []),
    ...(msg.bcc?.length ? [`Bcc: ${msg.bcc.join(", ")}`] : []),
    `Subject: ${encodeHeaderValue(msg.subject)}`,
    ...(msg.inReplyTo ? [`In-Reply-To: ${msg.inReplyTo}`, `References: ${msg.references ?? msg.inReplyTo}`] : []),
    "MIME-Version: 1.0",
    'Content-Type: text/plain; charset="UTF-8"',
    "Content-Transfer-Encoding: 8bit",
    "",
    msg.body,
  ];
  return Buffer.from(lines.join("\r\n"), "utf8").toString("base64url");
}

/** Turns Google API errors into something readable instead of a wall of JSON. */
export function describeError(err: unknown): string {
  const e = err as any;
  const apiMessage = e?.response?.data?.error?.message ?? e?.errors?.[0]?.message;
  const status = e?.response?.status ?? e?.code;

  if (status === 401 || status === 403) {
    return (
      `${apiMessage ?? "Gmail rejected the request"} (HTTP ${status}). ` +
      `The stored token may have been revoked or expired. Re-run: npm run auth -- <alias>`
    );
  }
  if (apiMessage) return `${apiMessage}${status ? ` (HTTP ${status})` : ""}`;
  return e instanceof Error ? e.message : String(err);
}
