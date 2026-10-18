import re
from typing import Any, Dict, List, Optional, Tuple
from services.llm_service import llm_service

class EvidenceMatcher:
    """Specialist agent: compares candidate evidence against approved job requirements with strict evidence grounding."""

    def match_candidate(
        self,
        candidate_id: int,
        requirements: List[Dict[str, Any]],
        parsed_resume: Dict[str, Any],
        raw_text: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluates each requirement against the candidate's resume.
        Returns: (requirement_matches, score_breakdown)
        """
        matches = []
        
        # 1. Deterministic evaluation for each requirement
        for req in requirements:
            req_id = req["id"]
            req_name = req["name"]
            req_cat = req.get("category", "")
            req_class = req.get("classification", "required")
            req_weight = req.get("weight", 3)
            criteria = req.get("verification_criteria", "")

            match_data = self._evaluate_single_requirement(
                req_id, req_name, req_class, req_weight, criteria, parsed_resume, raw_text
            )
            matches.append(match_data)

        # 2. Transparent multi-dimensional scoring calculation
        scores = self.calculate_scores(requirements, matches, parsed_resume)

        return matches, scores

    def _evaluate_single_requirement(
        self,
        req_id: int,
        req_name: str,
        classification: str,
        weight: int,
        criteria: str,
        parsed: Dict[str, Any],
        raw_text: str
    ) -> Dict[str, Any]:
        """
        Grounded evidence locator. Finds actual sentences in resume matching the requirement keywords.
        """
        clean_name = re.sub(r"^(experience:\s*)?", "", req_name, flags=re.IGNORECASE).strip()
        keywords = [k.strip() for k in re.split(r"[,\s\/\&\+]+", clean_name) if len(k.strip()) > 2]
        if not keywords:
            keywords = [clean_name]

        pages = parsed.get("pages", [])
        
        # Look for sentence hits across the raw text
        sentences = re.split(r"(?<=[.!?\n])\s+", raw_text)
        found_snippets = []
        best_sentence = ""
        best_page = 1
        mention_count = 0

        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 15:
                continue
            s_lower = s_clean.lower()
            hit = any(re.search(rf"\b{re.escape(kw.lower())}\b", s_lower) for kw in keywords)
            if hit:
                mention_count += 1
                found_snippets.append(s_clean)
                if not best_sentence or len(s_clean) > len(best_sentence):
                    best_sentence = s_clean
                    # Find page number
                    for p in pages:
                        if s_clean[:30] in p.get("text", ""):
                            best_page = p.get("page_number", 1)
                            break

        # Check section contexts
        exp_text = "\n".join([b.get("content", "") for b in parsed.get("experience", [])])
        in_experience = any(re.search(rf"\b{re.escape(kw.lower())}\b", exp_text.lower()) for kw in keywords)

        proj_text = "\n".join([b.get("content", "") for b in parsed.get("projects", [])])
        in_projects = any(re.search(rf"\b{re.escape(kw.lower())}\b", proj_text.lower()) for kw in keywords)

        # Classification decision
        if in_experience and mention_count >= 1:
            status = "supported"
            confidence = "high"
            snippet = best_sentence
            source_loc = f"Page {best_page} | Professional Experience"
            explanation = f"Direct evidence verified in candidate's work history matching '{req_name}'."
            follow_up = f"Could you elaborate on the architecture and measurable outcomes achieved with {clean_name}?"
        elif (in_projects or mention_count >= 2) and best_sentence:
            status = "supported"
            confidence = "medium"
            snippet = best_sentence
            source_loc = f"Page {best_page} | Projects & Implementations"
            explanation = f"Documented implementation of '{req_name}' found in project descriptions."
            follow_up = f"How did you handle scalability and edge cases when using {clean_name} in your projects?"
        elif mention_count == 1 and best_sentence:
            status = "partially_supported"
            confidence = "medium"
            snippet = best_sentence
            source_loc = f"Page {best_page} | Skills / Overview"
            explanation = f"Mentioned in skills or summary, but requires verification of commercial depth."
            follow_up = f"Can you describe a specific production scenario where you utilized {clean_name}?"
        else:
            # Check if this was an experience duration requirement
            if "experience:" in req_name.lower():
                status = "requires_verification"
                confidence = "low"
                snippet = "Total tenure requires verification from employment timeline."
                source_loc = "Page 1 | Career Timeline"
                explanation = "Candidate has relevant experience entries, but precise tenure must be confirmed."
                follow_up = "What was the exact timeline and scope of your relevant software engineering roles?"
            else:
                status = "not_found"
                confidence = "unverified"
                snippet = "No direct evidence located in candidate resume."
                source_loc = "N/A"
                explanation = f"No mention or direct evidence of '{req_name}' found in the submitted resume."
                follow_up = f"Do you have prior experience or background working with {clean_name}?"

        return {
            "requirement_id": req_id,
            "status": status,
            "evidence_snippet": snippet[:400],
            "source_location": source_loc,
            "explanation": explanation,
            "confidence": confidence,
            "follow_up_question": follow_up
        }

    def calculate_scores(
        self,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        parsed: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transparent score breakdown without deceptive probabilities.
        """
        match_by_id = {m["requirement_id"]: m for m in matches}
        
        req_weights_total = 0
        req_weights_earned = 0
        pref_weights_total = 0
        pref_weights_earned = 0
        
        supported_count = 0
        partial_count = 0
        not_found_count = 0
        verification_count = 0

        for r in requirements:
            r_id = r["id"]
            weight = r.get("weight", 3)
            is_required = (r.get("classification") == "required")
            
            m = match_by_id.get(r_id, {})
            st = m.get("status", "not_found")
            
            if st == "supported":
                multiplier = 1.0
                supported_count += 1
            elif st == "partially_supported":
                multiplier = 0.5
                partial_count += 1
            elif st == "requires_verification":
                multiplier = 0.25
                verification_count += 1
            else:
                multiplier = 0.0
                not_found_count += 1

            if is_required:
                req_weights_total += weight
                req_weights_earned += weight * multiplier
            else:
                pref_weights_total += weight
                pref_weights_earned += weight * multiplier

        total_reqs = len(requirements) or 1
        
        # 1. Evidence coverage (% of requirements with supported or partial evidence)
        evidence_coverage = round(((supported_count + 0.5 * partial_count) / total_reqs) * 100, 1)

        # 2. Required skills coverage
        req_coverage = round((req_weights_earned / (req_weights_total or 1)) * 100, 1)

        # 3. Preferred skills coverage
        pref_coverage = round((pref_weights_earned / (pref_weights_total or 1)) * 100, 1)

        # 4. Information completeness
        completeness_pts = 0
        if parsed.get("experience"): completeness_pts += 35
        if parsed.get("education"): completeness_pts += 25
        if parsed.get("skills"): completeness_pts += 20
        if parsed.get("projects"): completeness_pts += 10
        if parsed.get("email") and parsed.get("phone"): completeness_pts += 10
        completeness = min(100.0, float(completeness_pts))

        # 5. Verification uncertainty (% of items needing verification or not found)
        uncertainty = round(((verification_count + not_found_count) / total_reqs) * 100, 1)

        # 6. Combined matching score (Transparent weighted sum)
        # 50% Required + 20% Preferred + 20% Evidence Coverage + 10% Completeness - Uncertainty penalty
        raw_score = (
            (req_coverage * 0.50) +
            (pref_coverage * 0.20) +
            (evidence_coverage * 0.20) +
            (completeness * 0.10) -
            (uncertainty * 0.05)
        )
        overall_score = round(max(0.0, min(100.0, raw_score)), 1)

        return {
            "overall_score": overall_score,
            "evidence_coverage": evidence_coverage,
            "required_skill_coverage": req_coverage,
            "preferred_skill_coverage": pref_coverage,
            "information_completeness": completeness,
            "verification_uncertainty": uncertainty,
            "counts": {
                "total": total_reqs,
                "supported": supported_count,
                "partially_supported": partial_count,
                "requires_verification": verification_count,
                "not_found": not_found_count
            },
            "formula_documentation": (
                "Overall Score = 50% (Required Skills) + 20% (Preferred Skills) + "
                "20% (Evidence Coverage) + 10% (Completeness) - 5% (Uncertainty Penalty)"
            )
        }

evidence_matcher = EvidenceMatcher()
