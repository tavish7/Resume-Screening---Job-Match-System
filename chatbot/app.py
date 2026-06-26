import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from build_db import ensure_db

ensure_db()

from resbot import db, graph, prompts, resume_ingest
from resbot.llm import MissingApiKey, ask

st.set_page_config(page_title="ResBot", page_icon="\N{ROBOT FACE}", layout="wide")

GREETING = (
    "Hi, I'm **ResBot** \N{ROBOT FACE} - your recruitment data assistant. "
    "I answer only from this project's data (job postings, companies, candidates and match results), "
    "in plain English. Try asking:\n\n"
    "- *Which industries hire the most remote roles?*\n"
    "- *What does the overall suitability breakdown look like?*\n"
    "- *What are the most in-demand skills for data roles?*\n\n"
    "Want to check a specific resume against a job? Head to the **Resume Checker** tab."
)


def skills_line(skills):
    return ", ".join(skills) if skills else "_none found_"


def resume_qa(question, ctx):
    a = ctx["analysis"]
    filled = prompts.RESUME_QA.format(
        suitability=a["suitability"],
        score=a["match_score"],
        resume_skills=skills_line(a["resume_skills"]),
        job_skills=skills_line(a["job_skills"]),
        matching=skills_line(a["matching_skills"]),
        missing=skills_line(a["missing_skills"]),
        resume_excerpt=ctx["resume_text"][:1500],
        jd_excerpt=ctx["jd_text"][:1500],
        question=question,
    )
    return ask([("system", prompts.PERSONA), ("human", filled)])


# ---- sidebar -------------------------------------------------------------
with st.sidebar:
    st.header("ResBot")
    try:
        counts = db.table_counts()
        st.success("Connected to the recruitment data.")
        st.caption(f"{counts['jobs']:,} jobs - {counts['candidates']:,} candidates")
    except Exception as exc:
        st.error(f"Data not ready: {exc}")

    st.divider()
    st.subheader("Bias awareness")
    st.caption(
        "ResBot judges fit only on job-relevant signals (skills and experience). "
        "It will not rank or filter people by gender, age, religion, location or marital "
        "status - those have no place in fair hiring."
    )

st.title("ResBot")
tab_chat, tab_resume = st.tabs(["Chat", "Resume Checker"])

# ---- chat tab ------------------------------------------------------------
with tab_chat:
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": GREETING}]

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form("chat_form", clear_on_submit=True):
        question = st.text_input(
            "Ask about the recruitment data",
            placeholder="e.g. which industries hire the most remote roles?",
        )
        asked = st.form_submit_button("Ask ResBot")

    if asked and question.strip():
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking..."):
                    reply = graph.answer(question)["answer"]
            except MissingApiKey as exc:
                reply = f"{exc}\n\nThe Resume Checker tab still works without a key."
            st.markdown(reply)
        st.session_state.chat.append({"role": "assistant", "content": reply})

# ---- resume checker tab --------------------------------------------------
with tab_resume:
    st.caption("Upload a resume, paste the job description, and I'll tell you how well they fit.")
    left, right = st.columns(2)
    with left:
        resume_file = st.file_uploader("Resume (PDF / DOCX)", type=["pdf", "docx", "txt"])
    with right:
        jd_text = st.text_area("Job description", height=220,
                               placeholder="Paste the full job description here...")

    if st.button("Check this resume"):
        if not resume_file or not jd_text.strip():
            st.warning("Please upload a resume and paste a job description first.")
        else:
            text = resume_ingest.extract_text(resume_file, resume_file.name)
            if not text.strip():
                st.error("I couldn't read any text from that file - is it a scanned image?")
            else:
                st.session_state.resume_ctx = {
                    "analysis": resume_ingest.check_resume(text, jd_text),
                    "resume_text": text,
                    "jd_text": jd_text,
                }
                st.session_state.resume_chat = []

    ctx = st.session_state.get("resume_ctx")
    if ctx:
        a = ctx["analysis"]
        fit = a["suitability"] != "Not Suitable"
        st.divider()
        c1, c2 = st.columns([1, 2])
        c1.metric("Match score", f"{a['match_score']} / 100")
        verdict = "\N{WHITE HEAVY CHECK MARK} Looks suitable" if fit else "\N{CROSS MARK} Not a strong fit"
        c2.markdown(f"### {verdict}\n**{a['suitability']}** for this role.")
        st.markdown(f"**Skills you have that the job wants:** {skills_line(a['matching_skills'])}")
        st.markdown(f"**Skills the job wants that are missing:** {skills_line(a['missing_skills'])}")

        st.divider()
        st.markdown("**Ask me about this resume** - suitability, missing skills, how to improve, etc.")
        for m in st.session_state.get("resume_chat", []):
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        with st.form("resume_form", clear_on_submit=True):
            rq = st.text_input("Your question",
                               placeholder="e.g. what should I improve to be a better fit?")
            rsent = st.form_submit_button("Ask")
        if rsent and rq.strip():
            st.session_state.resume_chat.append({"role": "user", "content": rq})
            with st.chat_message("user"):
                st.markdown(rq)
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Reading the resume..."):
                        reply = resume_qa(rq, ctx)
                except MissingApiKey as exc:
                    reply = str(exc)
                st.markdown(reply)
            st.session_state.resume_chat.append({"role": "assistant", "content": reply})
