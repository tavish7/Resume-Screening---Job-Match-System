# Raw data (not all files are in Git — large files must be added locally)

| File | Source / notes |
|------|----------------|
| `Resume.csv` | Resume dataset (~54MB) |
| `postings.csv` | Job postings (~490MB) — **not in Git**; required for notebook `01` |
| `companies/*.csv` | Company reference tables |
| `jobs/*.csv` | Job child tables (skills, salaries, etc.) |
| `mappings/*.csv` | Skill and industry mappings |

After notebook `01_job_data_cleaning.ipynb`, outputs land in `cleaned_data/`.
