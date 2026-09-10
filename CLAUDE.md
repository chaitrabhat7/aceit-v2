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
- Chapter / photo OCR (Sprint 2B): Google Cloud Vision DOCUMENT_TEXT_DETECTION
  — pure OCR, replaces the Groq/Haiku image transcription that was in
  vision.py. Chosen Sep 2026: 1,000 pages/month free covers the class,
  <200ms/page, batch API, no hallucination. See Sprint 2B.

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
Live-tested with a Class 7 student Sep 2026, plus a Class 9-10 user report —
five follow-up problems found (F1-F5, see "Sprint 2 — live-test findings"
below). Sprint 2A (logging) is deprioritized behind them.
Sprint 2B-prime (F5 + F4) — DONE, shipped (commit d38fe61): whole chapter in
context, top-k RAG dropped for single chapters, 1-hour prompt cache.
Sprint 2B (F1, photo upload) — DONE, pending commit: Google Vision OCR + page
images in Haiku's cached context ("Path B"), merged uploader, works for all
three personas. max_tokens 1500 -> 2500.
Next: Sprint 2D (F2 + F3) -> Sprint 2A before releasing to the class.

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
SUPERSEDED Sep 2026 by Sprint 2B-prime for the default path: top-k retrieval
caused F5 (Columbus saw only ~8-10% of the chapter). Single chapters now go to
the model whole, prompt-cached. rag.py's chunk/embed/retrieve is kept only for
the oversized (multi-chapter) fallback.

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

## Sprint 2 patch — downscale image before send (Sep 2026)
Follow-up fix to the Sprint 2 image path. Patch in the working tree,
commit pending.

- Problem: a real phone photo of a textbook page is ~6-10 MB and
  3000-4000px on the long edge. Base64-encoding that produces an ~8-13 MiB
  string, which trips an upstream request-size cap — the call failed before
  the image ever reached Groq or Haiku, so the image-upload feature was
  effectively unusable with an actual camera photo (only small/pre-shrunk
  images worked). The throwaway "debug: log image payload size" commit
  (ad4aa53) was chasing this.
- Fix: new _downscale_to_jpeg() helper in vision.py, called once inside
  transcribe_images_to_text() before either provider. Opens the upload with
  Pillow, applies EXIF rotation then drops EXIF, converts to RGB/L, caps the
  long edge at 1568px (_MAX_EDGE_PX — Anthropic's recommended vision size)
  via a LANCZOS thumbnail, re-encodes as JPEG q85 (_JPEG_QUALITY),
  optimize=True. A typical page photo drops to well under 1 MiB with no
  readable loss of text.
- Side effect, deliberate: output MIME is now always image/jpeg regardless
  of upload format, so PNG / HEIC-exported / etc. all go through one path.
  The debug payload-size print line is removed.
- Dependency: uses Pillow (pillow==12.3.0, already in requirements.txt via
  Streamlit's transitive deps — now imported directly).
- Not changed: Groq-primary / Haiku-fallback logic, the exactly-1-image
  scope, the token caps, the ValueError guards. Both providers see the same
  downscaled JPEG.

## Sprint 2 — live-test findings (Sep 2026)
Reviewed a 1-hour Class 7 revision session on the live app (student + parent
watching). Four problems surfaced. All are Sprint 2 follow-ups and all block
the class release, so Sprint 2A (logging) drops to last priority behind them.

- F1 — no whole-chapter path for Classes 7-8. These grades have no official
  chapter PDF, only the physical textbook. Image upload takes exactly one page
  (vision.py transcribe_images_to_text hard-raises on >1); a chapter is 6-15
  pages. So there is no way to give AceIt a full chapter — the core "explain
  and revise my whole chapter" function. Evidence: student wanted full-chapter
  revision, had no upload path, typed the chapter from memory.
- F2 — Columbus trusts student-typed text as the authoritative chapter. When
  the uploaded source looks thin, Columbus asks the student to type the missing
  content, then quotes it back as "your chapter states...", builds keyword
  lists from it, and grades answers against it — against its defining rule.
  Neither student nor parent is told the source is unverified. Evidence:
  Columbus rejected the PDF as "fragments," student typed the chapter from
  memory, the whole hour (including "your chapter clearly states..." claims and
  a final keyword checklist) ran on that recollection.
- F3 — Columbus stalls on imperfect / garbled source text. Given disordered or
  repetitive text it declares the file incomplete and stops, asking for a
  re-upload, instead of proceeding with the usable content already present.
  Also sometimes restates uncertain content as confident, tidy fact. Bad-text
  root cause: PyPDF2 garbles some NCERT fonts (Sprint 1B known issue) and
  image-only PDFs extract to nothing. Evidence: chapter had real usable content
  across pages; Columbus called it "fragments" and refused to proceed.
- F4 — conversation-history cost grows every turn. Every tutor call resends the
  full accumulated transcript as uncached input (app.py passes
  messages=st.session_state.messages — no cache_control, no window). Cost
  scales with session length, the wrong direction for long revision sessions.
  Evidence: 1-hour / 30-call session cost ~$0.50, ~5.6x the documented
  ~$0.003/question RAG estimate; bulk attributed to resent history, answer
  length secondary.
- F5 — Columbus retrieval is inconsistent and serves content not in the
  uploaded chapter, even on clean official PDFs. On iest106.pdf (Ch 6
  "Democracy") across five upload attempts Columbus reported "fragments /
  partial", cited different non-overlapping snippets each time, surfaced
  Elections material (Electoral Roll, Representation of the People Act 1951),
  and once mis-called it "Chapter 7". DIAGNOSTIC (Sep 2026, scratchpad
  diag_pdf.py): the PDF is a clean SINGLE chapter — 24 pages, 44,089 chars
  (~11K tokens), 0 empty pages, "Chapter 6" footer on every page, no other
  chapter present. "Electoral Roll" appears 0 times in the file. So it is NOT
  a multi-chapter PDF — Columbus was either backfilling from its own civics
  training (the chapter does discuss elections, so with only 3 thin RAG
  fragments it could not tell chapter from general knowledge) or serving a
  stale index from an earlier upload. Source quality is NOT the cause (unlike
  F3). Root cause: RAG serves only the top-3 800-char chunks per question, in
  similarity order, query = latest message only -> Columbus sees ~8-10% of the
  chapter, a different slice each question, and cannot locate the chapter
  boundary. Reported by a user Sep 2026; hits the Class 9-10 PDF path that
  works today -> showstopper.

Fix mapping and order (revised Sep 2026):
- F5 + F4 -> Sprint 2B-prime, URGENT and first — breaks Columbus on the working
  Class 9-10 PDF path. Whole chapter in context, no top-k retrieval, 1-hour
  prompt cache. Also removes the retrieval-drift half of F3.
- F1 -> Sprint 2B — whole-chapter photo upload for Classes 7-8; feeds text into
  2B-prime's non-RAG path.
- F2 + remaining F3 (genuine garble) -> Sprint 2D, deferred — Columbus's
  typed-text workaround is the only path for Classes 7-8 today, so it stays
  until 2B is tested.
Execution order 2B-prime -> 2B -> 2D -> 2A. Sprint 2C is folded into 2B-prime
(prompt caching); an optional history window can wait. Working style unchanged:
explain first, diffs not rewrites, one function at a time, test after each step.

## Sprint 2B-prime — Whole-chapter context + prompt caching (Sep 2026, DONE — commit d38fe61, pushed)
Fixes F5 (retrieval serves fragments / wrong-chapter content even on clean
PDFs) and F4 (history cost), and removes the retrieval-drift half of F3.
Bumped ahead of Sprint 2B because it breaks Columbus on the Class 9-10 PDF
path — the one that works today.

STATUS (Sep 2026): steps 0-3 done and live-tested on iest106.pdf. Columbus now
teaches the whole chapter — complete, consistent, correct chapter, no
Electoral-Roll / RPA / "Chapter 7" hallucination (test transcript saved to
OneDrive usage-logs). Cache confirmed: Q1 write=10074 read=0 (~$0.03),
Q2 write=1469 read=10074 (~$0.01) — chapter served from cache at ~10%.
Step 4 (reading-order retrieve + k=12 for oversized uploads) SKIPPED — not
supporting multi-chapter uploads for now; the oversized branch stays as
degraded-but-warned (k=3 + "upload a single chapter" notice). Steps 5-6 were
folded into step 2 / covered by the test transcript.
Watch-item: max_tokens=1500 is borderline for "summarise the whole chapter"
asks — one test hit out=1500 (truncated). Revisit if students hit it.
The [cache] print in app.py's answer block is a monitoring probe — keep or
drop as wanted.

### Why (root cause of F5)
Sprint 1B's RAG sends Columbus only the top-3 800-char chunks per question
(~2,400 chars), joined in similarity order not reading order, with the query =
the latest user message only. An NCERT chapter is 25,000-35,000 chars / 30+
chunks, so Columbus never sees more than ~8-10% of it, a different slice each
question. That alone produces every F5 symptom: "fragments" on clean text,
non-overlapping citations between attempts, "can't say what is between X and
Y", asking the student for section headings, latching onto a cross-reference
to mis-call the chapter number. RAG was built to cut cost for factual lookups;
it is the wrong tool for "teach me this whole chapter".

### The fix
For a normal-sized chapter, stop retrieving. Put the WHOLE chapter text in the
tutor's context every question, and cache it so cost stays at RAG levels.
- Prompt caching (Anthropic, 1-hour extended TTL): the [persona + chapter]
  block is a stable prefix -> cached. Q1 pays a one-time cache write (~2x base
  on ~8-9K tokens, ~Rs 1.4); Q2+ read it at ~10% price (~Rs 0.07). Expected
  ~$0.13 / 30-question session vs the measured ~$0.50 today.
- 1-hour TTL not 5-minute: a student pauses >5 min often (reading the page,
  thinking); the 5-min cache would re-charge the write on each pause.
- Cost is flat-to-cheaper vs today AND the tutor sees the whole chapter in
  order every question. Full cost table + caching caveats: chat, Sep 2026.

### Usage model (confirmed Sep 2026)
AceIt is a subject-doubt tutor, not a revision drill. Disengaged student =
uploads, asks 1-2 questions, leaves = few calls = cheap regardless of caching.
Engaged student = 20+ min back-and-forth = many calls = caching amortises the
one write. No usage pattern blows cost up.

### Scope
- Tutor mode only (all three personas get the whole-chapter context; Columbus
  is where F5 bit).
- NO Columbus / persona prompt changes (that is 2D).
- Quiz mode untouched.
- rag.py is KEPT but demoted to an oversized-upload fallback (whole-textbook
  PDFs). Not deleted, not the default path anymore.

### Decisions (locked Sep 2026)
- 1-hour cache TTL via the extended-cache-ttl beta header.
- Size threshold: OVERSIZE_CHARS ~= 80,000 chars of extracted text (~20K
  tokens). Calibration: a real 24-page NCERT chapter (iest106.pdf) is 44K
  chars / ~11K tokens, so a big single chapter stays well under. Under ->
  whole chapter, no retrieval. Over -> RAG fallback with k ~= 12 and a
  one-time st.info "this looks like more than one chapter — upload just the
  chapter you need for best results".
- Light PDF-text cleanup before it becomes chapter_text: strip InDesign
  print-production footer lines (regex like r"^.*\.indd\s+\d+.*$") and
  standalone page-number lines. PyPDF2 splices these mid-sentence on every
  NCERT page (~700 chars of noise in iest106.pdf) — removing them helps both
  the "fragments" feel and cache-block cleanliness. New helper, e.g.
  rag.clean_pdf_text(raw) or inline in the upload handler.
- Cached prefix must be byte-stable. Order: [persona prompt (static)] then
  [chapter text (static per upload)] then the cache breakpoint, then the
  conversation messages. The uploaded filename stays OUT of the cached block
  (small uncached lead-in) so a re-upload under a different name still hits.
- Re-upload staleness: today app.py reloads only when uploaded_file.name
  changes, so a same-named replaced/edited file is silently ignored. Switch
  the guard to a content hash of the extracted text.

### Changes, file by file
rag.py:
- No public API change. Still chunk_text -> embed_texts -> build_index ->
  retrieve -> format_context. Used now only by the oversized fallback.
- retrieve(): return the k chunks in READING ORDER (original chunk index),
  not similarity order. Default k stays 3 for other callers; the tutor
  fallback passes k=12.
- build_index() only called when the upload is oversized.

app.py — upload handler (~L415-439):
- Extract raw text as today, then run the light PDF cleanup (strip .indd
  footers + bare page numbers) -> chapter_text.
- chapter_hash = hash of chapter_text; reload only when the hash changes
  (replaces the name-only check).
- chapter_oversized = len(chapter_text) > OVERSIZE_CHARS. Build rag_index
  only when oversized; otherwise leave rag_index None.

app.py — the answer block (~L527-551):
- context: chapter_oversized -> rag.format_context(rag.retrieve(index, query,
  k=12)); else -> the full chapter_text.
- system becomes a list of blocks:
  [ {type:text, text: persona + "Student is in <grade>. Answer only from the
     uploaded material below."},
    {type:text, text: "=== UPLOADED CHAPTER ===\n"+context+"\n=== END ===",
     cache_control: {type: ephemeral, ttl: "1h"}} ]
- client.messages.create(model=haiku, system=<blocks>, messages=<history>,
  + the 1h-TTL beta header). Exact SDK call for anthropic==0.120.2 confirmed
  against the claude-api skill / installed SDK before coding.
- Optional second cache breakpoint on the conversation history — covers the
  rest of F4. Decide during build whether to include it here.

app.py — session state:
- Add chapter_hash, chapter_oversized. rag_index kept (now conditional).
- Update the bot-switch and Clear-Chat resets for the new keys.

### Build order (each step = explain -> diff -> test)
0. Diagnostic — DONE Sep 2026 (scratchpad diag_pdf.py). iest106.pdf is a clean
   single chapter, ~11K tokens, "Electoral Roll" absent -> F5 is RAG
   fragmentation + boundary-backfill, not a multi-chapter file.
1. DONE. rag.clean_pdf_text() (strips .indd footers + trailing page numbers);
   app.py sends the whole cleaned chapter (rag_index built only when
   len > OVERSIZE_CHARS=80_000, else None -> answer block's existing `else`
   sends full chapter_text). New session key chapter_oversized + resets.
2. DONE. app.py answer block: `if context` system is now a 1-block list with
   cache_control {ephemeral, ttl 1h} (no beta header on anthropic==0.120.2).
   Filename removed from the instruction line (cache invalidator on re-upload;
   not load-bearing). Second cache breakpoint on messages[-1] for the history
   prefix. [cache] usage line printed per call.
3. DONE. app.py: hashlib.md5(uploaded_file.getvalue()) fingerprint replaces the
   name-only reload check (new key loaded_sig; image path sets "image:<name>").
   A same-named replaced file now reloads.
4. SKIPPED — not supporting multi-chapter for now (see STATUS above).
5. DONE in step 2 (messages[-1] cache breakpoint).
6. DONE — validated by the iest106.pdf test transcript.

### Acceptance test
- Clean NCERT chapter PDF: the tutor lists the chapter's real section
  structure, the same way across 5 repeated attempts, never says "fragments",
  never cites another chapter, never asks the student for headings.
- Anthropic console: Q1 cache-write, Q2+ cache-read; ~30-question session near
  ~$0.13 not ~$0.50.
- Oversized upload (whole textbook): one-time warning, app still answers.
- Re-upload a same-named edited file: new content used.

### Not in this sprint
- Columbus / persona prompt changes (2D: F2 source-lock, F3 genuine-garble).
- Photo upload (2B) — sequenced AFTER 2B-prime, feeds text into this path.

## Sprint 2B — Whole-chapter photo upload (Sep 2026, DONE — pending commit)
Goal: a Classes 7-8 student (no official chapter PDF, physical textbook only)
can photograph a full chapter and upload it. Fixes F1. Also serves Archimedes
and Shakespeare (photograph a problem / an exercise). Live-tested with Columbus
(soil + seasons tables) and Archimedes (figure-heavy maths chapter) — both
excellent.

### WHAT SHIPPED — "Path B" (supersedes the text-only plan below)
Deciding against pure OCR-to-text: on real phone photos, Google Vision
linearises a 3-column table only ~70% right and a 4-column / merged-cell table
much worse (the "Months of" seasons table came out scrambled). OCR also gives
nothing for diagrams, maps, flowcharts. Options B1 (hand-rolled geometry
reconstruction) and B2 (LLM over block coords) both failed the 4-column case in
testing. So:

- **OCR text stays** as a cheap fluent-reading layer for prose.
- **The downscaled page images also go into Haiku's context**, in a cached
  synthetic priming turn:
    system   = [ persona + OCR text ]                      cache_control 1h
    messages = [ user:[img_1..img_N, "my chapter pages"]   cache_control 1h
                 assistant:"I've looked at the pages."
                 ...real conversation... ]
  Haiku reads the actual table / diagram from the image. (Images are NOT
  allowed in `system` — API rejects them there; they must be in `messages`.)
- Caching verified in-app: a figure-heavy maths chapter = ~17.7K tokens, Q1
  `write=17666`, Q2+ `read=17666+`. Cost ~Rs 3 for Q1, ~Rs 0.5/question after.
- Table accuracy measured 6.5/7 on real photos incl. the merged-cell seasons
  table; the residual error is region-column bleed on a *rotated* photo — the
  "hold the phone straight" caption + Sprint 2D hedging cover it.
- No Mistral, no Document AI. Google Vision + Haiku only, keys already in use.
- PDF chapters (9-10) unchanged: text only, no page images (no PDF->image
  render yet). Revisit if PDF tables become a complaint.

Also in this commit: max_tokens 1500 -> 2500 for the tutor call (a
whole-chapter overview was hitting the 1500 cap and truncating).

### Historical plan (mostly as-built; note the Path B change above)

Scope: tutor mode only. The single-image "quick ask" path is REMOVED and folded
in — one uploader, one function handles 1..N images (1 image is just N=1). The
OCR'd page text feeds the SAME path a PDF chapter does (2B-prime decides
full-context vs oversized fallback) — no separate RAG handling. NO Columbus
prompt changes here (that is 2D). Quiz mode untouched.

Provider: Google Cloud Vision DOCUMENT_TEXT_DETECTION (locked Sep 2026).
- Auth: service-account JSON in st.secrets["gcp_service_account"]. Key created,
  Vision API enabled, billing + budget alert set. google-cloud-vision==3.15.0
  added to requirements.txt (also normalised that file from UTF-16 to UTF-8);
  verified it coexists with fastembed (shared protobuf 7.35.1 / grpcio, no
  conflict, pip check clean). Local credential test passed.
- Batch: client.batch_annotate_images, <=16 images/request, so a <=20-photo
  chapter is 1-2 calls, ~1-2s total. No per-page rate-limit handling needed.
- SUPERSEDED by Path B (see above): text-only was the plan; we now also send
  the page images. transcribe_images returns pages + jpegs + ocr_failed.

Decisions (locked Sep 2026):
- Photo cap: 20 images (a spread photo = 2 book pages; 20 covers either
  shooting style). Module constant, easy to retune.
- One merged uploader: PDF / TXT / one-to-many images. A mixed PDF+images
  upload is rejected with a short message.
- Page order = upload order. Caveat: Streamlit's multi-file uploader does not
  strictly guarantee selection order on every browser — verify in testing;
  fallback is "name photos 1,2,3 and sort by filename".
- Chapter-build budget: CHAPTER_BUILD_LIMIT = 8 image-based builds per session
  (raised from 3 — Archimedes/Shakespeare upload per-problem, not per-chapter;
  each build is only ~Rs 1-4 of cache write). MAX_PAGE_IMAGES = 20 per upload.
  New counter chapter_build_count; PDF/TXT builds stay uncounted. Replaces
  IMAGE_SESSION_LIMIT / image_session_count. A new upload REPLACES the loaded
  source (images + text); the conversation history stays.
- Partial failure: a page with no OCR text is kept (image still sent to Haiku);
  a one-time st.info names those page numbers.
- Uploader reset: st.file_uploader keeps its own state, so Clear Chat / bot-
  switch bump st.session_state.uploader_gen, which is in the widget `key`, to
  force it empty (otherwise the files re-process on the next rerun).

vision.py rewrite (AS BUILT):
- transcribe_images(images, credentials_info) -> {"pages": [str per image,
  "" if OCR found nothing], "jpegs": [downscaled JPEG bytes per image],
  "ocr_failed": [1-based indices]}. Client from credentials_info
  (st.secrets["gcp_service_account"]); falls back to
  GOOGLE_APPLICATION_CREDENTIALS for local scripts.
- _downscale_to_jpeg kept, _MAX_EDGE_PX 1568 -> 1600.
- DELETED: _transcribe_with_groq/_haiku, TranscriptionTruncatedError, all
  _GROQ_*/_HAIKU_* constants, module-level Groq/anthropic clients, the
  langchain/anthropic/base64/os/load_dotenv imports.
- test_vision.py: plain-script (no pytest), 7 cases with a fake Vision client,
  all passing.

Build order (each step is its own explain -> diff -> test cycle):
1. Secrets: .streamlit/secrets.toml (local) + .gitignore + Streamlit Cloud
   Edit Secrets. Confirm st.secrets loads.
2. vision.py: swap transcription internals to Google Vision; new tests; manual
   smoke test.
3. app.py: merge the two tutor-mode uploaders into one.
4. app.py: rewrite the upload handler (pdf/txt | all-images | mixed-reject;
   images -> downscale -> transcribe_images -> concat in order -> set
   chapter_text, same as a PDF; surface failed pages once).
5. app.py: counters + session state (chapter_build_count / loaded_via_photos;
   drop IMAGE_SESSION_LIMIT; remove the image branches in the user_input
   block; fix the bot-switch / clear-chat resets).
6. app.py: photo-source chapter banner.
7. End-to-end: real 8-12 page Class 7 chapter photos; Columbus full-chapter
   revision on its current prompt (any F3 stalls are logged for 2D, not fixed
   here).

Acceptance test: photograph a real 8-12 page Class 7 chapter, upload; every
page transcribes or partial-fails cleanly; chapter_text is built; Columbus (on
its current prompt) teaches the whole chapter from it. If Columbus stalls on
imperfect transcription that is F3 / Sprint 2D, not a 2B failure — record it
and continue.

## Sprint 2C — Tutor conversation cost control (FOLDED INTO 2B-prime, Sep 2026)
Status: DONE via 2B-prime + 2B. Caching the [persona + chapter] block and the
conversation-history prefix (2B-prime) plus the page-image priming turn (2B)
covers F4 — sessions measured at ~Rs 0.5/question after Q1. max_tokens bumped
1500 -> 2500 in the 2B commit (was truncating chapter overviews). What could
still be added later if measurements demand it: an optional last-N-turns
history window as a backstop for the rare >1-hour cache miss. Original plan
kept below for reference.

Goal: a long revision session stops costing multiples of the estimate, with
zero change to what the student sees or does. Fixes F4.

Hard constraints (Chaitra, Sep 2026):
- The student uses voice input and gives long, verbose answers during revision.
  That is expected and fine. Do NOT block, truncate, or shorten student input.
- Do NOT show the student any warning, notice, or nudge about message length or
  cost. All handling is invisible.
- The app absorbs verbose input without large cost overruns.

Approach (all invisible to the student):
- Prompt caching: mark the message history with cache_control so every re-sent
  turn bills at cache-read rate (~10% of input) instead of full price. Main
  lever — directly attacks "whole transcript resent every call." Use the
  1-hour cache TTL (beta header); the default 5-min TTL would expire during a
  student's thinking pauses.
- History window: send only the last N turns to the API (proposal: last ~20,
  or first turn + last ~18 so the session framing survives). Silent — the
  student still sees the full chat in the UI; only the request is trimmed.
  Caps the worst case even when the cache expires.
- Retrieve RAG context only on question turns, not on every message. A verbose
  answer turn is a poor retrieval query and currently triggers an embed call
  plus a fresh, cache-busting context block. Skipping it on answer turns cuts
  embed calls and lets the system block stay cacheable.
- Minor: a brevity instruction for Columbus's own replies + a small max_tokens
  trim (currently 1500). Assistant-side only; output length is a secondary
  factor per the evidence.

Explicitly NOT doing: summarising or compressing old turns (adds a call, risks
dropping detail the tutor needs to grade an answer); truncating student input.

Open decisions:
- Ship caching + window + retrieval-on-questions-only together, or caching
  first and measure?
- Window size N, and whether to pin the first turn.
- How to tell a question turn from an answer turn for the retrieval skip.

Acceptance test: scripted ~20-turn session with deliberately long (200+ word)
answer turns; console token cost compared before/after (target: at or below
the ~$0.09 the RAG estimate implies for 30 calls); Columbus still recalls a
fact from early in the session; the student-facing UI is byte-for-byte
unchanged.

## Sprint 2D — Columbus source integrity + graceful degradation (planned, Sep 2026)
Deferred until 2B is built and tested. Combines F2 and F3 — both are "Columbus
mishandles weak source text": one invents a source (student-typed text treated
as authoritative), one rejects a usable one ("fragments, re-upload"). One
Columbus-prompt hardening pass covers both.

F2: source lock in COLUMBUS_PROMPT (the chapter is only the delimited block in
the system prompt; chat text is never chapter content; never ask the student
to type it; never say "your chapter states..." about anything not in the
block) + a delimited context block in app.py's prompt assembly. Revised per
the F4 constraints: NO student-facing paste warning and NO input blocking —
the fix is prompt-only, the app does not police what the student types.

F3: prompt tells Columbus the chapter block may carry OCR/extraction noise, to
teach from usable content, ask for a re-upload only when there is essentially
nothing, and to hedge ("the chapter seems to say...") rather than assert when a
passage is unclear. Optional retrieval robustness (higher k, or low-score
fallback to raw text).

Also in scope here: guard for image-only PDFs uploaded via the PDF button ->
detect near-empty extraction, point the student at the photo uploader.

Not started. Full plan when 2B + 2C are done.

## Sprint 2A — planned: anonymous usage logging (Sep 2026)
Status: DEPRIORITIZED to after Sprint 2D. The F1-F4 live-test findings above
take precedence before the tool goes to the class.

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