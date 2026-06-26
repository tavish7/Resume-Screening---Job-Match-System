"""Upload a resume, match it against a chosen job, and score it with the Phase 5 model.

We rebuild the same features the classifier was trained on (notebook 04). A few of
those features simply aren't knowable from a raw uploaded file - years of experience,
education, the QC completeness score - so we parse what we can and fall back to neutral
defaults for the rest. The score is therefore a close approximation of the trained
pipeline's inputs, not a byte-identical feature vector.
"""
import re
from functools import lru_cache

import numpy as np
import pandas as pd
import joblib

from .config import BEST_MODEL, FEATURE_PIPELINE, LABELS

# same skill lexicon used by the matcher in notebook 03, so resume/job skills line up
SKILL_DICT = {
    "python": r"python", "java": r"java(?!script)", "javascript": r"java\s?script|\bjs\b",
    "c++": r"c\+\+", "c#": r"c#|c sharp", ".net": r"\.net|dotnet|asp\.net",
    "sql": r"\bsql\b|mysql|postgre|t-?sql|pl/?sql", "sql_server": r"sql server|mssql",
    "r_language": r"\br programming\b|\brstudio\b", "scala": r"\bscala\b", "go_language": r"\bgolang\b",
    "html": r"\bhtml5?\b", "css": r"\bcss3?\b", "php": r"\bphp\b", "ruby": r"\bruby\b",
    "matlab": r"matlab", "sas": r"\bsas\b", "vba": r"\bvba\b", "perl": r"\bperl\b",
    "machine_learning": r"machine learning|\bml\b", "deep_learning": r"deep learning",
    "nlp": r"natural language processing|\bnlp\b", "data_analysis": r"data analysis|data analytics",
    "data_science": r"data science", "tableau": r"tableau", "power_bi": r"power\s?bi",
    "excel": r"\bexcel\b|ms excel|microsoft excel", "spark": r"\bspark\b|pyspark",
    "hadoop": r"hadoop", "tensorflow": r"tensorflow", "pytorch": r"pytorch", "pandas": r"pandas",
    "aws": r"\baws\b|amazon web services", "azure": r"\bazure\b", "gcp": r"\bgcp\b|google cloud",
    "docker": r"docker", "kubernetes": r"kubernetes|k8s", "linux": r"\blinux\b|unix",
    "git": r"\bgit\b|github|gitlab", "jenkins": r"jenkins", "ci_cd": r"ci/?cd",
    "project_management": r"project management", "agile": r"\bagile\b|scrum",
    "ms_office": r"ms office|microsoft office", "powerpoint": r"power\s?point",
    "communication": r"communication skills?", "leadership": r"leadership",
    "customer_service": r"customer service", "sales": r"\bsales\b", "marketing": r"marketing",
    "negotiation": r"negotiation", "budgeting": r"budgeting|budget management",
    "accounting": r"accounting", "quickbooks": r"quickbooks", "auditing": r"auditing|audit",
    "financial_analysis": r"financial analysis", "taxation": r"\btax(ation)?\b", "sap": r"\bsap\b",
    "payroll": r"payroll", "forecasting": r"forecasting",
    "recruitment": r"recruitment|recruiting|talent acquisition", "onboarding": r"onboarding",
    "patient_care": r"patient care", "nursing": r"\bnursing\b|registered nurse|\brn\b",
    "autocad": r"autocad", "solidworks": r"solidworks", "photoshop": r"photoshop",
    "illustrator": r"illustrator", "adobe": r"adobe", "seo": r"\bseo\b",
    "social_media": r"social media", "salesforce": r"salesforce", "crm": r"\bcrm\b",
    # broader modern stack so the checker catches today's common job requirements
    "databricks": r"databricks", "snowflake": r"snowflake", "airflow": r"airflow",
    "kafka": r"kafka", "mongodb": r"mongo\s?db|mongodb", "postgresql": r"postgre(?:sql)?",
    "redshift": r"redshift", "bigquery": r"big\s?query", "terraform": r"terraform",
    "ansible": r"ansible", "react": r"\breact(?:\.js|js)?\b", "angular": r"\bangular\b",
    "nodejs": r"node\.?js", "django": r"\bdjango\b", "flask": r"\bflask\b",
    "fastapi": r"fast\s?api", "rest_api": r"rest(?:ful)?\s?apis?", "graphql": r"graphql",
    "scikit_learn": r"scikit-?learn|sklearn", "numpy": r"numpy", "etl": r"\betl\b",
    "data_warehouse": r"data\s?warehous(?:e|ing)", "looker": r"looker", "jira": r"\bjira\b",
    "snowpark": r"snowpark", "vertex_ai": r"vertex\s?ai", "spark_ml": r"\bmllib\b",
}
SKILL_RX = {name: re.compile(pat, re.IGNORECASE) for name, pat in SKILL_DICT.items()}

EDU_RANK = {"high_school": 1, "diploma": 2, "associate": 3, "bachelor": 4, "master": 5, "doctorate": 6}
NUM_ORDER = ["n_matching_skills", "n_missing_skills", "skill_count", "years_experience",
             "has_experience_info", "education_level", "resume_word_count",
             "resume_completeness_score", "required_skill_count", "description_word_count"]
# turn the 3 classes into a smooth 0-100 match score
SCORE_WEIGHTS = np.array([0.0, 0.5, 1.0])


@lru_cache(maxsize=1)
def _artifacts():
    return joblib.load(BEST_MODEL), joblib.load(FEATURE_PIPELINE)


def extract_text(file, filename):
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(file)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(file).paragraphs)
    # plain text fallback
    raw = file.read()
    return raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)


def find_skills(text):
    return {name for name, rx in SKILL_RX.items() if rx.search(text or "")}


def _years_experience(text):
    m = re.search(r"(\d{1,2})\+?\s*(?:years|yrs)", text or "", re.IGNORECASE)
    if m:
        return float(m.group(1)), 1
    return 5.0, 0  # neutral fallback; flag says "unknown", same idea as training


def _education_level(text):
    t = (text or "").lower()
    if re.search(r"ph\.?d|doctorate", t):
        return 6
    if re.search(r"master|m\.?s\b|mba", t):
        return 5
    if re.search(r"bachelor|b\.?s\b|b\.?tech|b\.?a\b", t):
        return 4
    if "associate" in t:
        return 3
    if "diploma" in t:
        return 2
    if "high school" in t:
        return 1
    return 0


def check_resume(resume_text, jd_text):
    """Score an uploaded resume against a pasted job description.

    Mirrors the Phase 5 feature build, but every job-side value now comes from the
    pasted text rather than a database row, so there's no job_id involved.
    """
    resume_skills = find_skills(resume_text)
    job_skills = find_skills(jd_text)
    matching = sorted(resume_skills & job_skills)
    missing = sorted(job_skills - resume_skills)

    years, has_exp = _years_experience(resume_text)
    feats = {
        "n_matching_skills": len(matching),
        "n_missing_skills": len(missing),
        "skill_count": len(resume_skills),
        "years_experience": years,
        "has_experience_info": has_exp,
        "education_level": _education_level(resume_text),
        "resume_word_count": len((resume_text or "").split()),
        "resume_completeness_score": 0.8,  # can't recompute the QC score, use a neutral value
        "required_skill_count": len(job_skills),
        "description_word_count": len((jd_text or "").split()),
    }

    model, pipe = _artifacts()
    combined = (resume_text or "") + " " + (jd_text or "")
    x_txt = pipe["svd"].transform(pipe["tfidf"].transform([combined]))
    # the scaler was fit on a named DataFrame in notebook 04, so feed it the same shape
    x_num = pipe["scaler"].transform(pd.DataFrame([feats], columns=NUM_ORDER))
    X = np.hstack([x_txt, x_num]).astype(np.float32)

    proba = model.predict_proba(X)[0]
    suitability = LABELS[int(np.argmax(proba))]
    match_score = round(float(np.dot(proba, SCORE_WEIGHTS) * 100), 1)

    return {
        "suitability": suitability,
        "match_score": match_score,
        "matching_skills": matching,
        "missing_skills": missing,
        "resume_skills": sorted(resume_skills),
        "job_skills": sorted(job_skills),
    }
