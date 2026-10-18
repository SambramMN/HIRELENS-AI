import os
import json
import pytest
from pathlib import Path
from app import create_app
from database.db import get_db_connection
from services.job_analyzer import job_analyzer
from services.resume_parser import resume_parser
from services.evidence_matcher import evidence_matcher
from services.interview_planner import interview_planner
from services.fairness_audit import fairness_audit

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_hirelens.db"
    test_uploads = tmp_path / "test_uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setattr("config.config.DATABASE_PATH", str(test_db))
    monkeypatch.setattr("config.config.UPLOAD_FOLDER", str(test_uploads))
    monkeypatch.setattr("config.config.OPENAI_API_KEY", "")

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_dashboard_loads(client):
    """Verify dashboard loads with HTTP 200 and initial pre-seeded benchmark data."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"HireLens" in response.data
    assert b"Candidate Evidence Leaderboard" in response.data

def test_job_analyzer_deterministic():
    """Verify Job Analyst extracts and structures requirements without hallucinations."""
    title = "Backend Python Engineer"
    required = "Python, Flask, PostgreSQL, Docker"
    preferred = "Redis, Kubernetes"
    res = job_analyzer.analyze_job(title, "Engineering", "3+ years", required, preferred, "", "")
    reqs = res["requirements"]
    assert len(reqs) >= 4
    req_names = [r["name"] for r in reqs]
    assert "Python" in req_names
    assert "PostgreSQL" in req_names
    # Check that required has high weight
    python_req = next(r for r in reqs if r["name"] == "Python")
    assert python_req["classification"] == "required"
    assert python_req["weight"] == 5

def test_resume_parser_and_evidence_matcher():
    """Verify resume extraction, section segmentation, and grounded evidence matching."""
    sample_text = """
    Jane Doe
    Email: jane.doe@example.com | Phone: (555) 123-4567
    Location: New York, NY
    
    PROFESSIONAL EXPERIENCE
    Senior Engineer | FinTech Systems | 2021 - Present
    - Developed scalable microservices in Python and Flask with PostgreSQL database.
    - Implemented Docker containerization for automated CI/CD deployments.
    
    TECHNICAL SKILLS
    Python, Flask, Docker, PostgreSQL, Redis
    """
    pages = [{"page_number": 1, "text": sample_text}]
    parsed = resume_parser.parse_resume(sample_text, pages, "Jane_Doe_Resume.pdf")
    
    assert parsed["full_name"] == "Jane Doe"
    assert parsed["email"] == "jane.doe@example.com"
    assert "Python" in parsed["skills"]
    assert len(parsed["experience"]) >= 1

    requirements = [
        {"id": 1, "name": "Python", "category": "Programming Languages", "classification": "required", "weight": 5, "verification_criteria": "Python production experience."},
        {"id": 2, "name": "PostgreSQL", "category": "Databases & Storage", "classification": "required", "weight": 4, "verification_criteria": "Relational DB experience."},
        {"id": 3, "name": "Kubernetes", "category": "Cloud & DevOps", "classification": "preferred", "weight": 3, "verification_criteria": "K8s experience."}
    ]

    matches, scores = evidence_matcher.match_candidate(101, requirements, parsed, sample_text)
    assert len(matches) == 3
    
    # Python should be supported with evidence snippet
    py_match = next(m for m in matches if m["requirement_id"] == 1)
    assert py_match["status"] == "supported"
    assert "Python" in py_match["evidence_snippet"]
    assert "Page 1" in py_match["source_location"]

    # Kubernetes was not in resume -> must be 'not_found'
    k8s_match = next(m for m in matches if m["requirement_id"] == 3)
    assert k8s_match["status"] == "not_found"
    assert "No direct evidence located" in k8s_match["evidence_snippet"]

    assert scores["overall_score"] > 50

def test_interview_planner_generation():
    """Verify adaptive interview questions are generated with criteria and rubrics."""
    requirements = [
        {"id": 1, "name": "Python", "classification": "required", "weight": 5},
        {"id": 2, "name": "Kubernetes", "classification": "preferred", "weight": 3}
    ]
    matches = [
        {"requirement_id": 1, "status": "supported", "evidence_snippet": "Developed microservices in Python."},
        {"requirement_id": 2, "status": "not_found", "evidence_snippet": "No direct evidence."}
    ]
    parsed = {"skills": ["Python"], "projects": []}
    questions = interview_planner.generate_interview_plan("Jane Doe", "Backend Engineer", requirements, matches, parsed)
    
    assert len(questions) >= 3
    for q in questions:
        assert "question" in q
        assert "why_relevant" in q
        assert "strong_answer_criteria" in q
        assert "evaluation_rubric" in q

def test_counterfactual_fairness_diagnostic(client):
    """Verify counterfactual diagnostic test proves 0 divergence for identical qualifications."""
    response = client.post("/api/audit/counterfactual", json={})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["test_passed"] is True
    assert data["score_difference"] == 0.0
    assert data["divergence_count"] == 0

def test_recruiter_decision_flow(client):
    """Verify recording a recruiter decision updates SQLite and logs audit event."""
    # Fetch first candidate ID
    with get_db_connection() as conn:
        cand = conn.execute("SELECT id FROM candidates LIMIT 1").fetchone()
        assert cand is not None
        cand_id = cand["id"]

    response = client.post(
        f"/api/candidates/{cand_id}/decision",
        json={"status": "shortlisted", "reason": "Candidate verified with exceptional Python and PostgreSQL evidence."}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # Verify in DB
    with get_db_connection() as conn:
        updated = conn.execute("SELECT status FROM candidates WHERE id = ?", (cand_id,)).fetchone()
        assert updated["status"] == "shortlisted"
        
        decision_rec = conn.execute("SELECT * FROM recruiter_decisions WHERE candidate_id = ?", (cand_id,)).fetchone()
        assert decision_rec is not None
        assert "exceptional Python" in decision_rec["reason"]

def test_blind_screening_toggle(client):
    """Verify blind screening toggle endpoint."""
    response = client.post("/api/settings/blind-screening", json={"enabled": True})
    assert response.status_code == 200
    assert response.get_json()["blind_screening"] is True
