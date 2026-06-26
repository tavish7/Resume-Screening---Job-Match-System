CREATE DATABASE IF NOT EXISTS resume_matching;
USE resume_matching;

-- 1. companies
CREATE TABLE companies (
  company_id              BIGINT PRIMARY KEY,
  name                    VARCHAR(255),
  company_description_clean LONGTEXT,
  company_size            VARCHAR(50),
  city                    VARCHAR(120),
  state                   VARCHAR(120),
  country                 VARCHAR(120),
  industries              VARCHAR(255),
  specialities            LONGTEXT,
  employee_count_latest   BIGINT,
  follower_count_latest   BIGINT,
  company_industry        VARCHAR(255)
);

-- 2. candidates
CREATE TABLE candidates (
  candidate_id              BIGINT PRIMARY KEY,
  category                  VARCHAR(60),
  category_clean            VARCHAR(60),
  role_applied              VARCHAR(60),
  resume_clean              LONGTEXT,
  resume_char_count         INT,
  resume_word_count         INT,
  extracted_skills          VARCHAR(500),
  skill_count               INT,
  education_levels          VARCHAR(120),
  highest_education         VARCHAR(30),
  years_experience          DECIMAL(4,1),
  candidate_email           VARCHAR(150),
  candidate_phone           VARCHAR(50),
  resume_completeness_score DECIMAL(4,3),
  is_low_quality            VARCHAR(5),
  INDEX idx_cand_role (category)
);

-- 3. jobs 
CREATE TABLE jobs (
  job_id                  BIGINT PRIMARY KEY,
  title                   VARCHAR(500),
  title_clean             VARCHAR(500),
  company_id              BIGINT,
  company_name            VARCHAR(255),
  company_industry        VARCHAR(255),
  company_size            VARCHAR(50),
  employee_count_latest   BIGINT,
  description_clean       LONGTEXT,
  required_skills         VARCHAR(255),
  required_skill_count    INT,
  experience_required     VARCHAR(50),
  industries              VARCHAR(255),
  work_type               VARCHAR(30),
  location                VARCHAR(255),
  location_clean          VARCHAR(255),
  min_salary              DECIMAL(12,2),
  max_salary              DECIMAL(12,2),
  normalized_salary_clean DECIMAL(12,2),
  has_salary              VARCHAR(5),
  pay_period              VARCHAR(20),
  currency                VARCHAR(10),
  benefits                VARCHAR(500),
  remote_allowed_bool     VARCHAR(5),
  listed_time_dt          DATETIME NULL,
  expiry_dt               DATETIME NULL,
  description_word_count  INT,
  jd_completeness_score   DECIMAL(4,2),
  job_quality_score       DECIMAL(4,3),
  INDEX idx_jobs_company (company_id),
  INDEX idx_jobs_exp (experience_required),
  INDEX idx_jobs_worktype (work_type),
  CONSTRAINT fk_jobs_company FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE SET NULL
);

-- 4. matches
CREATE TABLE matches (
  candidate_id      BIGINT,
  candidate_role    VARCHAR(60),
  job_id            BIGINT,
  job_title         VARCHAR(500),
  company_name      VARCHAR(255),
  text_match_pct    DECIMAL(5,2),
  skill_overlap_pct DECIMAL(5,2),
  final_match_score DECIMAL(5,2),
  match_rank        INT,
  matching_skills   VARCHAR(500),
  missing_skills    VARCHAR(500),
  suitability       VARCHAR(20),
  PRIMARY KEY (candidate_id, job_id),
  INDEX idx_m_job (job_id),
  INDEX idx_m_cand (candidate_id),
  INDEX idx_m_suit (suitability),
  CONSTRAINT fk_matches_cand FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  CONSTRAINT fk_matches_job FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- 5. job_skills
CREATE TABLE job_skills (
  job_id      BIGINT,
  skill_abr   VARCHAR(10),
  skill_name  VARCHAR(60),
  skill_clean VARCHAR(60),
  INDEX idx_js_job (job_id),
  INDEX idx_js_skill (skill_clean),
  CONSTRAINT fk_js_job FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- 6. job_industries
CREATE TABLE job_industries (
  job_id        BIGINT,
  industry_id   INT,
  industry_name VARCHAR(120),
  INDEX idx_ji_job (job_id),
  INDEX idx_ji_ind (industry_name),
  CONSTRAINT fk_ji_job FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);