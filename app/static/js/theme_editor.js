/**
 * PortfolioAI - Theme Builder & Live Customizer Controller
 * Uses direct same-origin DOM access as primary live-update method,
 * with postMessage and src-reload as fallbacks.
 */

document.addEventListener("DOMContentLoaded", () => {
    // ── Active Configuration State (seeded from server-rendered values) ──
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

    // Track whether iframe finished first load
    let iframeReady = false;

    // ── DOM References ──
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

    // ── Known class lists (must match CSS) ──
    const THEME_CLASSES  = [
        "modern-dark", "minimal-light", "creative-gradient", "professional-blue",
        "creative-colorful", "premium-elegant", "terminal-hacker", "student-starter"
    ];
    const FONT_CLASSES   = ["plus-jakarta-sans", "outfit", "inter", "serif", "mono"];
    const LAYOUT_CLASSES = ["standard", "compact", "sidebar"];

    // ── Helper: CSRF token ──
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    // ── Helper: safely swap a prefixed class on an element ──
    function swapClass(el, prefix, knownList, newSuffix) {
        knownList.forEach(s => el.classList.remove(prefix + s));
        // sweep for any unlisted stray classes with same prefix
        const stray = [];
        el.classList.forEach(c => { if (c.startsWith(prefix)) stray.push(c); });
        stray.forEach(c => el.classList.remove(c));
        el.classList.add(prefix + newSuffix);
    }

    // ── Helper: build live preview URL with current config ──
    function buildLiveUrl() {
        if (!previewIframe) return "";
        const base = previewIframe.src.split("?")[0];
        return `${base}?theme=${encodeURIComponent(config.theme)}&accent=${encodeURIComponent(config.accent_color)}&font=${encodeURIComponent(config.font_family)}&layout=${encodeURIComponent(config.layout_style)}`;
    }

    /**
     * Apply current config to the live preview iframe.
     *
     * Layer 1 — Direct same-origin DOM (instant, no flash, most reliable)
     * Layer 2 — postMessage (works when DOM is accessible but locked)
     * Layer 3 — Full src reload with query params (always works, brief flash)
     */
    function broadcastLiveUpdate() {
        if (!previewIframe) return;

        // Layer 1: Direct same-origin DOM manipulation
        try {
            const iDoc = previewIframe.contentDocument
                || (previewIframe.contentWindow && previewIframe.contentWindow.document);

            if (iDoc && iDoc.readyState !== "loading" && iDoc.getElementById("portfolioBody")) {
                // Swap theme / font / layout body classes
                const body = iDoc.getElementById("portfolioBody");
                swapClass(body, "theme-",  THEME_CLASSES,  config.theme);
                swapClass(body, "font-",   FONT_CLASSES,   config.font_family);
                swapClass(body, "layout-", LAYOUT_CLASSES, config.layout_style);

                // Update accent CSS variables on the iframe's :root
                const root = iDoc.documentElement;
                root.style.setProperty("--theme-accent",       config.accent_color);
                root.style.setProperty("--theme-accent-hover", config.accent_color);
                const hex = config.accent_color.replace("#", "");
                const r = parseInt(hex.substring(0, 2), 16);
                const g = parseInt(hex.substring(2, 4), 16);
                const b = parseInt(hex.substring(4, 6), 16);
                if (!isNaN(r) && !isNaN(g) && !isNaN(b)) {
                    root.style.setProperty("--theme-accent-rgb", `${r}, ${g}, ${b}`);
                }

                // Section visibility
                const vis = config.visible_sections;
                Object.keys(vis).forEach(key => {
                    const el = iDoc.getElementById("section-" + key);
                    if (el) el.style.display = vis[key] ? "" : "none";
                });

                return; // ✓ done — no reload needed
            }
        } catch (e) {
            // DOM access blocked — try postMessage
        }

        // Layer 2: postMessage
        if (previewIframe.contentWindow) {
            try {
                previewIframe.contentWindow.postMessage({
                    theme: config.theme,
                    accent_color: config.accent_color,
                    font_family: config.font_family,
                    layout_style: config.layout_style,
                    visible_sections: config.visible_sections,
                }, "*");
                return;
            } catch (e) { /* fall through */ }
        }

        // Layer 3: Full src reload
        const url = buildLiveUrl();
        if (url) previewIframe.src = url;
    }

    /** Show alert banner */
    function showAlert(message, type = "info") {
        if (!editorAlert) return;
        editorAlert.className = `alert alert-${type} glass-card mb-3 d-block`;
        editorAlert.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${type === "success" ? "bi-check-circle-fill text-success" : "bi-exclamation-triangle-fill text-danger"} fs-5"></i>
                <div class="small">${message}</div>
            </div>
        `;
        setTimeout(() => {
            if (type === "success") editorAlert.className = "alert d-none";
        }, 4000);
    }

    // ── 1. Theme Card Click ──
    themeCards.forEach(card => {
        card.addEventListener("click", () => {
            const selectedTheme = card.dataset.theme;
            if (!selectedTheme) return;

            themeCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");

            config.theme = selectedTheme;
            if (activeThemeBadge) {
                activeThemeBadge.textContent = selectedTheme.split("-").join(" ");
            }

            broadcastLiveUpdate();
        });
    });

    // ── 2. Accent Color Swatch Click ──
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

    // ── 3. Font Selector ──
    if (fontSelect) {
        fontSelect.addEventListener("change", (e) => {
            config.font_family = e.target.value;
            broadcastLiveUpdate();
        });
    }

    // ── 4. Layout Selector ──
    if (layoutSelect) {
        layoutSelect.addEventListener("change", (e) => {
            config.layout_style = e.target.value;
            broadcastLiveUpdate();
        });
    }

    // ── 5. Section Visibility Toggles ──
    sectionToggles.forEach(toggle => {
        toggle.addEventListener("change", (e) => {
            const section = e.target.dataset.section;
            if (section) {
                config.visible_sections[section] = e.target.checked;
                broadcastLiveUpdate();
            }
        });
    });

    // ── 6. Viewport Device Switcher ──
    function setViewportMode(mode) {
        if (!viewportFrame) return;
        [btnViewDesktop, btnViewTablet, btnViewMobile].forEach(btn => {
            if (btn) btn.classList.remove("active");
        });
        viewportFrame.className = `viewport-frame-wrapper viewport-${mode}`;
        if (mode === "desktop" && btnViewDesktop) btnViewDesktop.classList.add("active");
        if (mode === "tablet"  && btnViewTablet)  btnViewTablet.classList.add("active");
        if (mode === "mobile"  && btnViewMobile)  btnViewMobile.classList.add("active");
    }

    if (btnViewDesktop) btnViewDesktop.addEventListener("click", () => setViewportMode("desktop"));
    if (btnViewTablet)  btnViewTablet.addEventListener("click",  () => setViewportMode("tablet"));
    if (btnViewMobile)  btnViewMobile.addEventListener("click",  () => setViewportMode("mobile"));

    // ── 7. Reset to Defaults ──
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

            themeCards.forEach(c => c.classList.toggle("active", c.dataset.theme === config.theme));
            if (activeThemeBadge) activeThemeBadge.textContent = "modern dark";

            colorSwatches.forEach(s => s.classList.toggle("active", s.dataset.color === config.accent_color));
            if (activeColorHex) activeColorHex.textContent = config.accent_color;

            if (fontSelect)   fontSelect.value   = config.font_family;
            if (layoutSelect) layoutSelect.value = config.layout_style;

            sectionToggles.forEach(t => { t.checked = true; });

            broadcastLiveUpdate();
            showAlert("Preferences reset to defaults. Click 'Save Theme' to persist.", "info");
        });
    }

    // ── 8. Save Theme (AJAX POST) ──
    if (btnSaveTheme) {
        btnSaveTheme.addEventListener("click", async () => {
            btnSaveTheme.disabled = true;
            if (saveBtnSpinner) saveBtnSpinner.classList.remove("d-none");
            if (saveBtnIcon)    saveBtnIcon.classList.add("d-none");

            try {
                const response = await fetch(`/portfolios/${config.portfolioId}/theme`, {
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
                if (saveBtnIcon)    saveBtnIcon.classList.remove("d-none");
            }
        });
    }

    // ── Iframe load handler ──
    if (previewIframe) {
        previewIframe.addEventListener("load", () => {
            iframeReady = true;
            // Apply current config right after iframe loads
            setTimeout(broadcastLiveUpdate, 100);
        });
    }
});
