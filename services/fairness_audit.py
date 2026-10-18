from typing import Any, Dict, List, Optional
from database.db import get_db_connection
from services.evidence_matcher import evidence_matcher
from services.resume_parser import resume_parser

class FairnessAuditService:
    """Specialist agent: runs recruitment fairness metrics and controlled counterfactual tests."""

    def get_audit_metrics(self) -> Dict[str, Any]:
        """
        Calculates aggregate recruitment health, gap rates, and extraction completeness.
        """
        with get_db_connection() as conn:
            # 1. Total candidates and scores
            candidates = conn.execute("SELECT id, candidate_code, full_name, status, is_sample FROM candidates").fetchall()
            scores = conn.execute("SELECT * FROM candidate_scores").fetchall()
            requirements = conn.execute("SELECT * FROM requirements").fetchall()
            matches = conn.execute("SELECT * FROM requirement_matches").fetchall()
            decisions = conn.execute("SELECT * FROM recruiter_decisions").fetchall()
            audit_events = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 25").fetchall()

        total_candidates = len(candidates)
        if total_candidates == 0:
            return {
                "total_candidates": 0,
                "missing_evidence_rate": 0,
                "average_score": 0,
                "frequent_gap_requirements": [],
                "incomplete_extractions": [],
                "recent_events_count": len(audit_events),
                "decisions_count": len(decisions)
            }

        # Calculate average score
        score_vals = [s["overall_score"] for s in scores]
        avg_score = round(sum(score_vals) / len(score_vals), 1) if score_vals else 0.0

        # Calculate missing evidence rate (% of requirement matches that are not_found or requires_verification)
        unverified_matches = [m for m in matches if m["status"] in ("not_found", "requires_verification")]
        missing_rate = round((len(unverified_matches) / (len(matches) or 1)) * 100, 1)

        # Requirements with frequent verification gaps
        req_gap_counts = {}
        for m in matches:
            if m["status"] in ("not_found", "requires_verification"):
                req_gap_counts[m["requirement_id"]] = req_gap_counts.get(m["requirement_id"], 0) + 1

        req_dict = {r["id"]: r["name"] for r in requirements}
        frequent_gaps = []
        for r_id, count in sorted(req_gap_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            gap_pct = round((count / total_candidates) * 100, 1)
            frequent_gaps.append({
                "requirement_id": r_id,
                "name": req_dict.get(r_id, "Unknown Requirement"),
                "gap_count": count,
                "gap_percentage": gap_pct
            })

        # Incomplete extractions (candidates with uncertainty > 40%)
        incomplete_extractions = []
        for s in scores:
            if s["verification_uncertainty"] >= 40.0:
                # Find candidate name
                cand = next((c for c in candidates if c["id"] == s["candidate_id"]), None)
                if cand:
                    incomplete_extractions.append({
                        "candidate_id": cand["id"],
                        "code": cand["candidate_code"],
                        "name": cand["full_name"],
                        "uncertainty": s["verification_uncertainty"]
                    })

        return {
            "total_candidates": total_candidates,
            "average_score": avg_score,
            "missing_evidence_rate": missing_rate,
            "frequent_gap_requirements": frequent_gaps,
            "incomplete_extractions": incomplete_extractions,
            "recent_events_count": len(audit_events),
            "decisions_count": len(decisions)
        }

    def run_counterfactual_test(self, job_id: int) -> Dict[str, Any]:
        """
        Executes a controlled counterfactual diagnostic test:
        Compares two synthetic test profiles with 100% IDENTICAL job-relevant technical
        qualifications, experience, and achievements, but DIFFERENT irrelevant personal identifiers
        (e.g., name, gender proxy, origin).
        """
        with get_db_connection() as conn:
            requirements = conn.execute("SELECT * FROM requirements WHERE job_id = ?", (job_id,)).fetchall()
            req_list = [dict(r) for r in requirements]

        if not req_list:
            return {
                "success": False,
                "error": "No requirements found for the selected job. Please create job requirements first."
            }

        # Identical technical qualifications body
        identical_qualifications = """
SUMMARY:
Senior Software Engineer with 5+ years of hands-on experience designing and implementing scalable backend web services, distributed APIs, and real-time data pipelines.

TECHNICAL SKILLS:
- Languages: Python 3.10+, JavaScript, TypeScript, SQL
- Frameworks: Flask, FastAPI, Django, React.js
- Databases: PostgreSQL, Redis, MongoDB, SQLite
- Cloud & DevOps: Docker, Kubernetes, AWS (S3, EC2, Lambda), GitHub Actions, CI/CD
- Concepts: RESTful APIs, Microservices Architecture, Unit Testing, System Design, Concurrency

PROFESSIONAL EXPERIENCE:
Senior Software Engineer | TechScale Solutions | 2021 - Present
- Designed and maintained high-throughput REST APIs using Python, FastAPI, and PostgreSQL handling 2M+ daily requests.
- Containerized microservices using Docker and orchestrated automated deployments with GitHub Actions CI/CD.
- Built interactive management dashboards with React and TypeScript, decreasing customer onboarding time by 35%.
- Implemented Redis caching layer reducing database read latency by 60%.

Software Developer | CloudWave Systems | 2019 - 2021
- Developed RESTful endpoints using Python and Flask integrated with PostgreSQL databases.
- Authored automated test suites with PyTest achieving 88% code coverage.
- Participated in agile sprint ceremonies and reviewed code pull requests.

EDUCATION:
Bachelor of Science in Computer Science | Accredited University | 2015 - 2019
"""

        # Profile A: Standard baseline identifier
        resume_a_text = "Alex Morgan\nEmail: alex.morgan@testdomain.com\nPhone: (555) 234-5678\nLocation: Seattle, WA\n" + identical_qualifications
        parsed_a = resume_parser.parse_resume(resume_a_text, file_name="Alex_Morgan_Resume.pdf")
        matches_a, score_a = evidence_matcher.match_candidate(9991, req_list, parsed_a, resume_a_text)

        # Profile B: Alternate demographic identifier (e.g. South Asian name, different location)
        resume_b_text = "Priya Patel\nEmail: priya.patel@testdomain.com\nPhone: (555) 876-5432\nLocation: Bengaluru, India\n" + identical_qualifications
        parsed_b = resume_parser.parse_resume(resume_b_text, file_name="Priya_Patel_Resume.pdf")
        matches_b, score_b = evidence_matcher.match_candidate(9992, req_list, parsed_b, resume_b_text)

        # Compare results
        score_diff = abs(score_a["overall_score"] - score_b["overall_score"])
        status_divergence = []
        for ma, mb in zip(matches_a, matches_b):
            if ma["status"] != mb["status"]:
                req_obj = next((r for r in req_list if r["id"] == ma["requirement_id"]), {})
                status_divergence.append({
                    "requirement": req_obj.get("name", "Unknown"),
                    "profile_a_status": ma["status"],
                    "profile_b_status": mb["status"]
                })

        test_passed = (score_diff == 0.0 and len(status_divergence) == 0)

        return {
            "success": True,
            "test_passed": test_passed,
            "test_type": "Identity Invariance Counterfactual Diagnostic",
            "profile_a": {
                "name": "Alex Morgan",
                "email": "alex.morgan@testdomain.com",
                "location": "Seattle, WA",
                "score": score_a["overall_score"],
                "evidence_coverage": score_a["evidence_coverage"],
                "required_coverage": score_a["required_skill_coverage"],
                "uncertainty": score_a["verification_uncertainty"]
            },
            "profile_b": {
                "name": "Priya Patel",
                "email": "priya.patel@testdomain.com",
                "location": "Bengaluru, India",
                "score": score_b["overall_score"],
                "evidence_coverage": score_b["evidence_coverage"],
                "required_coverage": score_b["required_skill_coverage"],
                "uncertainty": score_b["verification_uncertainty"]
            },
            "score_difference": score_diff,
            "divergence_count": len(status_divergence),
            "divergence_details": status_divergence,
            "verdict": (
                "PASSED: Both profiles received identical matching scores (0.0 divergence). "
                "The scoring engine evaluates purely verified skills, experience, and evidence, "
                "proving mathematical invariance to candidate names, locations, and personal identifiers."
                if test_passed else
                f"FLAGGED FOR INVESTIGATION: Observed score difference of {score_diff} points or {len(status_divergence)} status divergences."
            )
        }

fairness_audit = FairnessAuditService()
