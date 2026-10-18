import json
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from database.db import get_db_connection
from services.fairness_audit import fairness_audit
from config import config

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
@views_bp.route("/dashboard")
def dashboard():
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    with get_db_connection() as conn:
        active_job = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
        candidates = conn.execute(
            """
            SELECT c.*, s.overall_score, s.evidence_coverage, s.required_skill_coverage, s.verification_uncertainty
            FROM candidates c
            LEFT JOIN candidate_scores s ON c.id = s.candidate_id
            ORDER BY s.overall_score DESC NULLS LAST
            """
        ).fetchall()
        requirements_count = 0
        if active_job:
            requirements_count = conn.execute(
                "SELECT COUNT(*) as count FROM requirements WHERE job_id = ?", (active_job["id"],)
            ).fetchone()["count"]

        recent_logs = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 6"
        ).fetchall()

        decisions = conn.execute("SELECT decision_status, count(*) as count FROM candidates GROUP BY decision_status").fetchall() if "decision_status" in [c[1] for c in conn.execute("PRAGMA table_info(candidates)").fetchall()] else []
        status_counts = conn.execute("SELECT status, count(*) as count FROM candidates GROUP BY status").fetchall()
        status_map = {r["status"]: r["count"] for r in status_counts}

    metrics = fairness_audit.get_audit_metrics()

    return render_template(
        "dashboard.html",
        active_job=active_job,
        candidates=candidates,
        requirements_count=requirements_count,
        status_map=status_map,
        recent_logs=recent_logs,
        metrics=metrics,
        blind_mode=blind_mode,
        llm_configured=bool(config.OPENAI_API_KEY)
    )

@views_bp.route("/jobs")
def jobs_view():
    with get_db_connection() as conn:
        jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        active_job = jobs[0] if jobs else None
        requirements = []
        if active_job:
            requirements = conn.execute(
                "SELECT * FROM requirements WHERE job_id = ? ORDER BY classification DESC, weight DESC",
                (active_job["id"],)
            ).fetchall()

    return render_template(
        "jobs.html",
        jobs=jobs,
        active_job=active_job,
        requirements=requirements,
        llm_configured=bool(config.OPENAI_API_KEY)
    )

@views_bp.route("/candidates")
def candidates_view():
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    with get_db_connection() as conn:
        active_job = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
        candidates = conn.execute(
            """
            SELECT c.*, s.overall_score, s.evidence_coverage, s.required_skill_coverage,
                   s.preferred_skill_coverage, s.verification_uncertainty,
                   r.file_name, r.extracted_at
            FROM candidates c
            LEFT JOIN candidate_scores s ON c.id = s.candidate_id
            LEFT JOIN resume_records r ON c.id = r.candidate_id
            ORDER BY s.overall_score DESC NULLS LAST
            """
        ).fetchall()

    return render_template(
        "candidates.html",
        active_job=active_job,
        candidates=candidates,
        blind_mode=blind_mode
    )

@views_bp.route("/candidates/<int:candidate_id>")
def candidate_detail(candidate_id: int):
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    with get_db_connection() as conn:
        candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not candidate:
            flash("Candidate not found.", "danger")
            return redirect(url_for("views.candidates_view"))

        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (candidate["job_id"],)).fetchone()
        resume_record = conn.execute("SELECT * FROM resume_records WHERE candidate_id = ?", (candidate_id,)).fetchone()
        scores = conn.execute("SELECT * FROM candidate_scores WHERE candidate_id = ?", (candidate_id,)).fetchone()

        matches = conn.execute(
            """
            SELECT m.*, r.name as req_name, r.category as req_category,
                   r.classification as req_classification, r.weight as req_weight,
                   r.verification_criteria as req_criteria
            FROM requirement_matches m
            JOIN requirements r ON m.requirement_id = r.id
            WHERE m.candidate_id = ?
            ORDER BY r.classification DESC, r.weight DESC
            """,
            (candidate_id,)
        ).fetchall()

        questions = conn.execute(
            "SELECT * FROM interview_questions WHERE candidate_id = ? ORDER BY id ASC",
            (candidate_id,)
        ).fetchall()

        decisions = conn.execute(
            "SELECT * FROM recruiter_decisions WHERE candidate_id = ? ORDER BY decided_at DESC",
            (candidate_id,)
        ).fetchall()

    parsed_data = {}
    if resume_record and resume_record["parsed_json"]:
        try:
            parsed_data = json.loads(resume_record["parsed_json"])
        except Exception:
            parsed_data = {}

    score_breakdown = {}
    if scores and scores["scoring_breakdown_json"]:
        try:
            score_breakdown = json.loads(scores["scoring_breakdown_json"])
        except Exception:
            score_breakdown = {}

    return render_template(
        "candidate_detail.html",
        candidate=candidate,
        job=job,
        resume_record=resume_record,
        parsed_data=parsed_data,
        scores=scores,
        score_breakdown=score_breakdown,
        matches=matches,
        questions=questions,
        decisions=decisions,
        blind_mode=blind_mode
    )

@views_bp.route("/comparison")
def comparison_view():
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    with get_db_connection() as conn:
        active_job = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
        candidates = conn.execute(
            """
            SELECT c.*, s.overall_score, s.evidence_coverage, s.required_skill_coverage,
                   s.preferred_skill_coverage, s.verification_uncertainty
            FROM candidates c
            LEFT JOIN candidate_scores s ON c.id = s.candidate_id
            ORDER BY s.overall_score DESC NULLS LAST
            """
        ).fetchall()

        requirements = []
        if active_job:
            requirements = conn.execute(
                "SELECT * FROM requirements WHERE job_id = ? ORDER BY classification DESC, weight DESC",
                (active_job["id"],)
            ).fetchall()

        all_matches = conn.execute("SELECT * FROM requirement_matches").fetchall()

    match_matrix = {}
    for m in all_matches:
        match_matrix[(m["candidate_id"], m["requirement_id"])] = dict(m)

    return render_template(
        "comparison.html",
        active_job=active_job,
        candidates=candidates,
        requirements=requirements,
        match_matrix=match_matrix,
        blind_mode=blind_mode
    )

@views_bp.route("/interview-copilot")
def interview_copilot():
    candidate_id = request.args.get("candidate_id", type=int)
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)

    with get_db_connection() as conn:
        candidates = conn.execute("SELECT id, candidate_code, full_name, status FROM candidates ORDER BY id ASC").fetchall()
        selected_candidate = None
        if candidate_id:
            selected_candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not selected_candidate and candidates:
            selected_candidate = candidates[0]
            candidate_id = selected_candidate["id"]

        questions = []
        if selected_candidate:
            questions = conn.execute(
                """
                SELECT q.*, r.name as req_name
                FROM interview_questions q
                LEFT JOIN requirements r ON q.requirement_id = r.id
                WHERE q.candidate_id = ?
                ORDER BY q.id ASC
                """,
                (candidate_id,)
            ).fetchall()

    return render_template(
        "interview_copilot.html",
        candidates=candidates,
        selected_candidate=selected_candidate,
        questions=questions,
        blind_mode=blind_mode,
        llm_configured=bool(config.OPENAI_API_KEY)
    )

@views_bp.route("/audit")
def audit_view():
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    with get_db_connection() as conn:
        active_job = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
        recent_logs = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20").fetchall()
    
    metrics = fairness_audit.get_audit_metrics()

    return render_template(
        "audit.html",
        active_job=active_job,
        metrics=metrics,
        recent_logs=recent_logs,
        blind_mode=blind_mode
    )

@views_bp.route("/activity-log")
def activity_log_view():
    search = request.args.get("q", "").strip()
    event_filter = request.args.get("event", "").strip()

    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if search:
        query += " AND (description LIKE ? OR record_id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if event_filter:
        query += " AND event_type = ?"
        params.append(event_filter)

    query += " ORDER BY timestamp DESC LIMIT 100"

    with get_db_connection() as conn:
        logs = conn.execute(query, params).fetchall()
        event_types = [r[0] for r in conn.execute("SELECT DISTINCT event_type FROM audit_logs ORDER BY event_type ASC").fetchall()]

    return render_template(
        "activity_log.html",
        logs=logs,
        event_types=event_types,
        search=search,
        selected_event=event_filter
    )

@views_bp.route("/settings")
def settings_view():
    blind_mode = session.get("blind_screening", config.BLIND_SCREENING_DEFAULT)
    return render_template(
        "settings.html",
        blind_mode=blind_mode,
        config=config,
        llm_configured=bool(config.OPENAI_API_KEY)
    )
