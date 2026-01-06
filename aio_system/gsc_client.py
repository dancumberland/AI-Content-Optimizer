# ABOUTME: Google Search Console client wrapper for AIO system
# ABOUTME: Reuses the CTR system's GSC client for consistency

import sys
from pathlib import Path

# Add Tools directory to path for cross-package imports
_tools_dir = Path(__file__).parent.parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from ctr_system.gsc_client import GSCClient, get_gsc_client

__all__ = ["GSCClient", "get_gsc_client"]
