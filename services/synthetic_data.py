import os
import json
from pathlib import Path
from typing import Dict, Any, List
from config import config
from database.db import get_db_connection, log_audit_event
from services.resume_parser import resume_parser
from services.evidence_matcher import evidence_matcher
from services.interview_planner import interview_planner

# ReportLab for creating genuine PDF resumes for testing
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

SAMPLE_CANDIDATE_RESUMES = {
    "candidate_a": {
        "code": "CAND-A101",
        "name": "Sarah Jenkins",
        "email": "sarah.jenkins.demo@syntheticmail.test",
        "phone": "(555) 349-8812",
        "location": "Austin, TX (Remote)",
        "file_name": "Sample_Candidate_A_Sarah_Jenkins.pdf",
        "status": "shortlisted",
        "decision_reason": "Exceptional evidence across required Python, React, PostgreSQL, and Docker stack with verified leadership impact.",
        "text": """Sarah Jenkins
Email: sarah.jenkins.demo@syntheticmail.test | Phone: (555) 349-8812 | Location: Austin, TX (Remote)
Portfolio: https://github.com/sarahjenkins-demo | LinkedIn: linkedin.com/in/sarahjenkins-demo

PROFESSIONAL SUMMARY
Senior Full Stack Engineer with 6 years of experience building mission-critical web applications, high-throughput REST APIs, and modern frontend dashboards. Proven track record leading architectural migrations to containerized microservices.

TECHNICAL SKILLS
- Programming Languages: Python 3.11, JavaScript (ES6+), TypeScript, SQL, Bash
- Web Frameworks: FastAPI, Flask, Django, React.js, Next.js, Redux Toolkit
- Databases & Caching: PostgreSQL, Redis, MongoDB, SQLAlchemy, SQLite
- Cloud & DevOps: Docker, Kubernetes, AWS (ECS, S3, RDS, CloudWatch), GitHub Actions, CI/CD pipelines
- Architecture & Practices: RESTful APIs, Microservices Architecture, TDD, Agile/Scrum, Git

PROFESSIONAL EXPERIENCE
Senior Full Stack Developer | Horizon Cloud Technologies | 2021 – Present
- Architected and delivered asynchronous REST APIs using Python and FastAPI, handling 15,000 requests per minute with 99.98% uptime.
- Led front-end redesign using React.js and TypeScript, reducing client dashboard load times by 42% for over 50,000 monthly active enterprise users.
- Designed relational schemas and query optimizations in PostgreSQL, cutting complex transaction execution latency by 55%.
- Containerized legacy services with Docker and implemented automated testing in GitHub Actions CI/CD pipelines, increasing deployment frequency from weekly to daily.
- Mentored 4 junior engineers on code review best practices and asynchronous Python programming.

Software Engineer | Apex FinTech Solutions | 2018 – 2021
- Developed financial transaction reporting services using Python and Flask integrated with PostgreSQL databases.
- Built reusable UI component libraries in React and modern CSS, ensuring strict WCAG 2.1 accessibility compliance.
- Configured Redis caching layers for volatile stock market data feeds, slashing peak database load by 65%.
- Authored automated unit and integration tests using PyTest and Jest, maintaining 91% code coverage.

KEY PROJECTS
- Distributed Task Pipeline: Built an open-source task queue with Python, Redis, and Docker with over 450 GitHub stars.
- Real-Time Analytics Portal: Created a responsive React and FastAPI telemetry visualizer utilized across 12 engineering teams.

EDUCATION & CERTIFICATIONS
- Bachelor of Science in Computer Science | University of Texas at Austin | 2014 – 2018
- AWS Certified Solutions Architect – Associate (2023)
"""
    },
    "candidate_b": {
        "code": "CAND-B204",
        "name": "Michael Chang",
        "email": "michael.chang.demo@syntheticmail.test",
        "phone": "(555) 782-9931",
        "location": "Chicago, IL",
        "file_name": "Sample_Candidate_B_Michael_Chang.pdf",
        "status": "needs_review",
        "decision_reason": "",
        "text": """Michael Chang
Email: michael.chang.demo@syntheticmail.test | Phone: (555) 782-9931 | Location: Chicago, IL
LinkedIn: linkedin.com/in/michaelchang-demo

PROFESSIONAL SUMMARY
Software Developer with 3 years of professional experience primarily focused on backend Python services and relational databases. Eager to expand into full stack development and cloud infrastructure.

TECHNICAL SKILLS
- Languages: Python, JavaScript, SQL, HTML5, CSS3
- Frameworks: Flask, Django, basic React
- Databases: PostgreSQL, MySQL, SQLite
- Tools & Practices: Git, REST APIs, Linux, Jira, Agile

PROFESSIONAL EXPERIENCE
Software Developer | MidWest Logistics Software | 2021 – Present
- Implemented RESTful endpoints using Python and Flask for shipment tracking and driver dispatch systems.
- Wrote complex SQL queries and migration scripts for PostgreSQL databases storing over 3 million freight records.
- Collaborated with frontend teammates to integrate JSON APIs with web client interfaces.
- Experimented with Docker for local developer container setup, but production deployments are managed by the IT infrastructure team.
- Participated in weekly agile standups and sprint planning sessions.

Junior Web Developer | Prairie Tech Agency | 2020 – 2021
- Created static and lightweight interactive web pages using HTML, CSS, JavaScript, and occasional React components.
- Assisted with bug fixes and data validation scripts in Python and Django.
- Maintained documentation for customer onboarding workflows.

EDUCATION & PROJECTS
- Bachelor of Science in Information Technology | University of Illinois Chicago | 2016 – 2020
- Package Tracker Demo: Personal side project in Python and Flask querying open shipping APIs.
"""
    },
    "candidate_c": {
        "code": "CAND-C309",
        "name": "Elena Rostova",
        "email": "elena.rostova.demo@syntheticmail.test",
        "phone": "(555) 914-2201",
        "location": "Seattle, WA",
        "file_name": "Sample_Candidate_C_Elena_Rostova.pdf",
        "status": "interview_planned",
        "decision_reason": "Extraordinary backend, PostgreSQL, and distributed systems depth. Minimal React evidence, but ideal if paired with frontend specialists.",
        "text": """Elena Rostova
Email: elena.rostova.demo@syntheticmail.test | Phone: (555) 914-2201 | Location: Seattle, WA
GitHub: github.com/erostova-demo

PROFESSIONAL SUMMARY
Senior Backend & Distributed Systems Specialist with 7 years of deep engineering experience in Python high-concurrency architectures, PostgreSQL database internals, Docker container orchestration, and cloud reliability engineering.

TECHNICAL SKILLS
- Core Languages: Python, Go, C++, SQL
- Backend & Microservices: FastAPI, Flask, gRPC, Celery, RESTful APIs, Message Queues (RabbitMQ, Kafka)
- Databases & Internals: PostgreSQL (Advanced Indexing, Partitioning, Query Planning), Redis, Cassandra
- Cloud & Infrastructure: Docker, Kubernetes, AWS (EKS, RDS, S3, IAM, CloudFormation), Linux Kernel Tuning, CI/CD
- Concepts: Distributed Systems, High Availability, Concurrency, Observability (Prometheus, Grafana)

PROFESSIONAL EXPERIENCE
Staff Backend Engineer | Cascade Cloud Infrastructure | 2021 – Present
- Led the backend engineering team in architecting a high-throughput event processing platform using Python and FastAPI, processing 40M+ events per day.
- Engineered PostgreSQL sharding and partitioning strategies that improved query response times by 70% at petabyte scale.
- Built automated multi-stage CI/CD deployment pipelines utilizing Docker and Kubernetes on AWS EKS with zero-downtime rolling updates.
- Authored internal RFCs on system architecture, API backwards compatibility, and disaster recovery.

Senior Systems Developer | Seattle Data Stream | 2018 – 2021
- Developed distributed data ingestion services using Python and Go communicating via REST APIs and RabbitMQ.
- Re-architected PostgreSQL connection pooling via PgBouncer and optimized slow queries, reducing database CPU utilization by 40%.
- Containerized all 18 core microservices with Docker, ensuring strict environment parity across staging and production.

EDUCATION & CERTIFICATIONS
- Master of Science in Computer Science | University of Washington | 2016 – 2018
- Bachelor of Engineering in Software Engineering | 2012 – 2016
- Certified Kubernetes Administrator (CKA)
"""
    }
}

def generate_pdf_file(file_path: Path, title: str, text: str):
    """Generates a clean, professional PDF file using ReportLab."""
    if not HAS_REPORTLAB:
        # Fallback to plain text file if reportlab is unavailable
        with open(file_path.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        return

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    # Custom styling
    header_style = ParagraphStyle(
        'HeaderName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0B0F19')
    )
    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4B5563')
    )
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#059669'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1F2937')
    )

    story = []
    lines = text.strip().splitlines()

    if lines:
        story.append(Paragraph(lines[0], header_style))
        story.append(Spacer(1, 4))
        if len(lines) > 1 and ("Email:" in lines[1] or "@" in lines[1]):
            story.append(Paragraph(lines[1], contact_style))
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E7EB'), spaceAfter=10))
            content_lines = lines[2:]
        else:
            content_lines = lines[1:]

        for line in content_lines:
            line_str = line.strip()
            if not line_str:
                story.append(Spacer(1, 4))
                continue
            if line_str.isupper() or any(line_str.startswith(h) for h in ["PROFESSIONAL", "TECHNICAL", "EDUCATION", "KEY PROJECTS", "CERTIFICATIONS"]):
                story.append(Paragraph(line_str, section_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#D1D5DB'), spaceAfter=6))
            else:
                clean_line = line_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(clean_line, body_style))
                story.append(Spacer(1, 2))

    doc.build(story)

def seed_synthetic_data(force: bool = False):
    """
    Seeds initial demonstration job, synthetic candidates, PDF files, and analysis.
    """
    with get_db_connection() as conn:
        existing_job = conn.execute("SELECT id FROM jobs LIMIT 1").fetchone()
        if existing_job and not force:
            return  # Already seeded

        # Clear existing data if forcing
        if force:
            conn.execute("DELETE FROM jobs")
            conn.execute("DELETE FROM candidates")
            conn.execute("DELETE FROM audit_logs")
            conn.commit()

        # 1. Create Job
        job_title = "Senior Full Stack Python Developer"
        job_dept = "Engineering & Cloud Platform"
        job_exp = "4+ years"
        job_desc = """We are seeking a talented Senior Full Stack Python Developer to design, build, and scale our core cloud platform.
You will architect robust backend microservices, engineer responsive web dashboards, optimize relational databases, and collaborate with cloud infrastructure teams.

Key Responsibilities:
- Design and maintain asynchronous RESTful APIs using Python, FastAPI, or Flask.
- Build clean, accessible, responsive frontend applications with React and modern JavaScript/TypeScript.
- Architect and optimize PostgreSQL databases, indexes, and queries for high performance.
- Containerize application components using Docker and participate in CI/CD pipeline deployments.
- Collaborate on system design, code reviews, and automated unit testing.
"""

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (title, department, experience_level, description_raw, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (job_title, job_dept, job_exp, job_desc)
        )
        job_id = cursor.lastrowid

        # 2. Create Requirements
        requirements_def = [
            ("Python Backend Development", "Programming Languages", "required", 5, "Proven production experience building web services or APIs with Python."),
            ("RESTful API Architecture", "Architecture & API", "required", 5, "Documented experience designing, implementing, and securing REST APIs."),
            ("PostgreSQL & Relational Databases", "Databases & Storage", "required", 4, "Experience writing complex SQL queries, database indexing, and schema design."),
            ("Docker Containerization", "Cloud & DevOps", "required", 4, "Hands-on experience creating Dockerfiles, multi-stage builds, and container runtimes."),
            ("React.js Frontend Development", "Frameworks & Libraries", "required", 4, "Demonstrated experience building interactive user interfaces with React."),
            ("Redis Caching & In-Memory Stores", "Databases & Storage", "preferred", 3, "Experience configuring Redis for caching, pub/sub, or rate limiting."),
            ("Kubernetes & Cloud Orchestration", "Cloud & DevOps", "preferred", 3, "Familiarity with Kubernetes clusters, Helm charts, or managed cloud EKS/ECS."),
            ("CI/CD Automation & GitHub Actions", "Cloud & DevOps", "preferred", 3, "Experience setting up automated build, test, and deployment workflows."),
            ("Relevant Experience (4+ Years)", "Domain & Qualifications", "required", 5, "Career timeline demonstrating at least 4 years in software development roles.")
        ]

        req_ids = []
        for name, cat, classification, weight, criteria in requirements_def:
            cursor.execute(
                """
                INSERT INTO requirements (job_id, name, category, classification, weight, verification_criteria)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, name, cat, classification, weight, criteria)
            )
            req_ids.append(cursor.lastrowid)

        conn.commit()

        # Retrieve requirements as dicts
        req_rows = conn.execute("SELECT * FROM requirements WHERE job_id = ?", (job_id,)).fetchall()
        req_list = [dict(r) for r in req_rows]

        # 3. Seed Candidates & PDF Files
        upload_dir = Path(config.UPLOAD_FOLDER)
        upload_dir.mkdir(parents=True, exist_ok=True)

        for key, data in SAMPLE_CANDIDATE_RESUMES.items():
            pdf_path = upload_dir / data["file_name"]
            generate_pdf_file(pdf_path, data["name"], data["text"])

            cursor.execute(
                """
                INSERT INTO candidates (job_id, candidate_code, full_name, email, phone, location, is_sample, status)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (job_id, data["code"], data["name"], data["email"], data["phone"], data["location"], data["status"])
            )
            candidate_id = cursor.lastrowid

            # Parse resume
            raw_text, pages, err = resume_parser.extract_text_from_pdf(str(pdf_path))
            if not raw_text:
                raw_text = data["text"]
                pages = [{"page_number": 1, "text": raw_text}]
            
            parsed_data = resume_parser.parse_resume(raw_text, pages, file_name=data["file_name"])

            cursor.execute(
                """
                INSERT INTO resume_records (candidate_id, file_name, file_path, raw_text, parsed_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (candidate_id, data["file_name"], str(pdf_path), raw_text, json.dumps(parsed_data))
            )

            # Match requirements
            matches, scores = evidence_matcher.match_candidate(candidate_id, req_list, parsed_data, raw_text)

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

            # Insert scores
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

            # Generate questions
            questions = interview_planner.generate_interview_plan(
                data["name"], job_title, req_list, matches, parsed_data
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

            # Insert recruiter decision if present
            if data["decision_reason"]:
                cursor.execute(
                    """
                    INSERT INTO recruiter_decisions (candidate_id, job_id, decision_status, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (candidate_id, job_id, data["status"], data["decision_reason"])
                )

            log_audit_event("CANDIDATE_INITIALIZED", str(candidate_id), f"Synthetic candidate {data['name']} ({data['code']}) preloaded with evidence matching.", conn=conn)

        log_audit_event("JOB_CREATED", str(job_id), f"Initial demo job '{job_title}' initialized with 9 requirements.", conn=conn)

seed_service = seed_synthetic_data
