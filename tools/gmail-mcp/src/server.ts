#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { buildRawMessage, describeError, extractBody, getClient, header } from "./gmail.js";
import { listAccounts } from "./store.js";

const server = new McpServer({ name: "gmail-mcp", version: "0.1.0" });

const text = (body: string) => ({ content: [{ type: "text" as const, text: body }] });
const fail = (err: unknown) => ({ content: [{ type: "text" as const, text: describeError(err) }], isError: true });

const accountArg = z
  .string()
  .describe("Which inbox to act on, by alias. Omit only when exactly one account is authorized.")
  .optional();

/**
 * Resolves the alias to use. With a single authorized account we let it be
 * implicit; with several, an explicit choice is required so a message never
 * goes out from the wrong inbox by default.
 */
async function resolveAlias(alias?: string): Promise<string> {
  if (alias) return alias;
  const accounts = await listAccounts();
  if (accounts.length === 1) return accounts[0].alias;
  if (accounts.length === 0) {
    throw new Error("No Gmail accounts are authorized yet. Run: npm run auth -- <alias>");
  }
  throw new Error(
    `Several accounts are authorized (${accounts.map((a) => a.alias).join(", ")}). ` +
      `Pass "account" to say which one to use.`,
  );
}

server.registerTool(
  "list_accounts",
  {
    title: "List authorized Gmail accounts",
    description:
      "Lists every Gmail account this server can act on, with its alias and email address. " +
      "Call this first when you are unsure which alias maps to which inbox.",
    inputSchema: {},
    annotations: { readOnlyHint: true },
  },
  async () => {
    try {
      const accounts = await listAccounts();
      if (!accounts.length) {
        return text("No accounts authorized yet. Run `npm run auth -- <alias>` in ~/Developer/gmail-mcp.");
      }
      return text(accounts.map((a) => `${a.alias}\t${a.email}\tauthorized ${a.authorizedAt.slice(0, 10)}`).join("\n"));
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "search_threads",
  {
    title: "Search threads",
    description:
      "Searches an inbox using Gmail query syntax (from:, to:, subject:, newer_than:, is:unread, has:attachment, " +
      "label:, in:, and boolean operators). Returns thread ids with subject, participants, date and a snippet. " +
      "Use read_thread to get full message bodies.",
    inputSchema: {
      account: accountArg,
      query: z.string().describe('Gmail search query, e.g. "from:vendor@x.com newer_than:30d is:unread".'),
      maxResults: z.number().int().min(1).max(50).default(15).describe("How many threads to return, 1-50."),
    },
    annotations: { readOnlyHint: true },
  },
  async ({ account, query, maxResults }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const list = await gmail.users.threads.list({ userId: "me", q: query, maxResults });
      const threads = list.data.threads ?? [];
      if (!threads.length) return text(`No threads in ${email} matched: ${query}`);

      const rows = await Promise.all(
        threads.map(async (t) => {
          const full = await gmail.users.threads.get({
            userId: "me",
            id: t.id!,
            format: "metadata",
            metadataHeaders: ["Subject", "From", "To", "Date"],
          });
          const messages = full.data.messages ?? [];
          const first = messages[0];
          const last = messages[messages.length - 1];
          return [
            `id: ${t.id}`,
            `subject: ${header(first, "Subject") || "(no subject)"}`,
            `from: ${header(last, "From")}`,
            `date: ${header(last, "Date")}`,
            `messages: ${messages.length}`,
            `labels: ${(last?.labelIds ?? []).join(", ") || "-"}`,
            `snippet: ${t.snippet ?? ""}`,
          ].join("\n");
        }),
      );
      return text(`${rows.length} thread(s) in ${email}\n\n${rows.join("\n\n")}`);
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "read_thread",
  {
    title: "Read a thread",
    description: "Returns every message in a thread with its headers and plain-text body.",
    inputSchema: {
      account: accountArg,
      threadId: z.string().describe("Thread id, as returned by search_threads."),
    },
    annotations: { readOnlyHint: true },
  },
  async ({ account, threadId }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const res = await gmail.users.threads.get({ userId: "me", id: threadId, format: "full" });
      const messages = res.data.messages ?? [];
      if (!messages.length) return text(`Thread ${threadId} has no messages.`);

      const rendered = messages.map((m, i) => {
        const parts = [
          `--- message ${i + 1} of ${messages.length} ---`,
          `id: ${m.id}`,
          `from: ${header(m, "From")}`,
          `to: ${header(m, "To")}`,
        ];
        const cc = header(m, "Cc");
        if (cc) parts.push(`cc: ${cc}`);
        parts.push(
          `date: ${header(m, "Date")}`,
          `subject: ${header(m, "Subject")}`,
          `labels: ${(m.labelIds ?? []).join(", ") || "-"}`,
          "",
          extractBody(m),
        );
        return parts.join("\n");
      });
      return text(`Thread ${threadId} in ${email}\n\n${rendered.join("\n\n")}`);
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "create_draft",
  {
    title: "Create a draft",
    description:
      "Saves a draft in the account's Drafts folder without sending it. Prefer this over send_message " +
      "unless the user has explicitly asked for the message to go out.",
    inputSchema: {
      account: accountArg,
      to: z.array(z.string()).min(1).describe("Recipient email addresses."),
      subject: z.string(),
      body: z.string().describe("Plain-text body."),
      cc: z.array(z.string()).optional(),
      bcc: z.array(z.string()).optional(),
      threadId: z.string().optional().describe("Attach the draft to an existing thread, making it a reply."),
    },
  },
  async ({ account, to, subject, body, cc, bcc, threadId }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const raw = buildRawMessage({ from: email, to, cc, bcc, subject, body });
      const res = await gmail.users.drafts.create({
        userId: "me",
        requestBody: { message: { raw, ...(threadId ? { threadId } : {}) } },
      });
      return text(`Draft saved in ${email}.\ndraft id: ${res.data.id}\nsubject: ${subject}\nto: ${to.join(", ")}`);
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "send_message",
  {
    title: "Send a message",
    description:
      "Sends an email immediately. This cannot be undone. Before calling this you MUST show the user the " +
      "exact sending account, recipients, subject and body, and get their explicit go-ahead in that turn. " +
      "If you have not done that, call create_draft instead. Set confirm to true only after the user has agreed.",
    inputSchema: {
      account: accountArg,
      to: z.array(z.string()).min(1).describe("Recipient email addresses."),
      subject: z.string(),
      body: z.string().describe("Plain-text body."),
      cc: z.array(z.string()).optional(),
      bcc: z.array(z.string()).optional(),
      threadId: z.string().optional().describe("Send as a reply within this thread."),
      inReplyTo: z.string().optional().describe("Message-ID header of the message being replied to."),
      confirm: z
        .literal(true)
        .describe("Must be true, and only after the user has seen the message and approved sending it."),
    },
    annotations: { destructiveHint: true, openWorldHint: true, idempotentHint: false },
  },
  async ({ account, to, subject, body, cc, bcc, threadId, inReplyTo, confirm }) => {
    try {
      if (confirm !== true) throw new Error("send_message requires confirm: true after the user approves the message.");
      const { gmail, email } = await getClient(await resolveAlias(account));
      const raw = buildRawMessage({ from: email, to, cc, bcc, subject, body, inReplyTo });
      const res = await gmail.users.messages.send({
        userId: "me",
        requestBody: { raw, ...(threadId ? { threadId } : {}) },
      });
      return text(
        `Sent from ${email}.\nmessage id: ${res.data.id}\nthread id: ${res.data.threadId}\n` +
          `to: ${to.join(", ")}\nsubject: ${subject}`,
      );
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "list_labels",
  {
    title: "List labels",
    description: "Lists the account's labels with their ids. Label ids are needed by modify_labels.",
    inputSchema: { account: accountArg },
    annotations: { readOnlyHint: true },
  },
  async ({ account }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const res = await gmail.users.labels.list({ userId: "me" });
      const labels = (res.data.labels ?? []).sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""));
      return text(`Labels in ${email}\n\n${labels.map((l) => `${l.id}\t${l.name}\t(${l.type})`).join("\n")}`);
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "modify_labels",
  {
    title: "Add or remove labels",
    description:
      "Adds or removes labels on a message. Common moves: archive by removing INBOX, mark read by removing UNREAD, " +
      "star by adding STARRED. Use list_labels for custom label ids.",
    inputSchema: {
      account: accountArg,
      messageId: z.string().describe("Message id, not thread id."),
      addLabelIds: z.array(z.string()).optional(),
      removeLabelIds: z.array(z.string()).optional(),
    },
  },
  async ({ account, messageId, addLabelIds, removeLabelIds }) => {
    try {
      if (!addLabelIds?.length && !removeLabelIds?.length) {
        throw new Error("Pass at least one of addLabelIds or removeLabelIds.");
      }
      const { gmail, email } = await getClient(await resolveAlias(account));
      const res = await gmail.users.messages.modify({
        userId: "me",
        id: messageId,
        requestBody: { addLabelIds, removeLabelIds },
      });
      return text(`Updated ${messageId} in ${email}.\nlabels now: ${(res.data.labelIds ?? []).join(", ") || "-"}`);
    } catch (err) {
      return fail(err);
    }
  },
);

server.registerTool(
  "trash_message",
  {
    title: "Move a message to trash",
    description:
      "Moves a message to Trash, where Gmail keeps it for 30 days. This server cannot permanently delete anything.",
    inputSchema: {
      account: accountArg,
      messageId: z.string(),
    },
    annotations: { destructiveHint: true, idempotentHint: true },
  },
  async ({ account, messageId }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      await gmail.users.messages.trash({ userId: "me", id: messageId });
      return text(`Moved ${messageId} to Trash in ${email}. Recoverable for 30 days.`);
    } catch (err) {
      return fail(err);
    }
  },
);

async function main(): Promise<void> {
  await server.connect(new StdioServerTransport());
}

main().catch((err: unknown) => {
  // stdout is the MCP transport, so diagnostics must go to stderr.
  console.error(`gmail-mcp failed to start: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
