// HireLens AI — Client Side Orchestration
document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Lucide Icons if available
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // 2. Global Toast Notification Helper
    window.showToast = function (message, type = "success") {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `glass-card glass-card-sm d-flex align-items-center gap-3`;
        toast.style.minWidth = "280px";
        toast.style.borderLeft = type === "success" ? "4px solid #10B981" : "4px solid #EF4444";
        toast.style.animation = "fadeIn 0.3s ease";

        const iconColor = type === "success" ? "#10B981" : "#EF4444";
        toast.innerHTML = `
            <div style="color: ${iconColor};">
                <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}"></i>
            </div>
            <div class="flex-grow-1" style="font-size: 0.88rem; color: #FFFFFF;">
                ${message}
            </div>
        `;

        container.appendChild(toast);
        if (window.lucide) window.lucide.createIcons();

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.4s ease";
            setTimeout(() => toast.remove(), 400);
        }, 3500);
    };

    // 3. Blind Screening Toggle Handler
    const blindToggle = document.getElementById("blindScreeningToggle");
    if (blindToggle) {
        blindToggle.addEventListener("change", async (e) => {
            const enabled = e.target.checked;
            try {
                const res = await fetch("/api/settings/blind-screening", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ enabled })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(enabled ? "Blind Screening Activated: Personal Identifiers Masked" : "Blind Screening Deactivated: Full Profile Visible");
                    setTimeout(() => window.location.reload(), 400);
                }
            } catch (err) {
                showToast("Failed to toggle blind screening", "error");
            }
        });
    }

    // 4. Job Creation Form
    const jobForm = document.getElementById("createJobForm");
    if (jobForm) {
        jobForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = jobForm.querySelector("button[type='submit']");
            const originalText = btn.innerHTML;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Structuring Requirements...`;
            btn.disabled = true;

            const payload = {
                title: document.getElementById("jobTitleInput").value,
                department: document.getElementById("jobDeptInput").value,
                experience_level: document.getElementById("jobExpInput").value,
                required_skills: document.getElementById("jobRequiredSkillsInput").value,
                preferred_skills: document.getElementById("jobPreferredSkillsInput").value,
                responsibilities: document.getElementById("jobResponsibilitiesInput").value,
                description: document.getElementById("jobDescInput").value
            };

            try {
                const res = await fetch("/api/jobs", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Job created with ${data.requirements_count} structured requirements!`);
                    setTimeout(() => window.location.href = "/jobs", 600);
                } else {
                    showToast(data.error || "Failed to create job", "error");
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                showToast("Error connecting to server", "error");
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }

    // 5. Resume Upload Form
    const uploadForm = document.getElementById("uploadResumeForm");
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = uploadForm.querySelector("button[type='submit']");
            const originalText = btn.innerHTML;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Specialist Pipeline Running...`;
            btn.disabled = true;

            const formData = new FormData(uploadForm);
            try {
                const res = await fetch("/api/candidates/upload", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Successfully analyzed ${data.processed_count} candidate(s) with evidence grounding!`);
                    setTimeout(() => window.location.href = "/candidates", 700);
                } else {
                    showToast(data.error || "Failed to parse resumes", "error");
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                showToast("Upload failed or timeout occurred", "error");
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }

    // 6. Recruiter Decision Modal & Submission
    const decisionForm = document.getElementById("recruiterDecisionForm");
    if (decisionForm) {
        decisionForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const candId = document.getElementById("decisionCandidateId").value;
            const status = document.getElementById("decisionStatusSelect").value;
            const reason = document.getElementById("decisionReasonInput").value;

            try {
                const res = await fetch(`/api/candidates/${candId}/decision`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status, reason })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Recruiter decision and rationale recorded to audit trail!");
                    setTimeout(() => window.location.reload(), 500);
                } else {
                    showToast(data.error || "Failed to record decision", "error");
                }
            } catch (err) {
                showToast("Connection error recording decision", "error");
            }
        });
    }

    // 7. Interactive Counterfactual Test Runner
    const runCounterfactualBtn = document.getElementById("btnRunCounterfactual");
    if (runCounterfactualBtn) {
        runCounterfactualBtn.addEventListener("click", async () => {
            const container = document.getElementById("counterfactualResultsContainer");
            const originalHtml = runCounterfactualBtn.innerHTML;
            runCounterfactualBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Evaluating Diagnostic Profiles...`;
            runCounterfactualBtn.disabled = true;

            try {
                const res = await fetch("/api/audit/counterfactual", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({})
                });
                const data = await res.json();
                runCounterfactualBtn.innerHTML = originalHtml;
                runCounterfactualBtn.disabled = false;

                if (data.success) {
                    container.style.display = "block";
                    document.getElementById("cfProfileAName").innerText = data.profile_a.name;
                    document.getElementById("cfProfileAScore").innerText = `${data.profile_a.score}%`;
                    document.getElementById("cfProfileBName").innerText = data.profile_b.name;
                    document.getElementById("cfProfileBScore").innerText = `${data.profile_b.score}%`;
                    document.getElementById("cfScoreDelta").innerText = `${data.score_difference.toFixed(1)}%`;
                    
                    const verdictElem = document.getElementById("cfVerdictText");
                    verdictElem.innerText = data.verdict;
                    verdictElem.className = data.test_passed ? "text-success fw-bold" : "text-danger fw-bold";

                    showToast("Counterfactual diagnostic executed successfully!");
                } else {
                    showToast(data.error || "Counterfactual diagnostic failed", "error");
                }
            } catch (err) {
                showToast("Error running counterfactual test", "error");
                runCounterfactualBtn.innerHTML = originalHtml;
                runCounterfactualBtn.disabled = false;
            }
        });
    }

    // 8. Clipboard Copy Helper
    window.copyToClipboard = function (text, message = "Copied to clipboard!") {
        navigator.clipboard.writeText(text).then(() => {
            showToast(message);
        }).catch(() => {
            showToast("Failed to copy", "error");
        });
    };

    // 9. Reset Demo System
    const resetBtn = document.getElementById("btnResetSystem");
    if (resetBtn) {
        resetBtn.addEventListener("click", async () => {
            if (!confirm("Reset database to clean benchmark demonstration data?")) return;
            try {
                const res = await fetch("/api/system/reset", { method: "POST" });
                const data = await res.json();
                if (data.success) {
                    showToast("System reset to benchmark demonstration data!");
                    setTimeout(() => window.location.href = "/dashboard", 600);
                }
            } catch (err) {
                showToast("Reset failed", "error");
            }
        });
    }
});

// Modal helpers
window.openDecisionModal = function (candidateId, currentStatus, candidateName) {
    document.getElementById("decisionCandidateId").value = candidateId;
    document.getElementById("decisionStatusSelect").value = currentStatus || "needs_review";
    document.getElementById("decisionCandidateNameModal").innerText = candidateName;
    const modal = new bootstrap.Modal(document.getElementById("recruiterDecisionModal"));
    modal.show();
};

window.openRequirementEditModal = function (reqId, name, weight, classification, criteria) {
    document.getElementById("editReqId").value = reqId;
    document.getElementById("editReqName").innerText = name;
    document.getElementById("editReqWeight").value = weight;
    document.getElementById("editReqClass").value = classification;
    document.getElementById("editReqCriteria").value = criteria;
    const modal = new bootstrap.Modal(document.getElementById("editRequirementModal"));
    modal.show();
};

window.saveRequirementEdit = async function () {
    const reqId = document.getElementById("editReqId").value;
    const weight = parseInt(document.getElementById("editReqWeight").value);
    const classification = document.getElementById("editReqClass").value;
    const criteria = document.getElementById("editReqCriteria").value;

    try {
        const res = await fetch(`/api/requirements/${reqId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ weight, classification, verification_criteria: criteria })
        });
        const data = await res.json();
        if (data.success) {
            window.showToast("Requirement updated and logged to audit trail!");
            setTimeout(() => window.location.reload(), 400);
        }
    } catch (e) {
        window.showToast("Failed to update requirement", "error");
    }
};

window.deleteCandidate = async function (candId, candCode) {
    if (!confirm(`Are you sure you want to permanently delete candidate ${candCode} and associated resume files?`)) return;
    try {
        const res = await fetch(`/api/candidates/${candId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
            window.showToast(`Candidate ${candCode} deleted successfully.`);
            setTimeout(() => window.location.href = "/candidates", 500);
        }
    } catch (e) {
        window.showToast("Failed to delete candidate", "error");
    }
};
