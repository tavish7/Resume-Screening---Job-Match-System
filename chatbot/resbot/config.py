from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "cleaned_data"

DB_PATH = CLEAN / "resume_matching.db"
BEST_MODEL = CLEAN / "models" / "best_model.joblib"
FEATURE_PIPELINE = CLEAN / "models" / "feature_pipeline.joblib"

GEMINI_MODEL = "gemini-2.5-flash"

# the three labels the Phase 5 model and the matches table use
LABELS = ["Not Suitable", "Suitable", "Highly Suitable"]

# how many times we let the LLM rewrite a failing query before giving up
MAX_SQL_RETRIES = 3

# we never rank or filter candidates on these
PROTECTED_ATTRS = ["gender", "age", "religion", "marital status", "marital", "race", "ethnicity"]

# keep result sets sane for both the LLM context and the UI
ROW_LIMIT = 200
