# LinkedIn API Setup Guide

## Getting Your Access Token

### Option A: LinkedIn Developer App (Recommended)

1. Go to https://www.linkedin.com/developers/apps
2. Click **Create App**
3. Fill in:
   - App name: `E-commerce AI Employee`
   - LinkedIn Page: your company page (or create one)
   - App logo: any image
4. Click **Create App**

5. Go to the **Auth** tab:
   - Copy your **Client ID** and **Client Secret**

6. Under **OAuth 2.0 scopes**, request:
   - `w_member_social` — post on your behalf
   - `r_liteprofile` — get your Person URN

7. Go to **Auth** > **OAuth 2.0 tools**:
   - Set redirect URL to `http://localhost:8080`
   - Click **Request access token**
   - Authorise the app
   - Copy the **Access Token**

8. Save the token:
   ```
   E:/AI_Employee_Vault/.secrets/linkedin_token.txt
   ```
   (paste the token, one line, no spaces)

### Token Expiry

LinkedIn access tokens expire after **60 days**. When expired:
1. Go back to LinkedIn Developer App > Auth > OAuth 2.0 tools
2. Request a new token
3. Overwrite the token file

## Getting Your Person URN

The `post_to_linkedin.py` script fetches this automatically via `/v2/userinfo`.
It looks like: `urn:li:person:AbCdEfGhIj1234`

## Required Scopes

| Scope | Used For |
|-------|----------|
| `w_member_social` | Creating UGC posts |
| `r_liteprofile` | Getting Person URN |
| `openid` | Userinfo endpoint |
| `profile` | Userinfo endpoint |

## Posting Limits

- LinkedIn allows ~150 posts per day via API
- Keep posts spaced at least 1 hour apart for best reach
- Optimal posting times: Tuesday–Thursday, 9 AM–12 PM local time

## Troubleshooting

**401 Unauthorized**: Token expired — get a new one
**403 Forbidden**: Scope not approved — check app permissions
**422 Unprocessable Entity**: Post content too long (max 3000 chars for UGC posts)
