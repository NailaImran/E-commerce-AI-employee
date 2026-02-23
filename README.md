# E-commerce AI Employee

A **Digital Full-Time Employee** that autonomously manages a Shopify store — handling customer emails, processing orders, posting to LinkedIn, and briefing the CEO. Built for the Panaversity Hackathon (Personal AI Employee Challenge 2026).

---

## Architecture

```
Perception → Reasoning → Action
```

| Layer | Technology | Role |
|-------|-----------|------|
| Brain | Claude Code + Skills | Reads vault, decides what to do |
| Memory/GUI | Obsidian Vault | File-based state and review interface |
| Senses | Python Watchers | Monitor Gmail, Orders folder, Approved folder |
| Hands | MCP Servers | Send emails, interact with GitHub |
| Persistence | PM2 | Keeps watchers alive, restarts on crash |

---

## Vault Structure

```
E:/AI_Employee_Vault/
├── Dashboard.md          ← live store metrics
├── Company_Handbook.md   ← rules and tone guidelines
├── Business_Goals.md     ← products and objectives
├── Orders/               ← drop Shopify CSV exports here
├── Inbox/                ← processed order summaries (normal priority)
├── Needs_Action/         ← items requiring Claude's attention
├── Plans/                ← action plans generated per order batch
├── Pending_Approval/     ← drafts waiting for human review (HITL)
├── Approved/             ← human-approved items ready to execute
├── Rejected/             ← declined items (logged, not acted on)
├── Done/                 ← completed items archive
├── Briefings/            ← weekly CEO briefings
├── Logs/                 ← JSON audit trail (YYYY-MM-DD.json)
└── .secrets/             ← OAuth tokens (gitignored)
```

---

## Skills

Skills are Python scripts + metadata that Claude Code can discover and invoke.

| Skill | Trigger | Output |
|-------|---------|--------|
| `order-reader` | CSV dropped in `/Orders/` | Order summary `.md` → `/Inbox/` or `/Needs_Action/` |
| `dashboard-updater` | After order processing | Refreshed `Dashboard.md` with metrics and alerts |
| `email-responder` | `EMAIL_*.md` in `/Needs_Action/` | Draft reply → `/Pending_Approval/` (HITL) |
| `linkedin-poster` | Weekly schedule or manual | Post draft → `/Pending_Approval/` (HITL) |
| `plan-creator` | After order batch processed | Step-by-step `Plan.md` → `/Plans/` |

---

## Watchers

Background Python processes that feed items into the vault.

| Watcher | What it monitors | What it creates |
|---------|-----------------|-----------------|
| `orders_watcher.py` | `E:/AI_Employee_Vault/Orders/` | Trigger `.md` in `/Needs_Action/` |
| `gmail_watcher.py` | Gmail primary inbox (unread) | `EMAIL_*.md` in `/Needs_Action/` |
| `approval_watcher.py` | `/Approved/` folder | Executes approved email sends / posts |
| `orchestrator.py` | All of the above | Starts, supervises, and restarts watchers |

All watchers inherit from `BaseWatcher` (exponential backoff retry, JSON audit logging, configurable poll interval).

### Run with PM2

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

Configured in `.claude/settings.json` — loaded automatically by Claude Code.

| MCP | Type | Tools |
|-----|------|-------|
| `email-mcp` | stdio (Node.js) | `send_email`, `draft_email`, `list_unread`, `search_emails`, `get_email` |
| `github` | HTTP (Copilot) | `create_repository`, `push_files`, `create_pull_request`, `list_commits`, … |

`send_email` only fires after a corresponding approval file exists in `/Approved/` — enforced by CLAUDE.md rules.

---

## HITL Approval Flow

```
Claude writes draft → /Pending_Approval/EMAIL_REPLY_*.md
         ↓
Human reviews in Obsidian
         ↓
Move to /Approved/          Move to /Rejected/
         ↓                          ↓
approval_watcher fires        Logged, no action
         ↓
email-mcp send_email called
         ↓
Action logged to /Logs/YYYY-MM-DD.json
```

---

## Scheduling

Managed by `orchestrator.py` + `Scheduler` class:

| Schedule | Action |
|----------|--------|
| Every day at 20:00 | Run `daily_summary.py` → daily briefing |
| Every Sunday at 20:00 | Generate `Briefings/YYYY-MM-DD_Monday_Briefing.md` |

---

## Setup

### 1. Prerequisites

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client watchdog
node --version   # v18+
npm install      # inside mcp-servers/email-mcp/
```

### 2. Gmail OAuth

```bash
python watchers/setup_gmail_auth.py
# Opens browser → authorize → token saved to E:/AI_Employee_Vault/.secrets/gmail_token.json
```

### 3. LinkedIn Token

Obtain via [LinkedIn OAuth Token Tools](https://www.linkedin.com/developers/tools/oauth).
Save the access token to `E:/AI_Employee_Vault/.secrets/linkedin_token.txt`.

### 4. Environment

Copy `.env.example` to `.env` and fill in credentials:

```
VAULT_PATH=E:/AI_Employee_Vault
GMAIL_TOKEN_PATH=E:/AI_Employee_Vault/.secrets/gmail_token.json
GMAIL_CREDENTIALS_PATH=E:/AI_Employee_Vault/.secrets/credentials.json
LINKEDIN_TOKEN_PATH=E:/AI_Employee_Vault/.secrets/linkedin_token.txt
DRY_RUN=false
MAX_EMAILS_PER_HOUR=10
```

### 5. Start

```bash
PYTHONUTF8=1 python watchers/orchestrator.py
```

---

## Tier Progress

| Tier | Hours | Status | Features |
|------|-------|--------|---------|
| Bronze | 8–12h | ✅ Complete | Vault, orders_watcher, order-reader, dashboard-updater |
| Silver | 20–30h | 🔄 In Progress | Gmail watcher, email-responder, LinkedIn, approval_watcher, MCP server, scheduling |
| Gold | 40h+ | 🔜 Planned | Odoo MCP, WhatsApp watcher, CEO briefing, Ralph Wiggum loop |

---

## Project Structure

```
E:/E-commerce-employee/
├── .claude/
│   ├── settings.json          ← MCP config (email-mcp, github)
│   ├── CLAUDE.md              ← project instructions for Claude
│   └── skills/
│       ├── order-reader/
│       ├── dashboard-updater/
│       ├── email-responder/
│       ├── linkedin-poster/
│       └── plan-creator/
├── mcp-servers/
│   └── email-mcp/             ← Node.js Gmail MCP server
│       ├── index.js
│       └── package.json
├── watchers/
│   ├── base_watcher.py        ← ABC with retry, logging, run loop
│   ├── orchestrator.py        ← master process (start/supervise all watchers)
│   ├── orders_watcher.py
│   ├── gmail_watcher.py
│   ├── approval_watcher.py
│   ├── daily_summary.py
│   └── setup_gmail_auth.py
├── .env                       ← credentials (gitignored)
├── .gitignore
└── README.md
```

---

## Tech Stack

- **Python 3.13+** — watchers and skill scripts
- **Node.js v24+** — email MCP server
- **Claude Code** — AI brain and skill executor
- **Obsidian** — vault GUI and HITL review interface
- **PM2** — process manager
- **Gmail API** — customer email integration
- **LinkedIn API** — social media posting
- **Shopify CSV** — order data source

---

## Security

- `.env` and all token files are gitignored
- OAuth tokens stored outside the repo in `E:/AI_Employee_Vault/.secrets/`
- Email sends require explicit human approval (HITL)
- All actions logged to `/Logs/` in JSON audit format
- `DRY_RUN=true` mode available for safe testing
