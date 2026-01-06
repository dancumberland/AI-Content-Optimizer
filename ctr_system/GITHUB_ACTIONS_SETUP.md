# GitHub Actions Setup for CTR Automation

This guide walks through setting up automated monthly CTR reviews using GitHub Actions with your Claude Max subscription.

## Prerequisites

- Claude Max subscription ($100/month plan)
- GitHub repository for this project
- GSC OAuth credentials already configured locally

## Step 1: Install GitHub App and Generate Token

Run these commands in your terminal:

```bash
# Connect Claude to your GitHub account
claude /install-github-app

# Generate OAuth token for CI/CD
claude setup-token
```

Copy the generated token - you'll need it for the next step.

## Step 2: Configure GitHub Secrets

Go to your repository on GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Create these secrets:

### 1. `CLAUDE_CODE_OAUTH_TOKEN`
Paste the token from Step 1.

### 2. `ENV_FILE`
Copy the contents of your `.env` file (excluding any comments):
```
WP_SITE_URL=https://themeaningmovement.com
WP_ADMIN_URL=https://themeaningmovement.com/wp-admin
WP_USER=dan
WP_PASS=your_password_here
Wordpress_Rest_API_KEY=your_app_password_here
GOOGLE_PAGESPEED_API_KEY=your_key_here

# Email configuration for CTR reports
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL=dan@themeaningmovement.com
```

**Gmail App Password Setup:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (Custom name)"
3. Name it "CTR Reports"
4. Copy the 16-character password
5. Use that as `SMTP_PASSWORD`

### 3. `GSC_OAUTH_JSON`
Copy the contents of `ClientData/credentials/gsc_oauth.json`

### 4. `GSC_TOKEN_JSON`
Copy the contents of `ClientData/credentials/gsc_token.json`

## Step 3: Push the Workflow

```bash
git add .github/workflows/ctr-monthly.yml
git add Operations/Tools/ctr_system/requirements.txt
git commit -m "Add GitHub Actions workflow for CTR automation"
git push
```

## Step 4: Test with Dry Run

1. Go to **Actions** tab in your GitHub repo
2. Click **CTR Monthly Review** workflow
3. Click **Run workflow**
4. Select `dry_run: true`
5. Click **Run workflow** (green button)

Watch the logs to verify everything works.

## Schedule

The workflow runs automatically at **6am UTC on the 1st of each month**.

You can also trigger it manually anytime via the Actions tab.

## Troubleshooting

### "Claude CLI not found"
The workflow installs Claude CLI via npm. If this fails, check the Node.js setup step logs.

### "GSC Authentication Failed"
Your `GSC_TOKEN_JSON` may have expired. Re-authenticate locally:
```bash
rm ClientData/credentials/gsc_token.json
python Operations/Tools/ctr_orchestrator.py status
```
Then update the GitHub secret with the new token.

### "WordPress API Error"
Check that `ENV_FILE` secret has the correct credentials and the application password is still valid.

## Reports

After each run, reports are:
1. Saved to `Operations/CTR_Reports/` and committed
2. Available as downloadable artifacts in the Actions run

## Security Notes

- Never commit credentials to the repository
- GitHub Secrets are encrypted and only exposed to workflow runs
- The OAuth token grants access to your Claude subscription - treat it like a password
