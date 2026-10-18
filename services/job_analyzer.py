import re
from typing import Any, Dict, List, Optional
from services.llm_service import llm_service

TECHNICAL_TAXONOMY = {
    "Programming Languages": ["python", "javascript", "typescript", "go", "golang", "java", "c++", "c#", "rust", "ruby", "php", "scala", "kotlin", "swift"],
    "Frameworks & Libraries": ["flask", "fastapi", "django", "react", "next.js", "vue", "angular", "node.js", "express", "spring boot", "pandas", "numpy", "pytorch", "tensorflow"],
    "Databases & Storage": ["postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch", "dynamodb", "cassandra", "sql"],
    "Cloud & DevOps": ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "github actions", "terraform", "linux", "nginx"],
    "Architecture & API": ["rest", "restful apis", "graphql", "microservices", "system design", "distributed systems", "event-driven", "message queues", "kafka", "rabbitmq"],
    "Testing & Quality": ["pytest", "unit testing", "tdd", "integration testing", "cypress", "jest"],
    "Domain & Qualifications": ["computer science", "bachelor", "master", "b.tech", "b.e.", "agile", "scrum", "git"]
}

def detect_category(skill_name: str) -> str:
    """Classifies a skill into a standard engineering category."""
    lower = skill_name.lower().strip()
    for cat, keywords in TECHNICAL_TAXONOMY.items():
        for kw in keywords:
            if kw == lower or f" {kw} " in f" {lower} " or lower.startswith(f"{kw} ") or lower.endswith(f" {kw}"):
                return cat
    return "Technical Competency"

class JobAnalyzer:
    """Specialist agent: structures and validates job descriptions into verifiable requirements."""
    
    def analyze_job(
        self,
        title: str,
        department: str,
        experience_level: str,
        required_skills: str,
        preferred_skills: str,
        responsibilities: str,
        description_raw: str
    ) -> Dict[str, Any]:
        """
        Structures the job description into a clear list of requirements.
        Attempts LLM analysis first; gracefully falls back to deterministic rule-based analysis.
        """
        llm_result = None
        if llm_service.is_configured:
            llm_result = self._analyze_with_llm(
                title, department, experience_level,
                required_skills, preferred_skills, responsibilities, description_raw
            )
            
        if llm_result and "requirements" in llm_result and len(llm_result["requirements"]) > 0:
            return {
                "source": "LLM (OpenAI-compatible)",
                "requirements": llm_result["requirements"],
                "notes": "Requirements extracted and weighted by AI specialist."
            }
            
        # Fallback deterministic analysis
        rule_reqs = self._analyze_rule_based(
            title, experience_level, required_skills, preferred_skills, responsibilities, description_raw
        )
        return {
            "source": "Deterministic Rule-Based Engine",
            "requirements": rule_reqs,
            "notes": "Requirements structured with high-precision keyword taxonomy."
        }

    def _analyze_with_llm(
        self,
        title: str,
        department: str,
        experience: str,
        required: str,
        preferred: str,
        responsibilities: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        system_prompt = (
            "You are an expert Talent Acquisition Technical Analyst. "
            "Analyze the given Job Description and extract structured, verifiable hiring requirements. "
            "Output valid JSON with key 'requirements' as a list of objects. "
            "Each requirement object must have:\n"
            "- name: concise name of skill or qualification (e.g., 'Python Backend Development')\n"
            "- category: one of 'Programming Languages', 'Frameworks & Libraries', 'Databases & Storage', 'Cloud & DevOps', 'Architecture & API', 'Testing & Quality', 'Domain & Qualifications'\n"
            "- classification: 'required' or 'preferred'\n"
            "- weight: integer from 1 to 5 (5 being critical for required, 2-3 for preferred)\n"
            "- verification_criteria: concrete objective criteria to verify on candidate resume\n"
            "Do NOT hallucinate requirements that are not stated in the job description."
        )

        user_prompt = f"""
Job Title: {title}
Department: {department}
Experience Level: {experience}
Required Skills: {required}
Preferred Skills: {preferred}
Key Responsibilities: {responsibilities}
Full Job Description: {description}
"""
        return llm_service.call_llm_json(system_prompt, user_prompt)

    def _analyze_rule_based(
        self,
        title: str,
        experience: str,
        required: str,
        preferred: str,
        responsibilities: str,
        description: str
    ) -> List[Dict[str, Any]]:
        requirements = []
        seen = set()

        def add_req(name: str, classification: str, weight: int, custom_criteria: Optional[str] = None):
            clean_name = name.strip()
            if not clean_name or len(clean_name) < 2:
                return
            key = clean_name.lower()
            if key in seen:
                return
            seen.add(key)
            
            category = detect_category(clean_name)
            criteria = custom_criteria or f"Candidate resume must demonstrate practical project or professional experience with {clean_name}."
            
            requirements.append({
                "name": clean_name,
                "category": category,
                "classification": classification,
                "weight": weight,
                "verification_criteria": criteria
            })

        # 1. Parse Required Skills
        if required:
            items = re.split(r"[,\n;•\*\-]+", required)
            for item in items:
                item = item.strip()
                if item:
                    add_req(item, "required", 5, f"Explicit evidence of production-level work using {item} with concrete impact.")

        # 2. Parse Preferred Skills
        if preferred:
            items = re.split(r"[,\n;•\*\-]+", preferred)
            for item in items:
                item = item.strip()
                if item:
                    add_req(item, "preferred", 3, f"Demonstrated familiarity, side projects, or commercial usage of {item}.")

        # 3. If required or preferred were empty, extract from raw description
        if not requirements and description:
            lines = description.splitlines()
            current_mode = "required"
            for line in lines:
                l_lower = line.lower()
                if "preferred" in l_lower or "nice to have" in l_lower or "bonus" in l_lower:
                    current_mode = "preferred"
                elif "required" in l_lower or "qualifications" in l_lower or "must have" in l_lower:
                    current_mode = "required"
                elif line.strip().startswith(("-", "•", "*", "1.", "2.", "3.", "4.", "5.")):
                    clean = re.sub(r"^[\s\-•\*0-9\.]+", "", line).strip()
                    if clean and len(clean) > 3:
                        w = 4 if current_mode == "required" else 2
                        add_req(clean, current_mode, w)

        # 4. Add experience requirement if provided
        if experience and experience.strip():
            add_req(
                f"Experience: {experience.strip()}",
                "required",
                5,
                f"Resume work history must verify at least {experience.strip()} of relevant engineering roles."
            )

        return requirements

job_analyzer = JobAnalyzer()
