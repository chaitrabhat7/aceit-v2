# AceIt v2 — Case Study

**A CBSE AI tutor built by a part-time tutor and returning-to-tech engineer, taken from prototype to a small live pilot.**

Live: https://aceit-v2-class7to10.streamlit.app/
Built by: Chaitra Bhat — BTech CS, part-time CBSE tutor, returning to software after 15 years.

---

## 1. The problem

CBSE students in Classes 7–10 need two things when they're stuck on a chapter: someone to explain it in a way that builds intuition (not just recite the textbook), and someone to quiz them on it afterward. A private tutor can do both, but doesn't scale to every student, every chapter, every evening before an exam.

AceIt is built to do the parts of that job an LLM is actually good at — patient, chapter-grounded explanation and instant practice quizzes — without pretending to replace the parts it isn't (a login system, a curriculum, a grade book).

## 2. Who it's for

A class of ~7 CBSE students, Classes 7–10, across three subjects. No accounts, no student data stored — a student opens the link, picks a tutor, and starts asking questions. Sessions are anonymous and stateless between visits by design (see [§7](#7-what-was-deliberately-not-built)).

## 3. The three tutors (personas)

| Persona | Subject | Teaching style | Model |
|---|---|---|---|
| **Archimedes** | Maths | Intuition before formula | Claude Haiku 4.5 |
| **Shakespeare** | English Grammar | Grammar through real sentences | Claude Haiku 4.5 |
| **Columbus** | Social Studies | Answers *only* from the uploaded chapter — never general knowledge | Claude Haiku 4.5 |

Columbus is the strictest and the most interesting engineering case — see [§6](#6-the-hard-part-columbus-and-five-live-test-findings).

## 4. Use cases

### 4.1 Tutor mode

- **Upload a chapter.** Two paths, chosen automatically by file type:
  - **PDF or TXT** (mainly Classes 9–10, which have official chapter PDFs): text extracted, lightly cleaned, sent to the tutor.
  - **Photos of textbook pages** (mainly Classes 7–8, which only have a physical book): 1–20 page photos, OCR'd via Google Cloud Vision, *and* the downscaled page images themselves are sent to the model — because OCR alone mangles tables, maps, and diagrams badly enough to be unusable (measured: a 4-column table came back scrambled). This dual text+image approach is called "Path B" internally.
  - A chapter that's clearly larger than one chapter (>80,000 characters, ~20K tokens) falls back to retrieval (RAG) over the whole document instead of whole-context, with a one-time note asking for a single chapter.
- **Ask questions.** Free-form chat, up to 30 questions per session. Columbus requires a chapter to be loaded first; Archimedes and Shakespeare work with or without one.
- **Switch tutors mid-session.** Clears the loaded chapter and chat history (a fresh persona starts clean).

### 4.2 Quiz mode

- **Two ways to pick a topic:** type one directly, or upload a PDF/TXT (capped at 25 pages / 1MB — a pre-launch fix, so this path has the same size guard tutor-mode chapter uploads already had) and let the app detect the topic.
- **Four difficulty levels:** Easy, Medium, Hard (all via Groq's free tier), and **HOTS** (Higher-Order Thinking Skills — via Claude Sonnet, because Groq's quality gap was too large for this tier in testing).
- **3–10 questions per quiz**, capped at 4 quiz-generation actions per session (an upload's topic-detection and the Generate button share this same counter).
- Quiz questions are always freshly generated, never copied from an uploaded document — even when a PDF was the topic source.

### 4.3 What's tracked

Usage logging, originally built fully anonymous — no student name, ID, or session identifier. For the trial pilot, each log row also carries a `student_id`, read automatically from a `?student=<name>` link given to each of the 10 trial students (no login, no typed name — just a per-student URL), so usage can be told apart during the trial without asking students to self-identify. Four event types (tutor question, PDF upload, photo upload, quiz generated), each with enough context (persona, grade, question text) to answer "how is the class actually using this." Written to both a local file and a Google Sheet, so the numbers survive Streamlit Community Cloud's non-persistent filesystem.

## 5. Architecture at a glance

```
Streamlit (UI + session state)
   ├── Tutor mode ─── Claude Haiku 4.5 (all 3 personas)
   │                   ├── PDF/TXT → PyPDF2 → clean → whole-chapter context (cached)
   │                   └── Photos  → Google Cloud Vision OCR + page images (cached)
   ├── Quiz mode  ─── Groq (Easy/Med/Hard, free) or Claude Sonnet (HOTS)
   ├── rag.py     ─── fastembed + NumPy cosine, used only as an oversized-chapter fallback
   └── usage_log.py ── local JSONL + Google Sheet (gspread)
```

No PyTorch, no ChromaDB, no sentence-transformers — deliberately, to stay under Streamlit Community Cloud's 1GB RAM ceiling. `fastembed`'s quantized ONNX embeddings do the one job that still needs embeddings (the oversized-document fallback).

## 6. The hard part: Columbus, and five live-test findings

The first live test (a real Class 7 student, parent watching, plus a separate Class 9–10 bug report) surfaced five distinct problems, all traced back to one root cause: **retrieval-based context (RAG) is the wrong tool for "teach me this whole chapter."**

| # | Finding | Root cause | Fix |
|---|---|---|---|
| F5 | Columbus cited content not in the uploaded chapter, and inconsistently across repeated attempts, even on a clean official PDF | Top-3-chunk retrieval showed the model only ~8–10% of the chapter, a different slice each question | **Sprint 2B-prime**: stop retrieving for normal-sized chapters — send the whole chapter, prompt-cached |
| F4 | A 1-hour, 30-question session cost ~$0.50 — 5.6x the per-question estimate | Full conversation history resent, uncached, every single call | Same fix — 1-hour prompt cache on both the chapter and the growing history |
| F1 | Classes 7–8 had no way to upload a *whole* chapter — only single photos, and no official PDF exists for them | Image path capped at 1 photo | **Sprint 2B**: multi-photo upload (up to 20 pages), OCR text + page images both fed to the model |
| F2 | Columbus sometimes asked the student to *type* the chapter, then treated that typed text as ground truth | No rule distinguishing "the uploaded chapter" from "anything in the chat" | **Sprint 2D**: explicit "what counts as the chapter" rule — chat text is never chapter content |
| F3 | Columbus stalled on OCR noise ("this looks incomplete") instead of teaching from what was readable | No guidance on how to handle imperfect scanned text | **Sprint 2D**: shared graceful-degradation instructions — hedge on unclear content, don't stall |

This sequence is the core engineering story of the project: a plausible-looking architecture (RAG for cost control) turned out to actively cause the product's worst bug, and the fix was to remove it for the common case rather than tune it further.

## 7. What was deliberately not built

No login/auth, no student database, no admin dashboard, no native mobile app, no multi-language support. Every one of these would have added real engineering weight to a 7-student pilot whose actual open question is simpler: *does the tutoring itself work well enough to be worth more investment?* Anonymous logging (§4.3) exists to answer that question with real usage data before committing to any of the above.

---

## 8. Cost model

All figures below use Anthropic's published per-token API pricing (verified at time of writing, not estimated from memory) and the app's own coded limits — not guesses about usage.

### 8.1 Pricing reference

| Model | Used for | Input $/1M tok | Output $/1M tok |
|---|---|---:|---:|
| Claude Haiku 4.5 | All 3 tutor personas | $1.00 | $5.00 |
| Claude Sonnet 4.6 | HOTS quiz only | $3.00 | $15.00 |
| Groq `openai/gpt-oss-120b` | Easy / Medium / Hard quiz | $0 (free tier) | $0 |

**Prompt caching (Haiku, 1-hour TTL, used throughout tutor mode):**
- Cache write: **2×** base input price ($2.00/1M tok)
- Cache read: **0.1×** base input price ($0.10/1M tok)
- Quiz mode uses neither model with caching — each quiz/topic-detect call is a single, uncached request.

### 8.2 Typical session (already measured in production)

From live testing on a real 24-page NCERT chapter (iest106.pdf, ~11K tokens): first question paid a cache write (~$0.03), every question after read from cache (~$0.01 each). A full ~30-question revision session lands close to **$0.13** — this is the caching architecture doing its job, and matches the Sprint 2B-prime acceptance test.

### 8.3 Worst-case session, Grade 9–10 student

Grades 9–10 use the PDF/TXT path only (no page-image tokens — that's the 7–8 photo path). "Worst case" below maxes out every dial the app allows a single student to touch in one sitting, with caching working normally (the realistic worst case, not a hypothetical failure):

**Assumptions (stated explicitly so the model can be checked/updated):**
- Largest single chapter allowed before the app switches to the cheaper RAG fallback: 80,000 characters ≈ 20,000 tokens (`OVERSIZE_CHARS` in `app.py`)
- Columbus's system prompt (the largest of the three) + shared instructions: ~1,000 tokens → cached system block ≈ **21,000 tokens**
- All 30 allowed tutor questions used (`TUTOR_QUESTION_LIMIT`)
- Each question is long and voice-transcribed (a real observed pattern) — 300 tokens
- Each answer hits the 2,500-token cap (`max_tokens` in the tutor call) every time
- All 4 allowed quiz generations used (`QUIZ_GENERATION_LIMIT`), each the most expensive combination: **HOTS difficulty, 10 questions**, topic typed directly (skipping PDF-detect is *more* expensive per generation than using it, since HOTS/Sonnet costs more per call than the Haiku topic-detect call it would replace)

**Tutor mode (30 questions, one persona, one chapter):**

| Component | Tokens | Rate | Cost |
|---|---:|---:|---:|
| System block: 1 cache write | 21,000 | $2.00/1M | $0.042 |
| System block: 29 cache reads | 609,000 | $0.10/1M | $0.061 |
| Growing history: cumulative reads across 30 turns | 1,218,000 | $0.10/1M | $0.122 |
| New question each turn: 30 cache writes | 9,000 | $2.00/1M | $0.018 |
| Answers: 30 × 2,500 tokens output | 75,000 | $5.00/1M | $0.375 |
| **Tutor subtotal** | | | **≈ $0.62** |

**Quiz mode (4 × HOTS, 10 questions each):**

| Component | Tokens | Rate | Cost |
|---|---:|---:|---:|
| Prompt input, 4 calls | ~2,000 | $3.00/1M | $0.006 |
| Output, 4 × 2,000-token cap | 8,000 | $15.00/1M | $0.120 |
| **Quiz subtotal** | | | **≈ $0.13** |

### **Worst-case total, one Grade 9–10 student, one sitting: ≈ $0.75 (~₹64 at ≈₹85/$1)**

Sanity check worth noting: splitting the same 30 questions across all three tutor personas in one sitting (nothing technically prevents this) costs almost exactly the same total — three shorter cache-write/read cycles instead of one long one — because the 30-question ceiling is a single shared counter regardless of how it's split. The architecture caps total exposure by design, not just in the common case.

### 8.4 Absolute ceiling — if caching never engages

A pathological edge case for reference: every question arrives more than an hour after the last (the cache TTL), so every single turn re-sends the full chapter and full growing history at uncached rates.

| | Cost |
|---|---:|
| Tutor mode, no caching at all | ≈ $2.23 |
| Quiz mode (unaffected — never cached anyway) | ≈ $0.13 |
| **Absolute ceiling per student, one sitting** | **≈ $2.36 (~₹200)** |

This closely matches the *actual pre-fix measurement* from the F4 finding (a real 1-hour/30-question session cost ~$0.50 before Sprint 2B-prime, with more typical — not worst-case — question/answer lengths), which is a useful cross-check that this model isn't off by an order of magnitude in either direction.

### 8.5 Class-wide exposure

For the pilot's ~7 students, even if every single one hit the realistic worst case in the same day: **7 × $0.75 ≈ $5.25 (~₹450)**. Even the pathological no-caching ceiling for all 7 students in one day is **≈ $16.50 (~₹1,400)**. Both are small enough that cost is not a constraint on running the pilot; the open questions are about answer quality and usage patterns, which is exactly what Sprint 2A's anonymous logging exists to surface.

### 8.6 Pre-launch fix: quiz-mode upload cap

Quiz-mode's PDF-topic-detection path (`detect_topic()`) originally had **no size cap** on the uploaded document — unlike the tutor path's 80,000-character oversized-fallback guard. A student uploading an unusually large document there (a full textbook rather than a chapter) would have cost proportionally more, uncached, with no warning shown. Fixed pre-launch: a 25-page / 1MB cap, checked before the file is even parsed, rejects an oversized upload with a friendly message instead of processing it.

---

## 9. Status

All planned sprints (1A, 1B, 1C, 2, 2B-prime, 2B, 2D, 2A) are complete and pushed, plus two pre-launch fixes for the trial pilot: the quiz-mode upload cap (§8.6) and per-student URL tracking (§4.3). The app is live and ready for the class pilot; usage data collection is the next input into deciding what (if anything) changes before a wider release.
