/**
 * PortfolioAI — Theme Builder & Live Customizer
 * Uses direct DOM class-swapping on #livePreviewPanel for instant theme changes.
 * No iframe, no network, no caching issues.
 */

document.addEventListener("DOMContentLoaded", () => {

    /* ── Config seeded from server ── */
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

    /* ── DOM ── */
    const preview        = document.getElementById("livePreviewPanel");
    const themeLabel     = document.getElementById("previewThemeLabel");
    const themeCards     = document.querySelectorAll(".theme-choice-card");
    const activeThemeBadge = document.getElementById("activeThemeBadge");
    const colorSwatches  = document.querySelectorAll(".color-swatch");
    const activeColorHex = document.getElementById("activeColorHex");
    const fontSelect     = document.getElementById("fontSelect");
    const layoutSelect   = document.getElementById("layoutSelect");
    const sectionToggles = document.querySelectorAll(".section-toggle-input");
    const btnSave        = document.getElementById("btnSaveTheme");
    const saveBtnSpinner = document.getElementById("saveBtnSpinner");
    const saveBtnIcon    = document.getElementById("saveBtnIcon");
    const btnReset       = document.getElementById("btnResetDefaults");
    const editorAlert    = document.getElementById("editorAlert");

    /* ── Known class lists ── */
    const THEME_CLASSES  = [
        "modern-dark","minimal-light","creative-gradient","professional-blue",
        "creative-colorful","premium-elegant","terminal-hacker","student-starter"
    ];
    const FONT_CLASSES   = ["plus-jakarta-sans","outfit","inter","serif","mono"];
    const LAYOUT_CLASSES = ["standard","compact","sidebar"];

    /* ── Swap a prefixed CSS class on an element ── */
    function swapClass(el, prefix, list, newVal) {
        list.forEach(v => el.classList.remove(prefix + v));
        el.classList.add(prefix + newVal);
    }

    /* ── Convert hex color to RGB string ── */
    function hexToRgb(hex) {
        hex = hex.replace("#","");
        if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
        const r = parseInt(hex.substring(0,2),16);
        const g = parseInt(hex.substring(2,4),16);
        const b = parseInt(hex.substring(4,6),16);
        return isNaN(r) ? null : `${r}, ${g}, ${b}`;
    }

    /* ── Apply all current config to the preview panel ── */
    function applyPreview() {
        if (!preview) return;

        // Swap theme / font / layout classes
        swapClass(preview, "theme-",  THEME_CLASSES,  config.theme);
        swapClass(preview, "font-",   FONT_CLASSES,   config.font_family);
        swapClass(preview, "layout-", LAYOUT_CLASSES, config.layout_style);

        // Update accent color CSS variables
        preview.style.setProperty("--theme-accent", config.accent_color);
        preview.style.setProperty("--theme-accent-hover", config.accent_color);
        const rgb = hexToRgb(config.accent_color);
        if (rgb) preview.style.setProperty("--theme-accent-rgb", rgb);

        // Update browser bar label
        if (themeLabel) themeLabel.textContent = config.theme;
    }

    /* ── CSRF ── */
    function getCsrf() {
        const m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute("content") : "";
    }

    /* ── Alert ── */
    function showAlert(msg, type = "info") {
        if (!editorAlert) return;
        const icon = type === "success"
            ? "bi-check-circle-fill text-success"
            : "bi-exclamation-triangle-fill text-danger";
        editorAlert.className = `alert alert-${type} glass-card mb-3 d-block`;
        editorAlert.innerHTML = `<div class="d-flex align-items-center gap-2">
            <i class="bi ${icon} fs-5"></i><div class="small">${msg}</div></div>`;
        if (type === "success")
            setTimeout(() => { editorAlert.className = "alert d-none"; }, 4000);
    }

    /* ══ 1. THEME CARD CLICK ══ */
    themeCards.forEach(card => {
        card.addEventListener("click", () => {
            const t = card.dataset.theme;
            if (!t) return;
            themeCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            config.theme = t;
            if (activeThemeBadge) activeThemeBadge.textContent = t.split("-").join(" ");
            applyPreview();
        });
    });

    /* ══ 2. ACCENT COLOR ══ */
    colorSwatches.forEach(s => {
        s.addEventListener("click", () => {
            const c = s.dataset.color;
            if (!c) return;
            colorSwatches.forEach(x => x.classList.remove("active"));
            s.classList.add("active");
            config.accent_color = c;
            if (activeColorHex) activeColorHex.textContent = c;
            applyPreview();
        });
    });

    /* ══ 3. FONT ══ */
    if (fontSelect) {
        fontSelect.addEventListener("change", e => {
            config.font_family = e.target.value;
            applyPreview();
        });
    }

    /* ══ 4. LAYOUT ══ */
    if (layoutSelect) {
        layoutSelect.addEventListener("change", e => {
            config.layout_style = e.target.value;
            applyPreview();
        });
    }

    /* ══ 5. SECTION VISIBILITY ══ */
    sectionToggles.forEach(t => {
        t.addEventListener("change", e => {
            const sec = e.target.dataset.section;
            if (!sec) return;
            config.visible_sections[sec] = e.target.checked;
            const el = preview && preview.querySelector(`[data-section="${sec}"]`);
            if (el) el.style.display = e.target.checked ? "" : "none";
        });
    });

    /* ══ 6. RESET ══ */
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            if (!confirm("Reset all theme preferences to defaults?")) return;
            config.theme        = "modern-dark";
            config.accent_color = "#6366f1";
            config.font_family  = "plus-jakarta-sans";
            config.layout_style = "standard";
            config.visible_sections = {
                about:true,skills:true,projects:true,
                experience:true,education:true,certifications:true,contact:true
            };
            themeCards.forEach(c => c.classList.toggle("active", c.dataset.theme === config.theme));
            if (activeThemeBadge) activeThemeBadge.textContent = "modern dark";
            colorSwatches.forEach(s => s.classList.toggle("active", s.dataset.color === config.accent_color));
            if (activeColorHex) activeColorHex.textContent = config.accent_color;
            if (fontSelect)   fontSelect.value   = config.font_family;
            if (layoutSelect) layoutSelect.value = config.layout_style;
            sectionToggles.forEach(t => { t.checked = true; });
            applyPreview();
            showAlert("Reset to defaults. Click 'Save Theme' to persist.", "info");
        });
    }

    /* ══ 7. SAVE THEME ══ */
    if (btnSave) {
        btnSave.addEventListener("click", async () => {
            btnSave.disabled = true;
            if (saveBtnSpinner) saveBtnSpinner.classList.remove("d-none");
            if (saveBtnIcon)    saveBtnIcon.classList.add("d-none");
            try {
                const res = await fetch(`/portfolios/${config.portfolioId}/theme`, {
                    method: "POST",
                    headers: { "Content-Type":"application/json","X-CSRFToken":getCsrf() },
                    body: JSON.stringify({
                        theme:            config.theme,
                        accent_color:     config.accent_color,
                        font_family:      config.font_family,
                        layout_style:     config.layout_style,
                        visible_sections: config.visible_sections,
                    }),
                });
                const data = await res.json();
                if (!res.ok || !data.success) showAlert(data.error || "Save failed.", "danger");
                else showAlert(data.message || "Theme saved!", "success");
            } catch {
                showAlert("Network error. Could not save.", "danger");
            } finally {
                btnSave.disabled = false;
                if (saveBtnSpinner) saveBtnSpinner.classList.add("d-none");
                if (saveBtnIcon)    saveBtnIcon.classList.remove("d-none");
            }
        });
    }

    /* ── Apply initial config on page load ── */
    applyPreview();
});
