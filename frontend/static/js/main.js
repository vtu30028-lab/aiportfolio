/**
 * PortfolioAI - Main Client Script
 * Handles UI interactions, navbar state, interactive theme previews, notifications,
 * and password visibility toggles.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Navbar Glassmorphic background elevation on scroll
    const navbar = document.querySelector(".custom-navbar");
    if (navbar) {
        window.addEventListener("scroll", () => {
            if (window.scrollY > 30) {
                navbar.classList.add("shadow-lg");
                navbar.style.background = "rgba(10, 14, 23, 0.95)";
            } else {
                navbar.classList.remove("shadow-lg");
                navbar.style.background = "rgba(10, 14, 23, 0.85)";
            }
        });
    }

    // 2. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 3. Interactive Theme Preview Switcher on Landing Page
    const themeButtons = document.querySelectorAll("[data-preview-theme]");
    const previewContainer = document.getElementById("hero-theme-display");

    if (themeButtons.length && previewContainer) {
        themeButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                themeButtons.forEach((b) => b.classList.remove("active", "btn-primary-gradient"));
                themeButtons.forEach((b) => b.classList.add("btn-secondary-glass"));
                
                btn.classList.remove("btn-secondary-glass");
                btn.classList.add("btn-primary-gradient", "active");

                const theme = btn.getAttribute("data-preview-theme");
                updateHeroPreview(theme);
            });
        });
    }

    // 4. Form submission loading indicator to prevent double submit
    const authForms = document.querySelectorAll("#register-form, #login-form");
    authForms.forEach((form) => {
        form.addEventListener("submit", (e) => {
            if (form.checkValidity()) {
                const btn = form.querySelector('button[type="submit"]');
                if (btn) {
                    btn.classList.add("disabled");
                    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...`;
                }
            }
        });
    });
});

/**
 * Toggles input type between 'password' and 'text' with icon toggle.
 */
function togglePasswordVisibility(fieldId, iconId) {
    const input = document.getElementById(fieldId);
    const icon = document.getElementById(iconId);
    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        if (icon) {
            icon.classList.remove("bi-eye");
            icon.classList.add("bi-eye-slash");
        }
    } else {
        input.type = "password";
        if (icon) {
            icon.classList.remove("bi-eye-slash");
            icon.classList.add("bi-eye");
        }
    }
}

/**
 * Updates the hero preview mockup content based on selected theme.
 */
function updateHeroPreview(theme) {
    const previewName = document.getElementById("preview-user-name");
    const previewTitle = document.getElementById("preview-user-title");
    const previewBio = document.getElementById("preview-user-bio");
    const previewAvatar = document.getElementById("preview-avatar-box");
    const previewThemeLabel = document.getElementById("preview-theme-label");

    if (!previewName) return;

    if (theme === "modern") {
        previewName.innerText = "Alex Rivera";
        previewTitle.innerText = "Senior Full-Stack & Generative AI Engineer";
        previewBio.innerText = "Architecting cloud-native distributed microservices and LLM-powered applications. Passionate about scalable AI workflows.";
        previewThemeLabel.innerText = "theme: modern-tech (dark)";
        if (previewAvatar) previewAvatar.style.background = "linear-gradient(135deg, #6366f1, #a855f7)";
    } else if (theme === "minimal") {
        previewName.innerText = "Dr. Elena Rostova";
        previewTitle.innerText = "Machine Learning Researcher & Data Scientist";
        previewBio.innerText = "Focused on deep learning interpretability, natural language processing benchmarks, and robust statistical evaluation.";
        previewThemeLabel.innerText = "theme: clean-minimalist";
        if (previewAvatar) previewAvatar.style.background = "linear-gradient(135deg, #0ea5e9, #38bdf8)";
    } else if (theme === "creative") {
        previewName.innerText = "Jordan Vance";
        previewTitle.innerText = "Creative Technologist & Interactive UI/UX Lead";
        previewBio.innerText = "Blending generative algorithms, interactive 3D WebGL experiences, and human-centered design systems.";
        previewThemeLabel.innerText = "theme: creative-studio";
        if (previewAvatar) previewAvatar.style.background = "linear-gradient(135deg, #ec4899, #f43f5e)";
    }
}
