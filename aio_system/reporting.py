# ABOUTME: Report generation for AIO optimization system
# ABOUTME: Creates markdown reports for structure analysis and experiment results

from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .config import REPORTS_DIR, STRUCTURE_ELEMENTS, MAX_STRUCTURE_SCORE
from . import database as db
from .measurement import get_experiment_summary


def generate_monthly_report(
    opportunities: List[Dict],
    experiments_started: List[Dict],
    completed_experiments: List[Dict],
    alerts: List[Dict],
) -> str:
    """Generate comprehensive monthly AIO report"""

    review_date = datetime.now().strftime("%Y-%m-%d")
    review_month = datetime.now().strftime("%B %Y")

    # Get experiment summary
    summary = get_experiment_summary()

    lines = [
        f"# AIO Structure Optimization Review - {review_month}",
        "",
        f"**Generated:** {review_date}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    # Summary stats
    lines.extend(
        [
            f"- **Pages Analyzed:** {len(opportunities)}",
            f"- **New Experiments Started:** {len(experiments_started)}",
            f"- **Experiments Completed:** {len(completed_experiments)}",
            f"- **Active Experiments:** {summary.get('active', 0)}",
            f"- **Overall Success Rate:** {summary.get('success_rate', 0):.1f}%",
            "",
        ]
    )

    # Alerts section
    if alerts:
        lines.extend(
            [
                "## ⚠️ Alerts",
                "",
            ]
        )
        for alert in alerts:
            lines.append(f"- {alert['message']}")
        lines.append("")

    # Completed experiments section
    if completed_experiments:
        lines.extend(
            [
                "## Completed Experiments",
                "",
                "| Page | Changes | Impression Δ | Outcome |",
                "|------|---------|--------------|---------|",
            ]
        )

        for exp in completed_experiments:
            changes = (
                (exp.get("changes_summary", "")[:30] + "...")
                if len(exp.get("changes_summary", "")) > 30
                else exp.get("changes_summary", "")
            )
            change = f"{exp.get('impression_change_pct', 0):+.1f}%"
            outcome_emoji = {
                "improved": "✅",
                "worsened": "❌",
                "no_change": "➖",
            }.get(exp.get("outcome", ""), "❓")

            lines.append(
                f"| {exp.get('page_slug', '')} | {changes} | {change} | {outcome_emoji} {exp.get('outcome', '')} |"
            )

        lines.append("")

        # Learnings from completed experiments
        lines.extend(
            [
                "### Key Learnings",
                "",
            ]
        )
        for exp in completed_experiments:
            if exp.get("outcome_notes"):
                lines.append(f"- {exp['outcome_notes']}")
        lines.append("")

    # New experiments section
    if experiments_started:
        lines.extend(
            [
                "## New Experiments Started",
                "",
                "| Page | Changes | Hypothesis |",
                "|------|---------|------------|",
            ]
        )

        for exp in experiments_started:
            changes = (
                (exp.get("changes_summary", "")[:40] + "...")
                if len(exp.get("changes_summary", "")) > 40
                else exp.get("changes_summary", "")
            )
            hypothesis = (
                (exp.get("hypothesis", "")[:50] + "...")
                if len(exp.get("hypothesis", "")) > 50
                else exp.get("hypothesis", "")
            )

            lines.append(
                f"| {exp.get('page_slug', '')} | {changes} | {hypothesis} |"
            )

        lines.append("")

    # Opportunities section
    if opportunities:
        lines.extend(
            [
                "## Top Opportunities Identified",
                "",
            ]
        )

        for i, opp in enumerate(opportunities[:10], 1):
            lines.extend(
                [
                    f"### {i}. {opp.get('page_slug', '')}",
                    "",
                    f"- **Structure Score:** {opp.get('structure_score', 0)}/{MAX_STRUCTURE_SCORE}",
                    f"- **Impressions:** {opp.get('impressions', 0):,}",
                    f"- **Opportunity Score:** {opp.get('opportunity_score', 0):,}",
                    f"- **Missing:** {', '.join(opp.get('missing_elements', [])[:4])}",
                    "",
                ]
            )

    # Structure element performance
    lines.extend(
        [
            "## Structure Elements Reference",
            "",
            "| Element | Points | Description |",
            "|---------|--------|-------------|",
        ]
    )

    for elem_name, elem_config in STRUCTURE_ELEMENTS.items():
        lines.append(
            f"| {elem_name} | {elem_config['points']} | {elem_config['description']} |"
        )

    lines.append("")

    # Footer
    lines.extend(
        [
            "---",
            "",
            "*Report generated automatically by AIO Structure Optimization System*",
            "*Next review scheduled: 1st of next month*",
        ]
    )

    return "\n".join(lines)


def save_report(report_content: str) -> str:
    """Save report to file"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"aio_review_{datetime.now().strftime('%Y%m')}.md"
    filepath = REPORTS_DIR / filename

    with open(filepath, "w") as f:
        f.write(report_content)

    return str(filepath)


def generate_weekly_status(
    active_experiments: List[Dict], alerts: List[Dict]
) -> str:
    """Generate weekly status update"""

    lines = [
        f"# AIO Weekly Status - {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]

    # Alerts first
    if alerts:
        lines.extend(
            [
                "## Alerts",
                "",
            ]
        )
        for alert in alerts:
            lines.append(f"- {alert['message']}")
        lines.append("")

    # Active experiments
    lines.extend(
        [
            "## Active Experiments",
            "",
            f"**Total Active:** {len(active_experiments)}",
            "",
        ]
    )

    if active_experiments:
        lines.extend(
            [
                "| Page | Days Active | Pre Imp | Post Imp | Change |",
                "|------|-------------|---------|----------|--------|",
            ]
        )

        for exp in active_experiments:
            pre = exp.get("pre_impressions", 0)
            post = exp.get("post_impressions")
            if post is not None:
                post_str = f"{post:,}"
                if pre > 0:
                    change = ((post - pre) / pre) * 100
                    change_str = f"{change:+.1f}%"
                else:
                    change_str = "-"
            else:
                post_str = "pending"
                change_str = "-"

            # Calculate days active
            created = datetime.fromisoformat(
                exp["created_at"].replace("Z", "+00:00")
            )
            days_active = (datetime.now() - created).days

            lines.append(
                f"| {exp.get('page_slug', '')} | {days_active} | "
                f"{pre:,} | {post_str} | {change_str} |"
            )

        lines.append("")

    # Summary
    summary = get_experiment_summary()
    lines.extend(
        [
            "## Overall Stats",
            "",
            f"- **Total Completed:** {summary.get('completed', 0)}",
            f"- **Success Rate:** {summary.get('success_rate', 0):.1f}%",
            "",
        ]
    )

    return "\n".join(lines)


def generate_analysis_report(
    pages: List[Dict], summary_stats: Dict = None
) -> str:
    """Generate structure analysis report"""

    lines = [
        f"# AIO Structure Analysis - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Overview",
        "",
    ]

    if summary_stats:
        lines.extend(
            [
                f"- **Pages Analyzed:** {summary_stats.get('total_pages', len(pages))}",
                f"- **Average Score:** {summary_stats.get('avg_score', 0):.1f}/{MAX_STRUCTURE_SCORE}",
                f"- **Pages Needing Optimization:** {summary_stats.get('needs_optimization', 0)}",
                "",
            ]
        )

    # Score distribution
    score_counts = {}
    for page in pages:
        score = page.get("structure_score", 0)
        score_counts[score] = score_counts.get(score, 0) + 1

    lines.extend(
        [
            "## Score Distribution",
            "",
            "| Score | Count |",
            "|-------|-------|",
        ]
    )

    for score in sorted(score_counts.keys()):
        lines.append(f"| {score}/{MAX_STRUCTURE_SCORE} | {score_counts[score]} |")

    lines.append("")

    # Missing elements analysis
    missing_counts = {}
    for page in pages:
        for elem in page.get("missing_elements", []):
            missing_counts[elem] = missing_counts.get(elem, 0) + 1

    lines.extend(
        [
            "## Most Common Missing Elements",
            "",
            "| Element | Missing From | Description |",
            "|---------|--------------|-------------|",
        ]
    )

    for elem, count in sorted(
        missing_counts.items(), key=lambda x: x[1], reverse=True
    ):
        desc = STRUCTURE_ELEMENTS.get(elem, {}).get("description", "")
        lines.append(f"| {elem} | {count} pages | {desc} |")

    lines.append("")

    return "\n".join(lines)
