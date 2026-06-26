"""Project-relative paths (no machine-specific absolute paths)."""
from pathlib import Path


def find_project_root() -> Path:
    """Folder that contains Data/ and cleaned_data/."""
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent,
    ]
    for base in candidates:
        if (base / "Data").is_dir() and (base / "cleaned_data").is_dir():
            return base
    return Path(__file__).resolve().parent


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "Data"
CLEANED_DIR = PROJECT_ROOT / "cleaned_data"

# Common outputs
RESUME_CSV = DATA_DIR / "Resume.csv"
POSTINGS_CSV = DATA_DIR / "postings.csv"
RESUME_MASTER = CLEANED_DIR / "master" / "resume_master.csv"
JOB_MASTER = CLEANED_DIR / "master" / "job_master.csv"
MATCH_SCORES = CLEANED_DIR / "matching" / "match_scores.csv"
BEST_MATCH = CLEANED_DIR / "matching" / "best_match_per_candidate.csv"


def rel(path: Path) -> str:
    """POSIX relative path for logs and SQL (e.g. cleaned_data/master/job_master.csv)."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
