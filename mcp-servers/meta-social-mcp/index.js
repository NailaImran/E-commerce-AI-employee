/**
 * Meta Social MCP Server — E-commerce AI Employee (Gold Tier)
 *
 * Exposes Meta Graph API capabilities as MCP tools:
 *   - post_to_facebook_page   Post text (+ optional image) to a Facebook Page
 *   - post_to_instagram       Post an image + caption to an Instagram Business account
 *   - get_page_insights       Fetch reach/engagement metrics for recent Facebook posts
 *
 * Config (from environment / .env):
 *   META_APP_ID                   Meta App ID
 *   META_APP_SECRET               Meta App Secret
 *   META_PAGE_ACCESS_TOKEN        Long-lived Page Access Token
 *   META_PAGE_ID                  Facebook Page ID
 *   META_INSTAGRAM_ACCOUNT_ID     Instagram Business Account ID (linked to the Page)
 *   VAULT_PATH                    E:/AI_Employee_Vault (for audit logging)
 *
 * Graph API version: v21.0
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import fs from "fs";
import path from "path";

// ── Config ────────────────────────────────────────────────────────────────────
const GRAPH_API_VERSION = "v21.0";
const GRAPH_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;
const VAULT_PATH = process.env.VAULT_PATH || "E:/AI_Employee_Vault";
const LOGS_PATH = path.join(VAULT_PATH, "Logs");

// ── Helpers ───────────────────────────────────────────────────────────────────
function getConfig() {
  const token = process.env.META_PAGE_ACCESS_TOKEN;
  const pageId = process.env.META_PAGE_ID;
  const igAccountId = process.env.META_INSTAGRAM_ACCOUNT_ID;

  if (!token) {
    throw new Error(
      "META_PAGE_ACCESS_TOKEN not set. Add it to .env — see .claude/skills/meta-poster/references/meta_api.md"
    );
  }
  return { token, pageId, igAccountId };
}

async function graphPost(endpoint, params) {
  const url = `${GRAPH_BASE}/${endpoint}`;
  const body = new URLSearchParams(params);
  const response = await fetch(url, {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  const data = await response.json();
  if (!response.ok || data.error) {
    const msg = data.error?.message || JSON.stringify(data);
    throw new Error(`Meta Graph API error: ${msg}`);
  }
  return data;
}

async function graphGet(endpoint, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const url = `${GRAPH_BASE}/${endpoint}${qs ? "?" + qs : ""}`;
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok || data.error) {
    const msg = data.error?.message || JSON.stringify(data);
    throw new Error(`Meta Graph API error: ${msg}`);
  }
  return data;
}

function writeAuditLog(entry) {
  try {
    if (!fs.existsSync(LOGS_PATH)) {
      fs.mkdirSync(LOGS_PATH, { recursive: true });
    }
    const dateStr = new Date().toISOString().split("T")[0];
    const logFile = path.join(LOGS_PATH, `${dateStr}.json`);
    let existing = [];
    if (fs.existsSync(logFile)) {
      try {
        existing = JSON.parse(fs.readFileSync(logFile, "utf8"));
      } catch {
        existing = [];
      }
    }
    existing.push({
      timestamp: new Date().toISOString(),
      actor: "meta-social-mcp",
      ...entry,
    });
    fs.writeFileSync(logFile, JSON.stringify(existing, null, 2), "utf8");
  } catch (err) {
    console.error("[meta-social-mcp] Audit log error:", err.message);
  }
}

// ── Tool Definitions ──────────────────────────────────────────────────────────
const TOOLS = [
  {
    name: "post_to_facebook_page",
    description:
      "Post a text update (with optional image) to the configured Facebook Page. " +
      "Always ensure a human has approved the post via the HITL workflow (FACEBOOK_*.md in /Approved/) before calling this.",
    inputSchema: {
      type: "object",
      properties: {
        message: {
          type: "string",
          description: "Post text content (recommended 100–500 characters)",
        },
        image_url: {
          type: "string",
          description: "Optional: publicly accessible URL of an image to attach",
        },
        link: {
          type: "string",
          description: "Optional: URL to attach as a link preview (store URL, product page)",
        },
        dry_run: {
          type: "boolean",
          description: "If true, validates but does not actually post",
          default: false,
        },
      },
      required: ["message"],
    },
  },
  {
    name: "post_to_instagram",
    description:
      "Post an image with caption to the Instagram Business account linked to the Facebook Page. " +
      "Requires a publicly accessible image URL. " +
      "Always ensure a human has approved via INSTAGRAM_*.md in /Approved/ before calling this.",
    inputSchema: {
      type: "object",
      properties: {
        caption: {
          type: "string",
          description: "Post caption including hashtags (recommended ≤2200 chars, keep caption under 300 before hashtags)",
        },
        image_url: {
          type: "string",
          description: "Publicly accessible URL of the image to post (required for Instagram)",
        },
        dry_run: {
          type: "boolean",
          description: "If true, validates but does not actually post",
          default: false,
        },
      },
      required: ["caption", "image_url"],
    },
  },
  {
    name: "get_page_insights",
    description:
      "Fetch engagement metrics (reach, impressions, reactions) for the Facebook Page's recent posts. " +
      "Useful for weekly reporting and CEO briefing.",
    inputSchema: {
      type: "object",
      properties: {
        limit: {
          type: "integer",
          description: "Number of recent posts to retrieve metrics for (1–25)",
          default: 5,
          minimum: 1,
          maximum: 25,
        },
      },
    },
  },
];

// ── Tool Handlers ─────────────────────────────────────────────────────────────
async function handlePostToFacebookPage(args) {
  const { message, image_url, link, dry_run = false } = args;
  const { token, pageId } = getConfig();

  if (!pageId) {
    throw new Error(
      "META_PAGE_ID not set in .env. Add your Facebook Page ID."
    );
  }

  if (dry_run) {
    writeAuditLog({
      action_type: "post_to_facebook_page",
      target: `[DRY RUN] page ${pageId}`,
      result: "dry_run",
      message_preview: message.substring(0, 80),
    });
    return {
      content: [
        {
          type: "text",
          text: `[DRY RUN] Would post to Facebook Page ${pageId}:\n\n"${message}"${image_url ? `\n\nImage: ${image_url}` : ""}${link ? `\n\nLink: ${link}` : ""}\n\nNo post was made.`,
        },
      ],
    };
  }

  let postId;
  let postUrl;

  if (image_url) {
    // Post with photo
    const data = await graphPost(`${pageId}/photos`, {
      caption: message,
      url: image_url,
      access_token: token,
    });
    postId = data.post_id || data.id;
  } else {
    // Text-only (+ optional link)
    const params = { message, access_token: token };
    if (link) params.link = link;
    const data = await graphPost(`${pageId}/feed`, params);
    postId = data.id;
  }

  postUrl = `https://www.facebook.com/${postId}`;

  writeAuditLog({
    action_type: "post_to_facebook_page",
    target: postId,
    result: "success",
    post_url: postUrl,
  });

  return {
    content: [
      {
        type: "text",
        text: `Facebook post published!\n\nPost ID: ${postId}\nURL: ${postUrl}\n\nContent:\n"${message}"`,
      },
    ],
  };
}

async function handlePostToInstagram(args) {
  const { caption, image_url, dry_run = false } = args;
  const { token, igAccountId } = getConfig();

  if (!igAccountId) {
    throw new Error(
      "META_INSTAGRAM_ACCOUNT_ID not set in .env. Add your Instagram Business Account ID."
    );
  }

  if (dry_run) {
    writeAuditLog({
      action_type: "post_to_instagram",
      target: `[DRY RUN] ig_account ${igAccountId}`,
      result: "dry_run",
      caption_preview: caption.substring(0, 80),
      image_url,
    });
    return {
      content: [
        {
          type: "text",
          text: `[DRY RUN] Would post to Instagram account ${igAccountId}:\n\nImage: ${image_url}\n\nCaption:\n"${caption}"\n\nNo post was made.`,
        },
      ],
    };
  }

  // Step 1: Create media container
  const container = await graphPost(`${igAccountId}/media`, {
    image_url,
    caption,
    access_token: token,
  });

  const containerId = container.id;
  if (!containerId) {
    throw new Error("Failed to create Instagram media container");
  }

  // Step 2: Publish the container
  const published = await graphPost(`${igAccountId}/media_publish`, {
    creation_id: containerId,
    access_token: token,
  });

  const mediaId = published.id;
  const postUrl = `https://www.instagram.com/p/${mediaId}/`;

  writeAuditLog({
    action_type: "post_to_instagram",
    target: mediaId,
    result: "success",
    post_url: postUrl,
  });

  return {
    content: [
      {
        type: "text",
        text: `Instagram post published!\n\nMedia ID: ${mediaId}\nURL: ${postUrl}\n\nCaption:\n"${caption}"`,
      },
    ],
  };
}

async function handleGetPageInsights(args) {
  const { limit = 5 } = args;
  const { token, pageId } = getConfig();

  if (!pageId) {
    throw new Error("META_PAGE_ID not set in .env.");
  }

  // Get recent posts
  const postsData = await graphGet(`${pageId}/posts`, {
    fields: "id,message,created_time,permalink_url",
    limit: String(limit),
    access_token: token,
  });

  const posts = postsData.data || [];
  if (posts.length === 0) {
    return {
      content: [{ type: "text", text: "No posts found on this Facebook Page." }],
    };
  }

  // Get insights for each post
  const results = [];
  for (const post of posts) {
    try {
      const insights = await graphGet(`${post.id}/insights`, {
        metric: "post_impressions,post_engaged_users,post_reactions_by_type_total",
        access_token: token,
      });
      const metrics = {};
      for (const m of insights.data || []) {
        metrics[m.name] = m.values?.[0]?.value ?? 0;
      }
      results.push({
        id: post.id,
        message: (post.message || "").substring(0, 80) + "...",
        created: post.created_time,
        url: post.permalink_url,
        impressions: metrics["post_impressions"] || 0,
        engaged_users: metrics["post_engaged_users"] || 0,
      });
    } catch {
      results.push({
        id: post.id,
        message: (post.message || "").substring(0, 80),
        created: post.created_time,
        url: post.permalink_url,
        impressions: "N/A",
        engaged_users: "N/A",
      });
    }
  }

  writeAuditLog({
    action_type: "get_page_insights",
    target: `page ${pageId} (${posts.length} posts)`,
    result: "success",
  });

  const table = results
    .map(
      (r) =>
        `[${r.created?.split("T")[0]}] ${r.impressions} impressions, ${r.engaged_users} engaged\n  "${r.message}"\n  ${r.url}`
    )
    .join("\n\n");

  return {
    content: [
      {
        type: "text",
        text: `Facebook Page Insights (last ${results.length} posts):\n\n${table}`,
      },
    ],
  };
}

// ── MCP Server ────────────────────────────────────────────────────────────────
const server = new Server(
  { name: "meta-social-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "post_to_facebook_page":
        return await handlePostToFacebookPage(args);
      case "post_to_instagram":
        return await handlePostToInstagram(args);
      case "get_page_insights":
        return await handleGetPageInsights(args);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    writeAuditLog({
      action_type: name,
      target: "error",
      result: "error",
      error: err.message,
    });
    return {
      content: [{ type: "text", text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[meta-social-mcp] Server running on stdio");
