"""Vision transcription for image-based tutor uploads.

Hybrid provider strategy: Groq (qwen/qwen3.8-27b) is the primary path —
free and tested to work for single-page images. Claude Haiku
(claude-haiku-4-5) is a fallback, used only when Groq's output cap
truncates the transcription. Both converge on the same plain-string
return, so app.py and rag.py never need to know which one answered.

Scope: exactly one image per call. This is for quick doubt-clearing on
a single page/section — multi-page chapter content should go through
PDF upload instead.
"""

import base64
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import anthropic

# Load .env directly rather than relying on whoever imports this module to
# have done it first — vision.py builds its clients at import time, so if
# app.py imports vision before calling its own load_dotenv(), the API keys
# below would read as None. Calling it again here is harmless either way.
load_dotenv()

_GROQ_MODEL = "qwen/qwen3.8-27b"
_HAIKU_MODEL = "claude-haiku-4-5"  # same model app.py uses for tutor mode

# Groq free tier caps output at 1000 tokens/minute account-wide (this is
# what raised RateLimitError during testing). Kept tight so a truncation
# is caught before burning most of the per-minute budget on a call that
# was going to come back incomplete anyway.
_GROQ_MAX_OUTPUT_TOKENS = 800

# Haiku is the fallback path — give it enough room that it doesn't also
# truncate on the same page that just defeated Groq.
_HAIKU_MAX_OUTPUT_TOKENS = 1500

_groq_client = ChatGroq(
    model=_GROQ_MODEL,
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=_GROQ_MAX_OUTPUT_TOKENS,
    temperature=0.2,
)

_haiku_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class TranscriptionTruncatedError(Exception):
    """Raised internally when a provider hits its output cap mid-transcription.

    Used by both provider helpers: Groq raising it triggers the Haiku
    fallback inside transcribe_images_to_text(); Haiku raising it means
    there's nothing left to fall back to, so it propagates to the caller.
    Carries the partial text either way — a silent partial transcription
    would chunk and embed fine, which would make Columbus confidently
    refuse questions about content that was simply never captured.
    """

    def __init__(self, partial_text):
        super().__init__(
            "Transcription hit the output token limit and is incomplete."
        )
        self.partial_text = partial_text

_TRANSCRIBE_PROMPT = (
    "Transcribe all visible text in this image exactly as written, preserving "
    "structure (headings, paragraphs, bullet points, numbered steps). Separate "
    "distinct paragraphs or sections with a blank line. Do not summarize or "
    "paraphrase the text.\n\n"
    "If the image contains a diagram, chart, map, or figure, add a brief "
    "description of what it shows under a 'Figure description:' heading, "
    "also separated by a blank line."
)


def _transcribe_with_groq(mime_type, encoded_image):
    """One Groq vision call. Returns text or raises TranscriptionTruncatedError."""
    data_url = f"data:{mime_type};base64,{encoded_image}"
    content = [
        {"type": "text", "text": _TRANSCRIBE_PROMPT},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    response = _groq_client.invoke([HumanMessage(content=content)])
    text = response.content.strip()
    if response.response_metadata.get("finish_reason") == "length":
        raise TranscriptionTruncatedError(text)
    return text


def _transcribe_with_haiku(mime_type, encoded_image):
    """One Claude Haiku vision call. Returns text or raises TranscriptionTruncatedError."""
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": mime_type, "data": encoded_image},
        },
        {"type": "text", "text": _TRANSCRIBE_PROMPT},
    ]
    response = _haiku_client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=_HAIKU_MAX_OUTPUT_TOKENS,
        temperature=0.2,
        messages=[{"role": "user", "content": content}],
    )
    text = response.content[0].text.strip()
    if response.stop_reason == "max_tokens":
        raise TranscriptionTruncatedError(text)
    return text


def transcribe_images_to_text(images):
    """Transcribe exactly one page image into text.

    `images` must be a list containing exactly 1 file-like object (e.g. a
    Streamlit UploadedFile) supporting .read() and, optionally, .type for
    MIME detection. Two-page uploads are out of scope — use PDF upload
    for multi-page chapter content.

    Tries Groq (qwen/qwen3.8-27b) first. If Groq's output cap truncates
    the transcription, retries once with Claude Haiku. Returns a plain
    string regardless of which provider answered; raises
    TranscriptionTruncatedError only if Haiku also truncates.
    """
    if len(images) != 1:
        raise ValueError("transcribe_images_to_text accepts exactly 1 image")

    image_file = images[0]
    mime_type = getattr(image_file, "type", None) or "image/jpeg"
    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    try:
        return _transcribe_with_groq(mime_type, encoded_image)
    except TranscriptionTruncatedError:
        return _transcribe_with_haiku(mime_type, encoded_image)
