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
Next: Sprint 1B — RAG for Columbus PDF uploads.
Then: Sprint 1C — session-level rate limiting.

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