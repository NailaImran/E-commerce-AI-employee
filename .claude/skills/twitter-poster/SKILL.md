---
name: twitter-poster
description: Generates and publishes weekly Twitter/X product highlight posts to drive Shopify store sales. Use when asked to "create a tweet", "post on Twitter", "post on X", "generate Twitter content", or on the weekly social media schedule. Reads Business_Goals.md and vault order data to write punchy tweets (≤280 chars), then publishes via Twitter API v2 using the stored bearer token. Saves tweet drafts to /Pending_Approval/ for human review before publishing.
---

# Twitter/X Poster

## Overview

Generates short, punchy product highlight tweets from store data and publishes them to
Twitter/X via API v2, or saves to `/Pending_Approval/` for human review first.

Tweets complement LinkedIn posts — same product, same week, different tone:
- **LinkedIn**: professional, story-driven, 500–700 chars
- **Twitter/X**: direct, punchy, ≤280 chars with 1-2 hashtags

## Workflow

1. Read `Business_Goals.md` for active products and goals
2. Read recent order data from `/Inbox/` and `/Done/` for social proof
3. Generate a tweet using the template below (keep ≤280 characters)
4. **Always HITL**: write draft to `/Pending_Approval/TWITTER_<date>.md`
5. After approval: `approval_watcher` calls `scripts/post_to_twitter.py`
6. Log post to `/Logs/twitter_posts.md`

## Tweet Generation Guidelines

Write tweets that:
- Lead with the strongest hook (product name, bold claim, or number)
- Are **≤280 characters total** (including spaces and hashtags)
- Include 1-2 targeted hashtags max (not keyword soup)
- Have a link or CTA at the end (store link, "DM to order")
- Sound like a real shop owner, not a marketing bot
- Avoid em-dashes, exclamation spam, and corporate filler

## Tweet Template

```
[Hook — product name + bold claim, 1 sentence]
[Benefit/proof — 1 line, keep tight]
[CTA] #hashtag1 #hashtag2
```

**280-char budget breakdown:**
- Hook: ~80 chars
- Benefit: ~60 chars
- CTA + link: ~60 chars
- Hashtags (2): ~30 chars
- Buffer: ~50 chars

## Example Output

```
Cotton Crew Tees — premium basics under $30.
30+ sold this week. 100% cotton, 8 colours, built to last.
Shop now → [store link] #fashion #shoplocal
```

*(~160 chars — leaves room for a Twitter card preview)*

## Publishing via API

```bash
python "E:/AI_Employee_Vault/.claude/skills/twitter-poster/scripts/post_to_twitter.py" \
  --text "Your tweet text here" \
  --vault "E:/AI_Employee_Vault"
```

Or from an approval file:
```bash
python "E:/AI_Employee_Vault/.claude/skills/twitter-poster/scripts/post_to_twitter.py" \
  --file "E:/AI_Employee_Vault/Approved/TWITTER_2026-02-23.md" \
  --vault "E:/AI_Employee_Vault"
```

## Credentials Setup

Store Twitter API v2 credentials in `.env`:
```
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

See `references/twitter_api.md` for getting these credentials.

## HITL Approval File

Write to `/Pending_Approval/TWITTER_<date>.md`:

```markdown
---
type: twitter_post_approval
action: post_to_twitter
created: 2026-02-23T10:00:00
status: pending
char_count: 142
---

## Draft Tweet

[tweet text here — max 280 chars]

---
Move to /Approved/ to publish. Move to /Rejected/ to discard.
```
