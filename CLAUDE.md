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
Sprint 2 complete — image upload. vision.py built and tested (hybrid
Groq/Haiku transcription), wired into app.py's tutor mode sidebar.
Next: Sprint 2A — anonymous usage logging, before releasing to the class.

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

## Sprint 2 — complete (Sep 2026)
Single-image transcription for quick doubt-clearing, feeding the same RAG
pipeline as PDF upload. Isolated in vision.py — app.py and rag.py only ever
see its plain-string return, never a provider name.

- Hybrid provider strategy: Groq (qwen/qwen3.8-27b) is the primary path —
  free, fast, works fine for single-page images. Claude Haiku
  (claude-haiku-4-5, same model already used for tutor mode) is a fallback,
  called ONLY when Groq raises TranscriptionTruncatedError. A non-truncation
  Groq error (e.g. a 429) is NOT caught — it propagates, deliberately not
  covered by the fallback.
- Scoped to exactly 1 image per call, not 1-2 — this is for a quick question
  on one page/section. Multi-page chapter content should go through PDF
  upload instead. 2 images or an empty list both raise ValueError.
- Why the fallback exists: Groq's free tier caps output at ~1000 tokens/min
  account-wide — hit a real 429 during testing on a single dense page.
  _GROQ_MAX_OUTPUT_TOKENS is kept tight (800) so a truncation is caught
  quickly rather than burning most of the per-minute budget on a call
  that's going to come back incomplete anyway. Haiku's cap is 1500 — no
  comparable ceiling on Anthropic's side for this volume.
- Tested with 6 scenarios, all passing, using fake clients (no live API
  calls, no dependency on either provider's account state): normal
  transcription, Groq-truncates-Haiku-succeeds, both-truncate-error-
  propagates, 2-image rejection, empty-list rejection, and non-truncation
  Groq error propagating uncaught with Haiku never invoked.
- Wired into app.py's tutor-mode sidebar (quiz mode untouched — this was
  never in scope there). Second file uploader "📷 Upload a pic for quick
  ask", single image only, sits below the existing PDF/TXT uploader.
- Deliberately tighter budget: IMAGE_SESSION_LIMIT = 10, a separate
  whole-session counter (image_session_count) from TUTOR_QUESTION_LIMIT's
  30 — covers the upload itself plus every follow-up question while an
  image is the loaded source. loaded_via_image flag tracks which mode is
  active; switching to a PDF/TXT chapter clears it.
- Chapter-loaded banner shows "Answering from the uploaded image" instead
  of a filename when image-sourced; the no-chapter-uploaded message was
  softened from st.warning to a friendlier st.info.
- Columbus's "chapter required" gate needed no change — it already checks
  loaded_file, which the image path also sets, so an image-sourced page
  satisfies it same as a PDF.
- Logging (Sprint 2A below) not yet wired in — image uploads and
  image-mode questions aren't logged yet.

## Sprint 2A — planned: anonymous usage logging (Sep 2026)
Goal: see how the class of 7 actually uses the tool (which persona, how
often, PDF vs image upload, what kinds of questions) before deciding
whether to keep Groq/Haiku as-is or swap providers for cost reasons.

Decisions already made (see chat history for full reasoning):
- Fully anonymous — no student name, ID, or session identifier captured
  anywhere in a log entry. This was a deliberate choice given "no student
  database" above and that students are minors.
- Storage: local JSONL file via usage_log.py's log_event(action, **fields)
  — one JSON object per line, module built and manually tested.
- Each entry: UTC timestamp, an action string (tutor_question,
  pdf_uploaded, image_uploaded, quiz_generated), plus context fields
  (persona, subject, difficulty) and, for tutor questions, the full
  question text — chosen over metadata-only so "what kind of questions are
  they asking" is actually answerable later.
- Known caveat: Streamlit Community Cloud's filesystem is not guaranteed
  persistent across redeploys/restarts. Treat usage_log.jsonl as something
  to check/export before pushing any code change, not a durable store.
  Open question, not yet decided: whether to add an in-app "download log"
  button as mitigation.
- Not yet wired into app.py. Wiring means a log_event() call at: each of
  the 3 personas' question-send path, PDF upload, image upload (once
  vision.py is also wired in), and quiz generation.