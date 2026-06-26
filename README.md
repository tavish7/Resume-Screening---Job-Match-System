# Resume Screening & Job-Match System

An end-to-end recruitment analytics pipeline that cleans job and resume data, scores candidate–job fit with NLP, trains classifiers to predict suitability, and exposes insights through an AI chatbot (**ResBot**).

**Live demo:** [https://resbotv1.streamlit.app/](https://resbotv1.streamlit.app/)

**Repository:** [github.com/tavish7/Resume-Screening---Job-Match-System](https://github.com/tavish7/Resume-Screening---Job-Match-System)

---

## Overview

This project turns messy hiring data into actionable match intelligence:

| Dimension | Scale (processed) |
|-----------|-------------------|
| Job postings | 96,926 (deduplicated) |
| Companies | 24,473 |
| Candidate resumes | 2,481 across 24 role categories |
| Candidate–job match pairs | 24,810 (top 10 jobs per candidate) |

The system supports recruiters and analysts with **hybrid text + skill matching**, **supervised ML suitability labels**, SQL-ready master tables, and a **Streamlit chatbot** that answers questions in plain English while grounding responses in the project database.

---

## Pipeline phases

### Phase 1 — Job data cleaning (`01_job_data_cleaning.ipynb`)

- Loads raw LinkedIn-style job feeds (`postings`, companies, salaries, skills, industries, mappings).
- Normalizes text, resolves skills/industries to a shared vocabulary, caps salary outliers, and deduplicates postings.
- Produces `cleaned_data/normalized/` and master tables `job_master.csv`, `company_master.csv`.
- Quarantines orphan child records; flags semantic and exact duplicate job descriptions.

**Quality scores:** data quality 100 · NLP readiness 100 · ML readiness 99 · matching readiness 92

### Phase 2 — Resume cleaning (`02_resume_cleaning.ipynb`)

- Cleans 2,484 raw resumes; outputs 2,481 usable profiles (24 role categories).
- Light text normalization, skill extraction (snake_case aligned with jobs), education/experience parsing, completeness scoring.
- Quarantines unusable resumes; tracks category and skill frequency for EDA.

**Quality scores:** data quality 100 · skill extraction readiness 97 · matching readiness 99  
**Coverage:** 97.3% with extracted skills · 71.3% education · 38.2% explicit years of experience

### Phase 3 — Resume–job matching (`03_resume_job_matching.ipynb`)

- Hybrid scorer: **70% TF-IDF cosine similarity** (resume vs. job description) + **30% skill overlap**.
- Keeps top **10** job matches per candidate; assigns suitability tiers:
  - **Highly Suitable** — score ≥ 40
  - **Suitable** — score 20–39
  - **Not Suitable** — score &lt; 20
- Outputs `match_scores.csv`, `best_match_per_candidate.csv`, and `matching_summary.json`.

**Matching summary:** 2,481 candidates · 24,810 pairs · average match score **25.57**  
**Suitability distribution (pair-level):** Suitable 13,270 · Not Suitable 8,390 · Highly Suitable 3,150

### Phase 4 — ML classification (`04_ml_classification.ipynb`)

Supervised multi-class task: predict suitability (**Not Suitable / Suitable / Highly Suitable**) from resume and job text features—without leaking the hand-tuned match score into training features.

- **24,810** labeled pairs · **GroupShuffleSplit** by `candidate_id` (80/20).
- Models compared: Logistic Regression, Linear SVM, Random Forest, XGBoost, Neural Net (tabular features), SBERT + Neural Net.

#### Model results (test set, macro averages)

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|-------|----------|-------------------|----------------|------------|
| **XGBoost** *(selected)* | **0.922** | **0.894** | **0.928** | **0.909** |
| Neural Net (features) | 0.913 | 0.878 | 0.932 | 0.899 |
| Logistic Regression | 0.895 | 0.859 | 0.919 | 0.881 |
| Linear SVM | 0.890 | 0.861 | 0.900 | 0.877 |
| Random Forest | 0.886 | 0.875 | 0.882 | 0.874 |
| SBERT + Neural Net | 0.543 | 0.525 | 0.550 | 0.512 |

**Best model:** XGBoost — saved as `cleaned_data/models/best_model.joblib` with `feature_pipeline.joblib`.  
Tabular + TF-IDF features outperformed end-to-end SBERT embeddings on this dataset, likely because labels were derived from the same hybrid scoring rule and skill overlap signal is already explicit in engineered features.

### Phase 5 — Analytics & warehouse

- **MySQL schema** (`schema.sql`) and bulk load script (`import_data.sql`) for six core tables.
- **Sample analytics** in `queries.sql` (skill demand, suitability funnel, salary vs. skills, etc.).
- **SQLite warehouse** (`chatbot/build_db.py`) for portable, read-only chatbot queries.

### Phase 6 — ResBot chatbot (`chatbot/`)

**ResBot** is a Streamlit app powered by **Google Gemini**, **LangGraph**, and the SQLite warehouse.

#### Architecture

```
User (Streamlit UI)
        │
        ▼
   chatbot/app.py
        │
        ├── Chat tab ──► resbot/graph.py (LangGraph)
        │                    │
        │                    ├─ route → generic | bias | off_topic | data
        │                    └─ data path: gen_sql → exec_sql → summarize
        │                         (with SQL auto-repair, max 3 retries)
        │
        └── Resume Checker ──► resbot/resume_ingest.py
                              (PDF/DOCX parse + XGBoost suitability)
```

| Module | Role |
|--------|------|
| `app.py` | Streamlit UI — Chat + Resume Checker tabs |
| `graph.py` | LangGraph router and text-to-SQL pipeline |
| `db.py` | Read-only SQLite access, schema introspection |
| `llm.py` | Gemini API client (`GOOGLE_API_KEY`) |
| `prompts.py` | Persona, routing, SQL, and summarization prompts |
| `tools.py` | Deterministic match lookups (skill gap, recommendations) |
| `resume_ingest.py` | Upload parsing + Phase 4 model inference |
| `build_db.py` | Builds `resume_matching.db` from cleaned CSVs |

**Fair hiring:** ResBot refuses bias-based requests (gender, age, religion, etc.) and only answers from project data.

---

## Project insights

1. **Skill alignment matters** — Explicit skill overlap contributes 30% of the match score; jobs with sparse skill metadata produce weaker matches (matching readiness 92 on jobs vs. 99 on resumes).
2. **Suitability is skewed toward “Suitable”** — Most pairs land in the middle tier; “Highly Suitable” is selective (~12.7% of pairs), useful as a shortlist signal.
3. **Experience is often implicit** — Only 38% of resumes state years of experience; models and rules rely more on skills and role text.
4. **Duplicate and orphan job data is real** — Thousands of orphan salary/skill rows were quarantined; semantic duplicate detection surfaced 7k+ near-duplicate postings.
5. **Classical ML beats raw SBERT here** — XGBoost on engineered features reached 92% accuracy; pure embedding + neural net underfit, suggesting hybrid features already capture most label signal.
6. **Cloud deployment uses a slim warehouse** — When full `job_master.csv` is absent, the app builds a reduced SQLite DB from match results (~10k jobs) for fast hosted demos.

---

## Project structure

```
Resume-Screening---Job-Match-System/
├── Data/                          # Raw inputs (see Data/README.md)
├── cleaned_data/
│   ├── master/                    # resume_master, job_master, company_master
│   ├── normalized/                # Cleaned relational CSVs
│   ├── matching/                  # match_scores, best_match_per_candidate
│   ├── models/                    # best_model.joblib, feature_pipeline.joblib
│   ├── analysis/                  # Skill/category frequency tables
│   ├── reports/                   # JSON metrics, confusion matrices
│   └── resume_matching.db         # SQLite warehouse (generated locally)
├── 01_job_data_cleaning.ipynb
├── 02_resume_cleaning.ipynb
├── 03_resume_job_matching.ipynb
├── 04_ml_classification.ipynb
├── chatbot/
│   ├── app.py                     # Streamlit entrypoint
│   ├── build_db.py                # SQLite builder (+ auto-build on Cloud)
│   ├── requirements.txt         # Streamlit Cloud dependencies
│   └── resbot/                    # Chatbot package
├── project_paths.py               # Portable paths (no hard-coded directories)
├── schema.sql                     # MySQL DDL
├── import_data.sql                # MySQL bulk load (relative paths)
├── queries.sql                    # Example analytics queries
├── requirements_chatbot.txt     # Local pip dependencies
└── README.md
```

Paths are resolved relative to the repo root via `project_paths.py`—no machine-specific absolute paths.

---

## Getting started

### Prerequisites

- Python 3.10+
- Raw data under `Data/` (see `Data/README.md`)
- **Gemini API key** for ResBot chat (`GOOGLE_API_KEY`)

### Run the full pipeline locally

```bash
git clone https://github.com/tavish7/Resume-Screening---Job-Match-System.git
cd Resume-Screening---Job-Match-System
```

1. Add `Data/postings.csv` and other raw files (large `postings.csv` is not in Git).
2. Run notebooks in order: `01` → `02` → `03` → `04`.
3. Optional: load MySQL with `schema.sql` + `import_data.sql` (run from repo root).

### Run ResBot locally

```bash
pip install -r requirements_chatbot.txt
```

Create `.env` in the project root:

```env
GOOGLE_API_KEY=your-gemini-api-key
```

Build the database and start the app:

```bash
python chatbot/build_db.py
streamlit run chatbot/app.py
```

### Deploy on Streamlit Community Cloud

1. Fork or use this repo; main file: **`chatbot/app.py`**
2. Dependencies: **`chatbot/requirements.txt`** (auto-detected)
3. **Secrets** (Settings → Secrets):

```toml
GOOGLE_API_KEY = "your-gemini-api-key"
```

4. On first boot, the app builds `cleaned_data/resume_matching.db` from CSVs in the repo (~30–60 seconds).

**Hosted app:** [https://resbotv1.streamlit.app/](https://resbotv1.streamlit.app/)

---

## Data not in GitHub

To keep the repository under GitHub size limits, these files are generated locally and listed in `.gitignore`:

| File | Reason |
|------|--------|
| `Data/postings.csv` | ~490 MB raw postings |
| `cleaned_data/master/job_master.csv` | ~372 MB full job catalog |
| `cleaned_data/resume_matching.db` | Generated by `build_db.py` |
| `cleaned_data/models/sbert_embeddings.npz` | Large embedding cache |

The hosted app uses a **slim** job table derived from match outputs when `job_master.csv` is unavailable.

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Data processing | pandas, scikit-learn, TF-IDF |
| Matching | Cosine similarity + skill overlap |
| ML | XGBoost, Logistic Regression, SVM, Random Forest, Keras |
| Database | MySQL (schema), SQLite (chatbot) |
| Chatbot | Streamlit, LangGraph, LangChain, Google Gemini |
| Resume parsing | pypdf, python-docx, joblib |

---

## License & attribution

Bootcamp capstone project. Datasets combine public job posting structures and resume corpora used for educational analysis. Review data licenses before commercial use.
