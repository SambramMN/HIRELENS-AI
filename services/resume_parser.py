import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# PyMuPDF
try:
    import pymupdf as fitz
    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False

# Fallback pypdf
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

class ResumeParser:
    """Specialist agent: extracts text, page-grounded evidence, and structured qualifications."""

    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
        """
        Extracts text and page-by-page mapping from a PDF file.
        Returns: (full_text, pages_list, error_message)
        """
        path = Path(file_path)
        if not path.exists():
            return "", [], f"File not found: {file_path}"

        pages = []
        full_text_parts = []

        if HAS_PYMUPDF:
            try:
                doc = fitz.open(file_path)
                if doc.is_encrypted:
                    return "", [], "PDF is password-protected and cannot be parsed."
                if len(doc) == 0:
                    return "", [], "PDF contains no pages."

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text("text") or ""
                    cleaned = text.strip()
                    pages.append({
                        "page_number": page_num + 1,
                        "text": cleaned
                    })
                    if cleaned:
                        full_text_parts.append(cleaned)
                doc.close()
                
                full_text = "\n\n".join(full_text_parts)
                if not full_text.strip():
                    return "", [], "PDF appears to be scanned or contains no extractable text."
                return full_text, pages, None
            except Exception as e:
                pass  # Try fallback below

        if HAS_PYPDF:
            try:
                reader = pypdf.PdfReader(file_path)
                if reader.is_encrypted:
                    return "", [], "PDF is encrypted and cannot be parsed."
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    cleaned = text.strip()
                    pages.append({
                        "page_number": idx + 1,
                        "text": cleaned
                    })
                    if cleaned:
                        full_text_parts.append(cleaned)
                full_text = "\n\n".join(full_text_parts)
                if not full_text.strip():
                    return "", [], "PDF appears to be empty or contains scanned images without text."
                return full_text, pages, None
            except Exception as e:
                return "", [], f"Failed to extract text from PDF: {str(e)}"

        return "", [], "No compatible PDF reader (PyMuPDF or pypdf) available."

    def parse_resume(
        self,
        raw_text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes raw resume text and extracts candidate metadata, sections, and qualifications.
        """
        if not pages:
            pages = [{"page_number": 1, "text": raw_text}]

        # 1. Contact & Identifier extraction
        email = self._extract_email(raw_text)
        phone = self._extract_phone(raw_text)
        name = self._extract_name(raw_text, file_name)
        location = self._extract_location(raw_text)
        candidate_code = f"CAND-{uuid.uuid4().hex[:6].upper()}"

        # 2. Section extraction
        sections = self._segment_sections(raw_text)

        # 3. Qualification breakdown
        skills = self._extract_skills(sections.get("skills", "") + "\n" + raw_text)
        experience = self._extract_experience_blocks(sections.get("experience", ""), pages)
        education = self._extract_education_blocks(sections.get("education", ""), pages)
        projects = self._extract_project_blocks(sections.get("projects", ""), pages)
        certifications = self._extract_certifications(sections.get("certifications", ""))

        # 4. Uncertainty & completeness flags
        missing_fields = []
        if not experience:
            missing_fields.append("Work history not explicitly segmented")
        if not education:
            missing_fields.append("Formal education degrees not clearly stated")
        if not skills:
            missing_fields.append("Skills section not explicitly labeled")

        return {
            "candidate_code": candidate_code,
            "full_name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "skills": skills,
            "experience": experience,
            "education": education,
            "projects": projects,
            "certifications": certifications,
            "missing_fields": missing_fields,
            "pages_count": len(pages),
            "pages": pages
        }

    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r"[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}", text)
        return match.group(0).lower() if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        match = re.search(r"(?:\+?\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}", text)
        return match.group(0) if match else None

    def _extract_name(self, text: str, file_name: Optional[str] = None) -> str:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines[:5]:
            # Skip emails, phone numbers, website links, or titles
            if "@" in line or "http" in line or re.search(r"\d{3,}", line):
                continue
            if len(line) < 40 and re.match(r"^[A-Za-z\s\.\,\-]+$", line):
                words = line.split()
                if 2 <= len(words) <= 4:
                    return line.title()

        if file_name:
            clean = re.sub(r"[\._\-]*(resume|cv|application)[\._\-]*", "", file_name, flags=re.IGNORECASE)
            clean = Path(clean).stem.replace("_", " ").replace("-", " ").strip()
            if clean:
                return clean.title()

        return "Candidate Profile"

    def _extract_location(self, text: str) -> Optional[str]:
        match = re.search(r"(?:Location|Address|City):\s*([A-Za-z\s,]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        common_cities = ["Bangalore", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "San Francisco", "New York", "London", "Seattle", "Austin", "Berlin", "Remote"]
        for city in common_cities:
            if re.search(rf"\b{city}\b", text, re.IGNORECASE):
                return city
        return "Not Stated"

    def _segment_sections(self, text: str) -> Dict[str, str]:
        section_headers = {
            "experience": ["experience", "work history", "employment", "professional experience"],
            "education": ["education", "academic background", "qualifications"],
            "skills": ["skills", "technical skills", "technologies", "core competencies"],
            "projects": ["projects", "personal projects", "key initiatives"],
            "certifications": ["certifications", "licenses", "certificates", "credentials"]
        }

        lines = text.splitlines()
        sections: Dict[str, List[str]] = {k: [] for k in section_headers}
        current_section = "other"

        for line in lines:
            line_str = line.strip()
            l_lower = line_str.lower()
            matched_header = False
            for sec, keywords in section_headers.items():
                if any(re.match(rf"^(?:[\d\.\-\#\*\s]*)?{kw}(?:\s*:)?$", l_lower) for kw in keywords):
                    current_section = sec
                    matched_header = True
                    break
            if not matched_header:
                if current_section in sections:
                    sections[current_section].append(line_str)

        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def _extract_skills(self, text: str) -> List[str]:
        from services.job_analyzer import TECHNICAL_TAXONOMY
        found = set()
        lower = text.lower()
        for cat, keywords in TECHNICAL_TAXONOMY.items():
            for kw in keywords:
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, lower):
                    found.add(kw.title() if len(kw) > 3 else kw.upper())
        return sorted(list(found))

    def _extract_experience_blocks(self, exp_text: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not exp_text:
            return []
        lines = [l.strip() for l in exp_text.splitlines() if l.strip()]
        blocks = []
        current = []
        for line in lines:
            if re.search(r"\b(20\d\d|19\d\d|present|current)\b", line, re.IGNORECASE) and len(line) < 80:
                if current:
                    blocks.append("\n".join(current))
                    current = []
            current.append(line)
        if current:
            blocks.append("\n".join(current))

        results = []
        for idx, b in enumerate(blocks[:6]):
            # Find which page it was likely on
            page_found = 1
            for p in pages:
                if b[:40] in p["text"]:
                    page_found = p["page_number"]
                    break
            results.append({
                "id": idx + 1,
                "content": b,
                "page": page_found
            })
        return results

    def _extract_education_blocks(self, edu_text: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not edu_text:
            return []
        lines = [l.strip() for l in edu_text.splitlines() if l.strip()]
        return [{"id": i + 1, "content": line} for i, line in enumerate(lines[:4])]

    def _extract_project_blocks(self, proj_text: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not proj_text:
            return []
        lines = [l.strip() for l in proj_text.splitlines() if l.strip()]
        return [{"id": i + 1, "content": line} for i, line in enumerate(lines[:5])]

    def _extract_certifications(self, cert_text: str) -> List[str]:
        if not cert_text:
            return []
        lines = [l.strip() for l in cert_text.splitlines() if l.strip()]
        return [l for l in lines if len(l) > 3][:5]

resume_parser = ResumeParser()
