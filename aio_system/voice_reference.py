# ABOUTME: Condensed voice reference for AIO content generation
# ABOUTME: Maps topics to exemplars and provides voice guidance for short-form content

from pathlib import Path
from typing import List, Optional
import random

# Path to voice exemplars
EXEMPLARS_DIR = Path(__file__).parent.parent.parent.parent / "ClientData" / "BrandVoice" / "VoiceExemplars"

# Condensed voice guidance for short-form AIO content (definitions, FAQs)
AIO_VOICE_GUIDE = """
## Dan Cumberland's Voice (for short-form content)

**Core approach:**
- Warm but direct— acknowledge difficulty while encouraging
- Use "you" language, speak to the reader personally
- Specific over generic (avoid vague platitudes)
- Process-oriented ("it takes time" not "just do it")
- Both/and tension: hold struggle and hope together

**Style:**
- Short sentences, punchy rhythm
- Em-dash with space after (word— next)
- No jargon, no corporate speak
- Conversational but thoughtful
- Vulnerable honesty without self-pity

**Avoid:**
- Toxic positivity ("just think positive!")
- Vague abstractions ("find your passion")
- Prescriptive commands ("you must...")
- Sarcasm or judgment
- Fluff phrases ("In this article we will explore...")
"""

# Topic keywords mapped to exemplar files
TOPIC_MAPPING = {
    "burnout": ["burnout", "exhausted", "tired", "overwhelmed", "stressed", "drained"],
    "career_change": ["career change", "new job", "quit", "leaving", "transition", "pivot"],
    "creativity": ["creative", "artist", "create", "making", "craft", "art"],
    "faith_spirituality": ["faith", "spiritual", "god", "prayer", "soul", "meaning"],
    "fear_and_risk": ["fear", "afraid", "scared", "risk", "brave", "courage", "anxiety"],
    "finding_purpose": ["purpose", "calling", "meaning", "vocation", "life's work", "destiny"],
    "hope_perseverance": ["hope", "persevere", "keep going", "don't give up", "persist", "endure"],
    "relationships": ["relationship", "marriage", "partner", "friend", "love", "connection"],
    "self_discovery": ["self", "identity", "who am i", "discover", "know yourself", "authentic"],
    "taking_action": ["action", "start", "begin", "do it", "move", "step", "momentum"],
}


def detect_topic(title: str, content: str) -> Optional[str]:
    """Detect the most relevant topic based on title and content"""
    text = (title + " " + content[:500]).lower()

    topic_scores = {}
    for topic, keywords in TOPIC_MAPPING.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            topic_scores[topic] = score

    if not topic_scores:
        return "general"

    return max(topic_scores, key=topic_scores.get)


def load_exemplars(topic: str, count: int = 3) -> List[str]:
    """Load exemplar paragraphs for a topic"""
    topic_file = EXEMPLARS_DIR / "by_topic" / f"{topic}.md"

    if not topic_file.exists():
        topic_file = EXEMPLARS_DIR / "by_topic" / "general.md"

    if not topic_file.exists():
        return []

    content = topic_file.read_text()

    # Extract quoted paragraphs (lines starting with >)
    exemplars = []
    for line in content.split("\n"):
        if line.startswith("> "):
            paragraph = line[2:].strip()
            # Only use reasonably sized paragraphs
            if 50 < len(paragraph) < 500:
                exemplars.append(paragraph)

    # Return random selection
    if len(exemplars) <= count:
        return exemplars
    return random.sample(exemplars, count)


def get_voice_context(title: str, content: str) -> str:
    """Get complete voice context for content generation prompts

    Note: Currently returns just the voice guide. Exemplar loading is disabled
    because the by_topic files contain noisy podcast transcripts mixed with
    written content. For short-form AIO content (40-80 words), the condensed
    voice guide provides sufficient guidance.
    """
    # For now, just return the voice guide
    # Future: Add curated exemplars when available
    return AIO_VOICE_GUIDE


def get_short_voice_reference() -> str:
    """Get just the voice guide without exemplars (for simpler prompts)"""
    return AIO_VOICE_GUIDE
