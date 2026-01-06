# ABOUTME: Specification for AIO Structure Optimization System
# ABOUTME: Reference document for building the AI Overview optimization tooling

# AIO Structure Optimization System - Specification

## Problem Statement

TMM ranks position 1-10 for high-value queries but isn't being cited in AI Overviews. AI systems prefer structured, extractable content over narrative prose.

**Evidence:**
- 8,965 queries in position 2-10 with 7.5M impressions
- "what is my purpose" = 4.85M impressions at position 7.7, 0.00% CTR
- Manual testing: TMM cited in only ~17% of AI responses on core topics
- Competing sites (HelpGuide, Wikipedia, Berkeley) have better structure

## Solution: Structure Score Optimization

Score pages on "AI-citable structure" and add structural elements without full rewrites.

### Structure Score Checklist (0-8 points)

| Point | Element | Detection Method |
|-------|---------|------------------|
| 1 | Clear definition in first 100 words | Regex for "X is/are" pattern in first paragraph |
| 1 | At least one numbered/bulleted list | HTML parsing for `<ol>`, `<ul>` |
| 1 | H2 headers as questions | Regex for `<h2>.*\?</h2>` |
| 1 | FAQ schema present | Check for FAQPage schema in JSON-LD |
| 1 | HowTo schema for process content | Check for HowTo schema in JSON-LD |
| 1 | Author credentials visible | Check for author bio/credentials section |
| 1 | Sources/citations included | Check for links to authoritative sources |
| 1 | TL;DR or summary box | Check for summary/key-takeaways section |

### System Architecture

```
Operations/Tools/aio_system/
├── SPEC.md               # This file
├── config.py             # Thresholds, weights, WordPress credentials
├── content_analyzer.py   # Fetch page, calculate structure score
├── analysis.py           # Cross-ref GSC rankings with structure scores
├── ideation.py           # Claude generates structural additions
├── implementation.py     # WordPress REST API updates
├── reporting.py          # Track scores + proxy metrics
└── requirements.txt      # Dependencies
```

### Data Flow

```
1. INPUT: GSC data (high-impression, low-CTR pages)
         ↓
2. FETCH: Get page content via WordPress REST API
         ↓
3. SCORE: Calculate structure score (0-8)
         ↓
4. FILTER: Pages with score < 5 AND impressions > threshold
         ↓
5. IDEATE: Claude generates specific structural additions
         ↓
6. IMPLEMENT: Add structure via WordPress REST API
         ↓
7. MEASURE: Track CTR changes as proxy metric
         ↓
8. LEARN: Which structural additions work best?
```

### Example Transformation

**BEFORE** (typical TMM article, score: 2/8):
```html
<h1>Finding Your Purpose in Life</h1>
<p>Have you ever felt lost, like you're wandering through life without
direction? Many people struggle with this feeling...</p>
[3 paragraphs of narrative intro before any actionable content]
```

**AFTER** (AI-optimized, score: 7/8):
```html
<h1>Finding Your Purpose in Life</h1>

<div class="definition-box">
<strong>What is life purpose?</strong> Life purpose is your overarching
sense of what matters in your life, providing direction and meaning to
your daily actions and long-term goals.
</div>

<h2>Key Steps to Find Your Purpose</h2>
<ol>
<li>Reflect on what energizes you</li>
<li>Identify your core values</li>
<li>Notice patterns in what you're drawn to</li>
<li>Experiment with different paths</li>
<li>Commit to a direction and iterate</li>
</ol>

[Rest of original article unchanged]
```

### Implementation Details

#### config.py
```python
# Thresholds
MIN_IMPRESSIONS = 1000          # Minimum impressions to consider
MIN_STRUCTURE_SCORE = 5         # Target score (pages below this are candidates)
MAX_PAGES_PER_BATCH = 20        # Safety limit per run

# Weights for prioritization
IMPRESSION_WEIGHT = 0.6
STRUCTURE_GAP_WEIGHT = 0.4

# WordPress API (from .env)
# WP_SITE_URL, WP_USER, WP_PASS loaded from environment
```

#### content_analyzer.py
```python
def analyze_page(url: str) -> dict:
    """Fetch page and calculate structure score."""
    return {
        'url': url,
        'structure_score': 0-8,
        'missing_elements': ['definition', 'list', ...],
        'existing_elements': ['h2_questions', ...],
        'content_type': 'how-to' | 'informational' | 'listicle',
        'word_count': int,
        'has_schema': {'faq': bool, 'howto': bool}
    }
```

#### ideation.py
```python
def generate_structural_additions(page_analysis: dict) -> dict:
    """Use Claude to generate specific structural additions."""
    # Prompt includes:
    # - Current page content (first 2000 chars)
    # - Missing elements list
    # - Content type
    # - Examples of good structure

    return {
        'definition_block': "What is X? X is...",
        'key_steps_list': ["Step 1", "Step 2", ...],
        'faq_items': [{"q": "...", "a": "..."}],
        'summary_box': "Key takeaways: ..."
    }
```

#### implementation.py
```python
def add_structure_to_page(post_id: int, additions: dict) -> bool:
    """Add structural elements via WordPress REST API."""
    # 1. Get current content
    # 2. Insert definition block after H1
    # 3. Add list if missing
    # 4. Add FAQ schema if items provided
    # 5. Update via REST API
    # 6. Log change for tracking
```

### Validation Strategy

Since we're not using expensive AI citation APIs:

1. **Proxy Metrics** (automated, weekly):
   - CTR changes for optimized pages
   - Time on page (if GA4 configured)
   - Scroll depth (already tracking)

2. **Manual Spot Checks** (quarterly):
   - Test 10 high-value queries in Perplexity, ChatGPT, Google AI Overview
   - Record: Is TMM cited? What format is cited?
   - Adjust optimization approach based on findings

3. **A/B Learning**:
   - Track which structural additions correlate with CTR improvements
   - Feed learnings back into ideation prompts

### Integration with Existing Systems

- **GSC Data**: Use existing `gsc_pull.py` or CTR system's GSC client
- **WordPress API**: Use existing patterns from CTR system
- **Database**: Could share SQLite with CTR system or use separate
- **Notifications**: Reuse CTR system's email notifications
- **GitHub Actions**: Similar workflow structure to CTR monthly review

### Priority Pages (from GSC analysis)

Top candidates for AIO optimization (high impressions, likely low structure):

1. `finding-purpose-in-life` - 5.3M impressions
2. `what-is-my-purpose` - 4.85M impressions, 0.00% CTR
3. `how-to-find-yourself` - high impressions
4. `meaning-of-life` - informational query
5. `finding-your-calling` - core topic

### Build Sequence

1. **Phase 1**: Content analyzer + scoring (can test immediately)
2. **Phase 2**: Analysis + prioritization (identify top 20 candidates)
3. **Phase 3**: Ideation prompts (Claude generates additions)
4. **Phase 4**: Implementation (WordPress REST API)
5. **Phase 5**: Measurement + learning loop

### Dependencies

```
requests          # HTTP client
beautifulsoup4    # HTML parsing
python-dotenv     # Environment variables
anthropic         # Claude API (or use Claude CLI)
```

### Success Criteria

- Structure scores improve from avg 2-3 to avg 6-7
- CTR improvements on optimized pages (proxy for AI citation)
- Quarterly manual checks show increased AI citations
- System runs autonomously with monthly reviews
