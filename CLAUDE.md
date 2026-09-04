# AceIt v2 — Project Context for Claude Code

## What this project is
CBSE AI learning platform for Classes 7–10. Built by Chaitra — homemaker, 
part-time CBSE tutor, BTech CS background, returning to tech after 15 years. 
This is both a real product and a learning project. Explain before writing.

## Current state
- Live at: https://aceit-v2-class7to10.streamlit.app/
- GitHub: https://github.com/chaitrabhat7/aceit-v2
- Stack: Python, Streamlit, Claude API, LangChain, Groq, PyPDF2, fpdf2, fastembed (RAG embeddings)

## Model routing — DO NOT change this without asking
- Easy / Medium / Hard quiz: Groq openai/gpt-oss-120b (free tier)
- HOTS quiz: Claude Sonnet only — never swap this to Groq
- All tutor mode personas: Claude Haiku (claude-haiku-4-5) only

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
Sprint 1C complete — session-level rate limiting.
Next: Sprint 2 — image upload.

## What NOT to build yet
No login/auth, no student database, no admin dashboard, 
no native mobile app, no multi-language support.

## Actual model routing (verified in code Sep 2026)
- Quiz Easy/Medium/Hard: Groq openai/gpt-oss-120b
- HOTS quiz: claude-sonnet-4-6
- All tutor personas (Archimedes, Shakespeare, Columbus): claude-haiku-4-5

Groq tested for all personas in playground — quality gap too large.
Haiku stays for all tutor mode. Sonnet stays for HOTS only.
Decision locked until after LinkedIn launch.

Do not use sentence-transformers or PyTorch — too heavy for 
Streamlit Community Cloud 1GB RAM limit.
(Superseded: ChromaDB also dropped — see "Sprint 1B — complete" below.)

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

## Sprint 1C — complete (Sep 2026)
Session-level rate limiting. Live and tested.

- Two counters in st.session_state: tutor_question_count, quiz_generation_count.
- Caps: TUTOR_QUESTION_LIMIT = 30, QUIZ_GENERATION_LIMIT = 4 (module-level
  constants in app.py, easy to retune).
- Tutor gate checks before the question is appended to chat history — a
  blocked question never sits unanswered in the conversation.
- Quiz gate covers both the PDF-upload detect_topic call and the Generate
  button, sharing one counter — an upload + a generate together spend 2 of
  the 4.
- Remaining counts shown in sidebar for both modes, live on every rerun.
- Resets on page refresh (session state clears naturally — no extra reset
  code needed).
- Tested at temporary low limits (5 tutor / 3 quiz) first to confirm gating
  works end to end, then set to real limits (30 / 4).