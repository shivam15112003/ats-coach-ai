# ATS Coach AI (Streamlit)

Live website: upload resume, optional cover letter, paste JD. Get match score, strengths/weaknesses/missing keywords, tailored resume + cover letter, before/after explanation, TXT/DOCX/PDF downloads.

## Run locally
```
cd ats-coach
pip install -r requirements.txt
streamlit run app.py
```
Optional: set `GEMINI_API_KEY` env var or paste in sidebar for AI-quality tailoring. Without a key, rule-based mode is used.

## Deploy (Streamlit Community Cloud)
1. Push this folder to GitHub
2. New app → `ats-coach/app.py`
3. Add Secret: `GEMINI_API_KEY = "your-key"`

Truthfulness: prompts only rephrase existing work experience/education wording, never invent employers, dates, or degrees.
