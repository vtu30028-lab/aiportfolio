/**
 * PortfolioAI — Theme Builder & Live Customizer
 * Uses direct DOM class-swapping on #livePreviewPanel for instant theme changes.
 * Layout changes use INLINE STYLES (highest CSS specificity, bypasses media queries).
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
    const preview           = document.getElementById("livePreviewPanel");
    const themeLabel        = document.getElementById("previewThemeLabel");
    const themeCards        = document.querySelectorAll(".theme-choice-card");
    const activeThemeBadge  = document.getElementById("activeThemeBadge");
    const colorSwatches     = document.querySelectorAll(".color-swatch");
    const activeColorHex    = document.getElementById("activeColorHex");
    const fontSelect        = document.getElementById("fontSelect");
    const layoutSelect      = document.getElementById("layoutSelect");
    const sectionToggles    = document.querySelectorAll(".section-toggle-input");
    const btnSave           = document.getElementById("btnSaveTheme");
    const saveBtnSpinner    = document.getElementById("saveBtnSpinner");
    const saveBtnIcon       = document.getElementById("saveBtnIcon");
    const customColorPicker = document.getElementById("customColorPicker");
    const customColorHexInput = document.getElementById("customColorHexInput");
    const btnReset          = document.getElementById("btnResetDefaults");
    const editorAlert       = document.getElementById("editorAlert");

    /* ── Known class lists ── */
    const THEME_CLASSES = [
        "modern-dark","minimal-light","creative-gradient","professional-blue",
        "creative-colorful","premium-elegant","terminal-hacker","student-starter",
        "mindful-organic","cyberpunk-neon","midnight-emerald","sunset-coral",
        "arctic-frost","monochrome-swiss"
    ];
    const FONT_CLASSES = [
        "plus-jakarta-sans","outfit","inter","serif","mono",
        "poppins","space-grotesk","playfair","dm-sans","fira-code"
    ];
    const LAYOUT_CLASSES = [
        "standard","compact","sidebar","bento-grid","split-hero",
        "magazine","timeline","minimal-zen"
    ];

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

    /* ── Helper: get section el inside preview ── */
    function sec(name) {
        return preview && preview.querySelector(`[data-section="${name}"]`);
    }

    /* ═══════════════════════════════════════════════════════════════
       APPLY LAYOUT — Uses JS inline styles (highest specificity,
       works at any container width, bypasses all @media queries)
    ═══════════════════════════════════════════════════════════════ */
    function applyPreviewLayout() {
        if (!preview) return;

        const layout    = config.layout_style;
        const container = preview.querySelector(".portfolio-layout-container");
        const grid      = preview.querySelector(".portfolio-main-grid");
        const sidebar   = preview.querySelector(".portfolio-sidebar-col");
        const heroEl    = preview.querySelector(".preview-hero");
        const heroName  = preview.querySelector(".preview-name");
        const sections  = preview.querySelectorAll("[data-section]");

        /* ── 1. Full reset of all inline layout styles ── */
        if (sidebar)   { sidebar.style.cssText = "display:none;"; }
        if (container) {
            container.style.cssText = "padding:0.75rem 1.1rem;";
            /* Clear properties that specific layouts may have set */
            container.style.borderLeft = "";
            container.style.marginLeft = "";
            container.style.maxWidth   = "";
            container.style.margin     = "";
        }
        if (grid) { grid.style.cssText = ""; }
        if (heroEl) {
            heroEl.style.paddingTop    = "";
            heroEl.style.paddingBottom = "";
            heroEl.style.minHeight     = "";
            heroEl.style.borderBottom  = "";
        }
        if (heroName) {
            heroName.style.fontSize      = "";
            heroName.style.fontWeight    = "";
            heroName.style.letterSpacing = "";
            heroName.style.lineHeight    = "";
        }
        sections.forEach(s => {
            s.style.gridColumn   = "";
            s.style.borderLeft   = "";
            s.style.paddingLeft  = "";
            s.style.borderRadius = "";
            s.style.borderTop    = "";
            s.style.paddingTop   = "";
        });

        /* ── 2. Apply layout-specific inline styles ── */
        switch (layout) {

            /* ── Standard: clean single-column flow ── */
            case "standard":
                if (grid) {
                    grid.style.display        = "flex";
                    grid.style.flexDirection  = "column";
                    grid.style.gap            = "1rem";
                }
                break;

            /* ── Compact: dense 2-column grid ── */
            case "compact":
                if (grid) {
                    grid.style.display             = "grid";
                    grid.style.gridTemplateColumns = "repeat(2,1fr)";
                    grid.style.gap                 = "0.85rem";
                    grid.style.alignItems          = "start";
                }
                /* Contact always full-width */
                const ctSec = sec("contact");
                if (ctSec) ctSec.style.gridColumn = "1 / -1";
                break;

            /* ── Sidebar: sticky profile column + content ── */
            case "sidebar":
                if (sidebar) {
                    sidebar.style.display   = "block";
                    sidebar.style.position  = "sticky";
                    sidebar.style.top       = "0.5rem";
                }
                if (container) {
                    container.style.display             = "grid";
                    container.style.gridTemplateColumns = "150px 1fr";
                    container.style.gap                 = "0.85rem";
                    container.style.alignItems          = "start";
                    container.style.padding             = "0.75rem 0.9rem";
                }
                if (grid) {
                    grid.style.display       = "flex";
                    grid.style.flexDirection = "column";
                    grid.style.gap           = "0.85rem";
                }
                break;

            /* ── Bento Grid: asymmetric mosaic dashboard ── */
            case "bento-grid":
                if (grid) {
                    grid.style.display             = "grid";
                    grid.style.gridTemplateColumns = "repeat(6,1fr)";
                    grid.style.gap                 = "0.65rem";
                    grid.style.alignItems          = "start";
                }
                /* Section-specific column spans */
                const bentoMap = {
                    about:"span 4", skills:"span 2", projects:"span 6",
                    experience:"span 4", education:"span 2",
                    certifications:"span 3", contact:"span 3"
                };
                Object.entries(bentoMap).forEach(([s, span]) => {
                    const el = sec(s);
                    if (el) el.style.gridColumn = span;
                });
                break;

            /* ── Split Hero: editorial — big bold hero + 2-col sections ── */
            case "split-hero":
                if (heroEl) {
                    heroEl.style.paddingTop    = "2.8rem";
                    heroEl.style.paddingBottom = "2.5rem";
                    heroEl.style.minHeight     = "170px";
                }
                if (heroName) {
                    heroName.style.fontSize      = "1.85rem";
                    heroName.style.fontWeight    = "900";
                    heroName.style.letterSpacing = "-0.04em";
                    heroName.style.lineHeight    = "1.08";
                }
                if (grid) {
                    grid.style.display             = "grid";
                    grid.style.gridTemplateColumns = "1fr 1fr";
                    grid.style.gap                 = "0.85rem";
                    grid.style.alignItems          = "start";
                }
                /* Full-width rows */
                ["about","projects","contact"].forEach(s => {
                    const el = sec(s); if (el) el.style.gridColumn = "1 / -1";
                });
                break;

            /* ── Magazine: 3-col editorial print-inspired grid ── */
            case "magazine":
                if (heroEl) {
                    heroEl.style.paddingTop    = "2.2rem";
                    heroEl.style.paddingBottom = "2.2rem";
                    heroEl.style.minHeight     = "140px";
                    heroEl.style.borderBottom  = "4px double var(--theme-accent, #6366f1)";
                }
                if (heroName) {
                    heroName.style.fontSize      = "1.6rem";
                    heroName.style.fontWeight    = "800";
                    heroName.style.letterSpacing = "0.01em";
                }
                if (grid) {
                    grid.style.display             = "grid";
                    grid.style.gridTemplateColumns = "repeat(3,1fr)";
                    grid.style.gap                 = "0.75rem";
                    grid.style.alignItems          = "start";
                }
                /* Full-width feature sections */
                ["about","projects","contact"].forEach(s => {
                    const el = sec(s); if (el) el.style.gridColumn = "1 / -1";
                });
                break;

            /* ── Timeline: vertical progression timeline with accent line ── */
            case "timeline":
                if (container) {
                    container.style.borderLeft  = "3px solid var(--theme-accent, #6366f1)";
                    container.style.paddingLeft = "1.4rem";
                    container.style.marginLeft  = "0.7rem";
                    container.style.padding     = "0.75rem 1rem 0.75rem 1.5rem";
                }
                if (grid) {
                    grid.style.display       = "flex";
                    grid.style.flexDirection = "column";
                    grid.style.gap           = "0.65rem";
                    grid.style.position      = "relative";
                }
                /* Section dot markers via border-left */
                sections.forEach(s => {
                    s.style.borderLeft  = "3px solid var(--theme-accent, #6366f1)";
                    s.style.paddingLeft = "0.75rem";
                    s.style.borderRadius = "0 8px 8px 0";
                });
                break;

            /* ── Minimal Zen: narrow centered column, maximal whitespace ── */
            case "minimal-zen":
                if (container) {
                    container.style.maxWidth = "500px";
                    container.style.margin   = "0 auto";
                    container.style.padding  = "1.2rem 2rem 2rem";
                }
                if (grid) {
                    grid.style.display       = "flex";
                    grid.style.flexDirection = "column";
                    grid.style.gap           = "2rem";
                }
                if (heroEl) {
                    heroEl.style.borderBottom  = "1px solid var(--theme-accent, #6366f1)";
                    heroEl.style.paddingBottom = "2rem";
                }
                break;
        }

        /* ── 3. Re-enforce section visibility (grid changes must not unhide hidden sections) ── */
        if (config.visible_sections) {
            Object.keys(config.visible_sections).forEach(s => {
                const el = sec(s);
                if (el) el.style.display = config.visible_sections[s] ? "" : "none";
            });
        }
    }

    /* ── Apply all current config to the preview panel ── */
    function applyPreview() {
        if (!preview) return;

        /* Swap theme / font / layout classes */
        swapClass(preview, "theme-",  THEME_CLASSES,  config.theme);
        swapClass(preview, "font-",   FONT_CLASSES,   config.font_family);
        swapClass(preview, "layout-", LAYOUT_CLASSES, config.layout_style);

        /* Update accent color CSS variables */
        preview.style.setProperty("--theme-accent", config.accent_color);
        preview.style.setProperty("--theme-accent-hover", config.accent_color);
        const rgb = hexToRgb(config.accent_color);
        if (rgb) preview.style.setProperty("--theme-accent-rgb", rgb);

        /* Update browser bar label */
        if (themeLabel) themeLabel.textContent = config.theme;

        /* Apply layout via inline styles (reliable, bypasses CSS/media issues) */
        applyPreviewLayout();
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

    /* ══ 2. ACCENT COLOR (Presets + Custom Color) ══ */
    function setAccentColor(hex) {
        if (!hex) return;
        hex = hex.trim();
        if (!hex.startsWith("#")) hex = "#" + hex;
        if (!/^#[0-9a-fA-F]{3,6}$/.test(hex)) return;

        config.accent_color = hex;
        if (activeColorHex)     activeColorHex.textContent = hex;
        if (customColorPicker && /^#[0-9a-fA-F]{6}$/.test(hex)) customColorPicker.value = hex;
        if (customColorHexInput) customColorHexInput.value = hex.toUpperCase();

        /* Sync preset swatches */
        colorSwatches.forEach(x => {
            x.classList.toggle("active", x.dataset.color.toLowerCase() === hex.toLowerCase());
        });

        applyPreview();
    }

    colorSwatches.forEach(s => {
        s.addEventListener("click", () => { const c = s.dataset.color; if (c) setAccentColor(c); });
    });

    if (customColorPicker) {
        customColorPicker.addEventListener("input", e => { setAccentColor(e.target.value); });
    }
    if (customColorHexInput) {
        customColorHexInput.addEventListener("input", e => {
            let val = e.target.value.trim();
            if (val && !val.startsWith("#")) val = "#" + val;
            if (/^#[0-9a-fA-F]{3,6}$/.test(val)) setAccentColor(val);
        });
    }

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
            const s = e.target.dataset.section;
            if (!s) return;
            config.visible_sections[s] = e.target.checked;
            /* Re-apply layout to restore grid column spans, then enforce visibility */
            applyPreviewLayout();
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
            if (activeThemeBadge)    activeThemeBadge.textContent = "modern dark";
            colorSwatches.forEach(s => s.classList.toggle("active", s.dataset.color.toLowerCase() === config.accent_color.toLowerCase()));
            if (activeColorHex)      activeColorHex.textContent   = config.accent_color;
            if (customColorPicker)   customColorPicker.value       = config.accent_color;
            if (customColorHexInput) customColorHexInput.value     = config.accent_color.toUpperCase();
            if (fontSelect)          fontSelect.value              = config.font_family;
            if (layoutSelect)        layoutSelect.value            = config.layout_style;
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
