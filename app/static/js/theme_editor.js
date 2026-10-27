/**
 * PortfolioAI - Theme Builder & Live Customizer Controller
 * Handles instant real-time theme previews via postMessage,
 * viewport resizing, section toggling, and asynchronous persistence.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Current Active Configuration State
    const config = Object.assign(
        {
            portfolioId: null,
            theme: "modern-dark",
            accent_color: "#6366f1",
            font_family: "plus-jakarta-sans",
            layout_style: "standard",
            visible_sections: {
                about: true,
                skills: true,
                projects: true,
                experience: true,
                education: true,
                certifications: true,
                contact: true,
            },
        },
        window.INITIAL_THEME_CONFIG || {}
    );

    // DOM Elements
    const previewIframe = document.getElementById("previewIframe");
    const viewportFrame = document.getElementById("viewportFrame");
    const btnViewDesktop = document.getElementById("btnViewDesktop");
    const btnViewTablet = document.getElementById("btnViewTablet");
    const btnViewMobile = document.getElementById("btnViewMobile");

    const themeCards = document.querySelectorAll(".theme-choice-card");
    const activeThemeBadge = document.getElementById("activeThemeBadge");
    const colorSwatches = document.querySelectorAll(".color-swatch");
    const activeColorHex = document.getElementById("activeColorHex");
    const fontSelect = document.getElementById("fontSelect");
    const layoutSelect = document.getElementById("layoutSelect");
    const sectionToggles = document.querySelectorAll(".section-toggle-input");

    const btnSaveTheme = document.getElementById("btnSaveTheme");
    const saveBtnSpinner = document.getElementById("saveBtnSpinner");
    const saveBtnIcon = document.getElementById("saveBtnIcon");
    const btnResetDefaults = document.getElementById("btnResetDefaults");
    const editorAlert = document.getElementById("editorAlert");

    /** Helper: CSRF token */
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    /** Broadcast state update to the live preview iframe */
    function broadcastLiveUpdate() {
        if (!previewIframe || !previewIframe.contentWindow) return;
        previewIframe.contentWindow.postMessage(
            {
                theme: config.theme,
                accent_color: config.accent_color,
                font_family: config.font_family,
                layout_style: config.layout_style,
                visible_sections: config.visible_sections,
            },
            "*"
        );
    }

    /** Show alert message */
    function showAlert(message, type = "info") {
        if (!editorAlert) return;
        editorAlert.className = `alert alert-${type} glass-card mb-3 d-block`;
        editorAlert.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger'} fs-5"></i>
                <div class="small">${message}</div>
            </div>
        `;
        setTimeout(() => {
            if (type === "success") {
                editorAlert.className = "alert d-none";
            }
        }, 4000);
    }

    // 1. Theme Selection Listener
    themeCards.forEach(card => {
        card.addEventListener("click", () => {
            const selectedTheme = card.dataset.theme;
            if (!selectedTheme) return;

            themeCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");

            config.theme = selectedTheme;
            if (activeThemeBadge) activeThemeBadge.textContent = selectedTheme.replace("-", " ");

            broadcastLiveUpdate();
        });
    });

    // 2. Accent Color Palette Listener
    colorSwatches.forEach(swatch => {
        swatch.addEventListener("click", () => {
            const color = swatch.dataset.color;
            if (!color) return;

            colorSwatches.forEach(s => s.classList.remove("active"));
            swatch.classList.add("active");

            config.accent_color = color;
            if (activeColorHex) activeColorHex.textContent = color;

            broadcastLiveUpdate();
        });
    });

    // 3. Font Family Selector Listener
    if (fontSelect) {
        fontSelect.addEventListener("change", (e) => {
            config.font_family = e.target.value;
            broadcastLiveUpdate();
        });
    }

    // 4. Layout Style Selector Listener
    if (layoutSelect) {
        layoutSelect.addEventListener("change", (e) => {
            config.layout_style = e.target.value;
            broadcastLiveUpdate();
        });
    }

    // 5. Section Visibility Toggle Listeners
    sectionToggles.forEach(toggle => {
        toggle.addEventListener("change", (e) => {
            const section = e.target.dataset.section;
            if (section) {
                config.visible_sections[section] = e.target.checked;
                broadcastLiveUpdate();
            }
        });
    });

    // 6. Viewport Device Switcher Listeners
    function setViewportMode(mode) {
        if (!viewportFrame) return;

        [btnViewDesktop, btnViewTablet, btnViewMobile].forEach(btn => {
            if (btn) btn.classList.remove("active");
        });

        viewportFrame.className = `viewport-frame-wrapper viewport-${mode}`;

        if (mode === "desktop" && btnViewDesktop) btnViewDesktop.classList.add("active");
        if (mode === "tablet" && btnViewTablet) btnViewTablet.classList.add("active");
        if (mode === "mobile" && btnViewMobile) btnViewMobile.classList.add("active");
    }

    if (btnViewDesktop) btnViewDesktop.addEventListener("click", () => setViewportMode("desktop"));
    if (btnViewTablet) btnViewTablet.addEventListener("click", () => setViewportMode("tablet"));
    if (btnViewMobile) btnViewMobile.addEventListener("click", () => setViewportMode("mobile"));

    // 7. Reset to Defaults
    if (btnResetDefaults) {
        btnResetDefaults.addEventListener("click", () => {
            if (!confirm("Reset all theme preferences to defaults?")) return;

            config.theme = "modern-dark";
            config.accent_color = "#6366f1";
            config.font_family = "plus-jakarta-sans";
            config.layout_style = "standard";
            config.visible_sections = {
                about: true,
                skills: true,
                projects: true,
                experience: true,
                education: true,
                certifications: true,
                contact: true,
            };

            // Update UI
            themeCards.forEach(c => c.classList.toggle("active", c.dataset.theme === config.theme));
            if (activeThemeBadge) activeThemeBadge.textContent = "modern dark";

            colorSwatches.forEach(s => s.classList.toggle("active", s.dataset.color === config.accent_color));
            if (activeColorHex) activeColorHex.textContent = config.accent_color;

            if (fontSelect) fontSelect.value = config.font_family;
            if (layoutSelect) layoutSelect.value = config.layout_style;

            sectionToggles.forEach(t => {
                t.checked = true;
            });

            broadcastLiveUpdate();
            showAlert("Preferences reset to default values. Click 'Save Theme' to persist.", "info");
        });
    }

    // 8. Save Theme Preferences (AJAX POST)
    if (btnSaveTheme) {
        btnSaveTheme.addEventListener("click", async () => {
            btnSaveTheme.disabled = true;
            if (saveBtnSpinner) saveBtnSpinner.classList.remove("d-none");
            if (saveBtnIcon) saveBtnIcon.classList.add("d-none");

            try {
                const response = await fetch(`/portfolios/${config.portfolioId}/theme`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: JSON.stringify({
                        theme: config.theme,
                        accent_color: config.accent_color,
                        font_family: config.font_family,
                        layout_style: config.layout_style,
                        visible_sections: config.visible_sections,
                    }),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    showAlert(data.error || "Failed to save theme preferences.", "danger");
                } else {
                    showAlert(data.message || "Theme preferences saved successfully!", "success");
                }
            } catch (err) {
                showAlert("Network error while saving theme preferences.", "danger");
            } finally {
                btnSaveTheme.disabled = false;
                if (saveBtnSpinner) saveBtnSpinner.classList.add("d-none");
                if (saveBtnIcon) saveBtnIcon.classList.remove("d-none");
            }
        });
    }

    // Ensure initial state broadcasts when iframe finishes loading
    if (previewIframe) {
        previewIframe.addEventListener("load", () => {
            setTimeout(broadcastLiveUpdate, 200);
        });
    }
});
