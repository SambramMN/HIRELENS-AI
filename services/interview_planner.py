from typing import Any, Dict, List, Optional
from services.llm_service import llm_service

class InterviewPlanner:
    """Specialist agent: formulates candidate-specific, evidence-grounded interview questions with structured evaluation rubrics."""

    def generate_interview_plan(
        self,
        candidate_name: str,
        job_title: str,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        parsed_resume: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generates structured interview questions categorized by competency and objective.
        Tries LLM first, gracefully falls back to deterministic generator.
        """
        if llm_service.is_configured:
            llm_result = self._generate_with_llm(candidate_name, job_title, requirements, matches, parsed_resume)
            if llm_result and "questions" in llm_result and len(llm_result["questions"]) > 0:
                return llm_result["questions"]

        return self._generate_deterministic(job_title, requirements, matches, parsed_resume)

    def _generate_with_llm(
        self,
        candidate_name: str,
        job_title: str,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        parsed_resume: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        req_map = {r["id"]: r["name"] for r in requirements}
        evidence_summary = []
        for m in matches:
            r_name = req_map.get(m["requirement_id"], "Requirement")
            evidence_summary.append(f"- {r_name}: Status={m['status']}, Snippet='{m.get('evidence_snippet', '')}'")

        system_prompt = (
            "You are an expert Technical Interview Planner. "
            "Generate candidate-specific interview questions grounded in job requirements and resume evidence gaps. "
            "CRITICAL: Do NOT ask about protected characteristics, family status, religion, caste, health, or personal attributes. "
            "Output valid JSON with key 'questions' as a list of 5 to 7 question objects. "
            "Each question object MUST contain:\n"
            "- category: one of 'Technical Knowledge', 'Practical Problem-Solving', 'Project Experience', 'Role-Specific Scenarios', 'Evidence Clarification'\n"
            "- competency: concise competency being assessed\n"
            "- question: specific, probing interview question\n"
            "- why_relevant: explanation linking question to candidate's resume evidence or verification gap\n"
            "- strong_answer_criteria: what a strong candidate response must demonstrate\n"
            "- evaluation_rubric: clear criteria for 1 (Poor), 3 (Adequate), 5 (Exemplary)"
        )

        user_prompt = f"""
Job Title: {job_title}
Candidate: {candidate_name}
Requirements & Evidence Match:
{chr(10).join(evidence_summary[:12])}

Candidate Skills: {', '.join(parsed_resume.get('skills', [])[:10])}
"""
        return llm_service.call_llm_json(system_prompt, user_prompt)

    def _generate_deterministic(
        self,
        job_title: str,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        parsed_resume: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        questions = []
        req_map = {r["id"]: r for r in requirements}

        # 1. Evidence Clarification for gaps or unverified requirements
        verification_matches = [m for m in matches if m["status"] in ("requires_verification", "partially_supported", "not_found")]
        for m in verification_matches[:2]:
            r = req_map.get(m["requirement_id"], {})
            r_name = r.get("name", "Technical Skill")
            questions.append({
                "requirement_id": m["requirement_id"],
                "category": "Evidence Clarification",
                "competency": f"{r_name} Proficiency",
                "question": f"Our role relies heavily on {r_name}. Can you walk us through your hands-on experience with this, including a specific challenge you overcame?",
                "why_relevant": f"The candidate's resume showed '{m['status']}' status with limited documentation for this key requirement.",
                "strong_answer_criteria": f"Describes practical implementation patterns, explains trade-offs, and highlights production outcomes using {r_name}.",
                "evaluation_rubric": (
                    "• 1 (Poor): Only theoretical definitions; no concrete project examples.\n"
                    "• 3 (Adequate): Mentions using the technology in a team or hobby project with basic comprehension.\n"
                    "• 5 (Exemplary): Deep architectural grasp, discusses performance pitfalls, concurrency, or scalability solutions."
                )
            })

        # 2. Technical Knowledge for supported core skills
        supported_matches = [m for m in matches if m["status"] == "supported"]
        for m in supported_matches[:2]:
            r = req_map.get(m["requirement_id"], {})
            r_name = r.get("name", "Software Architecture")
            questions.append({
                "requirement_id": m["requirement_id"],
                "category": "Technical Knowledge",
                "competency": f"{r_name} Deep Dive",
                "question": f"In your previous work with {r_name}, what was the most complex technical hurdle you encountered, and how did you diagnose and resolve it?",
                "why_relevant": f"Candidate has verified evidence for {r_name} ('{m.get('evidence_snippet', '')[:100]}...'). Testing senior technical depth.",
                "strong_answer_criteria": "Demonstrates structured root-cause analysis, profiling, metrics monitoring, and robust system recovery.",
                "evaluation_rubric": (
                    "• 1 (Poor): Vague description; unable to explain technical specifics or diagnostics.\n"
                    "• 3 (Adequate): Explains the bug/issue and how it was resolved using standard tools.\n"
                    "• 5 (Exemplary): Systematic root cause analysis, mentions profiling/logging/benchmarks, and long-term preventative measures."
                )
            })

        # 3. Practical Problem-Solving / System Architecture
        questions.append({
            "requirement_id": None,
            "category": "Practical Problem-Solving",
            "competency": "System Reliability & API Design",
            "question": f"Suppose an API endpoint in our {job_title} service experiences an unexpected 10x traffic spike with degraded latency. How would you systematically isolate the bottleneck and stabilize the service?",
            "why_relevant": "Validates candidate's real-world debugging, rate-limiting, caching, and database query optimization capabilities.",
            "strong_answer_criteria": "Checks telemetry, database connection pools, caching layers (Redis), query execution plans, and horizontal scaling.",
            "evaluation_rubric": (
                "• 1 (Poor): Random guessing without metrics or structured observability.\n"
                "• 3 (Adequate): Identifies common bottlenecks (DB, CPU) and suggests basic caching or restarts.\n"
                "• 5 (Exemplary): End-to-end observability approach: APM traces, slow query logs, read replicas, circuit breakers, and rate limiting."
            )
        })

        # 4. Project Experience
        projects = parsed_resume.get("projects", [])
        proj_context = projects[0]["content"] if projects else "your recent technical project"
        questions.append({
            "requirement_id": None,
            "category": "Project Experience",
            "competency": "Technical Ownership & Trade-offs",
            "question": f"Referring to your work on {proj_context[:60]}..., what was a key engineering trade-off you had to make between delivery speed and architectural scalability?",
            "why_relevant": "Grounded in candidate's project portfolio to assess architectural judgment and engineering maturity.",
            "strong_answer_criteria": "Articulates reasons for technology choices, debt accrued, and how technical debt was subsequently managed.",
            "evaluation_rubric": (
                "• 1 (Poor): Blames teammates or management; fails to see trade-offs.\n"
                "• 3 (Adequate): Acknowledges trade-off (e.g. monolithic vs microservices) and rationalizes the choice.\n"
                "• 5 (Exemplary): High business acumen; balances ROI, team velocity, maintainability, and clean migration paths."
            )
        })

        return questions

interview_planner = InterviewPlanner()
