/**
 * PortfolioAI - Resume Parser Client Controller
 * Manages drag & drop PDF uploads, AJAX parsing, structured preview rendering,
 * and portfolio import with overwrite protection.
 */

let selectedResumeFile = null;
let parsedResumeData = null;

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("resume-file-input");

    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());

        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileSelection(e.target.files[0]);
            }
        });

        // Drag & drop listeners
        ["dragenter", "dragover"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.style.background = "rgba(99, 102, 241, 0.12)";
                dropZone.style.borderColor = "var(--primary)";
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.style.background = "rgba(255, 255, 255, 0.02)";
                dropZone.style.borderColor = "var(--border-accent)";
            });
        });

        dropZone.addEventListener("drop", (e) => {
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }
});

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
}

function showResumeAlert(message, category = "info") {
    const alertBox = document.getElementById("resume-alert-box");
    const alertMsg = document.getElementById("resume-alert-message");
    const alertIcon = document.getElementById("resume-alert-icon");

    if (!alertBox || !alertMsg) return;

    alertBox.className = `alert alert-${category === "error" ? "danger" : category} alert-custom alert-dismissible fade show mb-4`;
    alertMsg.innerText = message;

    if (alertIcon) {
        alertIcon.className = category === "error" || category === "danger"
            ? "bi bi-exclamation-triangle-fill me-2 fs-5"
            : "bi bi-check-circle-fill me-2 fs-5";
    }

    alertBox.classList.remove("d-none");
    window.scrollTo({ top: alertBox.offsetTop - 80, behavior: "smooth" });
}

function handleFileSelection(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showResumeAlert("Invalid file format. Please upload a PDF document (.pdf).", "danger");
        return;
    }

    const maxBytes = 5 * 1024 * 1024; // 5 MB
    if (file.size > maxBytes) {
        showResumeAlert(`File size exceeds 5MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB). Please upload a smaller file.`, "danger");
        return;
    }

    selectedResumeFile = file;

    const fileChosenText = document.getElementById("file-chosen-text");
    const fileBadge = document.getElementById("selected-file-badge");
    const filenameLabel = document.getElementById("selected-filename");
    const filesizeLabel = document.getElementById("selected-filesize");
    const parseBtn = document.getElementById("btn-parse-resume");

    if (fileChosenText) fileChosenText.innerText = `Selected: ${file.name}`;
    if (filenameLabel) filenameLabel.innerText = file.name;
    if (filesizeLabel) filesizeLabel.innerText = `${(file.size / 1024).toFixed(0)} KB`;
    if (fileBadge) fileBadge.classList.remove("d-none");
    if (parseBtn) parseBtn.disabled = false;
}

async function handleParseResume() {
    if (!selectedResumeFile) {
        showResumeAlert("Please select a PDF resume file first.", "warning");
        return;
    }

    const parseBtn = document.getElementById("btn-parse-resume");
    const progressBox = document.getElementById("parsing-progress-box");
    const statusHeading = document.getElementById("parsing-status-heading");

    if (parseBtn) parseBtn.disabled = true;
    if (progressBox) progressBox.classList.remove("d-none");

    const formData = new FormData();
    formData.append("resume", selectedResumeFile);

    try {
        if (statusHeading) statusHeading.innerText = "Extracting text layer with pypdf...";

        setTimeout(() => {
            if (statusHeading) statusHeading.innerText = "Structuring skills & experience with Gemini AI...";
        }, 1500);

        const response = await fetch("/resume/parse", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
            },
            body: formData,
        });

        const data = await response.json();
        if (progressBox) progressBox.classList.add("d-none");
        if (parseBtn) parseBtn.disabled = false;

        if (response.ok && data.success) {
            parsedResumeData = data.data;
            populateReviewForm(data.data, data.page_count);
            document.getElementById("upload-card").classList.add("d-none");
            document.getElementById("review-card").classList.remove("d-none");
            showResumeAlert(`Resume parsed successfully (${data.page_count} pages analyzed). Please review the extracted fields below.`, "success");
            window.scrollTo({ top: document.getElementById("review-card").offsetTop - 80, behavior: "smooth" });
        } else {
            showResumeAlert(data.error || "Failed to parse resume.", "danger");
        }
    } catch (err) {
        if (progressBox) progressBox.classList.add("d-none");
        if (parseBtn) parseBtn.disabled = false;
        showResumeAlert("Communication error during parsing. Please try again.", "danger");
    }
}

function populateReviewForm(data, pageCount) {
    document.getElementById("review-full-name").value = data.full_name || "";
    document.getElementById("review-email").value = data.email || "";
    document.getElementById("review-phone").value = data.phone || "";
    document.getElementById("review-location").value = data.location || "";
    document.getElementById("review-headline").value = data.headline || "Software Engineer & Technology Specialist";
    document.getElementById("review-about").value = data.summary || "";
    document.getElementById("review-github").value = data.github_url || "";
    document.getElementById("review-linkedin").value = data.linkedin_url || "";

    // Skills
    const techSkills = data.technical_skills || [];
    const softSkills = data.soft_skills || [];
    const allSkills = [...techSkills, ...softSkills];

    const badgesContainer = document.getElementById("skills-badges-container");
    if (badgesContainer) {
        badgesContainer.innerHTML = "";
        allSkills.slice(0, 15).forEach((skill) => {
            const badge = document.createElement("span");
            badge.className = "badge-tag text-light";
            badge.innerHTML = `<i class="bi bi-check2 text-success me-1"></i>${skill}`;
            badgesContainer.appendChild(badge);
        });
    }

    const rawSkillsText = document.getElementById("review-skills-raw");
    if (rawSkillsText) rawSkillsText.value = allSkills.join(", ");

    // Pre-fill new portfolio title suggestion
    const newTitleInput = document.getElementById("new-portfolio-title");
    if (newTitleInput && data.full_name) {
        newTitleInput.value = `${data.full_name}'s Professional Portfolio`;
    }

    // Education preview list
    const eduList = document.getElementById("education-list-preview");
    if (eduList) {
        eduList.innerHTML = "";
        const edu = data.education || [];
        if (edu.length) {
            edu.forEach((e) => {
                const li = document.createElement("li");
                li.className = "mb-1 text-light";
                li.innerHTML = `<strong>${e.degree || "Degree"}</strong> - ${e.institution || ""} <span class="text-muted">(${e.year || ""})</span>`;
                eduList.appendChild(li);
            });
        } else {
            eduList.innerHTML = '<li class="small text-muted">No education found.</li>';
        }
    }

    // Projects preview list
    const projList = document.getElementById("projects-list-preview");
    if (projList) {
        projList.innerHTML = "";
        const projs = data.projects || [];
        if (projs.length) {
            projs.forEach((p) => {
                const li = document.createElement("li");
                li.className = "mb-1 text-light";
                li.innerHTML = `<strong>${p.title || "Project"}</strong> <span class="text-muted small">(${p.technologies || ""})</span>`;
                projList.appendChild(li);
            });
        } else {
            projList.innerHTML = '<li class="small text-muted">No projects found.</li>';
        }
    }

    // Experience preview list
    const expList = document.getElementById("experience-list-preview");
    if (expList) {
        expList.innerHTML = "";
        const exps = data.experience || [];
        if (exps.length) {
            exps.forEach((x) => {
                const li = document.createElement("li");
                li.className = "mb-1 text-light";
                li.innerHTML = `<strong>${x.role || "Role"}</strong> at ${x.company || ""} <span class="text-muted small">(${x.duration || ""})</span>`;
                expList.appendChild(li);
            });
        } else {
            expList.innerHTML = '<li class="small text-muted">No experience found.</li>';
        }
    }
}

function toggleDestinationChoice() {
    const isNew = document.getElementById("dest-create-new").checked;
    const newGroup = document.getElementById("new-portfolio-title-group");
    const existingGroup = document.getElementById("existing-portfolio-group");

    if (isNew) {
        if (newGroup) newGroup.classList.remove("d-none");
        if (existingGroup) existingGroup.classList.add("d-none");
    } else {
        if (newGroup) newGroup.classList.add("d-none");
        if (existingGroup) existingGroup.classList.remove("d-none");
    }
}

async function handleImportPortfolio(e) {
    if (e) e.preventDefault();

    const isNew = document.getElementById("dest-create-new").checked;
    const portfolioSelect = document.getElementById("existing-portfolio-select");
    const overwriteCheck = document.getElementById("confirm-overwrite-check");
    const submitBtn = document.getElementById("btn-submit-import");

    const portfolioId = isNew ? null : (portfolioSelect ? portfolioSelect.value : null);
    const overwrite = isNew ? false : (overwriteCheck ? overwriteCheck.checked : false);

    const approvedData = {
        full_name: document.getElementById("review-full-name").value,
        email: document.getElementById("review-email").value,
        phone: document.getElementById("review-phone").value,
        location: document.getElementById("review-location").value,
        headline: document.getElementById("review-headline").value,
        about: document.getElementById("review-about").value,
        github_url: document.getElementById("review-github").value,
        linkedin_url: document.getElementById("review-linkedin").value,
    };

    const payload = {
        create_new: isNew,
        new_portfolio_title: document.getElementById("new-portfolio-title").value,
        portfolio_id: portfolioId,
        overwrite: overwrite,
        approved_data: approvedData,
    };

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Importing...`;
    }

    try {
        const response = await fetch("/resume/import-portfolio", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> Save to Portfolio`;
        }

        if (response.status === 409 && data.require_confirmation) {
            showResumeAlert(data.error, "warning");
            if (overwriteCheck) {
                overwriteCheck.checked = true;
                overwriteCheck.focus();
            }
            return;
        }

        if (response.ok && data.success) {
            showResumeAlert(data.message, "success");
            setTimeout(() => {
                window.location.href = `/portfolios/${data.portfolio_id}`;
            }, 1200);
        } else {
            showResumeAlert(data.error || "Failed to import resume data.", "danger");
        }
    } catch (err) {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> Save to Portfolio`;
        }
        showResumeAlert("Network error while saving to portfolio.", "danger");
    }
}

function resetParser() {
    selectedResumeFile = null;
    parsedResumeData = null;

    const fileInput = document.getElementById("resume-file-input");
    if (fileInput) fileInput.value = "";

    const fileChosenText = document.getElementById("file-chosen-text");
    if (fileChosenText) fileChosenText.innerHTML = `Drag and drop your PDF here, or <span class="text-primary text-decoration-underline">browse file</span>`;

    const fileBadge = document.getElementById("selected-file-badge");
    if (fileBadge) fileBadge.classList.add("d-none");

    const parseBtn = document.getElementById("btn-parse-resume");
    if (parseBtn) parseBtn.disabled = true;

    document.getElementById("review-card").classList.add("d-none");
    document.getElementById("upload-card").classList.remove("d-none");
}
