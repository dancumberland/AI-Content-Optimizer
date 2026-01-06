# CTR Optimization System

Automated system for identifying underperforming pages and optimizing titles for better click-through rates.

## Overview

This system:
1. **Monthly**: Pulls GSC data, identifies CTR gaps, generates title ideas with AI, automatically implements best options
2. **Weekly**: Updates metrics for active experiments, evaluates completed experiments, sends alerts
3. **Continuously**: Learns from results to improve future recommendations

## Quick Start

```bash
# Check system status
python ctr_orchestrator.py status

# Run monthly review (dry run first!)
python ctr_orchestrator.py monthly --dry-run

# Run monthly review (live)
python ctr_orchestrator.py monthly

# Run weekly measurement
python ctr_orchestrator.py weekly
```

## Architecture

```
ctr_system/
├── config.py          # Configuration and thresholds
├── database.py        # SQLite operations
├── gsc_client.py      # Google Search Console API
├── analysis.py        # Gap analysis and benchmarks
├── ideation.py        # Claude-powered title generation
├── implementation.py  # RankMath API updates
├── measurement.py     # Experiment evaluation
├── reporting.py       # Report generation
├── notifications.py   # Slack/email alerts
└── schema.sql         # Database schema

ctr_orchestrator.py    # Main entry point
```

## Configuration

Required environment variables in `.env`:

```bash
# WordPress (already configured)
WP_SITE_URL=https://themeaningmovement.com
WP_USER=your_username
Wordpress_Rest_API_KEY=your_app_password

# Optional: Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_password
NOTIFICATION_EMAIL=dan@example.com
```

## Claude Integration

The system uses the **Claude CLI** for title ideation, which means:
- **No API key required** - uses your existing Claude Code subscription
- Claude Code must be installed: `npm install -g @anthropic-ai/claude-code`
- You must be logged in to Claude Code

## Automation Setup

### Option 1: GitHub Actions (Recommended)

Runs automatically in the cloud using your Claude Max subscription.

See **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)** for full setup instructions.

Quick summary:
1. Run `claude /install-github-app` and `claude setup-token`
2. Add secrets to GitHub: `CLAUDE_CODE_OAUTH_TOKEN`, `ENV_FILE`, `GSC_OAUTH_JSON`, `GSC_TOKEN_JSON`
3. Push the workflow file (already created in `.github/workflows/ctr-monthly.yml`)

The workflow runs automatically on the 1st of each month, or manually via GitHub Actions tab.

### Option 2: System Cron

```bash
# Edit crontab
crontab -e

# Add these lines:
# Monthly review - 1st of each month at 6am
0 6 1 * * cd /path/to/TheMeaningMovement_Content && /usr/bin/python3 Operations/Tools/ctr_orchestrator.py monthly >> /var/log/ctr_monthly.log 2>&1

# Weekly measurement - Every Monday at 6am
0 6 * * 1 cd /path/to/TheMeaningMovement_Content && /usr/bin/python3 Operations/Tools/ctr_orchestrator.py weekly >> /var/log/ctr_weekly.log 2>&1
```

### Option 3: Launchd (macOS)

Create `~/Library/LaunchAgents/com.tmm.ctr-monthly.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tmm.ctr-monthly</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/dancumberland/Documents/Work/AI_Content_Systems/TheMeaningMovement_Content/Operations/Tools/ctr_orchestrator.py</string>
        <string>monthly</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/dancumberland/Documents/Work/AI_Content_Systems/TheMeaningMovement_Content</string>
    <key>StandardOutPath</key>
    <string>/tmp/ctr_monthly.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ctr_monthly_error.log</string>
</dict>
</plist>
```

Load with: `launchctl load ~/Library/LaunchAgents/com.tmm.ctr-monthly.plist`

### Option 4: Claude Code SDK (Advanced)

For more sophisticated automation with Claude Code SDK:

```python
# Example: ctr_agent.py
from claude_code_sdk import Agent

agent = Agent(
    system_prompt="You are a CTR optimization agent...",
    tools=[...]
)

# Run monthly review with intelligent decision making
result = agent.run("Run the monthly CTR review and handle any issues")
```

## How It Works

### Monthly Review Process

1. **Benchmark Calculation**: Calculates site-specific CTR expectations by position
2. **Gap Analysis**: Identifies pages with CTR below expected for their position
3. **Time Filtering**: Only considers data AFTER the last change to each page
4. **Opportunity Ranking**: Prioritizes by impact potential (impressions × CTR gap)
5. **Title Generation**: Uses Claude to generate 10 title variations per page
6. **Auto-Selection**: Picks best title based on site learnings
7. **Implementation**: Updates via RankMath API
8. **Reporting**: Generates comprehensive markdown report

### Evaluation Criteria

- **Improved**: CTR increased ≥5%
- **Worsened**: CTR decreased ≥5%
- **No Change**: CTR change within ±5%
- **Inconclusive**: Insufficient data (< 50 impressions post-change)

### Idea Types

The system generates titles using 10 psychological triggers:

1. **Specificity**: Numbers, dates, details
2. **Curiosity**: Intrigue without clickbait
3. **Power Words**: Emotional triggers
4. **Question**: Mirror search queries
5. **How-To**: Instructional framing
6. **List**: Numbers first
7. **Brackets**: Context additions [2025]
8. **Social Proof**: Popularity signals
9. **Benefit-First**: Lead with value
10. **Problem-Solution**: Address pain points

## Database Tables

- `optimization_experiments`: Track each title experiment
- `title_ideas`: Store all generated ideas (prevents repeats)
- `ctr_benchmarks`: Position-adjusted CTR expectations
- `monthly_reviews`: Review session records
- `ctr_learnings`: Extracted insights from experiments
- `gsc_page_metrics`: GSC data snapshots

## Reports

Reports are saved to: `Operations/CTR_Reports/`

Format: `ctr_review_YYYYMM.md`

## Thresholds (Configurable)

```python
MIN_IMPRESSIONS_FOR_ANALYSIS = 100    # Minimum impressions to consider
MIN_DAYS_BETWEEN_CHANGES = 21         # Days before re-optimizing
MIN_DAYS_FOR_EVALUATION = 21          # Days before evaluating
MAX_PAGES_PER_MONTH = 20              # Experiments per month
MAX_TITLE_LENGTH = 60                 # Max title characters
```

## Troubleshooting

### GSC Authentication Failed
```bash
# Delete token and re-authenticate
rm ClientData/credentials/gsc_token.json
python ctr_orchestrator.py status
```

### RankMath API Error
Ensure Rank Math API Manager plugin is installed and activated.

### No Opportunities Found
- Check `MIN_IMPRESSIONS_FOR_ANALYSIS` threshold
- Verify GSC data is being pulled correctly
- Check `MIN_DAYS_BETWEEN_CHANGES` for recently updated pages

## Safety Features

- **Dry Run Mode**: Test without making changes
- **Time Guards**: Minimum 21 days between changes per page
- **Experiment Tracking**: Full audit trail of all changes
- **Revert Capability**: Can revert experiments to original titles
- **Alert System**: Notifications for significant CTR drops
