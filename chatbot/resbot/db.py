"""Thin read-only access layer over the SQLite warehouse.

Everything here opens the DB in read-only mode (`mode=ro`). That's the real
guard against a generated query doing anything destructive - the keyword check
in `run_sql` is just there to fail fast with a friendlier message.
"""
import re
import sqlite3
from functools import lru_cache

from .config import DB_PATH, ROW_LIMIT

TABLES = ["companies", "candidates", "jobs", "matches", "job_skills", "job_industries"]

_WRITE_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum)\b",
    re.IGNORECASE,
)


def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} is missing - run `python chatbot/build_db.py` first."
        )
    # uri=True lets us pass the read-only flag; check_same_thread off for Streamlit
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)


@lru_cache(maxsize=1)
def schema_text():
    """A compact CREATE-style description of every table, for the SQL prompt."""
    conn = connect()
    blocks = []
    for table in TABLES:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        lines = [f"  {c[1]} {c[2] or 'TEXT'}" for c in cols]
        blocks.append(f"{table} (\n" + ",\n".join(lines) + "\n)")
    conn.close()
    return "\n\n".join(blocks)


@lru_cache(maxsize=1)
def table_counts():
    conn = connect()
    out = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    conn.close()
    return out


@lru_cache(maxsize=1)
def suitability_values():
    conn = connect()
    vals = [r[0] for r in conn.execute("SELECT DISTINCT suitability FROM matches").fetchall()]
    conn.close()
    return vals


def is_read_only(sql):
    stripped = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.MULTILINE | re.DOTALL).strip()
    if not stripped:
        return False
    first = stripped.lower().lstrip("(")
    if not (first.startswith("select") or first.startswith("with")):
        return False
    # don't let "show me the schema" turn into a sqlite_master dump
    if "sqlite_master" in stripped.lower() or "sqlite_schema" in stripped.lower():
        return False
    return _WRITE_WORDS.search(stripped) is None


def run_sql(sql, limit=ROW_LIMIT):
    """Run a SELECT and return (columns, rows). Raises on anything non-read-only."""
    if not is_read_only(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")
    conn = connect()
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit)
        return cols, rows
    finally:
        conn.close()
