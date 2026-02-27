---
name: meta-poster
description: Generates and publishes product highlight posts to Facebook Pages and Instagram Business accounts to drive Shopify store sales. Use when asked to "post on Facebook", "post on Instagram", "create a Facebook post", "create an Instagram post", or on the weekly social media schedule. Reads Business_Goals.md and vault order data to write engaging posts, then publishes via Meta Graph API. Always saves drafts to /Pending_Approval/ for human review before publishing.
---

# Meta Social Poster (Facebook + Instagram)

## Overview

Generates product highlight posts for **Facebook Pages** and **Instagram Business accounts**
via the Meta Graph API v21.0. Both platforms are covered by the same Page Access Token.

| Platform | Format | Tone | Length |
|---|---|---|---|
| Facebook | Text + optional image | Conversational, story-driven | 100–500 chars |
| Instagram | Caption + image/reel | Visual, hashtag-rich | 138–300 chars |
| LinkedIn | Text-only | Professional | 500–700 chars |
| Twitter/X | Text-only | Punchy, direct | ≤280 chars |

## Workflow

1. Read `Business_Goals.md` for active products and goals
2. Read recent order data from `/Inbox/` and `/Done/` for social proof
3. Generate post(s) using the templates below
4. **Always HITL** — write draft to `/Pending_Approval/FACEBOOK_<date>.md` and/or `/Pending_Approval/INSTAGRAM_<date>.md`
5. After approval: `approval_watcher` calls the appropriate post script
6. Log posts to `/Logs/meta_posts.md`

## Facebook Post Template

```
[Hook — 1 sentence that stops the scroll]

[Product story — 2-3 sentences. Benefits, what makes it special, why customers love it.]

[Social proof — "X orders this week" or customer quote]

[CTA — link to store or "Comment SHOP to order"]

#hashtag1 #hashtag2 #shoplocal
```

**Facebook tips:**
- Post natively (no links in caption — put link in first comment or CTA button)
- Tag the product if you have a Facebook Shop linked
- 100-500 chars sweet spot for reach
- Emojis work well on Facebook

## Instagram Caption Template

```
[Hook — bold visual claim, 1 sentence]
[2-3 sentences product description]
[Social proof line]
[CTA — "Link in bio" or "DM to order"]

#hashtag1 #hashtag2 #hashtag3 #fashion #shoplocal #ecommerce #shopify #newcollection
```

**Instagram tips:**
- Always needs an image (script posts text-only if no image URL given, but image performs better)
- 5-10 hashtags sweet spot (avoid 30-tag spam)
- Keep caption under 300 chars before hashtags
- Put hashtags after line break

## Example Facebook Post

```
Our Cotton Crew Tees are flying off the shelves this week.

Premium 100% cotton, 8 colours, built to last through hundreds of washes.
No fading, no shrinking — just everyday comfort that actually holds up.

30+ sold this week. Customers keep reordering.

Shop here 👉 [your store link]

#fashion #cottonbasics #shoplocal
```

## Example Instagram Caption

```
Quality basics shouldn't cost a fortune. 🧵

Our Cotton Crew Tees — 100% cotton, 8 colours, preshrunk.
30+ sold this week and the reviews speak for themselves.

DM us to order or tap the link in bio 👆

#fashion #casualwear #cottonbasics #shoplocal #ecommerce #shopify #ootd #basics
```

## Publishing via Scripts

```bash
# Post to Facebook Page:
python "E:/AI_Employee_Vault/.claude/skills/meta-poster/scripts/post_to_facebook.py" \
  --file "E:/AI_Employee_Vault/Approved/FACEBOOK_2026-02-23.md" \
  --vault "E:/AI_Employee_Vault"

# Post to Instagram:
python "E:/AI_Employee_Vault/.claude/skills/meta-poster/scripts/post_to_instagram.py" \
  --file "E:/AI_Employee_Vault/Approved/INSTAGRAM_2026-02-23.md" \
  --vault "E:/AI_Employee_Vault"
```

## Credentials Setup

Add to `.env`:
```
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_PAGE_ACCESS_TOKEN=your_page_access_token
META_PAGE_ID=your_facebook_page_id
META_INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id
```

See `references/meta_api.md` for step-by-step setup.

## HITL Approval Files

**Facebook** — `/Pending_Approval/FACEBOOK_<date>.md`:
```markdown
---
type: facebook_post_approval
action: post_to_facebook
created: 2026-02-23T10:00:00
status: pending
image_url: (optional)
---

## Draft Post

[post text here]

---
Move to /Approved/ to publish. Move to /Rejected/ to discard.
```

**Instagram** — `/Pending_Approval/INSTAGRAM_<date>.md`:
```markdown
---
type: instagram_post_approval
action: post_to_instagram
created: 2026-02-23T10:00:00
status: pending
image_url: https://your-image-url.com/image.jpg
---

## Draft Caption

[caption here]

---
Move to /Approved/ to publish. Move to /Rejected/ to discard.
```

> Note: Instagram requires a public image URL. If no image is available, the post will be
> skipped with a warning. Use a product photo URL from your Shopify store.
