import streamlit as st
import anthropic
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
groq_client = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=2000,
    temperature=0.4
)
# NOTE: Groq output has been observed using LaTeX notation (e.g. \frac{24}{36})
# in question/explanation text. st.markdown won't render this as math unless
# wrapped in $...$, so it may show as raw backslash text in the quiz UI.

# ─── System Prompts ───────────────────────────────────────────
ARCHIMEDES_PROMPT = """You are Archimedes, a warm and encouraging CBSE Mathematics tutor for Class 7-10 students.
Students follow NCERT textbooks.

CRITICAL RULE - NO EXCEPTIONS:
NEVER solve a problem directly for the student.
If a student asks for the answer, respond only with a guiding question.
This rule overrides everything else in this prompt.

YOUR TEACHING STYLE:
You teach exactly like an experienced Indian maths tutor who knows her students well.

STEP 1 - ALWAYS MAKE THE STUDENT ATTEMPT FIRST:
Whether the topic is new or familiar, never show the solution before the student tries.

If topic appears new:
- Briefly introduce the concept in 1-2 lines.
- Then ask: "Now you try - what do you think the first step should be?"
- Wait for their attempt before showing anything.

If topic is familiar (visible from chat history):
- Skip introduction, go straight to a guiding question.
- Use the Socratic method - ask guiding questions.
- If they seem lost after 1-2 attempts, switch to direct explanation.

STEP 2 - YOUR SIGNATURE TRICKS:
- Only reveal shortcuts AFTER the student has attempted and shown their working.
- For linear equations: the MOVE and FLIP method (+ becomes -, x becomes divide).
- Teach the shortcut as a reward for attempting, not as an opener.
- Do not break down simple arithmetic steps like 8 divided by 2 into separate questions.

STEP 3 - CHECKING ANSWERS:
- ALWAYS verify the student's answer mathematically before responding.
- Use the appropriate verification method for the topic.
- If wrong, NEVER say "Perfect!", "Correct!" or "Well done!".
- Guide them to verify it themselves.
- Only praise after the correct answer is confirmed.

YOUR BOUNDARIES:
- Only discuss Maths topics relevant to Class 7-10 NCERT syllabus.
- Warmly redirect if student goes off topic.
- NEVER solve a problem directly. If a student asks for the answer, respond only with a guiding question. No exceptions."""

SHAKESPEARE_PROMPT = """You are Shakespeare, a warm, creative and encouraging CBSE Class 7-10 English Grammar tutor for students in India.

YOUR CORE PHILOSOPHY:
- Grammar is best learned in context, not in isolation
- Never teach a grammar rule without showing it alive in a real sentence or passage first
- Students must know correct terminology for exams — but understand it through natural use

YOUR TEACHING APPROACH:

For CONCEPT questions (e.g. "what is a verb?"):
- First give 2-3 natural sentences containing examples of that concept
- Ask the student to identify the pattern
- Guide them to discover the rule themselves
- Then give the formal exam-ready definition
- End with a quick practice question

For PASSAGE-BASED learning:
- When a student asks for a passage, first ask: "What difficulty would you like? Easy, Medium or Hard?"
- Easy: Short simple passage (5-6 sentences), basic vocabulary, one grammar concept
- Medium: One paragraph (8-10 sentences), moderate vocabulary, two grammar concepts
- Hard: Two paragraphs (12-15 sentences), rich vocabulary, multiple grammar concepts
- After the passage ask 3-4 questions

YOUR PERSONALITY:
- Warm and encouraging always
- Make English feel like storytelling, not memorisation
- Gently correct errors without embarrassing

YOUR BOUNDARIES:
- Only CBSE Class 7-10 English Grammar topics
- Never write essays or homework for students
- Guide them to write themselves

PASSAGE WRITING STYLE:
- Use Indian contexts — school life, festivals, cricket, family, markets, nature
- Characters should have Indian names
- Vocabulary appropriate to Class 7 level"""

COLUMBUS_PROMPT = """You are Columbus, a warm and engaging CBSE Social Studies tutor for Classes 7-10 students in India.

CRITICAL RULE:
- You ONLY answer from the uploaded chapter. If no chapter is uploaded, politely tell the student to upload their chapter PDF first before asking questions.
- Never answer Social Studies questions from general knowledge alone — always stay anchored to the textbook.

YOUR TEACHING APPROACH:

For CONCEPT questions:
- Explain concepts from the uploaded chapter in simple, story-like language
- Make history feel like an interesting story without diluting facts
- For civics concepts, always give a LOCAL real-world example the student can relate to:
  Example: "Your local Municipal Corporation works exactly like what this chapter describes about urban local bodies"
- For geography, connect physical features to places the student might know

For CURRENT AFFAIRS connections:
- Only when student specifically asks, connect the chapter concept to something happening in India or the world today
- Always make clear what is from the textbook and what is current affairs
- Never let current affairs overshadow the textbook content

For KEYWORD identification:
- When student asks for keywords from a section or paragraph, identify the 5-8 most important terms
- Explain why each keyword is important for exams
- Show how to use each keyword in a model answer sentence

For EXAM PREPARATION:
- Teach students to identify keywords while reading
- Show how keywords become the backbone of good answers
- Always use CBSE answer-writing format

YOUR PERSONALITY:
- Make history feel like an adventure, not a list of dates
- Civics should feel relevant to the student's actual life
- Geography should paint pictures in the student's mind
- Patient and encouraging always

YOUR BOUNDARIES:
- Stay strictly within the uploaded chapter
- NCERT textbook is your anchor — never wander far from it
- If student goes off topic, warmly redirect them back to the chapter
- Never write full answers for students — guide them to construct answers themselves"""

# ─── Bot Configuration ────────────────────────────────────────
BOTS = {
    "🧮 Maths — Archimedes": {
        "prompt": ARCHIMEDES_PROMPT,
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "topics": ["Algebra", "Geometry", "Trigonometry", "Statistics", "Mensuration"],
        "placeholder": "Ask Archimedes a maths question..."
    },
    "📚 English — Shakespeare": {
        "prompt": SHAKESPEARE_PROMPT,
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "topics": ["Nouns", "Pronouns", "Verbs", "Adjectives", "Adverbs",
           "Tenses", "Articles", "Prepositions", "Conjunctions",
           "Direct & Indirect Speech", "Active & Passive Voice",
           "Sentence Types", "Punctuation", "Clauses", 
           "Determiners", "Modals", "Subject-Verb Agreement",
           "Editing & Omission", "Gap Filling"],
        "placeholder": "Ask Shakespeare an English Grammar question..."
    },
    "🌍 Social Studies — Columbus": {
        "prompt": COLUMBUS_PROMPT,
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "topics": ["History", "Geography", "Civics", "Economics"],
        "placeholder": "Upload your chapter first, then ask Columbus anything..."
    }
}
# ─── Quiz Mode: Difficulty Instructions ───────────────────────
DIFFICULTY_INSTRUCTIONS = {
    "Easy": """
- Questions test direct concept recall
- One option is clearly correct, others are clearly wrong
- Simple straightforward language
""",
    "Medium": """
- Questions require one step of thinking beyond recall
- Options are plausible but one is clearly best
- Moderate language complexity
""",
    "Hard": """
- Questions test application of concepts to new situations
- No direct answers from textbook
- All options feel somewhat plausible
- Student must think before answering
""",
    "HOTS": """
- Higher Order Thinking Skills questions ONLY
- No question should have a direct answer from the textbook
- Student must APPLY concept to an unfamiliar situation
- ALL 4 options must be plausible — no obviously wrong options
- Wrong options must represent common misconceptions
- Question stems must use: "What would happen if...", 
  "Why does...", "A student observes that... what can you conclude", 
  "Which of these BEST explains..."
- Explanation must explain WHY each wrong option is wrong,
  not just why the correct one is right
- Student should need at least 60 seconds to answer
"""
}

QUIZ_SUBJECTS = {
    "🧮 Maths": {
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "full_name": "Mathematics"
    },
    "📚 English": {
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "full_name": "English Grammar"
    },
    "🌍 Social Studies": {
        "grades": ["Class 7", "Class 8", "Class 9", "Class 10"],
        "full_name": "Social Studies"
    }
}

# ─── Quiz Mode: Core Functions ────────────────────────────────
def build_quiz_prompt(subject, grade, difficulty,
                      num_questions, topic=None, chapter_text=None):

    diff_instructions = DIFFICULTY_INSTRUCTIONS[difficulty]

    if chapter_text:
        if difficulty != "Easy":
            application_note = "Questions must test APPLICATION. No direct recall answers."
        else:
            application_note = "Questions can test direct concept recall."

        content_section = (
            f"The student uploaded a document.\n"
            f"Detected topic: {topic}\n\n"
            f"Generate {num_questions} FRESH MCQs on this topic.\n"
            f"Do NOT copy or reuse any questions from the uploaded content.\n"
            f"Generate completely new questions that test the same concept.\n\n"
            f"{application_note}"
        )
    else:
        content_section = f"Subject: {subject}\nTopic: {topic}\nCBSE {grade} syllabus"

    return (
        f"Generate {num_questions} CBSE {grade} {subject} MCQs.\n\n"
        f"{content_section}\n\n"
        f"Difficulty: {difficulty}\n"
        f"{diff_instructions}\n\n"
        f"STRICT OUTPUT RULES:\n"
        f"- Respond with ONLY a valid JSON array. Nothing else.\n"
        f"- No markdown, no code blocks, no explanation before or after.\n"
        f"- If the topic is not relevant to {subject} for {grade} CBSE syllabus,\n"
        f"  respond with exactly: [{{\"error\": \"invalid_topic\"}}]\n"
        f"- Each question MUST follow this EXACT structure:\n\n"
        f"[\n"
        f"  {{\n"
        f"    \"question\": \"string\",\n"
        f"    \"options\": {{\n"
        f"      \"A\": \"string\",\n"
        f"      \"B\": \"string\",\n"
        f"      \"C\": \"string\",\n"
        f"      \"D\": \"string\"\n"
        f"    }},\n"
        f"    \"answer\": \"A or B or C or D\",\n"
        f"    \"explanation\": \"string\"\n"
        f"  }}\n"
        f"]"
    )


def generate_quiz(subject, grade, difficulty, num_questions,
                  topic=None, chapter_text=None):

    prompt = build_quiz_prompt(subject, grade, difficulty,
                               num_questions, topic, chapter_text)

    if difficulty == "HOTS":
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text
    else:
        response = groq_client.invoke(prompt)
        raw = response.content

    clean = raw.replace("```json", "").replace("```", "").strip()
    if "[" in clean:
        clean = clean[clean.index("["):]
    
    return json.loads(clean)

def detect_topic(subject, grade, chapter_text):
    
    prompt = f"""Analyse this uploaded content carefully.
It may be a textbook chapter, a quiz, a worksheet, 
or a question paper.

CONTENT:
{chapter_text}

Your job:
1. Identify the main topic(s) being covered or tested
2. Confirm which CBSE grade level it appears to be for

Respond with ONLY this JSON structure, nothing else:
{{
    "detected_topic": "string — main topic in 3-5 words",
    "detected_grade": "string — e.g. Class 9",
    "confidence": "high or medium or low",
    "summary": "string — one sentence describing what this content covers"
}}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


# ─── Initialize Session State ─────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_bot" not in st.session_state:
    st.session_state.current_bot = None
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_revealed" not in st.session_state:
    st.session_state.quiz_revealed = {}
if "quiz_topic" not in st.session_state:
    st.session_state.quiz_topic = ""
if "quiz_grade" not in st.session_state:
    st.session_state.quiz_grade = ""
if "quiz_difficulty" not in st.session_state:
    st.session_state.quiz_difficulty = ""
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "student_answers" not in st.session_state:
    st.session_state.student_answers = {}


# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(page_title="AceIt", page_icon="🎯", layout="centered")

# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 AceIt")
    st.caption("Your CBSE AI Tutor")
    st.divider()
    st.caption("⬆️ Tutor Mode controls only")

    selected_bot = st.selectbox("Choose your tutor", list(BOTS.keys()))

    # Reset chat if bot changes
    if st.session_state.current_bot != selected_bot:
        st.session_state.messages = []
        st.session_state.chapter_text = ""
        st.session_state.loaded_file = ""
        st.session_state.current_bot = selected_bot

    bot = BOTS[selected_bot]
    grade = st.selectbox("Class", bot["grades"])
    topic = st.selectbox("Topic", bot["topics"])

    st.divider()
    uploaded_file = st.file_uploader("📄 Upload Chapter (PDF or TXT)", type=["pdf", "txt"])
    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.chapter_text = ""
        st.session_state.loaded_file = ""

# ─── File Upload Handler ──────────────────────────────────────
if uploaded_file:
    if uploaded_file.name != st.session_state.get("loaded_file"):
        if uploaded_file.type == "text/plain":
            st.session_state.chapter_text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                st.session_state.chapter_text = ""
                for page in pdf_reader.pages:
                    st.session_state.chapter_text += page.extract_text()
            except Exception as e:
                st.error(f"❌ Could not read PDF: {e}")
        st.session_state.loaded_file = uploaded_file.name

chapter_text = st.session_state.get("chapter_text", "")
# ─── TABS ─────────────────────────────────────────────────────
tutor_tab, quiz_tab = st.tabs(["💬 Tutor Mode", "🧠 Quiz Mode"])
with tutor_tab:
    # ─── Main Area ────────────────────────────────────────────────
    st.title("🎯 AceIt")
    st.subheader(f"{selected_bot} • {grade}")
    st.divider()

    # Chapter indicator
    if st.session_state.get("loaded_file"):
        st.success(f"📖 Answering from: **{st.session_state.loaded_file}**")
    else:
        st.warning("⚠️ No chapter uploaded — tutor is using general knowledge.")

    # Force PDF upload for Columbus
    if selected_bot == "🌍 Social Studies — Columbus" and not st.session_state.get("loaded_file"):
        st.error("📚 Columbus works only with uploaded chapters. Please upload your Social Studies chapter PDF from the sidebar first!")
        st.stop()

  # Display chat history
    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

    # Handle input
    user_input = st.chat_input(bot["placeholder"])

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.spinner("Thinking..."):
            if chapter_text:
                active_system = bot["prompt"] + f"\n\nStudent is in {grade}. Answer STRICTLY from uploaded chapter: '{st.session_state.loaded_file}'.\nContent:\n{chapter_text}"
            else:
                active_system = bot["prompt"] + f"\n\nStudent is in {grade}. Use general NCERT knowledge."

            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1500,
                system=active_system,
                messages=st.session_state.messages
            )
            reply = response.content[0].text

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
with quiz_tab:
    st.title("🧠 Quiz Mode")
    st.caption("Generate MCQs instantly — by topic or from your own PDF")
    st.divider()

    # ── Subject + Grade ───────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        quiz_subject_key = st.selectbox(
            "Subject",
            list(QUIZ_SUBJECTS.keys()),
            key="quiz_subject"
        )
    with col2:
        quiz_grade = st.selectbox(
            "Class",
            QUIZ_SUBJECTS[quiz_subject_key]["grades"],
            key="quiz_grade_select"
        )

    quiz_subject = QUIZ_SUBJECTS[quiz_subject_key]["full_name"]

    # ── Input Method ──────────────────────────────────────────
    input_method = st.radio(
        "How would you like to generate the quiz?",
        ["📝 Type a topic", "📄 Upload a PDF"],
        horizontal=True,
        key="quiz_input_method"
    )

    quiz_topic = None
    quiz_chapter_text = None

    if input_method == "📝 Type a topic":
        quiz_topic = st.text_input(
            "Enter topic",
            placeholder="e.g. Fractions, Tenses, French Revolution",
            key="quiz_topic_input"
        )

    else:
        quiz_pdf = st.file_uploader(
            "Upload a chapter, worksheet or question paper (PDF or TXT)",
            type=["pdf", "txt"],
            key="quiz_pdf_uploader"
        )

        if quiz_pdf:
            if quiz_pdf.type == "text/plain":
                quiz_chapter_text = quiz_pdf.read().decode("utf-8")
            elif quiz_pdf.type == "application/pdf":
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(quiz_pdf)
                    quiz_chapter_text = ""
                    for page in pdf_reader.pages:
                        quiz_chapter_text += page.extract_text()
                except Exception as e:
                    st.error(f"❌ Could not read PDF: {e}")

            if quiz_chapter_text:
                with st.spinner("📖 Reading your document..."):
                    try:
                        detected = detect_topic(
                            quiz_subject, quiz_grade, quiz_chapter_text
                        )
                        quiz_topic = detected["detected_topic"]
                        st.success(
                            f"📌 Detected: **{detected['detected_topic']}** "
                            f"— {detected['summary']}"
                        )
                    except Exception as e:
                        st.error(f"❌ Could not detect topic: {e}")

    st.divider()

    # ── Difficulty + Question Count ───────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        quiz_difficulty = st.selectbox(
            "Difficulty",
            ["Easy", "Medium", "Hard", "HOTS"],
            key="quiz_difficulty_select"
        )
    with col4:
        num_questions = st.slider(
            "Number of Questions",
            min_value=3,
            max_value=10,
            value=5,
            key="quiz_num_questions"
        )

    if quiz_difficulty == "HOTS":
        st.info("💡 HOTS uses a more powerful AI model for deeper questions. May take a few extra seconds.")

    st.divider()

    # ── Generate Button ───────────────────────────────────────
    if st.button("⚡ Generate Quiz", type="primary", key="quiz_generate_btn"):
        if not quiz_topic:
            st.warning("⚠️ Please enter a topic or upload a PDF first.")
        else:
            with st.spinner(f"Generating {num_questions} {quiz_difficulty} questions on '{quiz_topic}'..."):
                try:
                    questions = generate_quiz(
                        subject=quiz_subject,
                        grade=quiz_grade,
                        difficulty=quiz_difficulty,
                        num_questions=num_questions,
                        topic=quiz_topic,
                        chapter_text=quiz_chapter_text
                    )

                    if questions and "error" in questions[0]:
                        st.error("❌ Topic doesn't seem relevant to this subject and grade. Please try a different topic.")
                        st.session_state.quiz_questions = []
                    else:
                        st.session_state.quiz_questions = questions
                        st.session_state.quiz_revealed = {}
                        st.session_state.quiz_topic = quiz_topic
                        st.session_state.quiz_grade = quiz_grade
                        st.session_state.quiz_difficulty = quiz_difficulty

                except Exception as e:
                    st.error(f"❌ Something went wrong: {e}")

    # ── Display Questions ─────────────────────────────────────
    if st.session_state.quiz_questions:
        st.divider()
        st.subheader(
            f"📋 {st.session_state.quiz_topic} — "
            f"{st.session_state.quiz_grade} — "
            f"{st.session_state.quiz_difficulty}"
        )

        if st.session_state.quiz_difficulty in ["Hard", "HOTS"]:
            st.caption("⚠️ For Hard and HOTS questions, always verify calculations independently.")

        # ── Student answers dict ──────────────────────────────
        if "student_answers" not in st.session_state:
            st.session_state.student_answers = {}

        # ── Render questions with radio buttons ───────────────
        for i, q in enumerate(st.session_state.quiz_questions):
            st.markdown(f"**Q{i+1}. {q['question']}**")

            options = [f"{k}. {v}" for k, v in q["options"].items()]
            selected = st.radio(
                f"Select answer for Q{i+1}",
                options,
                key=f"q_{i}",
                index=None,
                label_visibility="collapsed"
            )

            if selected:
                st.session_state.student_answers[i] = selected[0]  # store just A/B/C/D

            st.markdown("")

        st.divider()

        # ── Submit Button ─────────────────────────────────────
        if st.button("📝 Submit Quiz", type="primary", key="quiz_submit"):
            answered = len(st.session_state.student_answers)
            total = len(st.session_state.quiz_questions)

            if answered < total:
                st.warning(f"⚠️ You've answered {answered}/{total} questions. Please answer all before submitting.")
            else:
                st.session_state.quiz_submitted = True

        # ── Report ────────────────────────────────────────────
        if st.session_state.get("quiz_submitted"):
            st.divider()
            st.subheader("📊 Your Results")

            score = 0
            report_lines = []
            report_lines.append(f"QUIZ REPORT")
            report_lines.append(f"Topic     : {st.session_state.quiz_topic}")
            report_lines.append(f"Class     : {st.session_state.quiz_grade}")
            report_lines.append(f"Difficulty: {st.session_state.quiz_difficulty}")
            report_lines.append("=" * 50)

            for i, q in enumerate(st.session_state.quiz_questions):
                student_ans = st.session_state.student_answers.get(i, "")
                correct_ans = q["answer"]
                is_correct = student_ans == correct_ans

                if is_correct:
                    score += 1
                    st.success(f"✅ Q{i+1}. {q['question']}")
                    report_lines.append(f"Q{i+1}: ✅ CORRECT")
                else:
                    st.error(f"❌ Q{i+1}. {q['question']}")
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;**Your answer:** {student_ans} — "
                        f"{q['options'].get(student_ans, 'Not answered')}"
                    )
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;**Correct answer:** {correct_ans} — "
                        f"{q['options'][correct_ans]}"
                    )
                    report_lines.append(f"Q{i+1}: ❌ WRONG")
                    report_lines.append(f"      Your answer   : {student_ans}. {q['options'].get(student_ans, 'Not answered')}")
                    report_lines.append(f"      Correct answer: {correct_ans}. {q['options'][correct_ans]}")

                st.info(f"💡 {q['explanation']}")
                st.divider()
                report_lines.append(f"      Explanation  : {q['explanation']}")
                report_lines.append("")

            # ── Score summary ─────────────────────────────────
            percentage = round((score / len(st.session_state.quiz_questions)) * 100)
            st.subheader(f"🎯 Score: {score}/{len(st.session_state.quiz_questions)} ({percentage}%)")

            if percentage == 100:
                st.balloons()
                st.success("Perfect score! Outstanding work! 🌟")
            elif percentage >= 60:
                st.success("Good effort! Review the ones you got wrong. 💪")
            else:
                st.warning("Keep practising! Go back to Tutor Mode to revise these concepts. 📚")

            report_lines.insert(4, f"Score     : {score}/{len(st.session_state.quiz_questions)} ({percentage}%)")
            report_lines.insert(5, "=" * 50)
            report_lines.insert(6, "")

            # ── PDF Generation ────────────────────────────────
            from fpdf import FPDF

            def generate_pdf_report(topic, grade, difficulty,
                                   score, total, questions,
                                   student_answers):
                def safe(text, width=180):
                    # Clean text to latin-1 safe characters
                    return text.encode('latin-1', 'replace').decode('latin-1')

                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_margins(15, 15, 15)
                effective_width = pdf.w - 40  # page width minus margins

                # Title
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(effective_width, 10, "AceIt Quiz Report", ln=True, align="C")
                pdf.ln(3)

                # Metadata
                pdf.set_font("Helvetica", "", 11)
                percentage = round((score / total) * 100)
                for line in [
                    f"Topic      : {topic}",
                    f"Class      : {grade}",
                    f"Difficulty : {difficulty}",
                    f"Score      : {score}/{total} ({percentage}%)"
                ]:
                    pdf.cell(effective_width, 7, safe(line), ln=True)

                pdf.ln(3)
                pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())
                pdf.ln(5)

                for i, q in enumerate(questions):
                    student_ans = student_answers.get(i, "")
                    correct_ans = q["answer"]
                    is_correct = student_ans == correct_ans

                    # Question
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.set_x(15)
                    pdf.multi_cell(effective_width, 7,
                                   safe(f"Q{i+1}. {q['question']}"))
                    pdf.ln(1)

                    # Options
                    pdf.set_font("Helvetica", "", 10)
                    for letter, text in q["options"].items():
                        pdf.set_x(15)
                        pdf.multi_cell(effective_width, 6,
                                       safe(f"{letter}. {text}"))

                    pdf.ln(2)

                    # Result
                    pdf.set_font("Helvetica", "B", 10)
                    if is_correct:
                        result = f"Result: CORRECT (Your answer: {student_ans})"
                    else:
                        your_opt = q['options'].get(student_ans, 'Not answered')
                        correct_opt = q['options'][correct_ans]
                        result = (f"Result: WRONG \n "
                                  f"Your answer: {student_ans}. {your_opt} | "
                                  f"Correct: {correct_ans}. {correct_opt}")
                        
                    pdf.set_x(15)
                    pdf.multi_cell(effective_width, 6, safe(result))
                    pdf.ln(2)

                    # Explanation — split into chunks if too long
                    pdf.set_font("Helvetica", "I", 10)
                    pdf.set_x(15)
                    exp = safe(f"Explanation: {q['explanation']}")
                    pdf.multi_cell(effective_width, 6, exp)

                    pdf.ln(4)
                    pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())
                    pdf.ln(4)

                return pdf.output()
            try:
                pdf_bytes = generate_pdf_report(
                    st.session_state.quiz_topic,
                    st.session_state.quiz_grade,
                    st.session_state.quiz_difficulty,
                    score,
                    len(st.session_state.quiz_questions),
                    st.session_state.quiz_questions,
                    st.session_state.student_answers
                )
                pdf_ok = True
            except Exception as pdf_err:
                st.error(f"PDF error: {pdf_err}")
                pdf_ok = False

            col_a, col_b = st.columns(2)

            with col_a:
                if pdf_ok:
                    st.download_button(
                        label="⬇️ Download Report (PDF)",
                        data=bytes(pdf_bytes),
                        file_name=f"aceit_report_{st.session_state.quiz_topic.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key="download_report"
                    )

            with col_b:
                if st.button("🔄 New Quiz", key="new_quiz"):
                    st.session_state.quiz_questions = []
                    st.session_state.quiz_revealed = {}
                    st.session_state.student_answers = {}
                    st.session_state.quiz_submitted = False
                    st.rerun()

            
