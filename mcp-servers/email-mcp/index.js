/**
 * Email MCP Server — E-commerce AI Employee (Silver Tier)
 *
 * Exposes Gmail capabilities as MCP tools so Claude can send,
 * draft, and search emails natively without Python scripts.
 *
 * Tools:
 *   - send_email       → send an approved email
 *   - draft_email      → create a draft (does not send)
 *   - search_emails    → search inbox by query
 *   - get_email        → get full email by ID
 *   - list_unread      → list unread primary emails
 *
 * Config (env vars or defaults):
 *   GMAIL_TOKEN_PATH   → path to gmail_token.json
 *   VAULT_PATH         → path to Obsidian vault
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { google } from "googleapis";
import fs from "fs";
import path from "path";

// ── Config ────────────────────────────────────────────────────────────────────
const VAULT_PATH =
  process.env.VAULT_PATH || "E:/AI_Employee_Vault";
const TOKEN_PATH =
  process.env.GMAIL_TOKEN_PATH ||
  path.join(VAULT_PATH, ".secrets/gmail_token.json");
const LOGS_PATH = path.join(VAULT_PATH, "Logs");

// ── Gmail Auth ────────────────────────────────────────────────────────────────
function getGmailClient() {
  if (!fs.existsSync(TOKEN_PATH)) {
    throw new Error(`Gmail token not found at ${TOKEN_PATH}. Run setup_gmail_auth.py first.`);
  }

  const tokenData = JSON.parse(fs.readFileSync(TOKEN_PATH, "utf-8"));
  const auth = new google.auth.OAuth2();
  auth.setCredentials(tokenData);
  return google.gmail({ version: "v1", auth });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function encodeEmail({ to, subject, body, replyToMessageId, threadId }) {
  const lines = [
    `To: ${to}`,
    `Subject: ${subject}`,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=utf-8",
    "",
    body,
  ];
  const raw = Buffer.from(lines.join("\r\n"))
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return { raw, threadId };
}

function writeAuditLog(entry) {
  try {
    const date = new Date().toISOString().split("T")[0];
    const logFile = path.join(LOGS_PATH, `${date}.json`);
    const logs = fs.existsSync(logFile)
      ? JSON.parse(fs.readFileSync(logFile, "utf-8"))
      : [];
    logs.push({ timestamp: new Date().toISOString(), ...entry });
    fs.writeFileSync(logFile, JSON.stringify(logs, null, 2));
  } catch (e) {
    // non-fatal
  }
}

function extractBody(payload) {
  if (!payload) return "";
  if (payload.mimeType === "text/plain" && payload.body?.data) {
    return Buffer.from(payload.body.data, "base64").toString("utf-8");
  }
  for (const part of payload.parts || []) {
    const text = extractBody(part);
    if (text) return text;
  }
  return "";
}

// ── MCP Server ────────────────────────────────────────────────────────────────
const server = new Server(
  { name: "email-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// List tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_email",
      description:
        "Send an email via Gmail. Use only after human approval in /Approved/. Logs action to /Logs/.",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email address" },
          subject: { type: "string", description: "Email subject" },
          body: { type: "string", description: "Plain text email body" },
          thread_id: {
            type: "string",
            description: "Gmail thread ID to reply in (optional)",
          },
          approval_file: {
            type: "string",
            description: "Path to the /Approved/ file that authorized this send",
          },
        },
        required: ["to", "subject", "body"],
      },
    },
    {
      name: "draft_email",
      description: "Create a Gmail draft without sending. Safe to call without approval.",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email address" },
          subject: { type: "string", description: "Email subject" },
          body: { type: "string", description: "Plain text email body" },
        },
        required: ["to", "subject", "body"],
      },
    },
    {
      name: "list_unread",
      description:
        "List unread emails from the primary inbox. Returns sender, subject, snippet, and ID.",
      inputSchema: {
        type: "object",
        properties: {
          max_results: {
            type: "number",
            description: "Maximum number of emails to return (default 10)",
          },
        },
      },
    },
    {
      name: "search_emails",
      description: "Search Gmail using a query string (same syntax as Gmail search bar).",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Gmail search query e.g. 'from:customer@email.com is:unread'",
          },
          max_results: { type: "number", description: "Max results (default 10)" },
        },
        required: ["query"],
      },
    },
    {
      name: "get_email",
      description: "Get the full content of a specific email by its Gmail message ID.",
      inputSchema: {
        type: "object",
        properties: {
          message_id: { type: "string", description: "Gmail message ID" },
        },
        required: ["message_id"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const gmail = getGmailClient();

    // ── send_email ──────────────────────────────────────────────────────────
    if (name === "send_email") {
      const { to, subject, body, thread_id, approval_file } = args;

      const message = encodeEmail({ to, subject, body, threadId: thread_id });
      const result = await gmail.users.messages.send({
        userId: "me",
        requestBody: message,
      });

      writeAuditLog({
        action_type: "email_send",
        actor: "claude_code_via_email_mcp",
        target: to,
        parameters: { subject, thread_id },
        approval_file: approval_file || "none",
        approval_status: approval_file ? "approved" : "auto",
        result: "success",
        message_id: result.data.id,
      });

      return {
        content: [
          {
            type: "text",
            text: `Email sent successfully.\nTo: ${to}\nSubject: ${subject}\nMessage ID: ${result.data.id}`,
          },
        ],
      };
    }

    // ── draft_email ─────────────────────────────────────────────────────────
    if (name === "draft_email") {
      const { to, subject, body } = args;
      const message = encodeEmail({ to, subject, body });
      const result = await gmail.users.drafts.create({
        userId: "me",
        requestBody: { message },
      });

      return {
        content: [
          {
            type: "text",
            text: `Draft created.\nTo: ${to}\nSubject: ${subject}\nDraft ID: ${result.data.id}`,
          },
        ],
      };
    }

    // ── list_unread ─────────────────────────────────────────────────────────
    if (name === "list_unread") {
      const maxResults = args.max_results || 10;
      const result = await gmail.users.messages.list({
        userId: "me",
        q: "is:unread category:primary",
        maxResults,
      });

      const messages = result.data.messages || [];
      if (messages.length === 0) {
        return { content: [{ type: "text", text: "No unread emails." }] };
      }

      const details = await Promise.all(
        messages.map((m) =>
          gmail.users.messages
            .get({ userId: "me", id: m.id, format: "metadata",
              metadataHeaders: ["From", "Subject", "Date"] })
            .then((r) => {
              const headers = Object.fromEntries(
                r.data.payload.headers.map((h) => [h.name, h.value])
              );
              return `ID: ${m.id}\nFrom: ${headers.From}\nSubject: ${headers.Subject}\nDate: ${headers.Date}\nSnippet: ${r.data.snippet}\n`;
            })
        )
      );

      return { content: [{ type: "text", text: details.join("\n---\n") }] };
    }

    // ── search_emails ───────────────────────────────────────────────────────
    if (name === "search_emails") {
      const { query, max_results = 10 } = args;
      const result = await gmail.users.messages.list({
        userId: "me",
        q: query,
        maxResults: max_results,
      });

      const messages = result.data.messages || [];
      if (messages.length === 0) {
        return { content: [{ type: "text", text: `No emails found for: "${query}"` }] };
      }

      const details = await Promise.all(
        messages.map((m) =>
          gmail.users.messages
            .get({ userId: "me", id: m.id, format: "metadata",
              metadataHeaders: ["From", "Subject", "Date"] })
            .then((r) => {
              const headers = Object.fromEntries(
                r.data.payload.headers.map((h) => [h.name, h.value])
              );
              return `ID: ${m.id}\nFrom: ${headers.From}\nSubject: ${headers.Subject}\nDate: ${headers.Date}\nSnippet: ${r.data.snippet}\n`;
            })
        )
      );

      return { content: [{ type: "text", text: details.join("\n---\n") }] };
    }

    // ── get_email ───────────────────────────────────────────────────────────
    if (name === "get_email") {
      const { message_id } = args;
      const result = await gmail.users.messages.get({
        userId: "me",
        id: message_id,
        format: "full",
      });

      const msg = result.data;
      const headers = Object.fromEntries(
        msg.payload.headers.map((h) => [h.name, h.value])
      );
      const body = extractBody(msg.payload);

      return {
        content: [
          {
            type: "text",
            text: [
              `From: ${headers.From}`,
              `To: ${headers.To}`,
              `Subject: ${headers.Subject}`,
              `Date: ${headers.Date}`,
              `Thread ID: ${msg.threadId}`,
              ``,
              `--- Body ---`,
              body || msg.snippet,
            ].join("\n"),
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[email-mcp] Server running. Tools: send_email, draft_email, list_unread, search_emails, get_email");
