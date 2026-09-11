import io
import json
import os
import re
from collections import Counter

STOPWORDS = set(
    """
a an and are as at be by for from has he in is it its of on that the to was were will with you your we they this that these those or not but have had his her she him our ours their them then than so such no yes if else when while where which who whom what how why can could should would may might must shall do does did done doing into out up down over under again once here there all any both each few more most other some only own same than too very just about into through during before after above below between both each
""".split()
)

SKILL_LEXICON = [
    "python",
    "java",
    "c++",
    "c#",
    "javascript",
    "typescript",
    "react",
    "node",
    "sql",
    "nosql",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "llm",
    "generative ai",
    "data analysis",
    "pandas",
    "numpy",
    "matplotlib",
    "spark",
    "hadoop",
    "airflow",
    "mlflow",
    "git",
    "linux",
    "rest api",
    "graphql",
    "fastapi",
    "flask",
    "django",
    "streamlit",
    "agile",
    "scrum",
    "ci/cd",
    "jenkins",
    "terraform",
    "excel",
    "tableau",
    "power bi",
    "communication",
    "leadership",
    "teamwork",
    "problem solving",
    "analytical",
    "mentoring",
]

ACTION_VERBS = set(
    "achieved built created delivered designed developed drove engineered executed improved increased launched led optimized reduced shipped streamlined automated analyzed collaborated deployed implemented managed mentored tested".split()
)

CONTACT_PATTERNS = [
    r"[\w\.-]+@[\w\.-]+\.\w+",
    r"\+?\d[\d\s\-\(\)]{7,}\d",
    r"linkedin\.com",
    r"github\.com",
]


def extract_text(uploaded_file) -> str:
    name = (uploaded_file.name or "").lower()
    data = uploaded_file.read()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs])
    return data.decode("utf-8", errors="ignore")


def _tokens(text: str):
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\.\-]{1,}", text.lower())


def jd_keywords(jd: str, top_n: int = 30):
    jd_low = jd.lower()
    found = []
    for skill in SKILL_LEXICON:
        if skill in jd_low:
            found.append(skill)
    toks = [t for t in _tokens(jd) if t not in STOPWORDS and len(t) > 2]
    freq = Counter(toks)
    for w, _ in freq.most_common(top_n):
        if w not in found:
            found.append(w)
        if len(found) >= top_n:
            break
    return found[:top_n]


def _grade(score: int) -> str:
    if score >= 85:
        return "Excellent — ready to submit"
    if score >= 70:
        return "Strong — minor tweaks left"
    if score >= 50:
        return "Fair — needs tailoring"
    return "Weak — tailor before applying"


def _ats_checks(text: str):
    low = text.lower()
    words = text.split()
    bullets = len(re.findall(r"(?m)^\s*[•\-\*]", text))
    metrics = len(
        re.findall(
            r"\d+\s?[%+]|\$\s?\d+|\d+\s?(years|yrs|months|projects|users|clients)", low
        )
    )
    verbs = sum(1 for v in ACTION_VERBS if v in low)
    has_email = bool(re.search(CONTACT_PATTERNS[0], text))
    has_phone = bool(re.search(CONTACT_PATTERNS[1], text))
    has_links = bool(
        re.search(CONTACT_PATTERNS[2], text) or re.search(CONTACT_PATTERNS[3], text)
    )
    sections = sum(
        1 for s in ("experience", "education", "skills", "summary") if s in low
    )
    fmt = 0
    fmt += 15 if 250 <= len(words) <= 900 else (8 if len(words) > 100 else 2)
    fmt += 10 if bullets >= 4 else (bullets * 2)
    fmt += 10 if sections >= 3 else (sections * 3)
    fmt += 5 if has_email else 0
    fmt = min(40, fmt)
    impact = min(30, metrics * 6 + min(12, verbs * 2))
    return {
        "words": len(words),
        "bullets": bullets,
        "metrics": metrics,
        "verbs": verbs,
        "has_email": has_email,
        "has_phone": has_phone,
        "has_links": has_links,
        "sections": sections,
        "formatting": fmt,
        "impact": impact,
    }


def score_resume(resume: str, jd: str):
    kws = jd_keywords(jd)
    res_low = resume.lower()
    matched = [k for k in kws if k in res_low]
    missing = [k for k in kws if k not in res_low]
    kw_score = 100 * len(matched) / max(1, len(kws))
    lex_hits = sum(1 for s in SKILL_LEXICON if s in res_low)
    skill_cov = min(100, lex_hits * 5)
    checks = _ats_checks(resume)
    score = round(
        kw_score * 0.55
        + skill_cov * 0.15
        + checks["formatting"] * 2.5 * 0.15
        + checks["impact"] * 3.33 * 0.15
    )
    score = max(0, min(100, score))
    strengths = [f"Covers '{m}'" for m in matched[:6]]
    if checks["metrics"] >= 3:
        strengths.append(
            f"Quantified impact in {checks['metrics']} places — recruiters trust numbers."
        )
    if checks["verbs"] >= 5:
        strengths.append(f"Strong action verbs ({checks['verbs']} found).")
    if checks["sections"] >= 3:
        strengths.append(
            "Clear ATS-friendly sections (experience / education / skills)."
        )
    if not strengths:
        strengths = [
            "Readable baseline — keyword alignment will lift the score quickly."
        ]
    weaknesses = []
    for m in missing[:6]:
        weaknesses.append(
            f"Missing keyword '{m}' — mirror the JD wording where truthful."
        )
    if checks["words"] < 200:
        weaknesses.append(
            f"Only {checks['words']} words — add 2-4 quantified work-experience bullets."
        )
    if checks["bullets"] < 4:
        weaknesses.append(
            "Few bullet points detected — use • bullets starting with action verbs."
        )
    if checks["metrics"] < 2:
        weaknesses.append(
            "Little quantified proof — add %, $, or time-saved numbers to 2+ bullets."
        )
    if not checks["has_email"]:
        weaknesses.append(
            "No email detected — ATS and recruiters expect one in the header."
        )
    if checks["sections"] < 3:
        weaknesses.append(
            "Add standard headings: Summary, Skills, Professional Experience, Education."
        )
    suggestions = [
        "Mirror exact JD skill phrases in a SKILLS section.",
        "Start each bullet with an action verb + metric (e.g. 'Built X, cutting Y by 30%').",
        "Keep one column, standard headings, no tables or graphics for ATS parsing.",
        "Rephrase work-experience and education wording only — never invent employers or degrees.",
    ]
    return {
        "score": score,
        "grade": _grade(score),
        "matched": matched,
        "missing": missing,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "keywords": kws,
        "stats": checks,
        "breakdown": {
            "Keyword match": round(kw_score),
            "Skill coverage": round(skill_cov),
            "Formatting / ATS": round(min(100, checks["formatting"] * 2.5)),
            "Impact evidence": round(min(100, checks["impact"] * 3.33)),
        },
    }


def analyze_cover(cover: str, jd: str):
    if not cover or len(cover.strip()) < 50:
        return {
            "score": 0,
            "grade": "No cover letter uploaded",
            "strengths": [],
            "weaknesses": [
                "No cover letter uploaded — generate one from the Tailored Docs tab."
            ],
            "suggestions": [
                "Open with role + top 2 JD skills.",
                "Keep 250-350 words in 3-4 paragraphs.",
                "End with a call to action.",
            ],
            "matched": [],
            "missing": jd_keywords(jd)[:10],
            "breakdown": {"Relevance": 0, "Structure": 0, "Brevity": 0},
            "stats": {"words": 0},
        }
    kws = jd_keywords(jd, 20)
    low = cover.lower()
    matched = [k for k in kws if k in low]
    missing = [k for k in kws if k not in low]
    rel = 100 * len(matched) / max(1, len(kws))
    words = len(cover.split())
    brevity = 100 if 200 <= words <= 380 else (70 if words <= 500 else 40)
    struct = 0
    struct += 25 if ("dear " in low) else 0
    struct += (
        25
        if len(re.findall(r"\n\s*\n", cover)) >= 2 or len(cover.split(". ")) >= 4
        else 0
    )
    struct += 25 if ("sincerely" in low or "regards" in low or "thank" in low) else 0
    struct += 25 if ("apply" in low or "role" in low or "position" in low) else 0
    score = round(rel * 0.6 + brevity * 0.2 + struct * 0.2)
    strengths = [f"Connects to '{m}'" for m in matched[:5]] or [
        "Has a narrative structure."
    ]
    if 200 <= words <= 380:
        strengths.append(f"Ideal length ({words} words).")
    weaknesses = []
    if "dear " not in low:
        weaknesses.append("Add a personalized greeting (Dear Hiring Manager / name).")
    if words > 400:
        weaknesses.append(f"Too long at {words} words — trim to 250-350.")
    if words < 150:
        weaknesses.append(
            f"Too short at {words} words — add one proof paragraph with a metric."
        )
    for m in missing[:4]:
        weaknesses.append(f"Could connect experience to '{m}'.")
    return {
        "score": score,
        "grade": _grade(score),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": [
            "Open with role + top 2 JD skills.",
            "One paragraph each: fit, proof, close.",
            "End with a call to action + contact details.",
        ],
        "matched": matched,
        "missing": missing,
        "breakdown": {
            "Relevance": round(rel),
            "Structure": round(struct),
            "Brevity": round(brevity),
        },
        "stats": {"words": words},
    }


def rule_tailor_resume(resume: str, jd: str, analysis: dict) -> str:
    missing = analysis.get("missing", [])[:12]
    lines = resume.strip().splitlines()
    out = []
    skills_idx = next(
        (
            i
            for i, l in enumerate(lines)
            if l.strip().lower() in ("skills", "technical skills", "core skills")
        ),
        None,
    )
    for i, line in enumerate(lines):
        out.append(line)
        if skills_idx is not None and i == skills_idx:
            add = ", ".join([m for m in missing if len(m) < 30])
            if add:
                out.append(f"Aligned strengths: {add}")
    if skills_idx is None and missing:
        out.append("")
        out.append("CORE SKILLS (aligned to job description)")
        out.append(", ".join(missing))
    out.append("")
    out.append(
        "NOTE: Only phrasing of existing work experience/education was mirrored to the job description. No new employers, dates, or degrees added — verify before submitting."
    )
    return "\n".join(out)


def rule_tailor_cover(resume: str, jd: str, job_title: str, company: str) -> str:
    kws = jd_keywords(jd, 8)
    return f"""Dear Hiring Manager{(" at " + company) if company else ""},

I am applying for the {job_title or "advertised role"}. My background aligns with {", ".join(kws[:4]) or "your requirements"}.

My recent work experience directly relates to this job description. I have applied these skills to deliver measurable results, and I tailor my approach to each team's stack and goals.

I would welcome the opportunity to discuss how my experience with {", ".join(kws[4:7]) or "relevant projects"} can contribute to your team.

Sincerely,
[Your Name]
[Phone] | [Email] | [LinkedIn]
"""


def gemini_key():
    try:
        import streamlit as st

        k = st.secrets.get("GEMINI_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


TRUTHFULNESS = (
    "Rules: NEVER invent employers, job titles, dates, degrees, or metrics. "
    "Only rephrase existing work experience bullets and education lines to mirror the job description wording. "
    "Keep all facts identical. If a JD skill is absent from the resume, list it under 'To develop' rather than claiming it."
)


def gemini_generate(resume: str, cover: str, jd: str, job_title: str, company: str):
    from google import genai

    client = genai.Client(api_key=gemini_key())
    prompt = f"""{TRUTHFULNESS}

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{jd[:6000]}

ORIGINAL RESUME:
{resume[:8000]}

ORIGINAL COVER LETTER:
{(cover or "(none provided)")[:4000]}

Return STRICT JSON with keys: resume_score, resume_strengths, resume_weaknesses, missing_keywords, tailored_resume, tailored_cover, cover_score, cover_strengths, cover_weaknesses, what_changed.
tailored_resume: full ATS-friendly plain text resume. tailored_cover: 250-350 word letter. what_changed: list of 4-8 short strings explaining edits."""
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    last_err = None
    for candidate in (
        model,
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-latest",
    ):
        try:
            resp = client.models.generate_content(model=candidate, contents=prompt)
            break
        except Exception as e:
            last_err = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                continue
            raise
    else:
        if last_err is not None:
            raise last_err
        raise RuntimeError("Gemini request failed")
    text = (resp.text or "").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("Gemini returned non-JSON")
    return json.loads(m.group(0))


def to_docx(title: str, body: str) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(title, level=1)
    for para in body.split("\n"):
        if para.strip().upper() == para.strip() and 2 < len(para.strip()) < 60:
            doc.add_heading(para.strip().title(), level=2)
        else:
            doc.add_paragraph(para)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
