/**
 * PortfolioAI — Theme Builder & Live Customizer
 * Live preview works by reloading the iframe with ?theme=... query params.
 * This is guaranteed reliable — Flask renders the correct theme server-side.
 */

document.addEventListener("DOMContentLoaded", () => {

    /* ── Seed config from server-rendered values ── */
    const config = Object.assign(
        {
            portfolioId: null,
            theme: "modern-dark",
            accent_color: "#6366f1",
            font_family: "plus-jakarta-sans",
            layout_style: "standard",
            visible_sections: {
                about: true, skills: true, projects: true,
                experience: true, education: true, certifications: true, contact: true,
            },
        },
        window.INITIAL_THEME_CONFIG || {}
    );

    /* ── DOM References ── */
    const previewIframe    = document.getElementById("previewIframe");
    const viewportFrame    = document.getElementById("viewportFrame");
    const btnViewDesktop   = document.getElementById("btnViewDesktop");
    const btnViewTablet    = document.getElementById("btnViewTablet");
    const btnViewMobile    = document.getElementById("btnViewMobile");
    const themeCards       = document.querySelectorAll(".theme-choice-card");
    const activeThemeBadge = document.getElementById("activeThemeBadge");
    const colorSwatches    = document.querySelectorAll(".color-swatch");
    const activeColorHex   = document.getElementById("activeColorHex");
    const fontSelect       = document.getElementById("fontSelect");
    const layoutSelect     = document.getElementById("layoutSelect");
    const sectionToggles   = document.querySelectorAll(".section-toggle-input");
    const btnSaveTheme     = document.getElementById("btnSaveTheme");
    const saveBtnSpinner   = document.getElementById("saveBtnSpinner");
    const saveBtnIcon      = document.getElementById("saveBtnIcon");
    const btnResetDefaults = document.getElementById("btnResetDefaults");
    const editorAlert      = document.getElementById("editorAlert");

    /* ── Build live preview URL with all current config params ── */
    function getLiveUrl() {
        const base = `/portfolios/${config.portfolioId}/live`;
        const params = new URLSearchParams({
            theme:   config.theme,
            accent:  config.accent_color,
            font:    config.font_family,
            layout:  config.layout_style,
        });
        return `${base}?${params.toString()}`;
    }

    /* ── Reload the preview iframe with the new config ── */
    function refreshPreview() {
        if (!previewIframe) return;
        previewIframe.src = getLiveUrl();
    }

    /* ── CSRF helper ── */
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    /* ── Alert banner ── */
    function showAlert(message, type = "info") {
        if (!editorAlert) return;
        const icon = type === "success"
            ? "bi-check-circle-fill text-success"
            : "bi-exclamation-triangle-fill text-danger";
        editorAlert.className = `alert alert-${type} glass-card mb-3 d-block`;
        editorAlert.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${icon} fs-5"></i>
                <div class="small">${message}</div>
            </div>`;
        if (type === "success") {
            setTimeout(() => { editorAlert.className = "alert d-none"; }, 4000);
        }
    }

    /* ══════════════════════════════════════════════
       1. THEME CARD SELECTION
    ══════════════════════════════════════════════ */
    themeCards.forEach(card => {
        card.addEventListener("click", () => {
            const selected = card.dataset.theme;
            if (!selected) return;

            // Highlight selected card
            themeCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");

            // Update config & badge
            config.theme = selected;
            if (activeThemeBadge) {
                activeThemeBadge.textContent = selected.split("-").join(" ");
            }

            // Reload iframe with new theme
            refreshPreview();
        });
    });

    /* ══════════════════════════════════════════════
       2. ACCENT COLOR SWATCH
    ══════════════════════════════════════════════ */
    colorSwatches.forEach(swatch => {
        swatch.addEventListener("click", () => {
            const color = swatch.dataset.color;
            if (!color) return;

            colorSwatches.forEach(s => s.classList.remove("active"));
            swatch.classList.add("active");

            config.accent_color = color;
            if (activeColorHex) activeColorHex.textContent = color;

            refreshPreview();
        });
    });

    /* ══════════════════════════════════════════════
       3. FONT FAMILY
    ══════════════════════════════════════════════ */
    if (fontSelect) {
        fontSelect.addEventListener("change", e => {
            config.font_family = e.target.value;
            refreshPreview();
        });
    }

    /* ══════════════════════════════════════════════
       4. LAYOUT STYLE
    ══════════════════════════════════════════════ */
    if (layoutSelect) {
        layoutSelect.addEventListener("change", e => {
            config.layout_style = e.target.value;
            refreshPreview();
        });
    }

    /* ══════════════════════════════════════════════
       5. SECTION VISIBILITY TOGGLES
       (section toggle uses postMessage for instant hide/show
        without reloading the entire iframe)
    ══════════════════════════════════════════════ */
    sectionToggles.forEach(toggle => {
        toggle.addEventListener("change", e => {
            const section = e.target.dataset.section;
            if (!section) return;
            config.visible_sections[section] = e.target.checked;

            // For section visibility, try direct DOM first (no full reload needed)
            try {
                const iDoc = previewIframe.contentDocument
                    || previewIframe.contentWindow.document;
                const el = iDoc && iDoc.getElementById("section-" + section);
                if (el) {
                    el.style.display = e.target.checked ? "" : "none";
                    return;
                }
            } catch (_) {}

            // Fallback: postMessage
            if (previewIframe && previewIframe.contentWindow) {
                previewIframe.contentWindow.postMessage({
                    visible_sections: config.visible_sections
                }, "*");
            }
        });
    });

    /* ══════════════════════════════════════════════
       6. VIEWPORT SWITCHER
    ══════════════════════════════════════════════ */
    function setViewport(mode) {
        if (!viewportFrame) return;
        [btnViewDesktop, btnViewTablet, btnViewMobile].forEach(b => b && b.classList.remove("active"));
        viewportFrame.className = `viewport-frame-wrapper viewport-${mode}`;
        const btn = { desktop: btnViewDesktop, tablet: btnViewTablet, mobile: btnViewMobile }[mode];
        if (btn) btn.classList.add("active");
    }
    if (btnViewDesktop) btnViewDesktop.addEventListener("click", () => setViewport("desktop"));
    if (btnViewTablet)  btnViewTablet.addEventListener("click",  () => setViewport("tablet"));
    if (btnViewMobile)  btnViewMobile.addEventListener("click",  () => setViewport("mobile"));

    /* ══════════════════════════════════════════════
       7. RESET TO DEFAULTS
    ══════════════════════════════════════════════ */
    if (btnResetDefaults) {
        btnResetDefaults.addEventListener("click", () => {
            if (!confirm("Reset all theme preferences to defaults?")) return;

            config.theme        = "modern-dark";
            config.accent_color = "#6366f1";
            config.font_family  = "plus-jakarta-sans";
            config.layout_style = "standard";
            config.visible_sections = {
                about: true, skills: true, projects: true,
                experience: true, education: true, certifications: true, contact: true,
            };

            // Sync UI controls
            themeCards.forEach(c =>
                c.classList.toggle("active", c.dataset.theme === config.theme));
            if (activeThemeBadge) activeThemeBadge.textContent = "modern dark";

            colorSwatches.forEach(s =>
                s.classList.toggle("active", s.dataset.color === config.accent_color));
            if (activeColorHex) activeColorHex.textContent = config.accent_color;

            if (fontSelect)   fontSelect.value   = config.font_family;
            if (layoutSelect) layoutSelect.value = config.layout_style;
            sectionToggles.forEach(t => { t.checked = true; });

            refreshPreview();
            showAlert("Preferences reset to defaults. Click 'Save Theme' to persist.", "info");
        });
    }

    /* ══════════════════════════════════════════════
       8. SAVE THEME (AJAX POST)
    ══════════════════════════════════════════════ */
    if (btnSaveTheme) {
        btnSaveTheme.addEventListener("click", async () => {
            btnSaveTheme.disabled = true;
            if (saveBtnSpinner) saveBtnSpinner.classList.remove("d-none");
            if (saveBtnIcon)    saveBtnIcon.classList.add("d-none");

            try {
                const res = await fetch(`/portfolios/${config.portfolioId}/theme`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: JSON.stringify({
                        theme:            config.theme,
                        accent_color:     config.accent_color,
                        font_family:      config.font_family,
                        layout_style:     config.layout_style,
                        visible_sections: config.visible_sections,
                    }),
                });
                const data = await res.json();
                if (!res.ok || !data.success) {
                    showAlert(data.error || "Failed to save theme.", "danger");
                } else {
                    showAlert(data.message || "Theme saved successfully!", "success");
                }
            } catch (err) {
                showAlert("Network error. Could not save theme.", "danger");
            } finally {
                btnSaveTheme.disabled = false;
                if (saveBtnSpinner) saveBtnSpinner.classList.add("d-none");
                if (saveBtnIcon)    saveBtnIcon.classList.remove("d-none");
            }
        });
    }

});
