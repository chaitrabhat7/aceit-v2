# AceIt v2 — Project Context for Claude Code

## What this project is
CBSE AI learning platform for Classes 7–10. Built by Chaitra — homemaker, 
part-time CBSE tutor, BTech CS background, returning to tech after 15 years. 
This is both a real product and a learning project. Explain before writing.

## Current state
- Live at: https://aceit-v2-class7to10.streamlit.app/
- GitHub: https://github.com/chaitrabhat7/aceit-v2
- Stack: Python, Streamlit, Claude API, LangChain, Groq, PyPDF2, fpdf2

## Model routing — DO NOT change this without asking
- Easy / Medium / Hard quiz: Groq llama-3.3-70b-versatile (free tier)
- HOTS quiz: Claude Sonnet only — never swap this to Groq
- All tutor mode personas: Claude Sonnet only

## Personas — DO NOT modify system prompts without asking
- Archimedes: CBSE Maths tutor, intuition before formula
- Shakespeare: CBSE English, grammar through real sentences
- Columbus: answers ONLY from uploaded chapter — never general knowledge

## How to work with me
1. Always explain what you are about to do before writing any code
2. Show diffs, not full file rewrites
3. One function at a time — do not refactor things I didn't ask about
4. After every change, tell me what to test and how

## Current sprint
Sprint 1A complete — Groq model swap done.
Sprint 1B complete — RAG for tutor PDF uploads (all three personas).
Next: Sprint 1C — session-level rate limiting.

## What NOT to build yet
No login/auth, no student database, no admin dashboard, 
no native mobile app, no multi-language support.
Append this to CLAUDE.md under model decisions:

## Actual model routing (verified in code Sep 2026)
- Quiz Easy/Medium/Hard: Groq llama-3.3-70b-versatile
- HOTS quiz: claude-sonnet-4-6
- All tutor personas (Archimedes, Shakespeare, Columbus): claude-haiku-4-5

Groq tested for all personas in playground — quality gap too large.
Haiku stays for all tutor mode. Sonnet stays for HOTS only.
Decision locked until after LinkedIn launch.

Do not use sentence-transformers or PyTorch — too heavy for 
Streamlit Community Cloud 1GB RAM limit.
(Superseded: ChromaDB also dropped — see "Sprint 1B — complete" below.)

Update CLAUDE.md — add these corrections to the Sprint 1B section:

1. RAG applies to ALL three personas (Archimedes, Shakespeare, Columbus) 
   — not Columbus only. All three have PDF upload in app.py.

2. ChromaDB dropped — too heavy, C++ build breaks on Streamlit Cloud.
   Using FastEmbed + in-memory NumPy cosine instead.

3. sentence-transformers dropped — PyTorch dependency too heavy 
   for Streamlit Cloud 1GB RAM limit.

4. New dependency: fastembed only. Add to requirements.txt.

5. Build RAG as one reusable function, called from all three 
   persona upload paths.

6. Chunk size 800, overlap 100, top-k 3 — tune after first test.

## Sprint 1B — complete (Sep 2026)
RAG for tutor-mode chapter uploads. Live and tested.

- Applies to all three personas (Archimedes, Shakespeare, Columbus) via the
  shared upload handler in app.py.
- Stack: fastembed (BAAI/bge-small-en-v1.5, quantized ONNX — no PyTorch) for
  embeddings; in-memory NumPy cosine for retrieval; hand-rolled text splitter.
  No ChromaDB.
- All RAG logic in rag.py: chunk_text -> embed_texts -> build_index -> retrieve
  -> format_context. Index kept in st.session_state["rag_index"], rebuilt only
  on a new upload.
- Params: chunk size 800, overlap 100, top-k 3.
- Result: 75-80% token reduction per question confirmed in Anthropic console.
  Answer quality excellent — Columbus grounding especially strong, out-of-chapter
  questions correctly refused.
- Known limitation: retrieval query is the latest user message only; multi-turn
  follow-ups ("explain that more") can drift. Revisit if it bites.
- Known issue (not RAG): PyPDF2 garbles some NCERT embedded fonts — flagged for
  a later sprint.