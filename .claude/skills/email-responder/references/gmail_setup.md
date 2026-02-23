# Gmail API Setup Guide

Follow these steps once to enable Gmail API access for the watcher and email sender.

## Step 1: Create a Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click **New Project** (top left dropdown)
3. Name it: `ecommerce-ai-employee`
4. Click **Create**

## Step 2: Enable the Gmail API

1. In your project, go to **APIs & Services > Library**
2. Search for **Gmail API**
3. Click it, then click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Choose **External** (for personal Gmail)
3. Fill in:
   - App name: `E-commerce AI Employee`
   - User support email: your Gmail
   - Developer contact: your Gmail
4. Click **Save and Continue** through all steps
5. On **Test users** page: add your own Gmail address
6. Click **Save and Continue**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Name: `AI Employee Desktop Client`
5. Click **Create**
6. Click **Download JSON**
7. Rename the downloaded file to `credentials.json`
8. Move it to: `E:/AI_Employee_Vault/.secrets/credentials.json`

## Step 5: First-Time Authentication

Run the Gmail watcher once — it will open a browser window:

```bash
python E:/E-commerce-employee/watchers/gmail_watcher.py --vault E:/AI_Employee_Vault
```

1. A browser window opens — sign in with your Gmail
2. Click **Allow** on the consent screen
3. The browser shows "Authentication successful"
4. A `gmail_token.json` is saved to `E:/AI_Employee_Vault/.secrets/`

From now on, the watcher runs without the browser prompt.

## Step 6: Add Send Permission (for approval watcher)

When you first run `send_approved_email.py`, it will request a **gmail.send** scope.
A second token (`gmail_send_token.json`) will be saved automatically.

## Scopes Used

| Script | Scope | Purpose |
|--------|-------|---------|
| gmail_watcher.py | gmail.readonly | Read unread emails |
| send_approved_email.py | gmail.send | Send approved replies |

## Security Notes

- `credentials.json` and `*.json` tokens live only in `.secrets/` — never commit this folder
- Add `.secrets/` to `.gitignore`
- Tokens refresh automatically when expired
- To revoke access: https://myaccount.google.com/permissions

## Troubleshooting

**403 access_denied**: Add your email to Test Users in OAuth consent screen
**Token expired error**: Delete `gmail_token.json` and re-run the watcher
**"App not verified" warning**: Click "Advanced" > "Go to app (unsafe)" — safe for personal use
