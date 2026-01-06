# ABOUTME: Measurement and evaluation module for AIO experiments
# ABOUTME: Updates metrics, determines outcomes based on impression changes

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .config import (
    IMPROVEMENT_THRESHOLD,
    WORSENED_THRESHOLD,
    POSITION_CHANGE_THRESHOLD,
    MIN_POST_CHANGE_IMPRESSIONS,
    MIN_DAYS_FOR_EVALUATION,
    MAX_DAYS_FOR_EVALUATION,
)
from . import database as db
from .gsc_client import get_gsc_client


def update_experiment_metrics(experiment: Dict) -> Dict:
    """Update post-change metrics for an AIO experiment"""
    client = get_gsc_client()

    page_url = experiment["page_url"]
    created_at = datetime.fromisoformat(
        experiment["created_at"].replace("Z", "+00:00")
    )

    # Get metrics from day after change to now
    start_date = (created_at + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Make sure we have at least MIN_DAYS_FOR_EVALUATION days
    days_since = (datetime.now() - created_at).days
    if days_since < MIN_DAYS_FOR_EVALUATION:
        return experiment

    metrics = client.get_page_metrics(page_url, start_date, end_date)

    if metrics:
        db.update_experiment_post_metrics(
            experiment_id=experiment["id"],
            post_impressions=metrics["impressions"],
            post_clicks=metrics["clicks"],
            post_ctr=metrics["ctr"],
            post_position=metrics["position"],
            post_start_date=start_date,
            post_end_date=end_date,
        )

        return {
            **experiment,
            "post_impressions": metrics["impressions"],
            "post_clicks": metrics["clicks"],
            "post_ctr": metrics["ctr"],
            "post_position": metrics["position"],
        }

    return experiment


def evaluate_experiment(experiment: Dict) -> Dict:
    """
    Evaluate an AIO experiment and determine outcome.

    For AIO, we primarily measure:
    1. Impression changes (primary metric for visibility)
    2. CTR changes (secondary, structure can affect clicks)
    3. Position stability (confounding factor)
    """

    # Check if we have enough data
    post_impressions = experiment.get("post_impressions", 0)
    if post_impressions < MIN_POST_CHANGE_IMPRESSIONS:
        return {
            "outcome": "inconclusive",
            "reason": f"Insufficient impressions ({post_impressions} < {MIN_POST_CHANGE_IMPRESSIONS})",
        }

    pre_impressions = experiment.get("pre_impressions", 0)
    pre_position = experiment.get("pre_position", 0)
    post_position = experiment.get("post_position", 0)
    pre_ctr = experiment.get("pre_ctr", 0)
    post_ctr = experiment.get("post_ctr", 0)

    # Calculate impression change
    if pre_impressions > 0:
        impression_change_pct = (post_impressions - pre_impressions) / pre_impressions
    else:
        impression_change_pct = 1.0 if post_impressions > 0 else 0

    # Calculate CTR change
    if pre_ctr > 0:
        ctr_change_pct = (post_ctr - pre_ctr) / pre_ctr
    else:
        ctr_change_pct = 1.0 if post_ctr > 0 else 0

    # Position change (negative = improved ranking)
    position_change = post_position - pre_position

    # Determine outcome based on impressions (primary metric for AIO)
    position_confounded = abs(position_change) > POSITION_CHANGE_THRESHOLD

    if impression_change_pct >= IMPROVEMENT_THRESHOLD:
        outcome = "improved"
        if position_confounded and position_change < 0:
            reason = f"Impressions up {impression_change_pct*100:+.1f}% (position also improved by {abs(position_change):.1f})"
        else:
            reason = f"Impressions increased {impression_change_pct*100:+.1f}%"
    elif impression_change_pct <= WORSENED_THRESHOLD:
        outcome = "worsened"
        if position_confounded and position_change > 0:
            reason = f"Impressions down {impression_change_pct*100:.1f}% (position also declined by {position_change:.1f})"
        else:
            reason = f"Impressions declined {impression_change_pct*100:.1f}%"
    else:
        outcome = "no_change"
        reason = f"Impression change {impression_change_pct*100:+.1f}% within noise threshold"

    # Generate outcome notes
    notes = generate_outcome_notes(
        experiment, outcome, impression_change_pct, ctr_change_pct, position_change
    )

    return {
        "outcome": outcome,
        "impression_change_pct": impression_change_pct * 100,
        "ctr_change_pct": ctr_change_pct * 100,
        "position_change": position_change,
        "reason": reason,
        "notes": notes,
        "position_confounded": position_confounded,
    }


def generate_outcome_notes(
    experiment: Dict,
    outcome: str,
    impression_change_pct: float,
    ctr_change_pct: float,
    position_change: float,
) -> str:
    """Generate detailed notes about the experiment outcome"""
    changes = experiment.get("changes_summary", "")

    if outcome == "improved":
        notes = f"✅ Structure optimization worked: {changes}\n"
        notes += f"   Impressions: {impression_change_pct*100:+.1f}%, CTR: {ctr_change_pct*100:+.1f}%"
    elif outcome == "worsened":
        notes = f"❌ Structure changes may have hurt visibility: {changes}\n"
        notes += f"   Impressions: {impression_change_pct*100:.1f}%, CTR: {ctr_change_pct*100:.1f}%"
    else:
        notes = f"➖ Neutral impact: {changes}\n"
        notes += f"   Impressions: {impression_change_pct*100:+.1f}%, CTR: {ctr_change_pct*100:+.1f}%"

    if abs(position_change) > POSITION_CHANGE_THRESHOLD:
        notes += f"\n   ⚠️ Position changed by {position_change:+.1f} (confounding factor)"

    return notes


def update_all_active_experiments() -> List[Dict]:
    """Update metrics for all active AIO experiments"""
    print("Updating metrics for active AIO experiments...")

    experiments = db.get_active_experiments()
    print(f"  Found {len(experiments)} active experiments")

    results = []
    for exp in experiments:
        print(f"  Updating: {exp['page_slug']}...")
        updated = update_experiment_metrics(exp)
        results.append(updated)

    return results


def get_experiments_ready_for_evaluation() -> List[Dict]:
    """Get experiments that have enough data for evaluation"""
    experiments = db.get_active_experiments()

    ready = []
    now = datetime.now()

    for exp in experiments:
        created_at = datetime.fromisoformat(
            exp["created_at"].replace("Z", "+00:00")
        )
        days_since = (now - created_at).days

        # Must be at least MIN_DAYS old
        if days_since < MIN_DAYS_FOR_EVALUATION:
            continue

        # Must have post metrics
        if exp.get("post_impressions") is None:
            continue

        # Must have enough impressions OR be past max wait time
        has_enough_data = exp.get("post_impressions", 0) >= MIN_POST_CHANGE_IMPRESSIONS
        past_deadline = days_since >= MAX_DAYS_FOR_EVALUATION

        if has_enough_data or past_deadline:
            ready.append(exp)

    return ready


def evaluate_ready_experiments() -> List[Dict]:
    """Evaluate experiments that are ready for evaluation"""
    print("Evaluating ready AIO experiments...")

    experiments = get_experiments_ready_for_evaluation()
    print(f"  Found {len(experiments)} experiments ready for evaluation")

    results = []
    for exp in experiments:
        print(f"  Evaluating: {exp['page_slug']}...")

        evaluation = evaluate_experiment(exp)

        # Update the experiment in database
        db.update_experiment_post_metrics(
            experiment_id=exp["id"],
            post_impressions=exp.get("post_impressions"),
            post_clicks=exp.get("post_clicks"),
            post_ctr=exp.get("post_ctr"),
            post_position=exp.get("post_position"),
            post_start_date=exp.get("post_start_date"),
            post_end_date=exp.get("post_end_date"),
            outcome=evaluation["outcome"],
            outcome_notes=evaluation["notes"],
        )

        results.append({**exp, **evaluation})

        print(f"    → {evaluation['outcome']}: {evaluation['reason']}")

    return results


def check_for_significant_changes() -> List[Dict]:
    """Check active experiments for significant changes that need attention"""
    experiments = db.get_active_experiments()

    alerts = []
    for exp in experiments:
        if exp.get("post_impressions") is None:
            continue

        pre_impressions = exp.get("pre_impressions", 0)
        post_impressions = exp.get("post_impressions", 0)

        if pre_impressions > 0:
            change_pct = (post_impressions - pre_impressions) / pre_impressions
        else:
            change_pct = 0

        # Alert on significant decline
        if change_pct < -0.25:  # 25% impression decline
            alerts.append(
                {
                    "type": "decline",
                    "experiment": exp,
                    "change_pct": change_pct * 100,
                    "message": f"⚠️ {exp['page_slug']} impressions down {change_pct*100:.1f}%",
                }
            )

        # Alert on significant improvement
        if change_pct > 0.30:  # 30% improvement
            alerts.append(
                {
                    "type": "success",
                    "experiment": exp,
                    "change_pct": change_pct * 100,
                    "message": f"🎉 {exp['page_slug']} impressions up {change_pct*100:+.1f}%",
                }
            )

    return alerts


def get_experiment_summary() -> Dict:
    """Get summary of all AIO experiments"""
    experiments = db.get_all_experiments()

    active = [e for e in experiments if e.get("status") == "active"]
    completed = [e for e in experiments if e.get("outcome") is not None]

    # Group by outcome
    outcomes = {}
    for exp in completed:
        outcome = exp["outcome"]
        if outcome not in outcomes:
            outcomes[outcome] = {"count": 0, "total_impression_change": 0}
        outcomes[outcome]["count"] += 1

    # Calculate success rate
    total_completed = len(completed)
    improved = outcomes.get("improved", {}).get("count", 0)
    success_rate = (improved / total_completed * 100) if total_completed > 0 else 0

    return {
        "active": len(active),
        "completed": total_completed,
        "outcomes": outcomes,
        "success_rate": success_rate,
    }
