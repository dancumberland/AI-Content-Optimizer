# ABOUTME: Configuration for AIO (AI Overview) optimization system
# ABOUTME: Thresholds, paths, and settings for structure optimization

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TOOLS_DIR = PROJECT_ROOT / "Operations" / "Tools"
AIO_SYSTEM_DIR = TOOLS_DIR / "aio_system"
DB_PATH = TOOLS_DIR.parent / "aio_optimizations.db"
REPORTS_DIR = PROJECT_ROOT / "Operations" / "AIO_Reports"

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# WORDPRESS API
# =============================================================================

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://themeaningmovement.com")
WP_USER = os.getenv("WP_USER", "dan")
WP_APP_PASSWORD = os.getenv("Wordpress_Rest_API_KEY")

# =============================================================================
# GOOGLE SEARCH CONSOLE
# =============================================================================

GSC_CREDENTIALS_FILE = os.getenv("GSC_CREDENTIALS_FILE")
GSC_TOKEN_FILE = os.getenv("GSC_TOKEN_FILE")
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "sc-domain:themeaningmovement.com")

# =============================================================================
# ANALYSIS THRESHOLDS
# =============================================================================

# Minimum impressions to consider a page for optimization
MIN_IMPRESSIONS_FOR_ANALYSIS = 100

# Minimum days since last change before re-optimization
MIN_DAYS_BETWEEN_CHANGES = 30

# Minimum days before evaluating an experiment
MIN_DAYS_FOR_EVALUATION = 30

# Maximum days to wait before declaring experiment inconclusive
MAX_DAYS_FOR_EVALUATION = 120

# Minimum post-change impressions needed to evaluate
MIN_POST_CHANGE_IMPRESSIONS = 50

# =============================================================================
# STRUCTURE SCORING
# =============================================================================

# Structure elements and their point values
STRUCTURE_ELEMENTS = {
    "has_definition_block": {
        "points": 2,
        "description": "Definition block in first 200 words",
        "pattern": r'<div class="definition-block"'
    },
    "has_numbered_list": {
        "points": 1,
        "description": "At least one numbered list",
        "pattern": r"<ol[^>]*>.*?</ol>"
    },
    "has_bulleted_list": {
        "points": 1,
        "description": "At least one bulleted list",
        "pattern": r"<ul[^>]*>.*?</ul>"
    },
    "has_question_headings": {
        "points": 1,
        "description": "H2 headers as questions",
        "pattern": r"<h2[^>]*>[^<]*\?</h2>"
    },
    "has_faq_schema": {
        "points": 2,
        "description": "RankMath FAQ schema block",
        "pattern": r'wp:rank-math/faq-block'
    },
    "has_howto_schema": {
        "points": 1,
        "description": "HowTo schema markup",
        "pattern": r'"@type"\s*:\s*"HowTo"'
    },
    "has_table": {
        "points": 1,
        "description": "HTML table with data",
        "pattern": r"<table[^>]*>.*?</table>"
    },
    "has_citations": {
        "points": 1,
        "description": "External citations/sources",
        "pattern": r'href="https?://(?!themeaningmovement)'
    },
}

# Maximum structure score
MAX_STRUCTURE_SCORE = sum(e["points"] for e in STRUCTURE_ELEMENTS.values())

# Minimum score to consider a page "optimized"
MIN_OPTIMIZED_SCORE = 4

# =============================================================================
# OPTIMIZATION THRESHOLDS
# =============================================================================

# Pages with score below this are candidates for optimization
OPTIMIZATION_THRESHOLD_SCORE = 3

# Minimum opportunity score (impressions * (MAX_SCORE - current_score))
MIN_OPPORTUNITY_SCORE = 500

# Safety limit per month
MAX_EXPERIMENTS_PER_MONTH = 50

# =============================================================================
# CONTENT GENERATION
# =============================================================================

# Definition block constraints
DEFINITION_MIN_WORDS = 40
DEFINITION_MAX_WORDS = 60

# FAQ constraints
FAQ_COUNT = 4
FAQ_ANSWER_MIN_WORDS = 20
FAQ_ANSWER_MAX_WORDS = 80

# TMM brand voice characteristics
TMM_VOICE = {
    "tone": "warm, encouraging, authentic",
    "perspective": "first/second person where appropriate",
    "style": "accessible, no jargon",
    "punctuation": "em-dash with space after (— )",
}

# =============================================================================
# NOTIFICATIONS
# =============================================================================

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")

# =============================================================================
# OUTCOME THRESHOLDS
# =============================================================================

# Impression change thresholds for outcome determination
IMPROVEMENT_THRESHOLD = 0.10  # 10% improvement = "improved"
WORSENED_THRESHOLD = -0.10   # 10% decline = "worsened"

# Position change threshold
POSITION_CHANGE_THRESHOLD = 2.0


def validate_config():
    """Check that required configuration is present"""
    errors = []

    if not WP_USER:
        errors.append("WP_USER not set in .env")
    if not WP_APP_PASSWORD:
        errors.append("Wordpress_Rest_API_KEY not set in .env")
    if not GSC_CREDENTIALS_FILE or not Path(GSC_CREDENTIALS_FILE).exists():
        errors.append("GSC_CREDENTIALS_FILE not set or file not found")

    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        return False
    return True
