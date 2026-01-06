# ABOUTME: AI-powered content generation for AIO structural elements
# ABOUTME: Generates definition blocks and FAQ schema using Claude CLI with voice guidance

import json
import re
import subprocess
from typing import List, Dict, Optional

from .config import (
    DEFINITION_MIN_WORDS,
    DEFINITION_MAX_WORDS,
    FAQ_COUNT,
    FAQ_ANSWER_MIN_WORDS,
    FAQ_ANSWER_MAX_WORDS,
)
from .voice_reference import get_voice_context


def call_claude_cli(prompt: str, model: str = "sonnet") -> str:
    """Call Claude CLI and return the response text"""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json", "--model", model],
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI error: {result.stderr}")

        # Parse the JSON output to extract the response text
        output = json.loads(result.stdout)

        # The output format has a 'result' field with the response
        if isinstance(output, dict) and "result" in output:
            return output["result"]
        elif isinstance(output, str):
            return output
        else:
            return str(output)

    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude CLI timed out after 180 seconds")
    except json.JSONDecodeError:
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("Claude CLI not found. Ensure 'claude' is in PATH.")


def generate_definition_block(
    title: str,
    content_excerpt: str,
    top_queries: List[str] = None,
) -> Dict:
    """
    Generate a definition block for the article.

    Returns dict with:
    - text: The definition block text
    - html: The formatted HTML
    - word_count: Number of words
    """
    queries_text = ""
    if top_queries:
        queries_text = f"\n\nTop search queries for this page:\n" + "\n".join(
            f"- {q}" for q in top_queries[:5]
        )

    # Get voice context with topic-relevant exemplars
    voice_context = get_voice_context(title, content_excerpt)

    prompt = f"""Generate a definition block for this article that will help it appear in AI Overviews and AI search results.

## Article Information
- Title: "{title}"
- Content excerpt (first 500 chars):
{content_excerpt[:500]}
{queries_text}

## Voice & Style Guide
{voice_context}

## Definition Block Requirements
1. Start with the main topic/keyword + "is" (e.g., "Life purpose is...")
2. Provide a clear, direct definition in 1-2 sentences
3. Add one supporting sentence with context or a fact
4. Total length: {DEFINITION_MIN_WORDS}-{DEFINITION_MAX_WORDS} words
5. Must be extractable as a standalone answer
6. No fluff phrases like "In this article..." or "Have you ever wondered..."
7. Match Dan's voice from the examples above

## Output Format
Return a JSON object with:
- "text": the definition block text only (no HTML)
- "word_count": number of words

Example output:
{{"text": "Finding your life purpose is a process, not a destination— and it's okay if you haven't figured it out yet. Most people discover their purpose through action, not contemplation. Start with what pulls your attention and energy, even when no one is watching.", "word_count": 47}}

Return ONLY the JSON object, no other text."""

    response = call_claude_cli(prompt)

    # Extract JSON
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        result = json.loads(json_match.group())
    else:
        raise ValueError(f"Could not parse definition from response: {response[:200]}")

    # Format as HTML
    text = result["text"]
    html = f'<div class="definition-block" style="background: #f8f9fa; border-left: 4px solid #1a73e8; padding: 20px; margin: 20px 0; font-size: 1.1em;">\n<p>{text}</p>\n</div>'

    return {
        "text": text,
        "html": html,
        "word_count": len(text.split()),
    }


def generate_faq_schema(
    title: str,
    content: str,
    existing_headings: List[str] = None,
) -> Dict:
    """
    Generate FAQ schema content for RankMath FAQ block.

    Returns dict with:
    - questions: List of Q&A dicts
    - gutenberg_block: The RankMath FAQ Gutenberg block markup
    """
    headings_text = ""
    if existing_headings:
        headings_text = "\n\nExisting H2 headings in article:\n" + "\n".join(
            f"- {h}" for h in existing_headings
        )

    # Get voice context with topic-relevant exemplars
    voice_context = get_voice_context(title, content)

    prompt = f"""Generate FAQ schema questions and answers for this article that will help it appear in AI search results.

## Article Information
- Title: "{title}"
- Content excerpt:
{content[:2000]}
{headings_text}

## Voice & Style Guide
{voice_context}

## FAQ Requirements
1. Generate exactly {FAQ_COUNT} question/answer pairs
2. Questions should be what people actually search for (conversational)
3. Answers should be {FAQ_ANSWER_MIN_WORDS}-{FAQ_ANSWER_MAX_WORDS} words each
4. Each answer must be standalone and extractable
5. Don't repeat content from existing headings
6. Match Dan's voice from the examples above

## Output Format
Return a JSON object with:
- "questions": array of objects with "question" and "answer" keys

Example:
{{
  "questions": [
    {{"question": "How do I know if I've found my purpose?", "answer": "You probably won't feel 100% certain— and that's normal. Purpose shows up gradually, through the work that keeps drawing you back even when it's hard. Pay attention to what you'd do even without recognition or pay."}},
    ...
  ]
}}

Return ONLY the JSON object, no other text."""

    response = call_claude_cli(prompt)

    # Extract JSON
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        result = json.loads(json_match.group())
    else:
        raise ValueError(f"Could not parse FAQ from response: {response[:200]}")

    questions = result["questions"]

    # Generate RankMath FAQ Gutenberg block
    faq_items = []
    for i, qa in enumerate(questions):
        faq_items.append(
            f'{{"id":"faq-question-{i}","title":"{escape_json_string(qa["question"])}","content":"{escape_json_string(qa["answer"])}","visible":true}}'
        )

    gutenberg_block = f"""<!-- wp:rank-math/faq-block {{"questions":[{",".join(faq_items)}]}} -->
<div class="wp-block-rank-math-faq-block">"""

    for qa in questions:
        gutenberg_block += f"""
<div class="rank-math-faq-item">
<h3 class="rank-math-question">{qa["question"]}</h3>
<div class="rank-math-answer">{qa["answer"]}</div>
</div>"""

    gutenberg_block += "\n</div>\n<!-- /wp:rank-math/faq-block -->"

    return {
        "questions": questions,
        "gutenberg_block": gutenberg_block,
    }


def escape_json_string(s: str) -> str:
    """Escape a string for use in JSON inside Gutenberg block"""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def generate_all_elements(
    title: str,
    content: str,
    missing_elements: List[str],
    top_queries: List[str] = None,
    existing_headings: List[str] = None,
) -> Dict:
    """
    Generate all missing AIO structural elements for a page.

    Returns dict with generated elements based on what's missing.
    """
    results = {
        "generated_elements": [],
        "definition_block": None,
        "faq_schema": None,
    }

    # Generate definition block if missing
    if "has_definition_block" in missing_elements:
        try:
            definition = generate_definition_block(
                title=title,
                content_excerpt=content[:500],
                top_queries=top_queries,
            )
            results["definition_block"] = definition
            results["generated_elements"].append("definition_block")
        except Exception as e:
            print(f"  Error generating definition block: {e}")

    # Generate FAQ schema if missing
    if "has_faq_schema" in missing_elements:
        try:
            faq = generate_faq_schema(
                title=title,
                content=content,
                existing_headings=existing_headings,
            )
            results["faq_schema"] = faq
            results["generated_elements"].append("faq_schema")
        except Exception as e:
            print(f"  Error generating FAQ schema: {e}")

    return results
