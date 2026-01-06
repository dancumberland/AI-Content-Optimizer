# ABOUTME: Implementation module for AIO structure optimization
# ABOUTME: Inserts definition blocks and FAQ schema into WordPress posts

import re
import requests
from base64 import b64encode
from typing import Optional, Dict, List

from .config import WP_SITE_URL, WP_USER, WP_APP_PASSWORD
from . import database as db


def get_auth_headers() -> Dict[str, str]:
    """Create Basic Auth headers for WordPress REST API"""
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def get_post_by_slug(slug: str) -> Optional[Dict]:
    """Get WordPress post by slug"""
    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    params = {"slug": slug, "status": "publish"}

    try:
        response = requests.get(url, params=params, headers=get_auth_headers())
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


def update_post_content(post_id: int, new_content: str) -> bool:
    """Update post content via WordPress REST API"""
    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts/{post_id}"

    data = {"content": new_content}

    try:
        response = requests.post(url, headers=get_auth_headers(), json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  Error updating post {post_id}: {e}")
        return False


def find_first_paragraph_end(content: str) -> int:
    """
    Find position after the first paragraph in content.
    Returns position after closing </p> tag of first real paragraph.
    """
    # Skip any initial whitespace, comments, or empty paragraphs
    # Look for first substantial paragraph
    paragraph_pattern = r"<p[^>]*>(?!<\/p>).+?<\/p>"
    match = re.search(paragraph_pattern, content, re.DOTALL)

    if match:
        return match.end()

    # Fallback: after first </p>
    p_end = content.find("</p>")
    if p_end != -1:
        return p_end + 4

    # Last resort: beginning
    return 0


def find_content_end(content: str) -> int:
    """
    Find position before the closing content area.
    This is where we insert FAQ schema.
    """
    # Look for common ending patterns
    # Before any existing FAQ block
    faq_match = re.search(r"<!-- wp:rank-math/faq-block", content)
    if faq_match:
        return faq_match.start()

    # Before conclusion/final heading
    conclusion_patterns = [
        r"<h2[^>]*>[^<]*(conclusion|final|summary|wrap)[^<]*</h2>",
        r"<h2[^>]*>[^<]*(wrapping up)[^<]*</h2>",
    ]

    for pattern in conclusion_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.start()

    # Before last </div> or at end
    last_div = content.rfind("</div>")
    if last_div != -1:
        return last_div

    return len(content)


def insert_definition_block(content: str, definition_html: str) -> str:
    """Insert definition block after first paragraph"""
    insert_pos = find_first_paragraph_end(content)

    # Add some spacing
    block_with_spacing = f"\n\n{definition_html}\n\n"

    return content[:insert_pos] + block_with_spacing + content[insert_pos:]


def insert_faq_block(content: str, faq_gutenberg: str) -> str:
    """Insert FAQ schema block at end of content (before conclusion if exists)"""
    insert_pos = find_content_end(content)

    # Add section heading and spacing
    faq_section = f"\n\n<h2>Frequently Asked Questions</h2>\n\n{faq_gutenberg}\n\n"

    return content[:insert_pos] + faq_section + content[insert_pos:]


def implement_optimization(
    page_url: str,
    page_slug: str,
    wp_post_id: int,
    definition_block: Optional[Dict] = None,
    faq_schema: Optional[Dict] = None,
    hypothesis: str = "",
    pre_impressions: int = None,
    pre_clicks: int = None,
    pre_ctr: float = None,
    pre_position: float = None,
    pre_structure_score: int = None,
) -> Optional[int]:
    """
    Implement AIO structural optimization on a post.

    Returns experiment_id if successful, None if failed.
    """
    # Fetch current post
    post = get_post_by_slug(page_slug)
    if not post:
        print(f"  Could not find post: {page_slug}")
        return None

    # Build changes summary
    changes = []
    content = post.get("raw_content") or post["content"]

    # Insert definition block if provided
    if definition_block and definition_block.get("html"):
        content = insert_definition_block(content, definition_block["html"])
        changes.append(f"definition_block ({definition_block['word_count']} words)")

    # Insert FAQ block if provided
    if faq_schema and faq_schema.get("gutenberg_block"):
        content = insert_faq_block(content, faq_schema["gutenberg_block"])
        changes.append(f"faq_schema ({len(faq_schema['questions'])} Q&As)")

    if not changes:
        print(f"  No changes to apply for {page_slug}")
        return None

    changes_summary = ", ".join(changes)

    # Update the post
    success = update_post_content(post["id"], content)
    if not success:
        print(f"  Failed to update post: {page_slug}")
        return None

    # Create experiment record
    experiment_id = db.create_experiment(
        page_url=page_url,
        page_slug=page_slug,
        wp_post_id=post["id"],
        changes_summary=changes_summary,
        hypothesis=hypothesis,
        pre_impressions=pre_impressions,
        pre_clicks=pre_clicks,
        pre_ctr=pre_ctr,
        pre_position=pre_position,
        pre_structure_score=pre_structure_score,
    )

    # Log individual changes
    if definition_block:
        db.log_change(
            experiment_id=experiment_id,
            change_type="insert",
            element_name="definition_block",
            element_content=definition_block["text"],
            insertion_point="after_first_paragraph",
        )

    if faq_schema:
        db.log_change(
            experiment_id=experiment_id,
            change_type="insert",
            element_name="faq_schema",
            element_content=str(faq_schema["questions"]),
            insertion_point="before_conclusion",
        )

    print(f"  ✅ Optimized {page_slug}: {changes_summary}")
    return experiment_id


def batch_implement(
    opportunities: List[Dict],
    generate_content_fn,
    max_per_batch: int = 10,
) -> List[int]:
    """
    Batch implement optimizations for multiple pages.

    Args:
        opportunities: List of opportunity dicts from analysis
        generate_content_fn: Function to generate content elements
        max_per_batch: Maximum pages to process in one batch

    Returns:
        List of experiment IDs created
    """
    experiment_ids = []

    for i, opp in enumerate(opportunities[:max_per_batch]):
        print(f"\n[{i+1}/{min(len(opportunities), max_per_batch)}] {opp['page_slug']}")

        try:
            # Generate content for missing elements
            generated = generate_content_fn(
                title=opp["title"],
                content=opp.get("content", ""),
                missing_elements=opp["missing_elements"],
            )

            # Build hypothesis
            if generated["generated_elements"]:
                hypothesis = f"Adding {', '.join(generated['generated_elements'])} to improve AI citation likelihood"
            else:
                print(f"  Skipping: no content generated")
                continue

            # Implement the optimization
            experiment_id = implement_optimization(
                page_url=opp["page_url"],
                page_slug=opp["page_slug"],
                wp_post_id=opp["wp_post_id"],
                definition_block=generated.get("definition_block"),
                faq_schema=generated.get("faq_schema"),
                hypothesis=hypothesis,
                pre_impressions=opp.get("impressions"),
                pre_structure_score=opp.get("structure_score"),
            )

            if experiment_id:
                experiment_ids.append(experiment_id)

        except Exception as e:
            print(f"  Error processing {opp['page_slug']}: {e}")
            continue

    return experiment_ids
