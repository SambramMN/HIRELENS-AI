import os
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from database.db import get_db_connection, log_audit_event
from services.job_analyzer import job_analyzer
from services.resume_parser import resume_parser
from services.evidence_matcher import evidence_matcher
from services.interview_planner import interview_planner
from services.fairness_audit import fairness_audit
from services.synthetic_data import seed_synthetic_data
from config import config

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/jobs", methods=["POST"])
def create_job():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    department = data.get("department", "").strip()
    experience = data.get("experience_level", "").strip()
    required = data.get("required_skills", "").strip()
    preferred = data.get("preferred_skills", "").strip()
    responsibilities = data.get("responsibilities", "").strip()
    description = data.get("description", "").strip()

    if not title:
        return jsonify({"success": False, "error": "Job title is required."}), 400

    # Specialist Agent 1: Job Analyst
    analysis = job_analyzer.analyze_job(
        title, department, experience, required, preferred, responsibilities, description
    )
    requirements = analysis.get("requirements", [])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (title, department, experience_level, description_raw, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (title, department, experience, description or f"{title} in {department}")
        )
        job_id = cursor.lastrowid

        for req in requirements:
            cursor.execute(
                """
                INSERT INTO requirements (job_id, name, category, classification, weight, verification_criteria)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    req["name"],
                    req["category"],
                    req["classification"],
                    req.get("weight", 3),
                    req.get("verification_criteria", "")
                )
            )

        conn.commit()

    log_audit_event(
        "JOB_CREATED",
        str(job_id),
        f"Job '{title}' created with {len(requirements)} structured requirements via {analysis.get('source')}."
    )

    return jsonify({
        "success": True,
        "job_id": job_id,
        "requirements_count": len(requirements),
        "source": analysis.get("source")
    })

@api_bp.route("/requirements/<int:req_id>", methods=["PUT"])
def update_requirement(req_id: int):
    data = request.get_json() or {}
    weight = data.get("weight")
    criteria = data.get("verification_criteria")
    classification = data.get("classification")

    with get_db_connection() as conn:
        req = conn.execute("SELECT * FROM requirements WHERE id = ?", (req_id,)).fetchone()
        if not req:
            return jsonify({"success": False, "error": "Requirement not found"}), 404

        conn.execute(
            """
            UPDATE requirements
            SET weight = COALESCE(?, weight),
                verification_criteria = COALESCE(?, verification_criteria),
                classification = COALESCE(?, classification)
            WHERE id = ?
            """,
            (weight, criteria, classification, req_id)
        )
        conn.commit()

    log_audit_event("REQUIREMENT_EDITED", str(req_id), f"Recruiter adjusted requirement '{req['name']}' configuration.")
    return jsonify({"success": True})

@api_bp.route("/candidates/upload", methods=["POST"])
def upload_candidate():
    job_id = request.form.get("job_id", type=int)
    manual_text = request.form.get("manual_text", "").strip()
    uploaded_files = request.files.getlist("resumes")

    with get_db_connection() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            job = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
            if not job:
                return jsonify({"success": False, "error": "No active job found. Please create a job description first."}), 400
        job_id = job["id"]
        job_title = job["title"]

        requirements = [dict(r) for r in conn.execute("SELECT * FROM requirements WHERE job_id = ?", (job_id,)).fetchall()]

    if not requirements:
        return jsonify({"success": False, "error": "No requirements configured for this job."}), 400

    processed_candidates = []
    upload_dir = Path(config.UPLOAD_FOLDER)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 1. Process files
    for file_obj in uploaded_files:
        if not file_obj or not file_obj.filename:
            continue
        filename = secure_filename(file_obj.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in config.ALLOWED_EXTENSIONS:
            continue

        file_path = upload_dir / filename
        file_obj.save(str(file_path))

        # Specialist Agent 2: Resume Analyst
        raw_text, pages, err = resume_parser.extract_text_from_pdf(str(file_path))
        if err or not raw_text:
            log_audit_event("PARSE_ERROR", None, f"Failed parsing {filename}: {err}")
            continue

        cand_info = _register_and_match_candidate(job_id, job_title, filename, str(file_path), raw_text, pages, requirements)
        if cand_info:
            processed_candidates.append(cand_info)

    # 2. Process manual text if provided
    if manual_text and len(manual_text) > 30:
        pages = [{"page_number": 1, "text": manual_text}]
        cand_info = _register_and_match_candidate(job_id, job_title, "Manual_Paste.txt", None, manual_text, pages, requirements)
        if cand_info:
            processed_candidates.append(cand_info)

    if not processed_candidates:
        return jsonify({"success": False, "error": "No valid resume text could be parsed or extracted."}), 400

    return jsonify({
        "success": True,
        "processed_count": len(processed_candidates),
        "candidates": processed_candidates
    })

def _register_and_match_candidate(job_id, job_title, file_name, file_path, raw_text, pages, requirements):
    # Specialist Agent 2: Resume Analyst
    parsed = resume_parser.parse_resume(raw_text, pages, file_name=file_name)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO candidates (job_id, candidate_code, full_name, email, phone, location, is_sample, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'needs_review')
            """,
            (job_id, parsed["candidate_code"], parsed["full_name"], parsed["email"], parsed["phone"], parsed["location"])
        )
        candidate_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO resume_records (candidate_id, file_name, file_path, raw_text, parsed_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (candidate_id, file_name, file_path, raw_text, json.dumps(parsed))
        )

        # Specialist Agent 3: Matching Analyst
        matches, scores = evidence_matcher.match_candidate(candidate_id, requirements, parsed, raw_text)

        for m in matches:
            cursor.execute(
                """
                INSERT INTO requirement_matches (
                    candidate_id, requirement_id, status, evidence_snippet,
                    source_location, explanation, confidence, follow_up_question
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, m["requirement_id"], m["status"], m["evidence_snippet"],
                    m["source_location"], m["explanation"], m["confidence"], m["follow_up_question"]
                )
            )

        cursor.execute(
            """
            INSERT INTO candidate_scores (
                candidate_id, overall_score, evidence_coverage, required_skill_coverage,
                preferred_skill_coverage, information_completeness, verification_uncertainty,
                scoring_breakdown_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id, scores["overall_score"], scores["evidence_coverage"],
                scores["required_skill_coverage"], scores["preferred_skill_coverage"],
                scores["information_completeness"], scores["verification_uncertainty"],
                json.dumps(scores)
            )
        )

        # Specialist Agent 4: Interview Planner
        questions = interview_planner.generate_interview_plan(
            parsed["full_name"], job_title, requirements, matches, parsed
        )
        for q in questions:
            cursor.execute(
                """
                INSERT INTO interview_questions (
                    candidate_id, requirement_id, category, competency, question,
                    why_relevant, strong_answer_criteria, evaluation_rubric
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, q.get("requirement_id"), q["category"], q["competency"],
                    q["question"], q["why_relevant"], q["strong_answer_criteria"],
                    q.get("evaluation_rubric", "")
                )
            )

        conn.commit()

    log_audit_event("CANDIDATE_ANALYZED", str(candidate_id), f"Candidate {parsed['full_name']} ({parsed['candidate_code']}) analyzed. Score: {scores['overall_score']}%.")
    return {
        "id": candidate_id,
        "code": parsed["candidate_code"],
        "name": parsed["full_name"],
        "score": scores["overall_score"]
    }

@api_bp.route("/candidates/<int:candidate_id>/decision", methods=["POST"])
def record_decision(candidate_id: int):
    data = request.get_json() or {}
    decision_status = data.get("status", "").strip()
    reason = data.get("reason", "").strip()

    valid_statuses = ("needs_review", "shortlisted", "interview_planned", "not_proceeding")
    if decision_status not in valid_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
    if not reason or len(reason) < 5:
        return jsonify({"success": False, "error": "A substantive reason is required to record a decision."}), 400

    with get_db_connection() as conn:
        cand = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not cand:
            return jsonify({"success": False, "error": "Candidate not found"}), 404

        conn.execute("UPDATE candidates SET status = ? WHERE id = ?", (decision_status, candidate_id))
        conn.execute(
            """
            INSERT INTO recruiter_decisions (candidate_id, job_id, decision_status, reason)
            VALUES (?, ?, ?, ?)
            """,
            (candidate_id, cand["job_id"], decision_status, reason)
        )
        conn.commit()

    log_audit_event(
        "RECRUITER_DECISION",
        str(candidate_id),
        f"Recruiter set status to '{decision_status}' for {cand['candidate_code']}. Reason: {reason}"
    )

    return jsonify({"success": True, "status": decision_status})

@api_bp.route("/candidates/<int:candidate_id>/interview-questions", methods=["POST"])
def generate_questions(candidate_id: int):
    with get_db_connection() as conn:
        candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not candidate:
            return jsonify({"success": False, "error": "Candidate not found"}), 404

        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (candidate["job_id"],)).fetchone()
        resume_record = conn.execute("SELECT * FROM resume_records WHERE candidate_id = ?", (candidate_id,)).fetchone()
        requirements = [dict(r) for r in conn.execute("SELECT * FROM requirements WHERE job_id = ?", (candidate["job_id"],)).fetchall()]
        matches = [dict(m) for m in conn.execute("SELECT * FROM requirement_matches WHERE candidate_id = ?", (candidate_id,)).fetchall()]

    parsed = json.loads(resume_record["parsed_json"]) if resume_record and resume_record["parsed_json"] else {}
    questions = interview_planner.generate_interview_plan(
        candidate["full_name"], job["title"], requirements, matches, parsed
    )

    with get_db_connection() as conn:
        conn.execute("DELETE FROM interview_questions WHERE candidate_id = ?", (candidate_id,))
        for q in questions:
            conn.execute(
                """
                INSERT INTO interview_questions (
                    candidate_id, requirement_id, category, competency, question,
                    why_relevant, strong_answer_criteria, evaluation_rubric
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, q.get("requirement_id"), q["category"], q["competency"],
                    q["question"], q["why_relevant"], q["strong_answer_criteria"],
                    q.get("evaluation_rubric", "")
                )
            )
        conn.commit()

    log_audit_event("INTERVIEW_QUESTIONS_GENERATED", str(candidate_id), f"Generated {len(questions)} interview questions for {candidate['candidate_code']}.")
    return jsonify({"success": True, "count": len(questions), "questions": questions})

@api_bp.route("/candidates/<int:candidate_id>", methods=["DELETE"])
def delete_candidate(candidate_id: int):
    with get_db_connection() as conn:
        cand = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not cand:
            return jsonify({"success": False, "error": "Candidate not found"}), 404

        resume_rec = conn.execute("SELECT file_path FROM resume_records WHERE candidate_id = ?", (candidate_id,)).fetchone()
        if resume_rec and resume_rec["file_path"]:
            p = Path(resume_rec["file_path"])
            if p.exists() and "Sample_" not in p.name:
                try:
                    p.unlink()
                except Exception:
                    pass

        conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        conn.commit()

    log_audit_event("CANDIDATE_DELETED", str(candidate_id), f"Deleted candidate {cand['candidate_code']} and purged files.")
    return jsonify({"success": True})

@api_bp.route("/audit/counterfactual", methods=["POST"])
def run_counterfactual():
    data = request.get_json() or {}
    job_id = data.get("job_id")

    with get_db_connection() as conn:
        if not job_id:
            job = conn.execute("SELECT id FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
            if not job:
                return jsonify({"success": False, "error": "No jobs available for counterfactual testing."}), 400
            job_id = job["id"]

    result = fairness_audit.run_counterfactual_test(job_id)
    log_audit_event("COUNTERFACTUAL_TEST_RUN", str(job_id), f"Executed identity counterfactual test. Result: {'PASSED' if result.get('test_passed') else 'FLAGGED'}.")
    return jsonify(result)

@api_bp.route("/settings/blind-screening", methods=["POST"])
def toggle_blind_screening():
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", False))
    session["blind_screening"] = enabled
    return jsonify({"success": True, "blind_screening": enabled})

@api_bp.route("/system/reset", methods=["POST"])
def reset_system():
    seed_synthetic_data(force=True)
    log_audit_event("SYSTEM_RESET", None, "Recruitment platform reset to clean demonstration benchmark.")
    return jsonify({"success": True, "message": "System reset to demonstration baseline."})
