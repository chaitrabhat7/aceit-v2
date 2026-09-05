"""Anonymous usage logging for AceIt.

Appends one JSON object per line to a local log file. No student name,
ID, or session identifier is captured anywhere in an entry — logging is
fully anonymous by design (see CLAUDE.md, Sept 2026 privacy decision).

Note: on Streamlit Community Cloud the filesystem is not guaranteed to
persist across redeploys, so this file should be treated as something to
check/export before pushing changes, not a durable long-term store.
"""

import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "usage_log.jsonl")


def log_event(action, **fields):
    """Append one anonymous usage event to the log file.

    `action` is a short string such as "tutor_question", "pdf_uploaded",
    "image_uploaded", or "quiz_generated". Extra keyword arguments (e.g.
    persona="Archimedes", question_text="...") are stored as-is alongside
    the action and a UTC timestamp. No student identity is recorded.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **fields,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
