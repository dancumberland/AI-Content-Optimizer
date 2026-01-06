#!/usr/bin/env python3
# ABOUTME: Main orchestrator for AIO (AI Overview) structure optimization system
# ABOUTME: Runs monthly reviews, weekly measurements, and automated optimizations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aio_system.config import (
    validate_config,
    OPTIMIZATION_THRESHOLD_SCORE,
    MIN_OPPORTUNITY_SCORE,
    MAX_EXPERIMENTS_PER_MONTH,
    MAX_STRUCTURE_SCORE,
    REPORTS_DIR,
)
from aio_system import database as db
from aio_system.gsc_client import get_gsc_client
from aio_system.analysis import (
    analyze_all_pages,
    get_optimization_opportunities,
    calculate_potential_impact,
    generate_analysis_summary,
)
from aio_system.content_generation import generate_all_elements
from aio_system.implementation import implement_optimization
from aio_system.measurement import (
    update_all_active_experiments,
    evaluate_ready_experiments,
    check_for_significant_changes,
    get_experiment_summary,
)
from aio_system.reporting import (
    generate_monthly_report,
    save_report,
    generate_weekly_status,
    generate_analysis_report,
)
from aio_system.notifications import (
    send_monthly_report_email,
    notify_weekly_status,
    notify_alert,
)


def get_pages_with_impressions() -> list:
    """Fetch pages with impression data from GSC for the last 28 days"""
    client = get_gsc_client()

    end_date = datetime.now() - timedelta(days=3)  # GSC data lag
    start_date = end_date - timedelta(days=28)

    print(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Get all pages
    pages = client.get_all_pages(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
    )

    # Convert to format expected by analysis
    result = []
    for page in pages:
        url = page.get('page', '')
        # Extract slug from URL
        slug = url.replace('https://themeaningmovement.com/', '').rstrip('/')
        if slug and '?' not in slug:  # Skip query string URLs
            result.append({
                'slug': slug,
                'page_url': url,
                'impressions': page.get('impressions', 0),
                'clicks': page.get('clicks', 0),
                'ctr': page.get('ctr', 0),
                'position': page.get('position', 0),
            })

    return result


def run_monthly_review(dry_run: bool = False):
    """Run the full monthly AIO structure review process"""
    print("=" * 60)
    print("AIO STRUCTURE MONTHLY REVIEW")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)
    print()

    if not validate_config():
        print("Configuration validation failed. Exiting.")
        return False

    # Initialize database if needed
    db.init_database()

    # Step 1: Get pages with impression data from GSC
    print("STEP 1: Fetching GSC data...")
    pages_with_impressions = get_pages_with_impressions()
    print(f"  Found {len(pages_with_impressions)} pages with data")
    print()

    # Step 2: Analyze all pages for structure
    print("STEP 2: Analyzing page structures...")
    all_pages = analyze_all_pages(pages_with_impressions)
    print()

    # Step 3: Get opportunities meeting thresholds
    print("STEP 3: Identifying optimization opportunities...")
    print(f"  Thresholds: Score <{OPTIMIZATION_THRESHOLD_SCORE}, Opportunity >={MIN_OPPORTUNITY_SCORE}")
    opportunities = get_optimization_opportunities(all_pages)
    print(f"  Found {len(opportunities)} pages meeting criteria")

    impact = calculate_potential_impact(opportunities)
    print(f"  Total impressions at stake: {impact['total_impressions']:,}")
    print(f"  Average current score: {impact['avg_current_score']}/{MAX_STRUCTURE_SCORE}")
    print()

    # Step 4: Evaluate any completed experiments from previous month
    print("STEP 4: Evaluating completed experiments...")
    completed = evaluate_ready_experiments()
    print(f"  Completed {len(completed)} experiments")
    print()

    # Step 5: Generate content and implement for opportunities
    num_to_optimize = min(len(opportunities), MAX_EXPERIMENTS_PER_MONTH)
    print(f"STEP 5: Optimizing {num_to_optimize} pages...")
    if num_to_optimize == MAX_EXPERIMENTS_PER_MONTH:
        print(f"  Hit safety limit of {MAX_EXPERIMENTS_PER_MONTH}")
    experiments_started = []

    for i, opp in enumerate(opportunities[:num_to_optimize], 1):
        page_url = opp['page_url']
        page_slug = opp['page_slug']

        print(f"\n[{i}/{num_to_optimize}] {page_slug}")
        print(f"  Structure score: {opp['structure_score']}/{MAX_STRUCTURE_SCORE}")
        print(f"  Impressions: {opp['impressions']:,}")
        print(f"  Missing: {', '.join(opp['missing_elements'][:4])}")

        try:
            # Generate content for missing elements
            print(f"  Generating content...")
            generated = generate_all_elements(
                title=opp['title'],
                content=opp.get('content', ''),
                missing_elements=opp['missing_elements'],
            )

            if not generated['generated_elements']:
                print(f"  Skipping: no content generated")
                continue

            hypothesis = f"Adding {', '.join(generated['generated_elements'])} to improve AI citation likelihood"
            print(f"  Generated: {', '.join(generated['generated_elements'])}")

            if dry_run:
                print(f"  [DRY RUN] Would implement changes")
                experiments_started.append({
                    'page_slug': page_slug,
                    'changes': generated['generated_elements'],
                    'hypothesis': hypothesis,
                })
            else:
                # Implement the optimization
                experiment_id = implement_optimization(
                    page_url=page_url,
                    page_slug=page_slug,
                    wp_post_id=opp['wp_post_id'],
                    definition_block=generated.get('definition_block'),
                    faq_schema=generated.get('faq_schema'),
                    hypothesis=hypothesis,
                    pre_impressions=opp['impressions'],
                    pre_structure_score=opp['structure_score'],
                )

                if experiment_id:
                    experiments_started.append({
                        'id': experiment_id,
                        'page_slug': page_slug,
                        'changes_summary': ', '.join(generated['generated_elements']),
                        'hypothesis': hypothesis,
                    })

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print()

    # Step 6: Check for alerts
    print("STEP 6: Checking for alerts...")
    alerts = check_for_significant_changes()
    if alerts:
        print(f"  Found {len(alerts)} alerts")
        for alert in alerts:
            print(f"    {alert['message']}")
    else:
        print("  No alerts")
    print()

    # Step 7: Generate report
    print("STEP 7: Generating report...")
    report_content = generate_monthly_report(
        opportunities=opportunities,
        experiments_started=experiments_started,
        completed_experiments=completed,
        alerts=alerts,
    )

    if not dry_run:
        report_path = save_report(report_content)
        print(f"  Report saved to: {report_path}")
    else:
        report_path = "[DRY RUN - not saved]"
        print("  [DRY RUN] Report not saved")

    # Print report preview
    print()
    print("=" * 60)
    print("REPORT PREVIEW")
    print("=" * 60)
    print(report_content[:2000])
    if len(report_content) > 2000:
        print("... [truncated]")
    print()

    # Step 8: Send email notification
    print("STEP 8: Sending email notification...")
    if not dry_run:
        # Calculate success rate from completed experiments
        if completed:
            success_count = len([e for e in completed if e.get('outcome') == 'improved'])
            success_rate = (success_count / len(completed)) * 100
        else:
            success_rate = 0.0

        email_sent = send_monthly_report_email(
            experiments_started=experiments_started,
            completed_experiments=completed,
            opportunities=opportunities,
            success_rate=success_rate,
            report_path=str(report_path),
        )
        if email_sent:
            print("  Email sent successfully")
        else:
            print("  Email not sent (check SMTP configuration)")
    else:
        print("  [DRY RUN] Email not sent")
    print()

    # Summary
    print("=" * 60)
    print("MONTHLY REVIEW COMPLETE")
    print("=" * 60)
    print(f"  Pages analyzed: {len(all_pages)}")
    print(f"  Opportunities found: {len(opportunities)}")
    print(f"  Experiments started: {len(experiments_started)}")
    print(f"  Experiments completed: {len(completed)}")
    print(f"  Report: {report_path}")
    print()

    return True


def run_weekly_measurement(dry_run: bool = False):
    """Run weekly measurement update"""
    print("=" * 60)
    print("AIO WEEKLY MEASUREMENT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()

    # Initialize database if needed
    db.init_database()

    # Update all active experiments
    print("Updating active experiment metrics...")
    active = update_all_active_experiments()
    print(f"  Updated {len(active)} experiments")
    print()

    # Evaluate any ready experiments
    print("Evaluating ready experiments...")
    completed = evaluate_ready_experiments()
    print(f"  Completed {len(completed)} experiments")
    print()

    # Check for alerts
    print("Checking for significant changes...")
    alerts = check_for_significant_changes()
    if alerts:
        print(f"  Found {len(alerts)} alerts:")
        for alert in alerts:
            print(f"    {alert['message']}")
    else:
        print("  No alerts")
    print()

    # Generate status
    status = generate_weekly_status(active, alerts)

    print("=" * 60)
    print("STATUS")
    print("=" * 60)
    print(status)
    print()

    # Send email notifications
    if not dry_run:
        print("Sending notifications...")
        # Send weekly status email
        notify_weekly_status(len(active), alerts)
        print("  Weekly status email sent")

        # Send individual alerts for significant declines
        for alert in alerts:
            notify_alert(alert)
        if alerts:
            print(f"  Sent {len([a for a in alerts if a.get('type') == 'decline'])} decline alerts")
    else:
        print("[DRY RUN] Notifications not sent")
    print()

    print("Weekly measurement complete.")
    return True


def show_status():
    """Show current AIO system status"""
    print("=" * 60)
    print("AIO SYSTEM STATUS")
    print("=" * 60)
    print()

    # Initialize database if needed
    db.init_database()

    summary = get_experiment_summary()

    print(f"Active Experiments: {summary.get('active', 0)}")
    print(f"Total Completed: {summary.get('completed', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    print()

    outcomes = summary.get('outcomes', {})
    if outcomes:
        print("Outcomes breakdown:")
        for outcome, data in outcomes.items():
            count = data.get('count', data) if isinstance(data, dict) else data
            print(f"  {outcome}: {count}")
    print()

    # Show active experiments
    active = db.get_active_experiments()
    if active:
        print("Active Experiments:")
        for exp in active[:10]:
            created = datetime.fromisoformat(exp['created_at'].replace('Z', '+00:00'))
            days = (datetime.now() - created).days
            print(f"  {exp['page_slug']} ({days} days)")
        if len(active) > 10:
            print(f"  ... and {len(active) - 10} more")
    print()

    # Show element type performance
    perf = db.get_experiments_by_change_type()
    if perf:
        print("Element Type Performance:")
        for p in perf:
            print(f"  {p['element_name']}: {p['success_rate']:.0f}% success ({p['total_experiments']} exp)")
    print()

    # Show successful patterns
    patterns = db.get_successful_patterns()
    if patterns:
        print("Successful Patterns (>50% success rate):")
        for p in patterns[:5]:
            print(f"  - {p['changes_summary']} ({p['count']} experiments)")
    print()


def run_analysis_only():
    """Run structure analysis without making changes"""
    print("=" * 60)
    print("AIO STRUCTURE ANALYSIS")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()

    if not validate_config():
        print("Configuration validation failed. Exiting.")
        return False

    # Initialize database if needed
    db.init_database()

    # Get pages with impression data
    print("Fetching GSC data...")
    pages_with_impressions = get_pages_with_impressions()
    print(f"  Found {len(pages_with_impressions)} pages")
    print()

    # Analyze all pages
    print("Analyzing page structures...")
    all_pages = analyze_all_pages(pages_with_impressions)
    print()

    # Generate analysis summary
    opportunities = get_optimization_opportunities(all_pages)
    summary = generate_analysis_summary(opportunities)

    print("=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print(summary)
    print()

    # Generate report
    summary_stats = {
        'total_pages': len(all_pages),
        'avg_score': sum(p['structure_score'] for p in all_pages) / len(all_pages) if all_pages else 0,
        'needs_optimization': len([p for p in all_pages if p['optimization_needed']]),
    }
    report = generate_analysis_report(all_pages, summary_stats)

    # Save report
    report_path = REPORTS_DIR / f"aio_analysis_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Analysis report saved to: {report_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description='AIO Structure Optimization System')
    parser.add_argument('mode', choices=['monthly', 'weekly', 'status', 'analyze'],
                       help='Operation mode')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without making changes')

    args = parser.parse_args()

    if args.mode == 'monthly':
        run_monthly_review(dry_run=args.dry_run)
    elif args.mode == 'weekly':
        run_weekly_measurement(dry_run=args.dry_run)
    elif args.mode == 'status':
        show_status()
    elif args.mode == 'analyze':
        run_analysis_only()


if __name__ == '__main__':
    main()
