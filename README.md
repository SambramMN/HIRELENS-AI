# HireLens AI — AI-Powered Recruitment Intelligence Platform
### Evidence Before Scores. Human Judgment Before Automated Decisions.

Built for the **Azentio Software Talent Acquisition Intern – AI & LLM** Technical Assignment.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-8%2F8%20Passing-brightgreen.svg)](#testing)
[![Live Demo](https://img.shields.io/badge/Production%20URL-hirelens--ai--liart.vercel.app-10B981.svg)](https://hirelens-ai-liart.vercel.app)

**Live Production URL:** [https://hirelens-ai-liart.vercel.app](https://hirelens-ai-liart.vercel.app)  
**GitHub Repository:** [https://github.com/SambramMN/HIRELENS-AI.git](https://github.com/SambramMN/HIRELENS-AI.git)

---

## 1. Executive Summary & Product Vision

Modern applicant tracking systems (ATS) often rely on superficial keyword density or opaque "AI percentage scores" that hallucinate qualifications, obscure critical missing evidence, and perpetuate algorithmic demographic biases.

**HireLens AI** re-architects recruitment screening around an uncompromising core principle:

> **"Evidence before scores. Human judgment before automated decisions."**

HireLens AI is not an ordinary resume-matcher or chatbot. It is an **explainable recruitment intelligence workstation** that breaks jobs down into verifiable criteria, grounds every match in verbatim resume sentences and page numbers, explicitly highlights verification gaps, provides blind screening, generates competency-tailored interview rubrics, maintains an auditable recruiter decision log, and offers an empirical counterfactual diagnostic test to demonstrate identifier invariance.

---

## 2. Key Proposed Innovations & Differentiators

| Capability | Legacy Resume Scanners | HireLens AI Platform |
| :--- | :--- | :--- |
| **Matching Foundation** | Opaque black-box similarity score | **Requirement-by-requirement verifiable evidence snippets** |
| **Source Traceability** | None (unattributed percentage) | **Page-grounded citations** (e.g. `Page 1 \| Professional Experience`) |
| **Missing Information** | Silently rejected or guessed | **Uncertainty-Aware Review** (`Requires Verification` status) |
| **Interviewer Support** | Generic static question banks | **Adaptive Interview Copilot** with 1–5 competency evaluation rubrics |
| **Demographic Fairness** | Unchecked demographic exposure | **Blind Screening Toggle** (masks names/contact while retaining technical evidence) |
| **Algorithmic Auditing** | None | **Controlled Counterfactual Diagnostic** (proves identity invariance) |
| **Human Accountability** | Automated binary accept/reject | **Mandatory Recruiter Rationale & Timestamped SQLite Audit Log** |

---

## 3. Specialist Multi-Agent Architecture

The system coordinates four modular, schema-validated specialist functions:

```
[Job Description] ──► (1) Job Analyst ──► [Structured Requirements]
                                                 │
[PDF Resumes]     ──► (2) Resume Analyst ────────┤
                                                 ▼
                                        (3) Matching Analyst
                                                 │
                             ┌───────────────────┴───────────────────┐
                             ▼                                       ▼
                   [Evidence Grounding]                  (4) Interview Planner
                   [Uncertainty Flags ]                              │
                   [Transparent Scores]                              ▼
                             │                          [Competency Rubrics]
                             └───────────────────┬───────────────────┘
                                                 ▼
                                    [Recruiter Decision Support]
                                    [  SQLite Audit Log Trail  ]
```

1. **Job Analyst Specialist** (`services/job_analyzer.py`): Structures raw job descriptions into prioritized requirements categorized into Programming Languages, Architecture, Databases, Cloud & DevOps, Testing, and Qualifications, with configured weights (1–5) and objective verification criteria.
2. **Resume Analyst Specialist** (`services/resume_parser.py`): Uses PyMuPDF to extract text from multi-page PDFs, tracking page numbers, segmenting work history, education, projects, and certifications, and handling corrupted or password-protected files gracefully.
3. **Matching Analyst Specialist** (`services/evidence_matcher.py`): Cross-references requirements against candidate resumes. Assigns one of 4 statuses (`Supported`, `Partially Supported`, `Requires Verification`, `Not Found`), extracts verbatim sentence snippets, assigns confidence levels, and computes a multi-dimensional transparent score.
4. **Interview Planner Specialist** (`services/interview_planner.py`): Generates candidate-tailored questions spanning technical depth, real-world troubleshooting, and evidence clarification, complete with 1–5 grading rubrics.

---

## 4. Technology Stack

- **Backend**: Python Flask 3.1.2 (WSGI compatible with standard local servers and Vercel Serverless Functions).
- **PDF Extraction**: PyMuPDF (`pymupdf`) with fallback page-tracking reader.
- **AI / LLM Integration**: Configurable OpenAI-compatible client (`openai` / `httpx`). Automatically falls back to high-precision deterministic regex & taxonomy parser when no API key is supplied.
- **Database & Storage**: SQLite3 with foreign keys, WAL mode, parameterization, and schema indexes.
- **Synthetic Data Generation**: ReportLab (`reportlab`) generating genuine multi-page demonstration PDF resumes.
- **Frontend**: Modern dark navy design system, CSS glassmorphism, responsive Bootstrap 5 grid, Lucide icons, and Chart.js radar/doughnut/bar visualizers.

---

## 5. Local Setup & Windows Launch Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.14 on Windows)
- Git

### Installation Steps

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/SambramMN/HIRELENS-AI.git
   cd HIRELENS-AI
   ```

2. **(Optional) Create and activate a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   python -m pip install -r requirements.txt
   ```

4. **Configure environment (Optional):**
   ```powershell
   Copy-Item .env.example .env
   ```
   *Note: HireLens AI runs out of the box with zero configuration using its local deterministic specialist engine. If you wish to connect an OpenAI-compatible LLM, add your `OPENAI_API_KEY` to `.env`.*

5. **Launch the application:**
   ```powershell
   python app.py
   ```

6. **Open in your browser:**
   ```
   http://127.0.0.1:5000
   ```

---

## 6. Pre-Loaded Demonstration Candidates

The platform automatically pre-seeds an initial role (**Senior Full Stack Python Developer**) and three realistic synthetic candidates:

- **Candidate A (`CAND-A101`, Sarah Jenkins)**: Strong senior full-stack developer with verified evidence across Python, FastAPI, React, PostgreSQL, Docker, and Redis. Overall Score: **88%** (Shortlisted).
- **Candidate B (`CAND-B204`, Michael Chang)**: Mid-level developer with strong Python and SQL background, partial React experience, and multiple requirements flagged for verification (Docker, CI/CD). Overall Score: **61%** (Needs Review).
- **Candidate C (`CAND-C309`, Elena Rostova)**: Staff-level backend and distributed systems architect with exceptional Python, PostgreSQL internals, and Kubernetes orchestration, but zero frontend React evidence. Overall Score: **68%** (Interview Planned).

*Pre-generated PDF resumes for all three candidates are placed in `uploads/` for direct inspection or re-upload testing.*

---

## 7. Video Demonstration Script & Voice-Over Talking Points

Use this script during your 3-to-5 minute screen recording:

### Minute 0:00 – 0:45 | Introduction & Product Philosophy
- *"Hello! This is HireLens AI, an AI-powered recruitment intelligence platform built for the Azentio Software talent acquisition assignment."*
- *"Our guiding design principle is: **Evidence before scores, human judgment before automated decisions.** Rather than treating hiring as an opaque percentage or chatbot query, HireLens AI gives recruiters explainable, auditable, evidence-backed tools."*
- Show the **Dashboard**: Highlight the 4 metrics cards, recruitment funnel doughnut chart, and the 5-step Specialist Workflow pipeline.

### Minute 0:45 – 1:30 | Job Intelligence & Structured Requirements
- Navigate to **Job Analysis** (`/jobs`):
- *"Here in the Job Analysis workstation, the recruiter inputs job requirements or raw descriptions. Our Job Analyst specialist extracts and categorizes skills into clear domains with verifiable criteria."*
- Click **Edit** on a requirement (e.g. *Docker Containerization*) to adjust importance weights (1–5) or verification criteria.
- Explain: *"Weights are recruiter-controlled and transparently logged to SQLite."*

### Minute 1:30 – 2:30 | Evidence-Grounded Candidate Screening
- Navigate to **Candidate Screening** (`/candidates`):
- Toggle the **Blind Screening** switch in the top navigation bar. Notice candidate names immediately convert to anonymized tokens (`CAND-A101`, `CAND-B204`) while keeping technical criteria visible.
- Click **Inspect** on Candidate A (`CAND-A101`):
- *"In the Candidate Evidence Report, notice how every single job requirement displays an exact verbatim sentence snippet from the candidate's resume, along with source page location (e.g. 'Page 1 \| Professional Experience')."*
- Point out the confidence indicator and the recommended interview follow-up question.
- Click **Record Decision**: Change status to *Shortlisted*, enter a required rationale, and save.

### Minute 2:30 – 3:30 | Side-by-Side Comparison & Adaptive Interview Copilot
- Navigate to **Candidate Comparison** (`/comparison`):
- Show the side-by-side metric matrix, the comparative bar chart, and the Requirement Evidence Grid comparing Candidate A, B, and C.
- Navigate to **Interview Copilot** (`/interview-copilot`):
- Select a candidate: Show how the system formulates questions categorized into Technical Knowledge, Problem-Solving, and Evidence Clarification.
- Demonstrate the 1–5 Evaluation Rubric and click **Copy Question & Rubric** to show the toast notification.

### Minute 3:30 – 4:30 | Fairness & Counterfactual Audit
- Navigate to **Fairness & Audit** (`/audit`):
- Explain: *"To prove that our matching engine is grounded purely in skills and evidence rather than demographic biases, we built an interactive Counterfactual Diagnostic."*
- Click **Run Counterfactual Test**:
- Show the two synthetic profiles: **Alex Morgan** (Seattle, WA) and **Priya Patel** (Bengaluru, India), who have **100% identical technical qualifications**.
- Highlight the result: **Score Delta is 0.0%**, with 0 requirement status divergence, confirming complete identity invariance.
- Navigate to **Activity Log** (`/activity-log`): Show the SQLite audit trail recording every event with timestamps.

---

## 8. Automated Testing

Run the test suite:
```powershell
python tests/test_suite.py
```
Expected output:
```
Ran 8 tests in 0.445s
OK
```

Critical test coverage:
1. Dashboard HTTP 200 & benchmark rendering
2. Job Analyst deterministic requirement extraction
3. PyMuPDF resume parsing & page location tracking
4. Evidence grounding without qualification hallucination
5. Adaptive interview questions with 1–5 rubrics
6. Identity invariance counterfactual test (0.0% divergence)
7. Recruiter decision recording and SQLite persistence
8. Navigation integrity across all 8 views

---

## 9. Vercel Serverless Deployment Architecture

HireLens AI is configured for seamless Vercel deployment:
- `api/index.py`: Serverless WSGI entry point exporting the Flask application.
- `vercel.json`: Directs routes to `@vercel/python` runtime.
- `config.py`: Detects serverless environment (`VERCEL=1`) and routes SQLite to `/tmp/hirelens.db` and temporary uploads to `/tmp/uploads`.

### Deploying to Vercel:
```bash
npx vercel
```
Or connect your GitHub repository directly to Vercel via the Vercel Dashboard.

---

## 10. Repository & License

- **GitHub Repository**: [https://github.com/SambramMN/HIRELENS-AI.git](https://github.com/SambramMN/HIRELENS-AI.git)
- **Author**: Technical Assignment for Azentio Software Talent Acquisition
- **License**: MIT License
