# AceIt v2 — Claude Project Instructions
## CBSE AI Learning Platform | Classes 7–10 | Go-Live Focused

---

## PURPOSE OF THIS PROJECT

Build AceIt v2 to production-ready state as fast as possible.
Target users: Chaitra's own kids first → her tuition class students → LinkedIn public release.
Every build decision optimises for: working fast, costing less, shipping sooner.

---

## CURRENT STATE (as of Sep 2026)

- **Live URL:** https://aceit-v2-class7to10.streamlit.app/
- **GitHub:** https://github.com/chaitrabhat7/aceit-v2
- **Stack:** Python, Streamlit, Claude API (Anthropic), PyPDF2, fpdf2
- **Models in use:** Claude Haiku (standard quiz), Claude Sonnet (HOTS quiz + all tutor mode)
- **What works:** Quiz mode (MCQ generation, 4 difficulty levels, PDF report), Tutor mode (Archimedes, Shakespeare, Columbus personas)
- **What is broken/missing:** No RAG (PDF costs explode), no image upload, no model switching, no rate limiting, open-ended API calls per user

---

## TECH STACK — FULL BUILD

| Layer | Tool | Purpose |
|---|---|---|
| UI | Streamlit | Web app frontend — no change |
| AI (tutor + HOTS) | Claude Sonnet via Anthropic SDK | Pedagogical complexity — do not swap |
| AI (standard quiz) | Groq API (Llama 3 or Mixtral) via LangChain | Cost reduction — free tier sufficient |
| Model abstraction | LangChain `ChatAnthropic` + `ChatGroq` | Clean model swapping without rewriting logic |
| RAG | LangChain + ChromaDB (local) | Chunk, embed, retrieve before sending to LLM |
| Embeddings | `sentence-transformers` (HuggingFace, free) | No API cost for embeddings |
| PDF reading | PyPDF2 (existing) | Keep for text PDFs |
| Image reading | Claude Vision API (Anthropic) | Send image bytes directly — no OCR step needed |
| PDF report output | fpdf2 (existing) | Keep — working |
| Deployment | Streamlit Community Cloud | Keep — free, already configured |
| Version control | GitHub | Keep |

---

## PRIORITY ORDER — BUILD SPRINTS

### SPRINT 1 — Cost Control (Do First, Blocks Everything Else)
**Goal:** Share the live link without anxiety.

**1A. Model swap — Quiz Mode**
- Replace direct Anthropic Haiku calls in quiz mode with LangChain `ChatGroq`
- Use `llama3-8b-8192` on Groq free tier for Easy/Medium/Hard difficulty
- Keep Claude Sonnet for HOTS only (requires reasoning depth Groq cannot match)
- LangChain abstraction means one config change swaps the model — do not rewrite prompt logic

**Implementation pattern:**
```python
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq

def get_quiz_model(difficulty: str):
    if difficulty == "HOTS":
        return ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1000)
    else:
        return ChatGroq(model="llama3-8b-8192", max_tokens=1000)
```

**Test:** Generate 10 quizzes each at Easy, Medium, Hard via Groq. Confirm JSON is clean and parseable. Generate 5 HOTS via Sonnet. Confirm quality gap is real. Log cost per run in a test sheet.

---

**1B. RAG for Columbus (Social Studies PDF uploads)**
- This is the main cost explosion point — full PDF sent to LLM on every question
- Replace with: chunk PDF → embed → store in ChromaDB → retrieve top 3 chunks per question → send only chunks to LLM

**Implementation pattern:**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def build_rag_index(pdf_text: str) -> Chroma:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_text(pdf_text)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return Chroma.from_texts(chunks, embeddings)

def get_context(vectorstore: Chroma, query: str) -> str:
    docs = vectorstore.similarity_search(query, k=3)
    return "\n\n".join([d.page_content for d in docs])
```

- Store the ChromaDB index in `st.session_state` so it persists for the session without rebuilding on every question
- Rebuild index only when a new PDF is uploaded

**Test:** Upload a 30-page NCERT chapter. Ask 10 questions. Confirm answers are accurate. Check token usage in Anthropic console — should be 80%+ reduction vs current. Ask a question not in the PDF — Columbus must say "I cannot find this in the uploaded chapter."

---

**1C. Session-level rate limiting**
- Add a simple per-session question counter in `st.session_state`
- Hard cap: 30 questions per session (tutor mode) + 3 quiz generations per session
- Show remaining count in sidebar
- Reset on page refresh (session = browser session, no auth needed)

```python
if st.session_state.get("question_count", 0) >= 30:
    st.warning("Session limit reached. Refresh to start a new session.")
    st.stop()
```

**Test:** Hit the limit deliberately. Confirm app stops cleanly. Confirm counter resets on refresh.

---

### SPRINT 2 — Image Upload (Must-Have for Real Use)
**Goal:** Students can photograph textbook pages instead of finding PDFs.

**Why this is simpler than you think:** Claude Vision API accepts base64 image bytes directly. No OCR, no conversion, no third-party service. Send the image with the question and Claude reads it.

**2A. Image upload for Columbus (textbook page photos)**
- Add `st.file_uploader` accepting `jpg, jpeg, png` in addition to `pdf`
- Convert uploaded image to base64
- Send as vision message to Claude Sonnet: `[image_block, text_block]`
- Do NOT run RAG on images — send image directly each time (images are already compressed, cost is manageable)
- RAG only for PDFs

**Implementation pattern:**
```python
import base64
from anthropic import Anthropic

def ask_columbus_with_image(image_bytes: bytes, question: str, client: Anthropic) -> str:
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": f"You are Columbus. Answer ONLY from what is visible in this textbook page. Question: {question}"}
            ]
        }]
    )
    return response.content[0].text
```

**2B. Image upload for Quiz Mode**
- Same pattern — upload textbook page image, generate MCQs from visible content
- Useful when PDF is not available (private school textbooks)

**Test:** Photograph a textbook page with phone. Upload. Ask 3 questions. Confirm answers are grounded in the page. Upload a blurry photo — confirm graceful error message. Generate a quiz from an image — confirm MCQs are from visible content only.

---

### SPRINT 3 — Voice Input (Nice to Have)
**Goal:** Student speaks question instead of typing.

- Use Streamlit's `st.audio_input` (available in Streamlit 1.31+) or `streamlit-webrtc`
- Send audio to OpenAI Whisper API (cheapest transcription option, ~$0.006/min)
- Feed transcript into existing question flow — no other change needed

**Test:** Speak a maths question. Confirm transcript is accurate. Confirm Archimedes responds correctly. Test with Indian-accented English — Whisper handles it well.

**Note:** Do not build this until Sprint 1 and 2 are live and tested with real students.

---

### SPRINT 4 — Phone UI (Post-Live)
- Streamlit apps are mobile-accessible via browser — test on phone first before building a native app
- If browser works for image upload from camera roll, no native app needed
- Defer native app decision until you have 20+ active student users giving feedback

---

## TESTING PROTOCOL — EVERY FEATURE

Before marking any feature done, run this checklist:

| Test Type | What to Check |
|---|---|
| Happy path | Feature works as expected with normal input |
| Edge case | Empty input, very long input, unsupported file type |
| Cost check | Check Anthropic console after each test session — log token usage |
| Student simulation | Give device to your kid, watch without helping — where do they get stuck? |
| Accuracy check | Ask 5 questions you know the answer to — verify AceIt is correct |
| Failure mode | What happens when API is down or returns error? App must not crash silently |

---

## COST TARGETS (post-Sprint 1)

| Mode | Current cost estimate | Target post-Sprint 1 |
|---|---|---|
| Quiz (Easy/Medium/Hard) | ~$0.003/quiz (Haiku) | ~$0.000/quiz (Groq free tier) |
| Quiz (HOTS) | ~$0.008/quiz (Sonnet) | Same — keep Sonnet |
| Tutor mode (per question) | ~$0.002/question (Sonnet) | Same — keep Sonnet |
| Columbus with PDF (per question) | ~$0.02–0.05/question (full PDF) | ~$0.003/question (RAG, 3 chunks only) |

---

## GO-LIVE CHECKLIST

- [ ] Sprint 1 complete — model swap + RAG + rate limiting
- [ ] Sprint 2 complete — image upload working on desktop and mobile browser
- [ ] Tested by Chaitra's own kids for 1 week with no major issues
- [ ] Case study updated with new features
- [ ] GitHub README updated with live link and feature list
- [ ] LinkedIn post drafted — problem/solution/demo format
- [ ] Shared with tuition class students for feedback round
- [ ] Public LinkedIn post published

---

## SYSTEM PROMPT REFERENCE — DO NOT CHANGE THESE

These personas are the core differentiation. Edit only if pedagogically necessary.

- **Archimedes** — teaches intuition before formula, verifies student answers mathematically before praise, CBSE Maths Classes 7–10
- **Shakespeare** — teaches grammar through real sentences, never rote rules, CBSE English Classes 7–10
- **Columbus** — answers ONLY from uploaded chapter content, never from general knowledge, CBSE Social Studies Classes 7–10

---

## WHAT NOT TO BUILD (SCOPE LOCK)

Until 20+ active student users and at least 2 paying clients:
- No login/auth system
- No student progress database
- No admin dashboard
- No native mobile app (test browser mobile first)
- No multi-language support
- No additional subjects beyond Maths, English, Social Studies

---

## DEPENDENCIES — INSTALL LIST

```bash
pip install streamlit anthropic langchain langchain-anthropic langchain-groq \
            langchain-community langchain-huggingface \
            chromadb sentence-transformers \
            PyPDF2 fpdf2 python-dotenv groq
```

---

## ENV VARIABLES REQUIRED

```
ANTHROPIC_API_KEY=
GROQ_API_KEY=       # Free at console.groq.com
```
Update ACEIT_PROJECT_INSTRUCTIONS.md — correct the model routing table to:
- Quiz Easy/Medium/Hard: Groq llama-3.3-70b-versatile (free tier)
- Quiz HOTS: claude-sonnet-4-6
- All tutor personas (Archimedes, Shakespeare, Columbus): claude-haiku-4-5

This is the verified state from actual code, not the original plan.