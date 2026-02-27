# Meta Graph API Setup Guide (Facebook + Instagram)

## Overview

Both Facebook Pages and Instagram Business accounts use the same **Meta Graph API**.
You need one **Page Access Token** that covers both platforms.

---

## Step 1 — Create a Meta Developer App

1. Go to https://developers.facebook.com/
2. Click **My Apps → Create App**
3. Select **Business** as the app type
4. Name it (e.g., "AI Employee Store Bot")
5. Connect to your **Business Portfolio** (or create one)

---

## Step 2 — Add Products to Your App

In your app dashboard, add:
- **Facebook Login** — for generating user/page tokens
- **Instagram Graph API** — for Instagram Business posting

---

## Step 3 — Get a Page Access Token

### Option A: Graph API Explorer (easiest for testing)
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app
3. Click **Generate Access Token**
4. Add permissions:
   - `pages_manage_posts` — post to Facebook Pages
   - `pages_read_engagement` — read insights
   - `instagram_basic` — read Instagram
   - `instagram_content_publish` — post to Instagram
5. Click **Generate Token**
6. Copy the token — this is a **short-lived token** (1 hour)

### Option B: Long-lived Page Access Token (recommended for production)
1. Get a short-lived **User Access Token** from Graph Explorer
2. Exchange for long-lived (60 days):
```
GET https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={META_APP_ID}
  &client_secret={META_APP_SECRET}
  &fb_exchange_token={SHORT_LIVED_TOKEN}
```
3. Get Page Access Token from the long-lived user token:
```
GET https://graph.facebook.com/v21.0/me/accounts
  ?access_token={LONG_LIVED_USER_TOKEN}
```
4. Find your page in the response — copy its `access_token` (this is a **never-expiring** Page Access Token)

---

## Step 4 — Get Your Page ID and Instagram Account ID

### Facebook Page ID
```
GET https://graph.facebook.com/v21.0/me/accounts?access_token={PAGE_TOKEN}
```
Find your page in the `data` array and copy the `id`.

Or: Go to your Facebook Page → **About** → scroll down to find Page ID.

### Instagram Business Account ID
Your Instagram account must be:
1. An **Instagram Business** or **Creator** account
2. **Linked to your Facebook Page** (in Instagram app: Settings → Account → Switch to Professional → Link Facebook Page)

Then get the ID:
```
GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={PAGE_TOKEN}
```
Copy the `id` from `instagram_business_account`.

---

## Step 5 — Add to .env

```env
# ── Meta (Facebook + Instagram) ──────────────────────────────────────────────
META_APP_ID=your_app_id_here
META_APP_SECRET=your_app_secret_here
META_PAGE_ACCESS_TOKEN=your_never_expiring_page_access_token_here
META_PAGE_ID=your_facebook_page_id_here
META_INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id_here
```

---

## Step 6 — Install Python Library

```bash
pip install requests
```

---

## Step 7 — Test the Connection

```bash
# Facebook dry-run:
python "E:/AI_Employee_Vault/.claude/skills/meta-poster/scripts/post_to_facebook.py" \
  --message "Test post from AI Employee!" \
  --dry-run

# Instagram dry-run:
python "E:/AI_Employee_Vault/.claude/skills/meta-poster/scripts/post_to_instagram.py" \
  --caption "Test caption #test" \
  --image-url "https://via.placeholder.com/1080x1080.jpg" \
  --dry-run
```

---

## Instagram Requirements

| Requirement | Detail |
|---|---|
| Account type | Must be Business or Creator (not Personal) |
| Linked to Facebook Page | Required — set in Instagram app settings |
| Image URL | Must be publicly accessible HTTPS URL |
| Image format | JPEG recommended, min 320px, max 1440px wide |
| Caption | Max 2,200 characters, max 30 hashtags |

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `OAuthException (#200)` | Missing permission | Re-generate token with correct permissions |
| `Invalid OAuth access token` | Token expired | Generate a new never-expiring Page token |
| `Instagram account not linked` | IG not connected to Page | Link in Instagram app → Settings → Account |
| `Media URL is not accessible` | Image URL is private/expired | Use a public HTTPS image URL |
| `Duplicate post` | Same content posted twice | Change caption slightly |
