"""Anonymous usage logging for AceIt.

Appends one JSON object per line to a local log file, and — when
configure_sheet() has been called — also appends a row to a Google Sheet.
No student name, ID, or session identifier is captured anywhere in an
entry — logging is fully anonymous by design (see CLAUDE.md, Sept 2026
privacy decision).

The local file stays useful for local dev/testing, but on Streamlit
Community Cloud its filesystem is not guaranteed to persist across
redeploys or container restarts — the Sheet is the durable copy to check.
"""

import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "usage_log.jsonl")

# Fixed column order for the Sheet — every event writes a full row in this
# order, blank for whichever fields don't apply to that action.
_SHEET_COLUMNS = [
    "timestamp", "action", "persona", "grade", "source", "question_text",
    "file_type", "chars", "oversized", "num_pages", "ocr_failed_count",
    "subject", "difficulty", "num_questions",
]

_sheet = None


def configure_sheet(credentials_info, sheet_id):
    """Wire up a Google Sheet as a second, durable log destination.

    Call once at app startup (cache it there — this does a network auth
    call). credentials_info is the dict from st.secrets["gcp_service_account"],
    same as vision.py uses. If this is never called, or setup fails,
    log_event() silently keeps writing only the local file.
    """
    global _sheet
    try:
        import gspread
        gc = gspread.service_account_from_dict(dict(credentials_info))
        _sheet = gc.open_by_key(sheet_id).sheet1
    except Exception:
        _sheet = None


def log_event(action, **fields):
    """Record one anonymous usage event, to the local file and the Sheet.

    `action` is a short string such as "tutor_question", "pdf_uploaded",
    "image_uploaded", or "quiz_generated". Extra keyword arguments (e.g.
    persona="Archimedes", question_text="...") are stored as-is alongside
    the action and a UTC timestamp. No student identity is recorded.

    Never raises — a failure in either destination (disk full, Sheets API
    hiccup, no network) must not break the tutor/quiz flow it's attached to.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **fields,
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    if _sheet is not None:
        try:
            row = [str(entry.get(col, "")) for col in _SHEET_COLUMNS]
            _sheet.append_row(row, value_input_option="RAW")
        except Exception:
            pass
