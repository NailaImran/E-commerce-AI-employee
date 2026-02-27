# Twitter/X API v2 Setup Guide

## Step 1 — Create a Twitter Developer Account

1. Go to https://developer.twitter.com/
2. Sign in with your Twitter/X account
3. Apply for a developer account (select "Personal use" or "Business")
4. Wait for approval (usually instant for basic tier)

## Step 2 — Create a Project and App

1. In the Developer Portal, click **Projects & Apps → New Project**
2. Give it a name (e.g., "AI Employee Store Bot")
3. Select **Use case**: "Making a bot" or "Building business solutions"
4. Create the project, then create an **App** inside it

## Step 3 — Set App Permissions

Your app needs **Read and Write** permissions to post tweets:
1. Go to **App Settings → User authentication settings**
2. Enable **OAuth 1.0a**
3. Set App permissions to **Read and Write**
4. Add a callback URL (any URL, e.g. `http://localhost`)
5. Save

## Step 4 — Get Your Credentials

From **App Settings → Keys and Tokens**:

| Credential | Where to find |
|---|---|
| API Key (Consumer Key) | Keys and Tokens → API Key and Secret |
| API Secret (Consumer Secret) | Keys and Tokens → API Key and Secret |
| Access Token | Keys and Tokens → Authentication Tokens |
| Access Token Secret | Keys and Tokens → Authentication Tokens |
| Bearer Token | Keys and Tokens → Bearer Token |

**Important**: Generate Access Token with **Read and Write** permissions (not Read-only).

## Step 5 — Add to .env

```env
# ── Twitter/X ──────────────────────────────────────────────────────────────────
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

## Step 6 — Install Python Library

```bash
pip install tweepy
```

## Step 7 — Test the Connection

```bash
python "E:/AI_Employee_Vault/.claude/skills/twitter-poster/scripts/post_to_twitter.py" \
  --text "Test tweet from AI Employee!" \
  --dry-run
```

## API Tier Notes

| Tier | Monthly Cost | Post limit | Notes |
|---|---|---|---|
| Free | $0 | 1,500 tweets/month | Sufficient for this use case |
| Basic | $100/month | 3,000 tweets/month | For higher volume |

For a Shopify store posting 1-2 tweets/week, **Free tier is sufficient**.

## Rate Limits (Free Tier)

- Post tweet: 17 per 24 hours per user
- Read timeline: 1 request per 15 minutes
- Search: 1 request per 15 minutes

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong credentials | Double-check API keys in .env |
| `403 Forbidden` | App lacks Write permission | Re-set app permissions in Dev Portal |
| `429 Too Many Requests` | Rate limit hit | Wait 15 minutes, then retry |
| `duplicate content` | Same tweet posted twice | Change text slightly |
