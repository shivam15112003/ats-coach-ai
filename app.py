import streamlit as st
import ats_engine as eng

st.set_page_config(page_title="ATS Coach AI", page_icon="◎", layout="wide")

CSS = """
<style>
.hero { background: linear-gradient(135deg,#0f172a,#1e3a8a 60%,#2563eb); border-radius:16px; padding:28px 32px; color:#fff; margin-bottom:18px; }
.hero h1 { margin:0; font-size:2rem; }
.hero p { margin:6px 0 0; opacity:.88; }
.badge { display:inline-block; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.25); padding:3px 10px; border-radius:999px; font-size:.75rem; margin-right:6px; }
.card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:18px 20px; box-shadow:0 1px 4px rgba(15,23,42,.06); margin-bottom:14px; }
.score-big { font-size:2.6rem; font-weight:800; margin:0; }
.grade { display:inline-block; background:#eff6ff; color:#1d4ed8; border-radius:999px; padding:4px 12px; font-size:.8rem; font-weight:600; }
.bar { background:#eef2ff; border-radius:999px; height:10px; overflow:hidden; margin:4px 0 10px; }
.bar > div { height:100%; background:linear-gradient(90deg,#2563eb,#60a5fa); border-radius:999px; }
.chip { display:inline-block; background:#f1f5f9; border:1px solid #e2e8f0; padding:3px 10px; border-radius:999px; font-size:.78rem; margin:2px 4px 2px 0; }
.chip.miss { background:#fef2f2; border-color:#fecaca; }
.strength { background:#f0fdf4; border-left:4px solid #22c55e; padding:8px 12px; border-radius:8px; margin:6px 0; }
.weak { background:#fffbeb; border-left:4px solid #f59e0b; padding:8px 12px; border-radius:8px; margin:6px 0; }
.tip { background:#eff6ff; border-left:4px solid #2563eb; padding:8px 12px; border-radius:8px; margin:6px 0; }
.footer { text-align:center; color:#64748b; font-size:.8rem; margin-top:22px; }
.stButton > button { background:linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff; border:none; border-radius:12px; padding:14px 24px; font-size:1.05rem; font-weight:700; box-shadow:0 4px 14px rgba(37,99,235,.35); transition:transform .12s ease, box-shadow .12s ease; }
.stButton > button:hover { transform:translateY(-1px); box-shadow:0 8px 22px rgba(37,99,235,.45); color:#fff; }
.stDownloadButton > button { background:#fff; color:#1d4ed8; border:1.5px solid #2563eb; border-radius:10px; padding:9px 16px; font-weight:600; transition:background .12s ease; }
.stDownloadButton > button:hover { background:#eff6ff; color:#1e40af; border-color:#1d4ed8; }
.stTabs [data-baseweb="tab"] { font-weight:600; border-radius:8px 8px 0 0; }
.stTabs [aria-selected="true"] { color:#1d4ed8; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    "<div class='hero'><h1>◎ ATS Coach AI</h1>"
    "<p>Applicant Tracking Systems reject ~75% of resumes before a human sees them. Upload your resume, paste any job description, optionally add your cover letter — get a detailed ATS diagnosis with scores, evidence, and tailored documents.</p>"
    "<span class='badge'>No login needed</span><span class='badge'>Gemini API — no browser</span><span class='badge'>Private — files never stored</span></div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("About")
    st.write(
        "ATS Coach AI scores your resume and cover letter against any job description, then tailors both."
    )
    st.divider()
    st.subheader("How scoring works")
    st.write(
        "Keyword match 55% · Skill coverage 15% · Formatting/ATS 15% · Impact evidence 15%. Cover: relevance 60% · structure 20% · brevity 20%."
    )
    st.caption(
        "Powered by the Gemini API (key in Secrets) with a built-in rule engine as fallback."
    )

left, right = st.columns([1, 1.2])
with left:
    st.subheader("Step 1 — Your documents")
    st.caption(
        "What to upload: a text-based PDF/DOCX resume (1-2 pages, single column). Cover letter is optional — if skipped, one is still generated for you."
    )
    resume_file = st.file_uploader(
        "Resume (PDF / DOCX / TXT) *", type=["pdf", "docx", "txt"]
    )
    cover_file = st.file_uploader(
        "Cover letter (optional)", type=["pdf", "docx", "txt"]
    )
    job_title = st.text_input("Job title", placeholder="e.g. AI Engineering Intern")
    company = st.text_input("Company", placeholder="e.g. Acme Corp")
with right:
    st.subheader("Step 2 — Target job")
    st.caption("Paste the full job description below.")
    _jd_raw = st.text_area(
        "Job description *",
        height=280,
        placeholder="Paste the full job description here...",
    )
    jd: str = _jd_raw or ""

go = st.button(
    "Analyze & Tailor My Application", type="primary", use_container_width=True
)

if go:
    if not resume_file or not (jd or "").strip():
        st.error("Resume and job description are required.")
        st.stop()
    resume_text = eng.extract_text(resume_file)
    cover_text = eng.extract_text(cover_file) if cover_file else ""
    if len(resume_text.strip()) < 100:
        st.error(
            "Could not read much text from that resume — try a text-based PDF or DOCX, not a scanned image."
        )
        st.stop()
    ai_data = None
    if eng.gemini_key():
        try:
            with st.spinner("Gemini API is scoring and tailoring..."):
                ai_data = eng.gemini_generate(
                    resume_text, cover_text, jd, job_title, company
                )
            st.success("Tailored with Gemini API.")
        except Exception as e:
            st.warning(f"Gemini API unavailable ({e}). Used rule engine.")
    else:
        st.info("No Gemini API key in Secrets. Used rule engine.")
    if ai_data:
        r = {
            "score": int(ai_data.get("resume_score", 0)),
            "grade": "",
            "strengths": ai_data.get("resume_strengths", []),
            "weaknesses": ai_data.get("resume_weaknesses", []),
            "missing": ai_data.get("missing_keywords", []),
            "suggestions": [],
            "matched": [],
            "breakdown": {},
            "stats": {},
        }
        c = {
            "score": int(ai_data.get("cover_score", 0)),
            "grade": "",
            "strengths": ai_data.get("cover_strengths", []),
            "weaknesses": ai_data.get("cover_weaknesses", []),
            "suggestions": [],
            "matched": [],
            "missing": [],
            "breakdown": {},
            "stats": {},
        }
        tailored_resume = ai_data.get("tailored_resume", "")
        tailored_cover = ai_data.get("tailored_cover", "")
        changed = ai_data.get("what_changed", [])
    else:
        r = eng.score_resume(resume_text, jd)
        c = eng.analyze_cover(cover_text, jd)
        tailored_resume = eng.rule_tailor_resume(resume_text, jd, r)
        tailored_cover = eng.rule_tailor_cover(resume_text, jd, job_title, company)
        changed = [
            f"Aligned {len(r['missing'][:8])} missing keywords where truthful: {', '.join(r['missing'][:8]) or 'none'}.",
            "Reworded work-experience bullets to mirror JD phrasing; no employers, dates, or metrics invented.",
            "Education lines rephrased only; no new degrees added.",
            "Restructured into single-column ATS-safe headings: Summary, Skills, Experience, Education.",
            f"Rule-engine detail: keyword match {r['breakdown'].get('Keyword match', 0)}, formatting {r['breakdown'].get('Formatting / ATS', 0)}, impact {r['breakdown'].get('Impact evidence', 0)}.",
        ]

    st.subheader("Match dashboard — what the numbers mean")
    st.caption(
        "Scores predict JD alignment, not hiring. 85+ submit-ready · 70+ strong with tweaks · 50+ needs tailoring · below 50 rewrite before applying."
    )
    d1, d2, d3 = st.columns(3)
    with d1:
        st.write("**Resume score**")
        st.markdown(
            f"<p class='score-big'>{r['score']}/100</p>", unsafe_allow_html=True
        )
        st.markdown(
            f"<span class='grade'>{r.get('grade', '')}</span>", unsafe_allow_html=True
        )
        st.progress(min(100, r["score"]) / 100)
        if r.get("stats"):
            s = r["stats"]
            st.caption(
                f"{s.get('words', 0)} words · {s.get('bullets', 0)} bullets · {s.get('metrics', 0)} quantified results · {s.get('verbs', 0)} action verbs"
            )
            st.caption(
                f"Contact check: {'email found' if s.get('has_email') else 'no email found'} · {'links found' if s.get('has_links') else 'no LinkedIn/GitHub found'} · {s.get('sections', 0)}/4 standard sections"
            )
    with d2:
        st.write("**Cover-letter score**")
        if cover_text:
            st.markdown(
                f"<p class='score-big'>{c['score']}/100</p>", unsafe_allow_html=True
            )
            st.markdown(
                f"<span class='grade'>{c.get('grade', '')}</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(100, c["score"]) / 100)
            if c.get("stats"):
                st.caption(
                    f"{c['stats'].get('words', 0)} words — ideal is 250-350 in 3-4 paragraphs."
                )
        else:
            st.info(
                "No cover uploaded — a tailored cover letter was still generated for you in the Tailored documents tab."
            )
    with d3:
        st.write("**Resume breakdown (why this score)**")
        for k, v in (r.get("breakdown") or {}).items():
            st.write(f"{k}: {v}/100")
            st.markdown(
                f"<div class='bar'><div style='width:{v}%'></div></div>",
                unsafe_allow_html=True,
            )
        st.caption(
            "Keyword match: share of JD terms found. Skill coverage: known tech skills. Formatting: length, bullets, sections, contact. Impact: numbers + action verbs."
        )

    t1, t2, t3, t4, t5 = st.tabs(
        [
            "Resume analysis",
            "Cover-letter analysis",
            "Tailored documents",
            "What changed",
            "Learn & FAQ",
        ]
    )
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Strengths (keep these)")
            for s in r["strengths"]:
                st.markdown(f"<div class='strength'>{s}</div>", unsafe_allow_html=True)
        with c2:
            st.subheader("Gaps to fix (in priority order)")
            for w in r["weaknesses"]:
                st.markdown(f"<div class='weak'>{w}</div>", unsafe_allow_html=True)
        st.subheader("Keyword detail — exact JD phrases")
        st.caption(
            "Matched: already in your resume. Missing: add truthfully or list under 'To develop'. Never claim skills you lack."
        )
        for m in (r.get("matched") or [])[:20]:
            st.markdown(f"<span class='chip'>{m}</span>", unsafe_allow_html=True)
        for m in (r.get("missing") or [])[:20]:
            st.markdown(
                f"<span class='chip miss'>missing: {m}</span>", unsafe_allow_html=True
            )
        with st.expander("Your 7-day improvement plan"):
            st.write(
                "Day 1: add missing JD keywords to Skills (only ones you truly have)."
            )
            st.write("Day 2: rewrite 3 bullets as Action verb + task + metric.")
            st.write("Day 3: add email, phone, LinkedIn, GitHub to header.")
            st.write(
                "Day 4: enforce headings Summary / Skills / Experience / Education."
            )
            st.write("Day 5: cut to 1 page, one column, no tables or graphics.")
            st.write("Day 6: re-run here and aim for 75+.")
            st.write(
                "Day 7: have a friend read it for 30 seconds — whatever they miss, clarify."
            )
    with t2:
        if not cover_text:
            st.info(
                "You uploaded only a resume — review your generated cover letter in the Tailored documents tab."
            )
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Strengths")
            for s in c["strengths"] or ["—"]:
                st.markdown(f"<div class='strength'>{s}</div>", unsafe_allow_html=True)
        with c2:
            st.subheader("Gaps to fix")
            for w in c["weaknesses"] or ["—"]:
                st.markdown(f"<div class='weak'>{w}</div>", unsafe_allow_html=True)
        if c.get("breakdown"):
            st.subheader("Breakdown — relevance, structure, brevity")
            for k, v in c["breakdown"].items():
                st.write(f"{k}: {v}/100")
                st.markdown(
                    f"<div class='bar'><div style='width:{v}%'></div></div>",
                    unsafe_allow_html=True,
                )
            st.caption(
                "Relevance: JD keywords echoed. Structure: greeting, fit/proof/close, sign-off. Brevity: 250-350 words scores highest."
            )
        with st.expander("Anatomy of a strong cover letter"):
            st.write("Para 1 (fit): role, company, your 2 strongest JD-matched skills.")
            st.write("Para 2 (proof): one project with a metric that maps to the JD.")
            st.write("Para 3 (close): why this team, call to action, contact details.")
    with t3:
        st.subheader("Tailored resume (TXT + DOCX — no PDF by request)")
        st.caption(
            "Generated by mirroring JD wording onto your existing experience and education. Verify every line — especially skills, dates, and numbers."
        )
        st.text_area(
            "resume_out", tailored_resume, height=320, label_visibility="collapsed"
        )
        st.download_button(
            "Download resume (.txt)", tailored_resume, "tailored_resume.txt"
        )
        st.download_button(
            "Download resume (.docx)",
            eng.to_docx("Resume", tailored_resume),
            "tailored_resume.docx",
        )
        st.divider()
        st.subheader("Tailored cover letter")
        st.text_area(
            "cover_out", tailored_cover, height=260, label_visibility="collapsed"
        )
        st.download_button(
            "Download cover letter (.txt)", tailored_cover, "tailored_cover_letter.txt"
        )
        st.download_button(
            "Download cover letter (.docx)",
            eng.to_docx("Cover Letter", tailored_cover),
            "tailored_cover_letter.docx",
        )
    with t4:
        st.subheader("What changed and why")
        for ch in changed:
            st.markdown(f"<div class='tip'>{ch}</div>", unsafe_allow_html=True)
        st.info(
            "Truthfulness promise: only wording of existing work experience and education is adjusted. No new employers, dates, degrees, or metrics are invented. Verify names, dates, and numbers before submitting."
        )
    with t5:
        st.subheader("Learn: how ATS screening really works")
        st.write(
            "1. Parsing: the ATS strips your file to raw text. Tables, graphics, and two-column layouts scramble order — hence single-column TXT/DOCX."
        )
        st.write(
            "2. Keyword match: it counts exact JD phrases. 'ML' does not match 'machine learning' — mirror exact wording."
        )
        st.write(
            "3. Knockout rules: missing degree, location, or work authorization can auto-reject — state them plainly."
        )
        st.write(
            "4. Ranking: recruiters skim top-ranked resumes for ~7 seconds — metrics and verbs decide who gets read."
        )
        with st.expander("FAQ"):
            st.write(
                "Q: Is my data stored? A: No — files live only in memory for your session."
            )
            st.write(
                "Q: Do I need a Gemini key? A: No — the rule engine works offline; a key just improves phrasing."
            )
            st.write(
                "Q: Why no PDF download? A: Removed by request — DOCX preserves ATS-safe formatting better."
            )
            st.write(
                "Q: Can friends use this from anywhere? A: Yes — once deployed to Streamlit Cloud, anyone with the public URL can use it on any network."
            )

st.markdown(
    "<div class='footer'>ATS Coach AI · educational project · verify every tailored claim before applying</div>",
    unsafe_allow_html=True,
)
