#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";

import {
  buildRawMessage,
  describeError,
  extractBody,
  getClient,
  guessMimeType,
  header,
  listAttachments,
  type OutgoingAttachment,
} from "./gmail.js";
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

// Gmail rejects messages over 25 MB; the base64 overhead means the real file budget is lower.
const MAX_ATTACHMENT_TOTAL_BYTES = 18 * 1024 * 1024;

const attachmentsArg = z
  .array(z.string())
  .optional()
  .describe("Local file paths to attach. ~ expands to the home directory. 18 MB total limit.");

/** Reads outgoing attachment files off disk, guessing each MIME type from its extension. */
async function loadOutgoingAttachments(paths?: string[]): Promise<OutgoingAttachment[] | undefined> {
  if (!paths?.length) return undefined;
  const loaded = await Promise.all(
    paths.map(async (p) => {
      const resolved = p.startsWith("~/") ? path.join(homedir(), p.slice(2)) : p;
      const content = await readFile(resolved);
      return { filename: path.basename(resolved), mimeType: guessMimeType(resolved), content };
    }),
  );
  const total = loaded.reduce((sum, a) => sum + a.content.length, 0);
  if (total > MAX_ATTACHMENT_TOTAL_BYTES) {
    throw new Error(
      `Attachments total ${(total / 1024 / 1024).toFixed(1)} MB; Gmail's limit means ` +
        `${MAX_ATTACHMENT_TOTAL_BYTES / 1024 / 1024} MB is the most this server will send.`,
    );
  }
  return loaded;
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
      pageToken: z
        .string()
        .optional()
        .describe("Continue an earlier search from the page token it returned."),
    },
    annotations: { readOnlyHint: true },
  },
  async ({ account, query, maxResults, pageToken }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const list = await gmail.users.threads.list({ userId: "me", q: query, maxResults, pageToken });
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
      const more = list.data.nextPageToken
        ? `\n\nMore results exist. Pass pageToken: "${list.data.nextPageToken}" to continue.`
        : "";
      return text(`${rows.length} thread(s) in ${email}\n\n${rows.join("\n\n")}${more}`);
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
  "save_attachments",
  {
    title: "Save a message's attachments to disk",
    description:
      "Downloads a message's attachments (images, PDFs, any file) to a local directory and returns the saved " +
      "paths, so the files can be opened or read. Pass a filename to fetch just one attachment; omit it to " +
      "save them all. With list set to true, only lists what is attached without downloading anything. " +
      "Attachments hang off messages, not threads — get the message id from read_thread.",
    inputSchema: {
      account: accountArg,
      messageId: z.string().describe("Message id, as shown by read_thread (not a thread id)."),
      filename: z.string().optional().describe("Save only the attachment with this exact filename."),
      outDir: z
        .string()
        .optional()
        .describe("Directory to save into. Defaults to ~/Downloads/gmail-attachments/<messageId>/."),
      list: z.boolean().optional().describe("If true, list the attachments without downloading."),
    },
    annotations: { readOnlyHint: true },
  },
  async ({ account, messageId, filename, outDir, list }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const msg = await gmail.users.messages.get({ userId: "me", id: messageId, format: "full" });
      let attachments = listAttachments(msg.data);
      if (!attachments.length) return text(`Message ${messageId} in ${email} has no attachments.`);
      if (filename) {
        attachments = attachments.filter((a) => a.filename === filename);
        if (!attachments.length) {
          throw new Error(
            `No attachment named "${filename}" on ${messageId}. Attached: ${listAttachments(msg.data)
              .map((a) => a.filename)
              .join(", ")}`,
          );
        }
      }

      if (list) {
        const rows = attachments.map((a) => `${a.filename}\t${a.mimeType}\t${a.sizeBytes} bytes`);
        return text(`${rows.length} attachment(s) on ${messageId} in ${email}\n\n${rows.join("\n")}`);
      }

      const dir = outDir ?? path.join(homedir(), "Downloads", "gmail-attachments", messageId);
      await mkdir(dir, { recursive: true });

      const saved = await Promise.all(
        attachments.map(async (a) => {
          const res = await gmail.users.messages.attachments.get({
            userId: "me",
            messageId,
            id: a.attachmentId,
          });
          if (!res.data.data) throw new Error(`Gmail returned no data for attachment "${a.filename}".`);
          // Strip path separators so a hostile filename can't escape the target directory.
          const safeName = path.basename(a.filename.replace(/[/\\]/g, "_")) || "unnamed";
          const dest = path.join(dir, safeName);
          await writeFile(dest, Buffer.from(res.data.data, "base64url"));
          return `${dest}\t${a.mimeType}\t${a.sizeBytes} bytes`;
        }),
      );
      return text(`Saved ${saved.length} attachment(s) from ${messageId} in ${email}\n\n${saved.join("\n")}`);
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
      attachments: attachmentsArg,
    },
  },
  async ({ account, to, subject, body, cc, bcc, threadId, attachments }) => {
    try {
      const { gmail, email } = await getClient(await resolveAlias(account));
      const files = await loadOutgoingAttachments(attachments);
      const raw = buildRawMessage({ from: email, to, cc, bcc, subject, body, attachments: files });
      const res = await gmail.users.drafts.create({
        userId: "me",
        requestBody: { message: { raw, ...(threadId ? { threadId } : {}) } },
      });
      const attached = files?.length ? `\nattached: ${files.map((f) => f.filename).join(", ")}` : "";
      return text(
        `Draft saved in ${email}.\ndraft id: ${res.data.id}\nsubject: ${subject}\nto: ${to.join(", ")}${attached}`,
      );
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
      "exact sending account, recipients, subject, body and any attachments, and get their explicit go-ahead " +
      "in that turn. " +
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
      attachments: attachmentsArg,
      confirm: z
        .literal(true)
        .describe("Must be true, and only after the user has seen the message and approved sending it."),
    },
    annotations: { destructiveHint: true, openWorldHint: true, idempotentHint: false },
  },
  async ({ account, to, subject, body, cc, bcc, threadId, inReplyTo, attachments, confirm }) => {
    try {
      if (confirm !== true) throw new Error("send_message requires confirm: true after the user approves the message.");
      const { gmail, email } = await getClient(await resolveAlias(account));
      const files = await loadOutgoingAttachments(attachments);
      const raw = buildRawMessage({ from: email, to, cc, bcc, subject, body, inReplyTo, attachments: files });
      const res = await gmail.users.messages.send({
        userId: "me",
        requestBody: { raw, ...(threadId ? { threadId } : {}) },
      });
      const attached = files?.length ? `\nattached: ${files.map((f) => f.filename).join(", ")}` : "";
      return text(
        `Sent from ${email}.\nmessage id: ${res.data.id}\nthread id: ${res.data.threadId}\n` +
          `to: ${to.join(", ")}\nsubject: ${subject}${attached}`,
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
      "Adds or removes labels on a message, or on every message in a thread at once. Common moves: archive by " +
      "removing INBOX, mark read by removing UNREAD, star by adding STARRED. Pass threadId to act on the whole " +
      "thread (the natural unit for archive/mark-read). Use list_labels for custom label ids.",
    inputSchema: {
      account: accountArg,
      messageId: z.string().optional().describe("Act on this one message. Pass exactly one of messageId or threadId."),
      threadId: z.string().optional().describe("Act on every message in this thread."),
      addLabelIds: z.array(z.string()).optional(),
      removeLabelIds: z.array(z.string()).optional(),
    },
  },
  async ({ account, messageId, threadId, addLabelIds, removeLabelIds }) => {
    try {
      if (!addLabelIds?.length && !removeLabelIds?.length) {
        throw new Error("Pass at least one of addLabelIds or removeLabelIds.");
      }
      if (!messageId === !threadId) {
        throw new Error("Pass exactly one of messageId or threadId.");
      }
      const { gmail, email } = await getClient(await resolveAlias(account));
      if (threadId) {
        const res = await gmail.users.threads.modify({
          userId: "me",
          id: threadId,
          requestBody: { addLabelIds, removeLabelIds },
        });
        const count = res.data.messages?.length ?? 0;
        return text(`Updated thread ${threadId} in ${email} (${count} message(s)).`);
      }
      const res = await gmail.users.messages.modify({
        userId: "me",
        id: messageId!,
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
