-- HireLens AI Database Schema
-- SQLite3 Compatible

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    department TEXT,
    experience_level TEXT,
    description_raw TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    classification TEXT NOT NULL CHECK(classification IN ('required', 'preferred')),
    weight INTEGER DEFAULT 3 CHECK(weight BETWEEN 1 AND 5),
    verification_criteria TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    candidate_code TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    location TEXT,
    is_sample BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'needs_review' CHECK(status IN ('needs_review', 'shortlisted', 'interview_planned', 'not_proceeding')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resume_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    file_name TEXT,
    file_path TEXT,
    raw_text TEXT NOT NULL,
    parsed_json TEXT,
    extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS requirement_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    requirement_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('supported', 'partially_supported', 'not_found', 'requires_verification')),
    evidence_snippet TEXT,
    source_location TEXT,
    explanation TEXT,
    confidence TEXT DEFAULT 'medium' CHECK(confidence IN ('high', 'medium', 'low', 'unverified')),
    follow_up_question TEXT,
    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY(requirement_id) REFERENCES requirements(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS candidate_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER UNIQUE NOT NULL,
    overall_score REAL NOT NULL,
    evidence_coverage REAL NOT NULL,
    required_skill_coverage REAL NOT NULL,
    preferred_skill_coverage REAL NOT NULL,
    information_completeness REAL NOT NULL,
    verification_uncertainty REAL NOT NULL,
    scoring_breakdown_json TEXT,
    computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    requirement_id INTEGER,
    category TEXT NOT NULL,
    competency TEXT NOT NULL,
    question TEXT NOT NULL,
    why_relevant TEXT NOT NULL,
    strong_answer_criteria TEXT NOT NULL,
    evaluation_rubric TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY(requirement_id) REFERENCES requirements(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS recruiter_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    job_id INTEGER,
    decision_status TEXT NOT NULL CHECK(decision_status IN ('needs_review', 'shortlisted', 'interview_planned', 'not_proceeding')),
    reason TEXT NOT NULL,
    decided_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    record_id TEXT,
    description TEXT NOT NULL,
    metadata_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_requirements_job_id ON requirements(job_id);
CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_candidate_id ON requirement_matches(candidate_id);
CREATE INDEX IF NOT EXISTS idx_scores_candidate_id ON candidate_scores(candidate_id);
CREATE INDEX IF NOT EXISTS idx_decisions_candidate_id ON recruiter_decisions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
