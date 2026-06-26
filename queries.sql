USE resume_matching;

-- 1. What is the distribution of job postings by experience level?
SELECT experience_required, COUNT(job_id) AS total_jobs
FROM jobs
GROUP BY experience_required
ORDER BY total_jobs DESC;


-- 2. Which top 5 industries are actively hiring the most remote roles?
SELECT company_industry, COUNT(job_id) AS remote_job_count
FROM jobs
WHERE remote_allowed_bool = 'True'
GROUP BY company_industry
ORDER BY remote_job_count DESC
LIMIT 5;


-- 3. What is the average candidate resume completeness score per education level?
SELECT highest_education, ROUND(AVG(resume_completeness_score), 2) AS avg_completeness
FROM candidates
WHERE is_low_quality = 'False'
GROUP BY highest_education
ORDER BY avg_completeness DESC;


-- 4. How many jobs have a listed salary versus those that do not?
SELECT has_salary, COUNT(*) as job_count
FROM jobs
GROUP BY has_salary;


-- 5. Which companies have the highest average job quality score? 
WITH CompanyJobStats AS (
    SELECT company_id, COUNT(job_id) AS jobs_posted, AVG(job_quality_score) AS avg_quality
    FROM jobs
    GROUP BY company_id
    HAVING jobs_posted > 5
)
SELECT c.name, c.company_size, s.jobs_posted, ROUND(s.avg_quality, 3) AS avg_quality
FROM CompanyJobStats s
JOIN companies c ON s.company_id = c.company_id
ORDER BY s.avg_quality DESC
LIMIT 10;


-- 6. What is the skill demand profile for Data & ML roles?
SELECT js.skill_name, COUNT(js.job_id) AS demand_count
FROM job_skills js
JOIN jobs j ON js.job_id = j.job_id
WHERE j.title_clean LIKE '%data%' OR j.title_clean LIKE '%machine learning%'
GROUP BY js.skill_name
ORDER BY demand_count DESC
LIMIT 10;


-- 7. Identify candidates applying for roles where they lack more than 3 required skills.
SELECT c.candidate_id, c.role_applied, m.job_title, m.missing_skills, 
       (LENGTH(m.missing_skills) - LENGTH(REPLACE(m.missing_skills, '|', '')) + 1) AS missing_skill_count
FROM matches m
JOIN candidates c ON m.candidate_id = c.candidate_id
WHERE m.suitability IN ('Low', 'Moderate')
HAVING missing_skill_count > 3;


-- 8. What is the average salary offered for roles based in specific tech hubs?
SELECT location_clean, 
       COUNT(job_id) as total_roles, 
       ROUND(AVG(normalized_salary_clean), 2) AS avg_market_salary
FROM jobs
WHERE location_clean IN ('Toronto', 'San Francisco', 'New York', 'Seattle')
  AND has_salary = 'True'
GROUP BY location_clean
ORDER BY avg_market_salary DESC;


-- 9. Rank the top 3 candidates for every single job posting.
WITH RankedCandidates AS (
    SELECT job_id, candidate_id, final_match_score, suitability,
           ROW_NUMBER() OVER(PARTITION BY job_id ORDER BY final_match_score DESC) as match_rank_calc
    FROM matches
)
SELECT job_id, candidate_id, final_match_score, suitability
FROM RankedCandidates
WHERE match_rank_calc <= 3;


-- 10. What is the salary percentile for each job within its specific industry?
SELECT job_id, title_clean, company_industry, normalized_salary_clean,
       NTILE(4) OVER(PARTITION BY company_industry ORDER BY normalized_salary_clean DESC) as salary_quartile
FROM jobs
WHERE has_salary = 'True';


-- 11. Show the running total of job postings listed over time.
WITH DailyPosts AS (
    SELECT DATE(listed_time_dt) AS list_date, COUNT(job_id) AS daily_jobs
    FROM jobs
    WHERE listed_time_dt IS NOT NULL
    GROUP BY DATE(listed_time_dt)
)
SELECT list_date, daily_jobs,
       SUM(daily_jobs) OVER(ORDER BY list_date ASC) as running_total_jobs
FROM DailyPosts;


-- 12. Find jobs that pay more than the average salary of their own company.
WITH CompanyAverages AS (
    SELECT company_id, AVG(normalized_salary_clean) as comp_avg_salary
    FROM jobs
    WHERE has_salary = 'True'
    GROUP BY company_id
)
SELECT j.job_id, j.title_clean, j.company_name, j.normalized_salary_clean, ROUND(ca.comp_avg_salary, 2) AS company_avg
FROM jobs j
JOIN CompanyAverages ca ON j.company_id = ca.company_id
WHERE j.normalized_salary_clean > ca.comp_avg_salary;


-- 13. Calculate the percentage difference in match scores between the 1st and 2nd ranked candidate for a job.
WITH TopTwo AS (
    SELECT job_id, candidate_id, final_match_score,
           LEAD(final_match_score) OVER(PARTITION BY job_id ORDER BY final_match_score DESC) as next_best_score
    FROM matches
    WHERE match_rank <= 2
)
SELECT job_id, candidate_id AS top_candidate, final_match_score, next_best_score,
       ROUND(((final_match_score - next_best_score) / next_best_score) * 100, 2) AS score_gap_pct
FROM TopTwo
WHERE next_best_score IS NOT NULL;


-- 14. Identify the most frequent highest education level per job category.
WITH CategoryEd AS (
    SELECT category_clean, highest_education, COUNT(*) as ed_count,
           RANK() OVER(PARTITION BY category_clean ORDER BY COUNT(*) DESC) as ed_rank
    FROM candidates
    GROUP BY category_clean, highest_education
)
SELECT category_clean, highest_education, ed_count
FROM CategoryEd
WHERE ed_rank = 1;


-- 15. What is the overall suitability funnel across the platform?
SELECT suitability, 
       COUNT(*) as total_matches,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage_of_total
FROM matches
GROUP BY suitability
ORDER BY total_matches DESC;


-- 16. Which companies are competing for the exact same talent pool?
SELECT m1.company_name AS company_a, m2.company_name AS company_b, COUNT(DISTINCT m1.candidate_id) AS shared_candidates
FROM matches m1
JOIN matches m2 ON m1.candidate_id = m2.candidate_id 
    AND m1.company_name < m2.company_name
WHERE m1.suitability IN ('Highly Suitable', 'Perfect Match')
  AND m2.suitability IN ('Highly Suitable', 'Perfect Match')
GROUP BY company_a, company_b
ORDER BY shared_candidates DESC
LIMIT 10;


-- 17. What is the correlation between a job's description completeness and the average text match percentage it receives?
SELECT j.jd_completeness_score, ROUND(AVG(m.text_match_pct), 2) AS avg_text_match
FROM jobs j
JOIN matches m ON j.job_id = m.job_id
GROUP BY j.jd_completeness_score
ORDER BY j.jd_completeness_score DESC;


-- 18. Extract the average and max salary for jobs requiring a specific high-value skill.
SELECT js.skill_name, 
       ROUND(AVG(j.normalized_salary_clean), 2) AS avg_salary,
       MAX(j.normalized_salary_clean) AS max_salary
FROM job_skills js
JOIN jobs j ON js.job_id = j.job_id
WHERE js.skill_name IN ('Python', 'SQL', 'GitLab', 'Vertex AI') 
  AND j.has_salary = 'True'
GROUP BY js.skill_name;


-- 19. Identify candidate applications that have expired job listings.
SELECT c.candidate_id, c.role_applied, j.title_clean, j.expiry_dt
FROM matches m
JOIN jobs j ON m.job_id = j.job_id
JOIN candidates c ON m.candidate_id = c.candidate_id
WHERE j.expiry_dt < CURRENT_DATE()
  AND m.match_rank = 1;


-- 20. Find jobs with zero 'Highly Suitable' candidates.
SELECT j.job_id, j.title_clean, j.company_name
FROM jobs j
LEFT JOIN matches m ON j.job_id = m.job_id AND m.suitability IN ('Highly Suitable', 'Perfect Match')
WHERE m.candidate_id IS NULL;