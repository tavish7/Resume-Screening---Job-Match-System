# Resume Screening & Job-Match System

## Setup

1. Clone the repo and open the project root (folder containing `Data/` and `cleaned_data/`).
2. Place raw inputs under `Data/` (see `Data/README.md`).
3. Run notebooks in order: `01` → `02` → `03` → `04`, or use existing `cleaned_data/` outputs.
4. Chatbot: `pip install -r requirements_chatbot.txt`, set `.env` with `GEMINI_API_KEY`, then:
   - `python chatbot/build_db.py`
   - `streamlit run chatbot/app.py`

**Streamlit Community Cloud:** uses `chatbot/requirements.txt` automatically when main file is `chatbot/app.py`. Set secret `GOOGLE_API_KEY` in the app dashboard. On first boot the app builds `cleaned_data/resume_matching.db` from CSVs in the repo (about 30–60s).

All paths are **relative to the project root** via `project_paths.py` (no machine-specific paths).

## GitHub

Large generated files (`job_master.csv`, `postings.csv`, SQLite DB, SBERT embeddings) are not in the repo. Regenerate locally with the notebooks.
