# AI Content Optimizer

AI-powered content optimization system for SEO and AI Overview (AIO) optimization.

## Overview

This system helps optimize web content for both traditional search engines and AI-powered search (like Google AI Overviews, Perplexity, ChatGPT).

### Core Components

- **AIO System** (`aio_system/`): Monthly review workflow for identifying and improving AI-extractable content
- **CTR System** (`ctr_system/`): Click-through rate optimization with Google Search Console integration
- **Orchestrator** (`aio_orchestrator.py`): Main CLI for running optimization workflows

## Features

- Structure analysis for AI-extractable content elements
- Automated content generation with voice consistency
- A/B experiment tracking and measurement
- Google Search Console integration
- Email notifications and reporting

## Usage

```bash
# Run monthly review (dry run)
python aio_orchestrator.py monthly --dry-run

# Run weekly measurement update
python aio_orchestrator.py weekly

# Check system status
python aio_orchestrator.py status

# Run analysis only (no changes)
python aio_orchestrator.py analyze
```

## Requirements

- Python 3.9+
- Claude CLI (for content generation)
- Google Search Console API access
- WordPress REST API access (for implementation)

## Configuration

Set environment variables or create a `.env` file:

```
GSC_CREDENTIALS_PATH=/path/to/credentials.json
WP_API_URL=https://yoursite.com/wp-json/wp/v2
WP_USERNAME=your_username
WP_APP_PASSWORD=your_app_password
```

## License

MIT
