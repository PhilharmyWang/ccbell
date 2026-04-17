"""
ccbell.__main__ — allow `python -m ccbell` as entry point.

Input:  JSON via stdin
Output: exit code (0)
Usage:
    echo '{"hook_event_name":"Stop"}' | python -m ccbell
Created: 2026-04-17
"""

import sys
from ccbell.dispatcher import main

sys.exit(main())
