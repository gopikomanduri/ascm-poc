"""Best-effort 'what is the user looking at' detection (macOS; others return None)."""

import subprocess
import sys
from typing import Optional, Dict

_SCRIPT = '''
tell application "System Events"
    set p to first application process whose frontmost is true
    set n to name of p
    try
        set t to name of front window of p
    on error
        set t to ""
    end try
end tell
return n & "|||" & t
'''


def get_active_app() -> Optional[Dict[str, str]]:
    """Return {'app': ..., 'window': ...} for the frontmost app, or None if unavailable."""
    if not sys.platform.startswith("darwin"):
        return None
    try:
        res = subprocess.run(["osascript", "-e", _SCRIPT], capture_output=True, text=True, timeout=3)
        if res.returncode != 0:
            return None
        app, _, window = res.stdout.strip().partition("|||")
        return {"app": app, "window": window}
    except Exception:
        return None
