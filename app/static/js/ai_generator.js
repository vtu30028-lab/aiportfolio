/**
 * PortfolioAI - AI Generator Client Controller
 * Manages asynchronous generation requests, loading states, output editing,
 * clipboard copy, and portfolio association.
 */

let currentFeatureType = "summary";
let lastPromptInput = "";

document.addEventListener("DOMContentLoaded", () => {
    const outputTextarea = document.getElementById("ai-output-textarea");
    const charCountLabel = document.getElementById("char-count-label");

    if (outputTextarea && charCountLabel) {
        outputTextarea.addEventListener("input", () => {
            const count = outputTextarea.value.length;
            charCountLabel.innerText = `${count} chars`;
        });
    }
});

/**
 * Helper to fetch the CSRF token from the meta tag.
 */
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
}

/**
 * Displays a styled alert message in the UI.
 */
function showAlert(message, category = "info") {
    const alertBox = document.getElementById("ai-alert-box");
    const alertMsg = document.getElementById("ai-alert-message");
    const alertIcon = document.getElementById("ai-alert-icon");

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

/**
 * Toggles the loading overlay and disable states during AI processing.
 */
function setLoading(isLoading) {
    const overlay = document.getElementById("ai-loading-overlay");
    const badge = document.getElementById("preview-status-badge");
    const textarea = document.getElementById("ai-output-textarea");

    if (overlay) {
        if (isLoading) {
            overlay.classList.remove("d-none");
        } else {
            overlay.classList.add("d-none");
        }
    }

    if (badge) {
        badge.innerText = isLoading ? "Generating..." : "Generated";
        badge.className = isLoading
            ? "badge bg-warning bg-opacity-25 text-warning small"
            : "badge bg-success bg-opacity-25 text-success small";
    }

    if (textarea && isLoading) {
        textarea.disabled = true;
    } else if (textarea) {
        textarea.disabled = false;
    }
}

/**
 * Handles AI generation for the 5 different feature types.
 */
async function handleGenerate(type, event) {
    if (event) event.preventDefault();
    currentFeatureType = type;

    let endpoint = "";
    let payload = {};

    if (type === "summary") {
        endpoint = "/ai/generate-summary";
        payload = {
            level: document.getElementById("summary-level").value,
            name: document.getElementById("summary-name").value,
            skills: document.getElementById("summary-skills").value,
            education: document.getElementById("summary-education").value,
            goals: document.getElementById("summary-goals").value,
            experience: document.getElementById("summary-experience").value,
        };
        lastPromptInput = `Level: ${payload.level} | Skills: ${payload.skills.slice(0, 80)}`;
    } else if (type === "about") {
        endpoint = "/ai/generate-about";
        payload = {
            name: document.getElementById("about-name").value,
            tone: document.getElementById("about-tone").value,
            headline: document.getElementById("about-headline").value,
            background: document.getElementById("about-background").value,
            interests: document.getElementById("about-interests").value,
        };
        lastPromptInput = `Tone: ${payload.tone} | Headline: ${payload.headline}`;
    } else if (type === "project") {
        endpoint = "/ai/generate-project";
        payload = {
            title: document.getElementById("project-title").value,
            format_style: document.getElementById("project-style").value,
            technologies: document.getElementById("project-tech").value,
            purpose: document.getElementById("project-purpose").value,
            key_details: document.getElementById("project-details").value,
        };
        lastPromptInput = `Project: ${payload.title} | Tech: ${payload.technologies}`;
    } else if (type === "skills") {
        endpoint = "/ai/analyze-skills";
        payload = {
            target_role: document.getElementById("skills-target").value,
            current_skills: document.getElementById("skills-current").value,
            career_goal: document.getElementById("skills-goals").value,
        };
        lastPromptInput = `Target: ${payload.target_role} | Skills: ${payload.current_skills.slice(0, 60)}`;
    } else if (type === "career") {
        endpoint = "/ai/recommend-careers";
        payload = {
            background: document.getElementById("career-bg").value,
            skills: document.getElementById("career-skills").value,
            interests: document.getElementById("career-interests").value,
        };
        lastPromptInput = `Background: ${payload.background.slice(0, 60)} | Skills: ${payload.skills.slice(0, 60)}`;
    }

    setLoading(true);

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        setLoading(false);

        if (response.ok && data.success) {
            const textarea = document.getElementById("ai-output-textarea");
            const charCount = document.getElementById("char-count-label");
            if (textarea) {
                textarea.value = data.result;
                if (charCount) charCount.innerText = `${data.result.length} chars`;
            }
            showAlert("Content generated successfully! Review and refine below.", "success");
        } else {
            showAlert(data.error || "Failed to generate content. Please try again.", "danger");
        }
    } catch (err) {
        setLoading(false);
        showAlert("Network or communication error. Please try again.", "danger");
    }
}

/**
 * Copies the preview textarea content to user's clipboard.
 */
function copyOutputContent() {
    const textarea = document.getElementById("ai-output-textarea");
    const copyText = document.getElementById("copy-text");
    const copyIcon = document.getElementById("copy-icon");

    if (!textarea || !textarea.value.trim()) {
        showAlert("Nothing to copy. Please generate some content first.", "warning");
        return;
    }

    navigator.clipboard.writeText(textarea.value).then(() => {
        if (copyText) copyText.innerText = "Copied!";
        if (copyIcon) copyIcon.className = "bi bi-check-lg text-success me-1";

        setTimeout(() => {
            if (copyText) copyText.innerText = "Copy";
            if (copyIcon) copyIcon.className = "bi bi-clipboard me-1";
        }, 2000);
    }).catch(() => {
        showAlert("Failed to copy automatically. Please select and copy manually.", "warning");
    });
}

/**
 * Clears the preview textarea.
 */
function clearOutputContent() {
    const textarea = document.getElementById("ai-output-textarea");
    const charCount = document.getElementById("char-count-label");
    const badge = document.getElementById("preview-status-badge");

    if (textarea) textarea.value = "";
    if (charCount) charCount.innerText = "0 chars";
    if (badge) {
        badge.innerText = "Ready";
        badge.className = "badge bg-secondary bg-opacity-25 text-light small";
    }
}

/**
 * Saves generated content to database and optionally applies it to a selected portfolio.
 */
async function saveGeneratedContent(applyToPortfolio = false) {
    const textarea = document.getElementById("ai-output-textarea");
    const portfolioSelect = document.getElementById("target-portfolio-select");

    if (!textarea || !textarea.value.trim()) {
        showAlert("Cannot save empty content. Generate or write something first.", "warning");
        return;
    }

    const portfolioId = portfolioSelect && portfolioSelect.value ? portfolioSelect.value : null;

    if (applyToPortfolio && !portfolioId) {
        showAlert("Please select a portfolio from the dropdown above to apply this content directly.", "warning");
        return;
    }

    const payload = {
        feature_type: currentFeatureType,
        generated_text: textarea.value.trim(),
        prompt_input: lastPromptInput,
        portfolio_id: portfolioId,
        apply_to_portfolio: applyToPortfolio,
    };

    try {
        const response = await fetch("/ai/save-content", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showAlert(data.message + (data.applied ? " Applied directly to portfolio About section!" : ""), "success");
        } else {
            showAlert(data.error || "Failed to save content.", "danger");
        }
    } catch (err) {
        showAlert("Network error while saving content.", "danger");
    }
}

/**
 * Loads a previously saved generation item into the preview textarea.
 */
function loadSavedItem(item) {
    const textarea = document.getElementById("ai-output-textarea");
    const charCount = document.getElementById("char-count-label");
    const badge = document.getElementById("preview-status-badge");
    const portfolioSelect = document.getElementById("target-portfolio-select");

    if (textarea) textarea.value = item.generated_text;
    if (charCount) charCount.innerText = `${item.generated_text.length} chars`;
    if (badge) {
        badge.innerText = `Loaded (${item.feature_type})`;
        badge.className = "badge bg-info bg-opacity-25 text-info small";
    }
    if (portfolioSelect && item.portfolio_id) {
        portfolioSelect.value = item.portfolio_id;
    }
    currentFeatureType = item.feature_type;

    showAlert(`Loaded saved ${item.feature_type} content into preview!`, "info");
}
