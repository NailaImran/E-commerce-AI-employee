---
name: linkedin-poster
description: Generates and publishes weekly LinkedIn product highlight posts to drive Shopify store sales. Use when asked to "create a LinkedIn post", "post a product highlight", "generate social media content", or on the weekly LinkedIn schedule. Reads Business_Goals.md and vault order data to write engaging posts, then publishes via LinkedIn API using the stored access token. Saves post drafts to /Plans/ for review before publishing if HITL mode is enabled.
---

# LinkedIn Poster

## Overview

Generates compelling weekly product highlight posts from store data and publishes them to LinkedIn via API, or saves to /Plans/ for human review first.

## Workflow

1. Read `Business_Goals.md` for active products and goals
2. Read recent order data from `/Inbox/` and `/Done/` for social proof
3. Generate a post using the template below
4. **If HITL mode**: write draft to `/Pending_Approval/LINKEDIN_<date>.md`
5. **If auto mode**: run `scripts/post_to_linkedin.py` to publish directly
6. Log post to `/Logs/linkedin_posts.md`

## Post Generation Guidelines

Write posts that:
- Open with a hook (question, bold claim, or surprising stat)
- Highlight one specific product or category
- Include 1-2 lines of social proof (e.g. "Sold 40+ units this month")
- End with a clear CTA (link to store, DM for orders, etc.)
- Use 3-5 relevant hashtags at the end
- Stay under 700 characters for best reach
- Avoid generic corporate language — write like a real store owner

## Post Template

```
[Hook — 1 sentence]

[Product highlight — 2-3 sentences about the product, its benefits, why customers love it]

[Social proof — orders/reviews this week]

[CTA — one clear action]

#hashtag1 #hashtag2 #hashtag3 #ecommerce #shopify
```

## Example Output

```
Tired of overpriced basics? Our Cotton Crew Tees are changing that.

Premium 100% cotton, available in 8 colours, and built to last
through hundreds of washes. No fading, no shrinking — just comfort
that works.

30+ sold this week alone. Customers keep coming back for more.

Shop now: [your store link] or DM us to place an order today.

#fashion #casualwear #shoplocal #ecommerce #qualitybasics
```

## Publishing via API

```bash
python "E:/E-commerce-employee/skills/linkedin-poster/scripts/post_to_linkedin.py" \
  --post "Your post text here" \
  --token-file "E:/AI_Employee_Vault/.secrets/linkedin_token.txt"
```

## Token Setup

Store LinkedIn access token at `E:/AI_Employee_Vault/.secrets/linkedin_token.txt`
(this folder is gitignored and never synced).

See `references/linkedin_api.md` for getting your Person URN and token scopes needed.

## HITL Approval File

Write to `/Pending_Approval/LINKEDIN_<date>.md`:

```markdown
---
type: linkedin_post_approval
action: post_to_linkedin
created: 2026-02-21T10:00:00
status: pending
---

## Draft Post

[post content here]

---
Move to /Approved/ to publish. Move to /Rejected/ to discard.
```
