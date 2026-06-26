"""Build the SQLite warehouse ResBot queries.

We don't have a live MySQL server, so we fold the cleaned CSVs into one portable
SQLite file. Run this once (or whenever the cleaned data changes):

    python chatbot/build_db.py
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


def build():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    counts = {}
    for table, path in SOURCES.items():
        df = pd.read_csv(path)
        # "rank" is a reserved word in newer SQLite and trips up generated SQL
        if table == "matches" and "rank" in df.columns:
            df = df.rename(columns={"rank": "match_rank"})
        df.to_sql(table, conn, if_exists="replace", index=False)
        counts[table] = len(df)

    for stmt in INDEXES:
        conn.execute(stmt)
    conn.commit()
    conn.close()

    width = max(len(t) for t in counts)
    print(f"Built {rel(DB_PATH)}")
    for table, n in counts.items():
        print(f"  {table:<{width}}  {n:>7,} rows")
    return counts


if __name__ == "__main__":
    build()
