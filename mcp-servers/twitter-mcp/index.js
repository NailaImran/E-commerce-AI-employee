/**
 * Twitter/X MCP Server — E-commerce AI Employee (Gold Tier)
 *
 * Exposes Twitter API v2 capabilities as MCP tools:
 *   - post_tweet        Post a tweet (text ≤280 chars)
 *   - get_home_timeline Fetch recent tweets from authenticated user's timeline
 *   - search_recent_tweets Search recent public tweets by keyword/hashtag
 *
 * Config (from environment / .env):
 *   TWITTER_API_KEY              OAuth 1.0a consumer key
 *   TWITTER_API_SECRET           OAuth 1.0a consumer secret
 *   TWITTER_ACCESS_TOKEN         OAuth 1.0a access token (for posting)
 *   TWITTER_ACCESS_TOKEN_SECRET  OAuth 1.0a access token secret
 *   TWITTER_BEARER_TOKEN         Bearer token (for read-only search)
 *   VAULT_PATH                   E:/AI_Employee_Vault (for audit logging)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { TwitterApi } from "twitter-api-v2";
import fs from "fs";
import path from "path";

// ── Config ────────────────────────────────────────────────────────────────────
const VAULT_PATH = process.env.VAULT_PATH || "E:/AI_Employee_Vault";
const LOGS_PATH = path.join(VAULT_PATH, "Logs");

// ── Auth ──────────────────────────────────────────────────────────────────────
function getTwitterClient() {
  const apiKey = process.env.TWITTER_API_KEY;
  const apiSecret = process.env.TWITTER_API_SECRET;
  const accessToken = process.env.TWITTER_ACCESS_TOKEN;
  const accessTokenSecret = process.env.TWITTER_ACCESS_TOKEN_SECRET;
  const bearerToken = process.env.TWITTER_BEARER_TOKEN;

  if (!apiKey || !apiSecret || !accessToken || !accessTokenSecret) {
    throw new Error(
      "Twitter credentials not configured. Set TWITTER_API_KEY, TWITTER_API_SECRET, " +
        "TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET in .env"
    );
  }

  return new TwitterApi({
    appKey: apiKey,
    appSecret: apiSecret,
    accessToken: accessToken,
    accessSecret: accessTokenSecret,
  });
}

function getReadOnlyClient() {
  const bearerToken = process.env.TWITTER_BEARER_TOKEN;
  if (!bearerToken) {
    throw new Error(
      "TWITTER_BEARER_TOKEN not configured. Set it in .env for read-only operations."
    );
  }
  return new TwitterApi(bearerToken);
}

// ── Audit Logging ─────────────────────────────────────────────────────────────
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
      actor: "twitter-mcp",
      ...entry,
    });
    fs.writeFileSync(logFile, JSON.stringify(existing, null, 2), "utf8");
  } catch (err) {
    console.error("[twitter-mcp] Audit log error:", err.message);
  }
}

// ── Tool Definitions ──────────────────────────────────────────────────────────
const TOOLS = [
  {
    name: "post_tweet",
    description:
      "Post a tweet to Twitter/X. Text must be ≤280 characters. " +
      "Always ensure a human has approved the tweet via the HITL workflow before calling this.",
    inputSchema: {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "Tweet text (max 280 characters)",
          maxLength: 280,
        },
        reply_to_tweet_id: {
          type: "string",
          description: "Optional: Tweet ID to reply to",
        },
        dry_run: {
          type: "boolean",
          description: "If true, validates but does not actually post",
          default: false,
        },
      },
      required: ["text"],
    },
  },
  {
    name: "get_home_timeline",
    description:
      "Fetch recent tweets from the authenticated user's home timeline. " +
      "Useful for monitoring brand mentions and customer engagement.",
    inputSchema: {
      type: "object",
      properties: {
        max_results: {
          type: "integer",
          description: "Number of tweets to return (1-100)",
          default: 10,
          minimum: 1,
          maximum: 100,
        },
      },
    },
  },
  {
    name: "search_recent_tweets",
    description:
      "Search recent public tweets (last 7 days) by keyword, hashtag, or phrase. " +
      "Useful for tracking brand mentions, competitors, or trending topics.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "Search query. Supports Twitter query syntax: keywords, #hashtags, @mentions, -exclusions",
        },
        max_results: {
          type: "integer",
          description: "Number of results to return (10-100)",
          default: 20,
          minimum: 10,
          maximum: 100,
        },
      },
      required: ["query"],
    },
  },
];

// ── Tool Handlers ─────────────────────────────────────────────────────────────
async function handlePostTweet(args) {
  const { text, reply_to_tweet_id, dry_run = false } = args;

  if (!text || text.trim().length === 0) {
    throw new Error("Tweet text cannot be empty");
  }
  if (text.length > 280) {
    throw new Error(
      `Tweet text is ${text.length} characters (max 280). Please shorten it.`
    );
  }

  if (dry_run) {
    writeAuditLog({
      action_type: "post_tweet",
      target: `[DRY RUN] tweet (${text.length} chars)`,
      result: "dry_run",
      text_preview: text.substring(0, 50),
    });
    return {
      content: [
        {
          type: "text",
          text: `[DRY RUN] Would post tweet (${text.length}/280 chars):\n\n"${text}"\n\nNo tweet was posted.`,
        },
      ],
    };
  }

  const client = getTwitterClient();
  const tweetParams = { text };
  if (reply_to_tweet_id) {
    tweetParams.reply = { in_reply_to_tweet_id: reply_to_tweet_id };
  }

  const response = await client.v2.tweet(tweetParams);
  const tweetId = response.data.id;
  const tweetUrl = `https://x.com/i/web/status/${tweetId}`;

  writeAuditLog({
    action_type: "post_tweet",
    target: tweetId,
    result: "success",
    tweet_url: tweetUrl,
    char_count: text.length,
  });

  return {
    content: [
      {
        type: "text",
        text: `Tweet posted successfully!\n\nID: ${tweetId}\nURL: ${tweetUrl}\nChars: ${text.length}/280\n\nContent:\n"${text}"`,
      },
    ],
  };
}

async function handleGetHomeTimeline(args) {
  const { max_results = 10 } = args;
  const client = getReadOnlyClient();

  // Get authenticated user ID first
  const me = await client.v2.me();
  const userId = me.data.id;

  const timeline = await client.v2.homeTimeline({
    max_results,
    "tweet.fields": ["created_at", "author_id", "public_metrics"],
    expansions: ["author_id"],
    "user.fields": ["name", "username"],
  });

  const tweets = timeline.data?.data || [];
  const users = {};
  for (const u of timeline.data?.includes?.users || []) {
    users[u.id] = u;
  }

  const formatted = tweets.map((t) => {
    const author = users[t.author_id];
    const authorStr = author ? `@${author.username}` : t.author_id;
    return `[${t.created_at}] ${authorStr}: ${t.text}`;
  });

  writeAuditLog({
    action_type: "get_home_timeline",
    target: `timeline (${tweets.length} tweets)`,
    result: "success",
  });

  return {
    content: [
      {
        type: "text",
        text:
          tweets.length > 0
            ? `Home timeline (${tweets.length} tweets):\n\n${formatted.join("\n\n")}`
            : "No tweets in home timeline.",
      },
    ],
  };
}

async function handleSearchRecentTweets(args) {
  const { query, max_results = 20 } = args;
  const client = getReadOnlyClient();

  const results = await client.v2.search(query, {
    max_results,
    "tweet.fields": ["created_at", "author_id", "public_metrics"],
    expansions: ["author_id"],
    "user.fields": ["name", "username"],
  });

  const tweets = results.data?.data || [];
  const users = {};
  for (const u of results.data?.includes?.users || []) {
    users[u.id] = u;
  }

  const formatted = tweets.map((t) => {
    const author = users[t.author_id];
    const authorStr = author ? `@${author.username}` : t.author_id;
    const metrics = t.public_metrics
      ? ` [♻${t.public_metrics.retweet_count} ♥${t.public_metrics.like_count}]`
      : "";
    return `[${t.created_at}] ${authorStr}${metrics}: ${t.text}`;
  });

  writeAuditLog({
    action_type: "search_recent_tweets",
    target: query,
    result: "success",
    result_count: tweets.length,
  });

  return {
    content: [
      {
        type: "text",
        text:
          tweets.length > 0
            ? `Search results for "${query}" (${tweets.length} tweets):\n\n${formatted.join("\n\n")}`
            : `No recent tweets found for query: "${query}"`,
      },
    ],
  };
}

// ── MCP Server ────────────────────────────────────────────────────────────────
const server = new Server(
  { name: "twitter-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "post_tweet":
        return await handlePostTweet(args);
      case "get_home_timeline":
        return await handleGetHomeTimeline(args);
      case "search_recent_tweets":
        return await handleSearchRecentTweets(args);
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
console.error("[twitter-mcp] Server running on stdio");
