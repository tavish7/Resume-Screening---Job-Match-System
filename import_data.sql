-- Data Import
-- Run from project root so relative paths resolve, e.g.:
--   mysql --local-infile=1 -u user -p resume_matching < import_data.sql

-- Disable Foreign Key checks so the import doesn't crash on orphaned records
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Load Companies
LOAD DATA LOCAL INFILE 'cleaned_data/master/company_master.csv'
INTO TABLE companies
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- 2. Load Candidates
LOAD DATA LOCAL INFILE 'cleaned_data/master/resume_master.csv'
INTO TABLE candidates
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- 3. Load Jobs
LOAD DATA LOCAL INFILE 'cleaned_data/master/job_master.csv'
INTO TABLE jobs
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(job_id, title, title_clean, company_id, company_name, company_industry, company_size, employee_count_latest, description_clean, required_skills, required_skill_count, experience_required, industries, work_type, location, location_clean, min_salary, max_salary, normalized_salary_clean, has_salary, pay_period, currency, benefits, remote_allowed_bool, @listed_time, @expiry, description_word_count, jd_completeness_score, job_quality_score)
SET 
    listed_time_dt = NULLIF(@listed_time, ''),
    expiry_dt = NULLIF(@expiry, '');

-- 4. Load Matches
LOAD DATA LOCAL INFILE 'cleaned_data/matching/match_scores.csv'
INTO TABLE matches
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- 5. Load Job Skills
LOAD DATA LOCAL INFILE 'cleaned_data/normalized/job_skills_resolved.csv'
INTO TABLE job_skills
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- 6. Load Job Industries
LOAD DATA LOCAL INFILE 'cleaned_data/normalized/job_industries_resolved.csv'
INTO TABLE job_industries
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- Re-enable Foreign Key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Verify the upload
SELECT 'Companies' AS Table_Name, COUNT(*) AS Row_Count FROM companies
UNION ALL
SELECT 'Jobs', COUNT(*) FROM jobs
UNION ALL
SELECT 'Candidates', COUNT(*) FROM candidates
UNION ALL
SELECT 'Matches', COUNT(*) FROM matches
UNION ALL
SELECT 'Job Skills', COUNT(*) FROM job_skills
UNION ALL 
SELECT 'Job Industries', COUNT(*) FROM job_industries;
