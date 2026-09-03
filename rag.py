"""RAG helpers for AceIt tutor mode — chunk, embed, retrieve.

Kept deliberately dependency-light (CLAUDE.md, Sprint 1B):
fastembed for embeddings, NumPy for similarity, a hand-rolled splitter
instead of langchain-text-splitters. No ChromaDB, no PyTorch.
"""

import re

import numpy as np
from fastembed import TextEmbedding

_EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_EMBED_DIM = 384
_MODEL = None


def _get_embedding_model():
    """Load the fastembed model once and reuse it.

    Streamlit reruns this whole script on every interaction; a module global
    survives that, so the ~130 MB ONNX model loads once per container instead
    of once per question.
    """
    global _MODEL
    if _MODEL is None:
        _MODEL = TextEmbedding(model_name=_EMBED_MODEL_NAME)
    return _MODEL


def embed_texts(texts):
    """Embed a list of strings into an (n, 384) float32 matrix.

    Rows are L2-normalised, so cosine similarity later is a plain dot product.
    An empty list returns a (0, 384) array.
    """
    if not texts:
        return np.zeros((0, _EMBED_DIM), dtype=np.float32)

    model = _get_embedding_model()
    matrix = np.array(list(model.embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def chunk_text(text, chunk_size=800, overlap=100):
    """Split chapter text into overlapping character windows.

    Paragraphs (separated by blank lines) are packed greedily into windows of
    at most chunk_size characters. Every window after the first is prefixed
    with the last `overlap` characters of the previous one, so a sentence
    straddling a boundary still shows up whole somewhere. A single paragraph
    longer than chunk_size is hard-split on whitespace first.

    Returns a list of non-empty stripped strings. Empty input returns [].
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    # Break oversized paragraphs into word-bounded pieces up front.
    units = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            units.append(para)
        else:
            units.extend(_hard_split(para, chunk_size))

    # Pack units into windows no larger than chunk_size.
    windows = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + 2 + len(unit) <= chunk_size:
            current += "\n\n" + unit
        else:
            windows.append(current)
            current = unit
    if current:
        windows.append(current)

    if overlap <= 0 or len(windows) < 2:
        return windows

    # Prefix each window with the tail of the one before it.
    overlapped = [windows[0]]
    for prev, curr in zip(windows, windows[1:]):
        overlapped.append((prev[-overlap:] + "\n\n" + curr).strip())
    return overlapped


def _hard_split(text, chunk_size):
    """Split one long paragraph on whitespace into <= chunk_size pieces."""
    pieces = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= chunk_size:
            current += " " + word
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def build_index(chapter_text):
    """Chunk and embed a chapter into a searchable in-memory index.

    Returns {"chunks": [str], "matrix": (n, 384) float32}, or None when the
    text has nothing usable in it (e.g. a scanned PDF PyPDF2 couldn't read).
    """
    chunks = chunk_text(chapter_text)
    if not chunks:
        return None
    return {"chunks": chunks, "matrix": embed_texts(chunks)}


def retrieve(index, query, k=3):
    """Return the k chunks most similar to the query, best first.

    Both the query and the chunks are unit-normalised, so the dot product is
    cosine similarity. Returns [] for an empty index or a blank query.
    """
    matrix = index["matrix"]
    if matrix.shape[0] == 0 or not query.strip():
        return []
    query_vec = embed_texts([query])[0]
    scores = matrix @ query_vec
    top = np.argsort(scores)[::-1][:k]
    return [index["chunks"][i] for i in top]


def format_context(chunks):
    """Join retrieved chunks into one block for the system prompt."""
    return "\n\n---\n\n".join(chunks)
