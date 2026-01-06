# ABOUTME: Notification system for AIO structure optimization
# ABOUTME: Sends monthly reports and alerts via email

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

from .config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    NOTIFICATION_EMAIL,
    MAX_STRUCTURE_SCORE,
)


def send_email(subject: str, body: str, html: bool = False) -> bool:
    """Send email notification"""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, NOTIFICATION_EMAIL]):
        print("  Email not configured, skipping...")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = NOTIFICATION_EMAIL

        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"  Email error: {e}")
        return False


def notify_monthly_review_complete(
    experiments_started: int,
    experiments_completed: int,
    success_rate: float,
    report_path: str
) -> None:
    """Send notification that monthly AIO review is complete"""

    message = f"""📐 AIO Structure Monthly Review Complete

New Experiments: {experiments_started}
Completed Experiments: {experiments_completed}
Success Rate: {success_rate:.1f}%

Report saved to: {report_path}"""

    subject = f"AIO Monthly Review Complete - {experiments_started} new experiments"
    send_email(subject, message)


def notify_weekly_status(
    active_experiments: int,
    alerts: List[dict]
) -> None:
    """Send weekly AIO status notification"""

    if alerts:
        alert_text = "\n".join([f"• {a['message']}" for a in alerts])
        message = f"""📐 AIO Weekly Status

Active Experiments: {active_experiments}

Alerts:
{alert_text}"""
    else:
        message = f"""📐 AIO Weekly Status

Active Experiments: {active_experiments}
No alerts this week."""

    subject = f"AIO Weekly Status - {active_experiments} active experiments"
    send_email(subject, message)


def notify_alert(alert: dict) -> None:
    """Send immediate alert for significant changes"""

    if alert['type'] == 'decline':
        urgency = "HIGH"
    else:
        urgency = "INFO"

    message = f"""AIO Alert ({urgency})

{alert['message']}

Page: {alert['experiment'].get('page_slug', '')}
Change: {alert['change_pct']:+.1f}%"""

    if alert['type'] == 'decline':
        subject = f"⚠️ AIO Decline Alert: {alert['experiment'].get('page_slug', '')}"
        send_email(subject, message)


def send_monthly_report_email(
    experiments_started: List[Dict],
    completed_experiments: List[Dict],
    opportunities: List[Dict],
    success_rate: float,
    report_path: str
) -> bool:
    """Send detailed monthly AIO report email"""

    month_name = datetime.now().strftime('%B %Y')

    # Build HTML email
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #9b59b6; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .summary-stat {{ display: inline-block; margin-right: 30px; }}
        .summary-stat .number {{ font-size: 24px; font-weight: bold; color: #9b59b6; }}
        .summary-stat .label {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #9b59b6; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
        tr:hover {{ background: #f8f9fa; }}
        .improved {{ color: #27ae60; font-weight: bold; }}
        .worsened {{ color: #e74c3c; font-weight: bold; }}
        .no-change {{ color: #95a5a6; }}
        .score {{ font-weight: bold; }}
        .changes {{ font-size: 13px; color: #7f8c8d; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>📐 AIO Structure Report - {month_name}</h1>

    <div class="summary">
        <div class="summary-stat">
            <div class="number">{len(experiments_started)}</div>
            <div class="label">New Optimizations</div>
        </div>
        <div class="summary-stat">
            <div class="number">{len(completed_experiments)}</div>
            <div class="label">Completed</div>
        </div>
        <div class="summary-stat">
            <div class="number">{success_rate:.0f}%</div>
            <div class="label">Success Rate</div>
        </div>
    </div>
"""

    # Completed experiments section
    if completed_experiments:
        improved = [e for e in completed_experiments if e.get('outcome') == 'improved']
        worsened = [e for e in completed_experiments if e.get('outcome') == 'worsened']
        no_change = [e for e in completed_experiments if e.get('outcome') == 'no_change']

        html += """
    <h2>📊 Completed Experiments</h2>
    <table>
        <tr>
            <th>Page</th>
            <th>Changes Made</th>
            <th>Impression Δ</th>
            <th>Result</th>
        </tr>
"""
        for exp in completed_experiments:
            outcome = exp.get('outcome', 'unknown')
            imp_change = exp.get('impression_change_pct', 0)
            outcome_class = outcome.replace('_', '-')

            if imp_change > 0:
                change_class = 'improved'
            elif imp_change < 0:
                change_class = 'worsened'
            else:
                change_class = 'no-change'

            html += f"""
        <tr>
            <td><strong>{exp.get('page_slug', 'N/A')}</strong></td>
            <td class="changes">{exp.get('changes_summary', 'N/A')}</td>
            <td class="{change_class}">{imp_change:+.1f}%</td>
            <td class="{outcome_class}">{outcome.replace('_', ' ').title()}</td>
        </tr>
"""
        html += "</table>"

        html += f"""
    <p>
        <span class="improved">✅ {len(improved)} improved</span> &nbsp;|&nbsp;
        <span class="worsened">❌ {len(worsened)} worsened</span> &nbsp;|&nbsp;
        <span class="no-change">➖ {len(no_change)} no change</span>
    </p>
"""

    # New experiments section
    if experiments_started:
        html += """
    <h2>🚀 New Optimizations Started</h2>
    <table>
        <tr>
            <th>Page</th>
            <th>Changes Made</th>
            <th>Hypothesis</th>
        </tr>
"""
        for exp in experiments_started:
            html += f"""
        <tr>
            <td><strong>{exp.get('page_slug', 'N/A')}</strong></td>
            <td class="changes">{exp.get('changes_summary', 'N/A')}</td>
            <td>{exp.get('hypothesis', 'N/A')[:80]}...</td>
        </tr>
"""
        html += "</table>"

    # Top opportunities section
    if opportunities:
        html += f"""
    <h2>🎯 Top Remaining Opportunities</h2>
    <table>
        <tr>
            <th>Page</th>
            <th>Score</th>
            <th>Impressions</th>
            <th>Missing Elements</th>
        </tr>
"""
        for opp in opportunities[:10]:
            html += f"""
        <tr>
            <td><strong>{opp.get('page_slug', 'N/A')}</strong></td>
            <td class="score">{opp.get('structure_score', 0)}/{MAX_STRUCTURE_SCORE}</td>
            <td>{opp.get('impressions', 0):,}</td>
            <td class="changes">{', '.join(opp.get('missing_elements', [])[:3])}</td>
        </tr>
"""
        html += "</table>"

    html += f"""
    <div class="footer">
        <p>Full report saved to: {report_path}</p>
        <p>Generated automatically by AIO Structure Optimization System</p>
    </div>
</body>
</html>
"""

    subject = f"📐 AIO Report {month_name}: {len(completed_experiments)} completed, {len(experiments_started)} new"
    return send_email(subject, html, html=True)
