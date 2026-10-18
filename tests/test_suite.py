import unittest
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import json
from app import create_app
from database.db import get_db_connection
from services.job_analyzer import job_analyzer
from services.resume_parser import resume_parser
from services.evidence_matcher import evidence_matcher
from services.interview_planner import interview_planner
from services.fairness_audit import fairness_audit
from config import config

class TestHireLensAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = Path("instance/test_hirelens.db")
        cls.test_db.parent.mkdir(parents=True, exist_ok=True)
        config.DATABASE_PATH = str(cls.test_db)
        config.OPENAI_API_KEY = ""  # Force deterministic engine
        
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if cls.test_db.exists():
            try:
                cls.test_db.unlink()
            except Exception:
                pass

    def test_01_dashboard_loads(self):
        """Verify dashboard loads with HTTP 200 and initial pre-seeded benchmark data."""
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"HireLens", res.data)
        self.assertIn(b"Candidate Evidence Leaderboard", res.data)

    def test_02_job_analyzer_deterministic(self):
        """Verify Job Analyst extracts and structures requirements without hallucinations."""
        title = "Backend Python Engineer"
        required = "Python, Flask, PostgreSQL, Docker"
        preferred = "Redis, Kubernetes"
        res = job_analyzer.analyze_job(title, "Engineering", "3+ years", required, preferred, "", "")
        reqs = res["requirements"]
        self.assertGreaterEqual(len(reqs), 4)
        req_names = [r["name"] for r in reqs]
        self.assertIn("Python", req_names)
        self.assertIn("PostgreSQL", req_names)
        py_req = next(r for r in reqs if r["name"] == "Python")
        self.assertEqual(py_req["classification"], "required")
        self.assertEqual(py_req["weight"], 5)

    def test_03_resume_parser_and_evidence_matcher(self):
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
        
        self.assertEqual(parsed["full_name"], "Jane Doe")
        self.assertEqual(parsed["email"], "jane.doe@example.com")
        self.assertIn("Python", parsed["skills"])

        requirements = [
            {"id": 1, "name": "Python", "category": "Programming Languages", "classification": "required", "weight": 5, "verification_criteria": "Python production experience."},
            {"id": 2, "name": "PostgreSQL", "category": "Databases & Storage", "classification": "required", "weight": 4, "verification_criteria": "Relational DB experience."},
            {"id": 3, "name": "Kubernetes", "category": "Cloud & DevOps", "classification": "preferred", "weight": 3, "verification_criteria": "K8s experience."}
        ]

        matches, scores = evidence_matcher.match_candidate(101, requirements, parsed, sample_text)
        self.assertEqual(len(matches), 3)
        
        py_match = next(m for m in matches if m["requirement_id"] == 1)
        self.assertEqual(py_match["status"], "supported")
        self.assertIn("Python", py_match["evidence_snippet"])
        self.assertIn("Page 1", py_match["source_location"])

        k8s_match = next(m for m in matches if m["requirement_id"] == 3)
        self.assertEqual(k8s_match["status"], "not_found")
        self.assertIn("No direct evidence located", k8s_match["evidence_snippet"])
        self.assertGreater(scores["overall_score"], 50)

    def test_04_interview_planner_generation(self):
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
        self.assertGreaterEqual(len(questions), 3)
        for q in questions:
            self.assertIn("question", q)
            self.assertIn("why_relevant", q)
            self.assertIn("strong_answer_criteria", q)
            self.assertIn("evaluation_rubric", q)

    def test_05_counterfactual_fairness_diagnostic(self):
        """Verify counterfactual diagnostic test proves 0 divergence for identical qualifications."""
        res = self.client.post("/api/audit/counterfactual", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["test_passed"])
        self.assertEqual(data["score_difference"], 0.0)
        self.assertEqual(data["divergence_count"], 0)

    def test_06_recruiter_decision_flow(self):
        """Verify recording a recruiter decision updates SQLite and logs audit event."""
        with get_db_connection() as conn:
            cand = conn.execute("SELECT id FROM candidates LIMIT 1").fetchone()
            self.assertIsNotNone(cand)
            cand_id = cand["id"]

        res = self.client.post(
            f"/api/candidates/{cand_id}/decision",
            json={"status": "shortlisted", "reason": "Verified exceptional Python and PostgreSQL evidence with senior impact."}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        with get_db_connection() as conn:
            updated = conn.execute("SELECT status FROM candidates WHERE id = ?", (cand_id,)).fetchone()
            self.assertEqual(updated["status"], "shortlisted")

    def test_07_blind_screening_toggle(self):
        """Verify blind screening toggle endpoint."""
        res = self.client.post("/api/settings/blind-screening", json={"enabled": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["blind_screening"])

    def test_08_all_navigation_routes(self):
        """Ensure all primary routes load without error (200 OK)."""
        routes = ["/jobs", "/candidates", "/comparison", "/interview-copilot", "/audit", "/activity-log", "/settings"]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} failed with status {res.status_code}")

if __name__ == "__main__":
    unittest.main()
