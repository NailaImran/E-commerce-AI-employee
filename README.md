# E-commerce AI Employee — Gold Tier

A **Digital Full-Time Employee** that autonomously manages a Shopify e-commerce store:
monitors customer emails, processes orders, posts to LinkedIn / Twitter / Facebook / Instagram,
reflects on its own performance, and briefs the CEO weekly — all with human-in-the-loop
approval before any external action is taken.

Built for the **Panaversity Personal AI Employee Hackathon 2026** — Gold Tier submission.

**Owner:** Naila Yaqoob

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PERCEPTION LAYER                            │
│  Gmail Watcher · Orders Watcher · Approval Watcher · Scheduler  │
└────────────────────────────┬────────────────────────────────────┘
                             │  writes to vault
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MEMORY / GUI LAYER                          │
│          Obsidian Vault  (file-based state + HITL review)       │
│  /Needs_Action/  →  /Pending_Approval/  →  /Approved/           │
└────────────────────────────┬────────────────────────────────────┘
                             │  read by
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REASONING LAYER                             │
│   Claude Code + Skills  (classify, draft, plan, reflect)        │
│   Skills: order-reader · email-responder · linkedin-poster      │
│           twitter-poster · meta-poster · plan-creator           │
│           dashboard-updater                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │  after human approval
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ACTION LAYER                               │
│   MCP Servers: email-mcp · twitter-mcp · meta-social-mcp       │
│   Python Scripts: post_to_linkedin · send_approved_email        │
│                   post_to_twitter · post_to_facebook            │
│                   post_to_instagram                             │
└─────────────────────────────────────────────────────────────────┘
                             │  logs every action to
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REFLECTION LAYER  (Gold)                     │
│   Ralph Wiggum Loop — reads 7 days of /Logs/, scores health,   │
│   surfaces bottlenecks, writes REFLECTION_YYYY-MM-DD.md        │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Role |
|-------|-----------|------|
| Brain | Claude Code + Skills | Reads vault, decides what to do |
| Memory / GUI | Obsidian Vault | File-based state and HITL review interface |
| Senses | Python Watchers | Monitor Gmail, Orders folder, Approved folder |
| Hands | MCP Servers + Scripts | Send emails, post to social platforms |
| Reflection | Ralph Wiggum Loop | Self-evaluates logs, scores system health |
| Persistence | PM2 | Keeps watchers alive, auto-restarts on crash |

---

## Vault Structure

```
E:/AI_Employee_Vault/
├── Dashboard.md              ← live store metrics (auto-refreshed)
├── Company_Handbook.md       ← tone rules and response guidelines
├── Business_Goals.md         ← products, objectives, target audience
│
├── Orders/                   ← drop Shopify CSV exports here
├── Inbox/                    ← processed order summaries (normal priority)
├── Needs_Action/             ← items requiring Claude's attention
│   ├── EMAIL_*.md            ← customer emails (from Gmail Watcher)
│   └── ORDERS_*.md           ← new order batches (from Orders Watcher)
│
├── Plans/                    ← action plans per order batch
├── Pending_Approval/         ← drafts waiting for human review (HITL)
│   ├── EMAIL_REPLY_*.md
│   ├── LINKEDIN_*.md
│   ├── TWITTER_*.md
│   ├── FACEBOOK_*.md
│   └── INSTAGRAM_*.md
│
├── Approved/                 ← human-approved items ready to execute
├── Rejected/                 ← declined items (logged, not acted on)
├── Done/                     ← completed items archive
│
├── Briefings/                ← generated briefing documents
│   ├── YYYY-MM-DD_Monday_Briefing.md   ← weekly CEO briefing
│   ├── YYYY-MM-DD_Daily_Summary.md     ← daily operations summary
│   └── REFLECTION_YYYY-MM-DD.md       ← Ralph Wiggum self-reflection
│
├── Logs/                     ← JSON audit trail
│   ├── YYYY-MM-DD.json       ← daily action log
│   ├── twitter_posts.md      ← Twitter post history
│   └── meta_posts.md         ← Facebook / Instagram post history
│
├── mcp-servers/
│   ├── email-mcp/            ← Gmail MCP server (Node.js)
│   ├── twitter-mcp/          ← Twitter/X MCP server (Node.js)
│   └── meta-social-mcp/      ← Facebook + Instagram MCP server (Node.js)
│
├── watchers/
│   ├── orchestrator.py       ← master process (starts + supervises all)
│   ├── base_watcher.py       ← ABC: retry logic, audit logging, poll loop
│   ├── gmail_watcher.py      ← polls Gmail, writes EMAIL_*.md
│   ├── orders_watcher.py     ← monitors /Orders/, triggers processing
│   ├── approval_watcher.py   ← watchdog on /Approved/, fires scripts
│   ├── daily_summary.py      ← generates daily operations briefing
│   └── ralph_wiggum_reflection.py  ← self-reflection engine
│
└── .secrets/                 ← OAuth tokens (gitignored)
    ├── gmail_token.json
    ├── credentials.json
    └── linkedin_token.txt
```

---

## Skills

Skills are Claude Code–discoverable agents: a `SKILL.md` descriptor + Python script.
Claude reads the skill's metadata, loads context from the vault, and calls the script.

| Skill | Trigger | Output |
|-------|---------|--------|
| `order-reader` | CSV in `/Orders/` | Order summary → `/Inbox/` or `/Needs_Action/` |
| `dashboard-updater` | After order processing | Refreshed `Dashboard.md` with KPIs and alerts |
| `email-responder` | `EMAIL_*.md` in `/Needs_Action/` | Draft reply → `/Pending_Approval/` (HITL) |
| `linkedin-poster` | Weekly schedule or manual trigger | Post draft → `/Pending_Approval/` (HITL) |
| `twitter-poster` | Weekly schedule or manual trigger | Tweet draft (≤280 chars) → `/Pending_Approval/` (HITL) |
| `meta-poster` | Weekly schedule or manual trigger | Facebook/Instagram draft → `/Pending_Approval/` (HITL) |
| `plan-creator` | After order batch processed | Step-by-step `Plan.md` → `/Plans/` |

---

## Watchers

Background Python processes that feed items into the vault autonomously.

| Watcher | Monitors | Creates |
|---------|---------|---------|
| `orders_watcher.py` | `/Orders/` for new CSVs | Trigger `.md` in `/Needs_Action/` |
| `gmail_watcher.py` | Gmail unread (filtered) | `EMAIL_*.md` in `/Needs_Action/` |
| `approval_watcher.py` | `/Approved/` folder | Calls email/social posting scripts |
| `daily_summary.py` | Triggered at 20:00 daily | `Briefings/YYYY-MM-DD_Daily_Summary.md` |
| `ralph_wiggum_reflection.py` | Triggered at 21:00 daily | `Briefings/REFLECTION_YYYY-MM-DD.md` |
| `orchestrator.py` | All of the above | Starts, supervises, and restarts watchers |

All watchers inherit from `BaseWatcher`: exponential backoff retry, JSON audit logging,
configurable poll interval, and crash reporting.

### Run with PM2 (recommended)

```bash
pm2 start watchers/orchestrator.py --interpreter python3 --name orchestrator
pm2 save
pm2 startup
```

### Or run directly

```bash
# Windows — PYTHONUTF8=1 required for Unicode on cp1252 systems
PYTHONUTF8=1 python watchers/orchestrator.py
PYTHONUTF8=1 python watchers/orchestrator.py --dry-run   # test mode
```

---

## MCP Servers

Three Node.js MCP servers registered in `.claude/settings.json`.
Claude Code loads them automatically on startup.

| MCP Server | Tools | Platform |
|-----------|-------|----------|
| `email-mcp` | `send_email`, `draft_email`, `list_unread`, `search_emails`, `get_email` | Gmail API |
| `twitter-mcp` | `post_tweet`, `get_home_timeline`, `search_recent_tweets` | Twitter API v2 |
| `meta-social-mcp` | `post_to_facebook_page`, `post_to_instagram`, `get_page_insights` | Meta Graph API v21.0 |

All MCP tools have HITL guards enforced in `CLAUDE.md` — no external post fires without an
approval file in `/Approved/` first.

---

## HITL Approval Flow

```
Claude drafts content
        │
        ▼
/Pending_Approval/TWITTER_*.md
/Pending_Approval/FACEBOOK_*.md
/Pending_Approval/INSTAGRAM_*.md
/Pending_Approval/EMAIL_REPLY_*.md
/Pending_Approval/LINKEDIN_*.md
        │
        ▼ Human reviews in Obsidian
        │
   ┌────┴────┐
   │         │
   ▼         ▼
/Approved/  /Rejected/
   │              │
   ▼              ▼
approval_watcher  Logged only,
fires script      no action taken
   │
   ▼
Action executed + logged to /Logs/YYYY-MM-DD.json
```

**approval_watcher.py routing table:**

| File prefix | Script called |
|-------------|---------------|
| `EMAIL_REPLY_*.md` | `email-responder/scripts/send_approved_email.py` |
| `LINKEDIN_*.md` | `linkedin-poster/scripts/post_to_linkedin.py` |
| `TWITTER_*.md` | `twitter-poster/scripts/post_to_twitter.py` |
| `FACEBOOK_*.md` | `meta-poster/scripts/post_to_facebook.py` |
| `INSTAGRAM_*.md` | `meta-poster/scripts/post_to_instagram.py` |

---

## Scheduling

Managed by `orchestrator.py` Scheduler class (checks every 60s):

| Time | Day | Action |
|------|-----|--------|
| 20:00 | Daily | `daily_summary.py` → `/Briefings/YYYY-MM-DD_Daily_Summary.md` |
| 21:00 | Daily | `ralph_wiggum_reflection.py` → `/Briefings/REFLECTION_YYYY-MM-DD.md` |
| 20:00 | Sunday | Weekly CEO briefing → `/Briefings/YYYY-MM-DD_Monday_Briefing.md` |

---

## Ralph Wiggum Self-Reflection Loop (Gold Tier)

Every evening at 21:00, `ralph_wiggum_reflection.py` reads the last 7 days of
`/Logs/YYYY-MM-DD.json` and produces a scored health report.

**Analyses:**
- **Action success rate** — success vs error per `action_type`; flags >20% error rate
- **Watcher stability** — counts `watcher_crashed` events; flags >2 crashes
- **Email filter effectiveness** — ratio of blocked vs passed emails
- **Approval lag** — files in `/Pending_Approval/` older than 24h
- **Stuck inputs** — files in `/Needs_Action/` older than 48h
- **Daily throughput** — actions per day, trend over the window
- **Dead days** — days with zero log entries (orchestrator wasn't running)

**Health scores:** `GREEN` (all clear) · `YELLOW` (1–2 minor issues) · `RED` (crashes/high errors)

**Sample output header:**
```markdown
---
type: reflection
period: 7 days
score: GREEN
---
# Ralph Wiggum Self-Reflection — Feb 23, 2026
*"I'm a helper!" — Overall system health: GREEN*

## Performance Scorecard
| Area              | Score  | Detail                        |
|-------------------|--------|-------------------------------|
| Watcher stability | GREEN  | 0 crashes in 7 days           |
| Email filter      | GREEN  | 27 blocked, 0 false negatives |
| Approval lag      | YELLOW | 2 items > 24h pending         |
| Action success    | GREEN  | 98% success rate              |
```

---

## Setup

### 1. Prerequisites

```bash
# Python dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client watchdog tweepy requests

# Node.js (v18+) — install MCP server dependencies
cd mcp-servers/email-mcp && npm install
cd mcp-servers/twitter-mcp && npm install
cd mcp-servers/meta-social-mcp && npm install
```

### 2. Environment Variables

Copy `.env` template and fill in credentials:

```env
# Vault
VAULT_PATH=E:/AI_Employee_Vault

# Gmail OAuth
GMAIL_TOKEN_PATH=E:/AI_Employee_Vault/.secrets/gmail_token.json
GMAIL_CREDENTIALS_PATH=E:/AI_Employee_Vault/.secrets/credentials.json

# LinkedIn
LINKEDIN_TOKEN_PATH=E:/AI_Employee_Vault/.secrets/linkedin_token.txt

# Twitter / X  (from developer.twitter.com)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# Meta (Facebook + Instagram)  (from developers.facebook.com)
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_PAGE_ACCESS_TOKEN=your_never_expiring_page_access_token
META_PAGE_ID=your_facebook_page_id
META_INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id

# Safety
DRY_RUN=false
MAX_EMAILS_PER_HOUR=10
REFLECTION_DAYS_BACK=7
```

### 3. Gmail OAuth

```bash
python watchers/setup_gmail_auth.py
# Opens browser → authorize → token saved to .secrets/gmail_token.json
```

### 4. LinkedIn Token

Go to [LinkedIn OAuth Token Tools](https://www.linkedin.com/developers/tools/oauth),
generate an access token with `w_member_social` scope, save to `.secrets/linkedin_token.txt`.

### 5. Twitter Credentials

1. Go to [developer.twitter.com](https://developer.twitter.com/)
2. Create an app with **Read and Write** permissions
3. Generate API Key, API Secret, Access Token, Access Token Secret, Bearer Token
4. Add to `.env` (see above)
5. Verify: `python .claude/skills/twitter-poster/scripts/post_to_twitter.py --dry-run`

### 6. Meta Credentials

Follow `.claude/skills/meta-poster/references/meta_api.md` step-by-step:
1. Create a Meta Developer App at [developers.facebook.com](https://developers.facebook.com/)
2. Add Facebook Login + Instagram Graph API products
3. Generate a never-expiring Page Access Token
4. Get your Facebook Page ID and Instagram Business Account ID
5. Add all five values to `.env`
6. Verify: `python .claude/skills/meta-poster/scripts/post_to_facebook.py --dry-run`

### 7. Start

```bash
# Development / test
PYTHONUTF8=1 python watchers/orchestrator.py --dry-run

# Production
PYTHONUTF8=1 python watchers/orchestrator.py

# With PM2 (recommended for production)
pm2 start watchers/orchestrator.py --interpreter python3 --name orchestrator
pm2 save && pm2 startup
```

---

## Tier Progress

| Tier | Hours | Status | Key Features |
|------|-------|--------|-------------|
| Bronze | 8–12h | ✅ Complete | Vault structure, orders_watcher, order-reader, dashboard-updater, plan-creator |
| Silver | 20–30h | ✅ Complete | Gmail watcher, email-responder, LinkedIn poster, approval_watcher, email-mcp, orchestrator |
| Gold | 40h+ | ✅ Complete | Twitter/X integration, Facebook + Instagram integration, Ralph Wiggum self-reflection loop, daily briefings, multi-platform HITL approval, cross-domain audit logging |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Brain | Claude Code (claude-sonnet-4-6) |
| Skills | Python 3.13 scripts + SKILL.md descriptors |
| MCP Servers | Node.js v24 + `@modelcontextprotocol/sdk` |
| Vault / GUI | Obsidian (markdown files) |
| Process Manager | PM2 |
| Email | Gmail API v1 (OAuth 2.0) |
| Social — LinkedIn | LinkedIn Marketing API v2 |
| Social — Twitter/X | Twitter API v2 (OAuth 1.0a) via `tweepy` |
| Social — Facebook | Meta Graph API v21.0 via `requests` |
| Social — Instagram | Meta Graph API v21.0 (two-step container + publish) |
| Orders | Shopify CSV export |

---

## Security Model

- `.env`, `.secrets/`, and all token files are gitignored
- OAuth tokens stored outside repo scope in `.secrets/`
- **All external actions require explicit human approval** — enforced in `CLAUDE.md`
- Approval watcher only fires after file exists in `/Approved/`
- `DRY_RUN=true` mode available — logs what would happen without executing
- All actions written to `/Logs/YYYY-MM-DD.json` (immutable audit trail)
- Email rate-limited: `MAX_EMAILS_PER_HOUR=10`
- Ralph Wiggum loop catches anomalies and surfaces them daily

---

## API Reference

| API | Setup Guide |
|-----|------------|
| Gmail | `watchers/setup_gmail_auth.py` |
| LinkedIn | [LinkedIn OAuth Tools](https://www.linkedin.com/developers/tools/oauth) |
| Twitter/X | `.claude/skills/twitter-poster/references/twitter_api.md` |
| Meta (Facebook + Instagram) | `.claude/skills/meta-poster/references/meta_api.md` |

---

*Built with Claude Code · Panaversity Hackathon 2026*
