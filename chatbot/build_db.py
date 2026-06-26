"""Build the SQLite warehouse ResBot queries.

We don't have a live MySQL server, so we fold the cleaned CSVs into one portable
SQLite file. Run this once (or whenever the cleaned data changes):

    python chatbot/build_db.py

On Streamlit Cloud, `job_master.csv` is not in Git (too large). When it is missing,
jobs are synthesized from `match_scores.csv` + `job_skills_resolved.csv`.
"""
import sys
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from project_paths import CLEANED_DIR, rel

CLEAN = CLEANED_DIR
DB_PATH = CLEAN / "resume_matching.db"

# table name -> source csv. mirrors the 6 tables in schema.sql
SOURCES = {
    "companies": CLEAN / "master" / "company_master.csv",
    "candidates": CLEAN / "master" / "resume_master.csv",
    "jobs": CLEAN / "master" / "job_master.csv",
    "matches": CLEAN / "matching" / "match_scores.csv",
    "job_skills": CLEAN / "normalized" / "job_skills_resolved.csv",
    "job_industries": CLEAN / "normalized" / "job_industries_resolved.csv",
}

# a few indexes the recruiter views and rankings actually hit
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_matches_cand ON matches(candidate_id)",
    "CREATE INDEX IF NOT EXISTS idx_matches_job ON matches(job_id)",
    "CREATE INDEX IF NOT EXISTS idx_matches_suit ON matches(suitability)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_id ON jobs(job_id)",
    "CREATE INDEX IF NOT EXISTS idx_jobskills_job ON job_skills(job_id)",
]


def _jobs_from_matches(matches_df: pd.DataFrame, job_skills_df: pd.DataFrame) -> pd.DataFrame:
    """Build a slim jobs table when the full job_master.csv is unavailable."""
    base = matches_df.groupby("job_id", as_index=False).agg(
        title=("job_title", "first"),
        company_name=("company_name", "first"),
    )
    base["title_clean"] = base["title"].fillna("").str.lower()

    if job_skills_df.empty:
        base["required_skills"] = ""
        base["required_skill_count"] = 0
    else:
        req = (
            job_skills_df.groupby("job_id")["skill_clean"]
            .apply(lambda skills: "|".join(sorted({s for s in skills if s})))
            .reset_index(name="required_skills")
        )
        base = base.merge(req, on="job_id", how="left")
        base["required_skill_count"] = base["required_skills"].fillna("").map(
            lambda s: len([x for x in s.split("|") if x]) if s else 0
        )

    base["company_id"] = pd.NA
    base["company_industry"] = pd.NA
    base["company_size"] = pd.NA
    base["employee_count_latest"] = pd.NA
    base["description_clean"] = pd.NA
    base["experience_required"] = pd.NA
    base["industries"] = pd.NA
    base["work_type"] = pd.NA
    base["location"] = pd.NA
    base["location_clean"] = pd.NA
    base["min_salary"] = pd.NA
    base["max_salary"] = pd.NA
    base["normalized_salary_clean"] = pd.NA
    base["has_salary"] = pd.NA
    base["pay_period"] = pd.NA
    base["currency"] = pd.NA
    base["benefits"] = pd.NA
    base["remote_allowed_bool"] = pd.NA
    base["listed_time_dt"] = pd.NA
    base["expiry_dt"] = pd.NA
    base["description_word_count"] = pd.NA
    base["jd_completeness_score"] = pd.NA
    base["job_quality_score"] = pd.NA
    return base


def build(force: bool = False) -> dict:
    if DB_PATH.exists() and not force:
        return {}

    if DB_PATH.exists():
        DB_PATH.unlink()

    matches_df = pd.read_csv(SOURCES["matches"])
    if "rank" in matches_df.columns:
        matches_df = matches_df.rename(columns={"rank": "match_rank"})

    matched_ids = set(matches_df["job_id"].unique())
    use_slim_jobs = not SOURCES["jobs"].exists()

    job_skills_df = pd.read_csv(SOURCES["job_skills"])
    job_skills_df = job_skills_df[job_skills_df["job_id"].isin(matched_ids)]

    job_industries_df = pd.read_csv(SOURCES["job_industries"])
    job_industries_df = job_industries_df[job_industries_df["job_id"].isin(matched_ids)]

    conn = sqlite3.connect(DB_PATH)
    counts = {}

    for table, path in SOURCES.items():
        if table == "matches":
            df = matches_df
        elif table == "jobs":
            if use_slim_jobs:
                df = _jobs_from_matches(matches_df, job_skills_df)
            else:
                df = pd.read_csv(path)
        elif table == "job_skills":
            df = job_skills_df
        elif table == "job_industries":
            df = job_industries_df
        else:
            df = pd.read_csv(path)

        df.to_sql(table, conn, if_exists="replace", index=False)
        counts[table] = len(df)

    for stmt in INDEXES:
        conn.execute(stmt)
    conn.commit()
    conn.close()

    width = max(len(t) for t in counts)
    mode = "slim (matches-derived jobs)" if use_slim_jobs else "full"
    print(f"Built {rel(DB_PATH)} [{mode}]")
    for table, n in counts.items():
        print(f"  {table:<{width}}  {n:>7,} rows")
    return counts


def ensure_db() -> bool:
    """Build the SQLite file if it is missing. Returns True if a build ran."""
    if DB_PATH.exists():
        return False
    build(force=True)
    return True


if __name__ == "__main__":
    build(force=True)
