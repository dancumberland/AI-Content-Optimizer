# ABOUTME: Structure analysis and opportunity identification for AIO system
# ABOUTME: Scores pages on AI-extractable elements and identifies optimization candidates

import re
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from base64 import b64encode

from .config import (
    STRUCTURE_ELEMENTS,
    MAX_STRUCTURE_SCORE,
    OPTIMIZATION_THRESHOLD_SCORE,
    MIN_OPPORTUNITY_SCORE,
    MIN_IMPRESSIONS_FOR_ANALYSIS,
    MAX_EXPERIMENTS_PER_MONTH,
    WP_SITE_URL,
    WP_USER,
    WP_APP_PASSWORD,
)
from . import database as db


def get_wp_auth_header() -> Dict[str, str]:
    """Get WordPress authentication header"""
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}


def fetch_post_content(slug: str) -> Optional[Dict]:
    """Fetch post content from WordPress REST API"""
    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"slug": slug, "status": "publish"}

    try:
        response = requests.get(url, params=params, headers=get_wp_auth_header())
        response.raise_for_status()
        posts = response.json()

        if posts:
            post = posts[0]
            return {
                "id": post["id"],
                "slug": post["slug"],
                "title": post["title"]["rendered"],
                "content": post["content"]["rendered"],
                "raw_content": post.get("content", {}).get("raw", ""),
            }
    except Exception as e:
        print(f"  Error fetching {slug}: {e}")

    return None


def score_structure(content: str, raw_content: str = "") -> Dict:
    """
    Score page content for AIO-optimized structural elements.
    Returns detailed breakdown of present/missing elements.
    """
    # Combine rendered and raw content for pattern matching
    full_content = content + " " + raw_content

    elements_found = {}
    total_score = 0

    for element_name, element_config in STRUCTURE_ELEMENTS.items():
        pattern = element_config["pattern"]
        points = element_config["points"]

        # Check if pattern exists in content
        if re.search(pattern, full_content, re.IGNORECASE | re.DOTALL):
            elements_found[element_name] = {
                "present": True,
                "points": points,
                "description": element_config["description"]
            }
            total_score += points
        else:
            elements_found[element_name] = {
                "present": False,
                "points": 0,
                "max_points": points,
                "description": element_config["description"]
            }

    return {
        "total_score": total_score,
        "max_score": MAX_STRUCTURE_SCORE,
        "elements": elements_found,
        "missing_elements": [
            name for name, data in elements_found.items()
            if not data["present"]
        ],
        "optimization_needed": total_score < OPTIMIZATION_THRESHOLD_SCORE
    }


def analyze_page(slug: str, impressions: int = 0) -> Optional[Dict]:
    """Analyze a single page for AIO optimization opportunities"""
    post = fetch_post_content(slug)
    if not post:
        return None

    # Score the structure
    structure = score_structure(post["content"], post.get("raw_content", ""))

    # Calculate opportunity score (impressions * improvement potential)
    improvement_potential = MAX_STRUCTURE_SCORE - structure["total_score"]
    opportunity_score = impressions * improvement_potential

    return {
        "page_url": f"{WP_SITE_URL}/{slug}/",
        "page_slug": slug,
        "wp_post_id": post["id"],
        "title": post["title"],
        "impressions": impressions,
        "structure_score": structure["total_score"],
        "max_score": MAX_STRUCTURE_SCORE,
        "elements": structure["elements"],
        "missing_elements": structure["missing_elements"],
        "opportunity_score": opportunity_score,
        "optimization_needed": structure["optimization_needed"],
    }


def analyze_all_pages(pages_with_impressions: List[Dict]) -> List[Dict]:
    """
    Analyze all pages and return structure scores.

    Args:
        pages_with_impressions: List of dicts with 'slug' and 'impressions' keys
    """
    print(f"Analyzing {len(pages_with_impressions)} pages for AIO structure...")

    results = []
    for i, page_data in enumerate(pages_with_impressions):
        slug = page_data.get("slug") or page_data.get("page_slug")
        impressions = page_data.get("impressions", 0)

        if impressions < MIN_IMPRESSIONS_FOR_ANALYSIS:
            continue

        analysis = analyze_page(slug, impressions)
        if analysis:
            # Check eligibility (not recently optimized)
            last_experiment = db.get_last_experiment_for_page(analysis["page_url"])
            if last_experiment:
                days_since = (datetime.now() - datetime.fromisoformat(
                    last_experiment["created_at"].replace("Z", "+00:00")
                )).days
                analysis["days_since_last_experiment"] = days_since
                analysis["eligible"] = days_since >= 30
            else:
                analysis["days_since_last_experiment"] = None
                analysis["eligible"] = True

            results.append(analysis)

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(pages_with_impressions)} pages...")

    print(f"  Analysis complete: {len(results)} pages processed")
    return results


def get_optimization_opportunities(
    pages: List[Dict],
    max_results: int = None
) -> List[Dict]:
    """
    Get pages that need optimization, sorted by opportunity score.

    Filters for:
    - Structure score below threshold
    - Opportunity score above minimum
    - Eligible for optimization (not recently changed)
    """
    if max_results is None:
        max_results = MAX_EXPERIMENTS_PER_MONTH

    opportunities = [
        p for p in pages
        if (
            p["optimization_needed"] and
            p["opportunity_score"] >= MIN_OPPORTUNITY_SCORE and
            p.get("eligible", True)
        )
    ]

    # Sort by opportunity score (highest first)
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    return opportunities[:max_results]


def calculate_potential_impact(opportunities: List[Dict]) -> Dict:
    """Calculate the total potential impact of optimizing these pages"""
    total_impressions = sum(o["impressions"] for o in opportunities)
    total_opportunity = sum(o["opportunity_score"] for o in opportunities)
    avg_score = sum(o["structure_score"] for o in opportunities) / len(opportunities) if opportunities else 0

    return {
        "pages_count": len(opportunities),
        "total_impressions": total_impressions,
        "total_opportunity_score": total_opportunity,
        "avg_current_score": round(avg_score, 1),
        "avg_improvement_potential": round(MAX_STRUCTURE_SCORE - avg_score, 1),
    }


def generate_analysis_summary(opportunities: List[Dict]) -> str:
    """Generate a text summary of the structure analysis"""
    if not opportunities:
        return "No AIO optimization opportunities found."

    impact = calculate_potential_impact(opportunities)

    # Count missing elements across all opportunities
    missing_counts = {}
    for opp in opportunities:
        for elem in opp.get("missing_elements", []):
            missing_counts[elem] = missing_counts.get(elem, 0) + 1

    # Sort by frequency
    sorted_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)

    lines = [
        "## AIO Structure Analysis Summary",
        "",
        f"**Pages needing optimization:** {impact['pages_count']}",
        f"**Total impressions:** {impact['total_impressions']:,}",
        f"**Average structure score:** {impact['avg_current_score']}/{MAX_STRUCTURE_SCORE}",
        f"**Average improvement potential:** +{impact['avg_improvement_potential']} points",
        "",
        "### Most Common Missing Elements",
        ""
    ]

    for elem, count in sorted_missing[:5]:
        elem_desc = STRUCTURE_ELEMENTS.get(elem, {}).get("description", elem)
        lines.append(f"- **{elem_desc}**: missing from {count} pages")

    lines.extend([
        "",
        "### Top Opportunities",
        ""
    ])

    for i, opp in enumerate(opportunities[:10], 1):
        lines.append(f"**{i}. {opp['page_slug']}**")
        lines.append(f"   - Score: {opp['structure_score']}/{MAX_STRUCTURE_SCORE}")
        lines.append(f"   - Impressions: {opp['impressions']:,}")
        lines.append(f"   - Opportunity: {opp['opportunity_score']:,}")
        lines.append(f"   - Missing: {', '.join(opp.get('missing_elements', [])[:3])}")
        lines.append("")

    return "\n".join(lines)


def get_page_context(page_url: str) -> Dict:
    """Get full context for a page including experiment history"""
    # Get experiment history
    history = db.get_experiments_for_page(page_url)

    # Get learnings from successful experiments
    learnings = db.get_successful_patterns()

    return {
        "page_url": page_url,
        "experiment_history": history,
        "successful_patterns": learnings,
    }
