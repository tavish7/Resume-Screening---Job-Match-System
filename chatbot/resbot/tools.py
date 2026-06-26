"""Structured recruiter features.

These don't go through the LLM-SQL path - they're deterministic lookups against
the matches table, so the numbers are always exact and reproducible.
"""
from .db import connect


def _rows(sql, params=()):
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def _skills(pipe):
    if not pipe:
        return []
    return [s for s in str(pipe).split("|") if s]


def skill_gap(candidate_id, job_id=None):
    """Matching vs missing skills for a candidate - for one job, or their best match."""
    if job_id is not None:
        rows = _rows(
            "SELECT candidate_id, job_id, job_title, matching_skills, missing_skills, "
            "final_match_score, suitability FROM matches "
            "WHERE candidate_id = ? AND job_id = ?",
            (int(candidate_id), int(job_id)),
        )
    else:
        rows = _rows(
            "SELECT candidate_id, job_id, job_title, matching_skills, missing_skills, "
            "final_match_score, suitability FROM matches "
            "WHERE candidate_id = ? ORDER BY final_match_score DESC LIMIT 1",
            (int(candidate_id),),
        )
    if not rows:
        return None
    r = rows[0]
    req = _rows("SELECT required_skills FROM jobs WHERE job_id = ?", (r["job_id"],))
    job_required = _skills(req[0]["required_skills"]) if req else []
    return {
        "candidate_id": r["candidate_id"],
        "job_id": r["job_id"],
        "job_title": r["job_title"],
        "has_skills": _skills(r["matching_skills"]),
        "missing_skills": _skills(r["missing_skills"]),
        "job_required_skills": job_required,
        "match_score": r["final_match_score"],
        "suitability": r["suitability"],
    }


def recommend_candidates_for_job(job_id, top_n=5):
    rows = _rows(
        "SELECT m.candidate_id, c.role_applied, m.final_match_score, m.suitability, "
        "m.matching_skills, m.missing_skills "
        "FROM matches m LEFT JOIN candidates c ON c.candidate_id = m.candidate_id "
        "WHERE m.job_id = ? ORDER BY m.final_match_score DESC LIMIT ?",
        (int(job_id), int(top_n)),
    )
    title = _rows("SELECT title FROM jobs WHERE job_id = ?", (int(job_id),))
    return {
        "job_id": int(job_id),
        "job_title": title[0]["title"] if title else None,
        "candidates": rows,
    }


def recommend_jobs_for_candidate(candidate_id, top_n=5):
    rows = _rows(
        "SELECT job_id, job_title, company_name, final_match_score, suitability, "
        "matching_skills, missing_skills FROM matches "
        "WHERE candidate_id = ? ORDER BY final_match_score DESC LIMIT ?",
        (int(candidate_id), int(top_n)),
    )
    role = _rows("SELECT role_applied FROM candidates WHERE candidate_id = ?", (int(candidate_id),))
    return {
        "candidate_id": int(candidate_id),
        "role_applied": role[0]["role_applied"] if role else None,
        "jobs": rows,
    }
