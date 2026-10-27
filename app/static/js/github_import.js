/**
 * PortfolioAI - GitHub Integration Frontend Controller
 * Handles repository fetching, live filtering, individual selection,
 * Gemini AI description generation, and conflict-safe portfolio import.
 */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let fetchedRepositories = [];
    let currentEditIndex = null;
    let pendingImportPayload = null;

    // DOM Elements
    const portfolioSelect = document.getElementById("portfolioSelect");
    const githubUsername = document.getElementById("githubUsername");
    const btnFetchRepos = document.getElementById("btnFetchRepos");
    const fetchBtnSpinner = document.getElementById("fetchBtnSpinner");
    const fetchBtnIcon = document.getElementById("fetchBtnIcon");

    const statusAlert = document.getElementById("statusAlert");
    const statusAlertMessage = document.getElementById("statusAlertMessage");
    const statusAlertIcon = document.getElementById("statusAlertIcon");

    const loadingState = document.getElementById("loadingState");
    const reposContainer = document.getElementById("reposContainer");
    const repoCardsGrid = document.getElementById("repoCardsGrid");
    const selectAllCheckbox = document.getElementById("selectAllCheckbox");
    const selectedCountBadge = document.getElementById("selectedCountBadge");
    const totalFoundBadge = document.getElementById("totalFoundBadge");
    const filterKeyword = document.getElementById("filterKeyword");
    const btnImportSelected = document.getElementById("btnImportSelected");
    const importBtnSpinner = document.getElementById("importBtnSpinner");
    const importBtnIcon = document.getElementById("importBtnIcon");

    // Edit Modal Elements
    const editModalEl = document.getElementById("editProjectModal");
    const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
    const modalRepoIndex = document.getElementById("modalRepoIndex");
    const modalProjectTitle = document.getElementById("modalProjectTitle");
    const modalLiveUrl = document.getElementById("modalLiveUrl");
    const modalTechStack = document.getElementById("modalTechStack");
    const modalDescription = document.getElementById("modalDescription");
    const modalGithubUrl = document.getElementById("modalGithubUrl");
    const btnModalAiPolish = document.getElementById("btnModalAiPolish");
    const aiPolishSpinner = document.getElementById("aiPolishSpinner");
    const aiPolishIcon = document.getElementById("aiPolishIcon");
    const btnSaveModalChanges = document.getElementById("btnSaveModalChanges");

    // Conflict Modal Elements
    const conflictModalEl = document.getElementById("conflictConfirmModal");
    const conflictModal = conflictModalEl ? new bootstrap.Modal(conflictModalEl) : null;
    const conflictModalMessage = document.getElementById("conflictModalMessage");
    const btnConfirmOverwrite = document.getElementById("btnConfirmOverwrite");

    /** Helper: Retrieve CSRF token from meta header */
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    /** Helper: Display status notification banner */
    function showAlert(message, type = "info") {
        if (!statusAlert || !statusAlertMessage) return;

        statusAlert.className = `alert alert-${type} glass-card mb-4 d-block`;
        statusAlertMessage.textContent = message;

        if (statusAlertIcon) {
            statusAlertIcon.className = type === "danger"
                ? "bi bi-exclamation-octagon-fill fs-5 text-danger"
                : type === "success"
                ? "bi bi-check-circle-fill fs-5 text-success"
                : type === "warning"
                ? "bi bi-exclamation-triangle-fill fs-5 text-warning"
                : "bi bi-info-circle-fill fs-5 text-info";
        }
    }

    function hideAlert() {
        if (statusAlert) statusAlert.className = "alert d-none";
    }

    /** Fetch Repositories from Backend */
    async function handleFetchRepositories() {
        const username = githubUsername.value.trim();
        const portfolioId = portfolioSelect ? portfolioSelect.value : null;

        if (!username) {
            showAlert("Please enter a GitHub username to search.", "warning");
            githubUsername.focus();
            return;
        }

        if (!portfolioId) {
            showAlert("Please select a target portfolio first.", "warning");
            return;
        }

        hideAlert();
        if (reposContainer) reposContainer.classList.add("d-none");
        if (loadingState) loadingState.classList.remove("d-none");

        // Toggle button loading
        btnFetchRepos.disabled = true;
        fetchBtnSpinner.classList.remove("d-none");
        fetchBtnIcon.classList.add("d-none");

        try {
            const response = await fetch("/github/fetch", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify({
                    username: username,
                    portfolio_id: parseInt(portfolioId, 10),
                }),
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(data.error || "Failed to fetch repositories.", "danger");
                return;
            }

            // Transform into mutable state
            fetchedRepositories = (data.repositories || []).map((repo, idx) => ({
                id: idx,
                name: repo.name,
                title: repo.name.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
                rawDescription: repo.description || "",
                description: repo.description || "",
                language: repo.language || "Other",
                stars: repo.stars || 0,
                forks: repo.forks || 0,
                topics: repo.topics || [],
                technologies: [repo.language, ...(repo.topics || [])].filter(Boolean).join(", "),
                html_url: repo.html_url,
                live_url: repo.homepage || "",
                already_imported: Boolean(repo.already_imported),
                selected: false,
                is_fork: repo.is_fork || false,
            }));

            if (fetchedRepositories.length === 0) {
                showAlert(`No public repositories found for @${data.username}.`, "info");
                return;
            }

            showAlert(`Found ${fetchedRepositories.length} public repositories for @${data.username}. Select projects to import below.`, "success");
            renderRepositoryCards(fetchedRepositories);
            updateSelectionState();

            if (totalFoundBadge) {
                totalFoundBadge.textContent = `(${fetchedRepositories.length} repositories)`;
            }
            if (reposContainer) reposContainer.classList.remove("d-none");

        } catch (err) {
            showAlert("A network error occurred while communicating with the server. Please try again.", "danger");
        } finally {
            if (loadingState) loadingState.classList.add("d-none");
            btnFetchRepos.disabled = false;
            fetchBtnSpinner.classList.add("d-none");
            fetchBtnIcon.classList.remove("d-none");
        }
    }

    /** Render repository cards into grid */
    function renderRepositoryCards(repos) {
        if (!repoCardsGrid) return;
        repoCardsGrid.innerHTML = "";

        repos.forEach((repo, index) => {
            const cardCol = document.createElement("div");
            cardCol.className = "col-md-6 col-lg-4 repo-card-item";
            cardCol.dataset.index = index;
            cardCol.dataset.name = repo.name.toLowerCase();
            cardCol.dataset.language = repo.language.toLowerCase();
            cardCol.dataset.description = repo.description.toLowerCase();

            const isSelected = repo.selected;
            const alreadyBadge = repo.already_imported
                ? `<span class="badge bg-warning bg-opacity-10 text-warning border border-warning border-opacity-25 small" title="Already present in this portfolio">
                     <i class="bi bi-check2-all me-1"></i>In Portfolio
                   </span>`
                : "";

            const forkBadge = repo.is_fork
                ? `<span class="badge bg-secondary bg-opacity-25 text-muted small ms-1">Fork</span>`
                : "";

            const topicsHtml = repo.topics.slice(0, 4).map(t =>
                `<span class="badge-tag me-1 mb-1 font-monospace" style="font-size: 0.72rem;">#${escapeHtml(t)}</span>`
            ).join("");

            cardCol.innerHTML = `
                <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between position-relative repo-card ${isSelected ? 'border-primary' : ''}">
                    <div>
                        <!-- Top Bar with Checkbox & Title -->
                        <div class="d-flex align-items-start gap-2 mb-2">
                            <div class="form-check pt-1">
                                <input class="form-check-input repo-select-checkbox" type="checkbox" data-index="${index}" ${isSelected ? 'checked' : ''} id="repoCheck${index}">
                            </div>
                            <div class="flex-grow-1 min-w-0">
                                <div class="d-flex align-items-center justify-content-between gap-1">
                                    <h5 class="text-white fw-bold mb-0 text-truncate" title="${escapeHtml(repo.name)}">
                                        ${escapeHtml(repo.title || repo.name)}
                                    </h5>
                                    ${alreadyBadge}
                                </div>
                                <div class="d-flex align-items-center gap-1 mt-1">
                                    <a href="${escapeHtml(repo.html_url)}" target="_blank" rel="noopener noreferrer" class="text-info text-decoration-none small text-truncate" style="max-width: 190px;">
                                        <i class="bi bi-github me-1"></i>${escapeHtml(repo.name)}
                                    </a>
                                    ${forkBadge}
                                </div>
                            </div>
                        </div>

                        <!-- Description -->
                        <p class="text-light text-opacity-75 small mb-3 line-clamp-3 repo-desc-text" style="min-height: 48px; font-size: 0.85rem;">
                            ${escapeHtml(repo.description || "No description provided on GitHub.")}
                        </p>

                        <!-- Topics & Tech -->
                        <div class="mb-3 d-flex flex-wrap align-items-center">
                            <span class="badge bg-primary bg-opacity-25 text-light small me-2 mb-1">
                                <i class="bi bi-code-square me-1 text-primary"></i>${escapeHtml(repo.language)}
                            </span>
                            ${topicsHtml}
                        </div>
                    </div>

                    <!-- Footer Bar -->
                    <div class="border-top border-secondary border-opacity-25 pt-3 mt-2 d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center gap-3 text-muted small">
                            <span title="GitHub Stars"><i class="bi bi-star-fill text-warning me-1"></i>${repo.stars}</span>
                            <span title="GitHub Forks"><i class="bi bi-diagram-2 me-1"></i>${repo.forks}</span>
                        </div>

                        <button type="button" class="btn btn-sm btn-secondary-glass btn-edit-repo px-2 py-1" data-index="${index}" title="Edit details or polish with Gemini AI">
                            <i class="bi bi-sliders me-1"></i> Customize
                        </button>
                    </div>
                </div>
            `;
            repoCardsGrid.appendChild(cardCol);
        });

        attachCardEventListeners();
    }

    /** Attach listeners to individual card controls */
    function attachCardEventListeners() {
        // Individual checkbox change
        document.querySelectorAll(".repo-select-checkbox").forEach(cb => {
            cb.addEventListener("change", (e) => {
                const idx = parseInt(e.target.dataset.index, 10);
                if (fetchedRepositories[idx]) {
                    fetchedRepositories[idx].selected = e.target.checked;
                    updateSelectionState();
                    const card = e.target.closest(".glass-card");
                    if (card) {
                        card.classList.toggle("border-primary", e.target.checked);
                    }
                }
            });
        });

        // Customize / AI Polish button
        document.querySelectorAll(".btn-edit-repo").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.currentTarget.dataset.index, 10);
                openEditModal(idx);
            });
        });
    }

    /** Update 'Select All' and selection counter */
    function updateSelectionState() {
        const selectedCount = fetchedRepositories.filter(r => r.selected).length;

        if (selectedCountBadge) {
            selectedCountBadge.textContent = `${selectedCount} selected`;
        }

        if (btnImportSelected) {
            btnImportSelected.disabled = selectedCount === 0;
            const spanText = btnImportSelected.querySelector("span:not(.spinner-border)");
            if (spanText) {
                spanText.textContent = selectedCount > 0 ? `Import Selected (${selectedCount})` : "Import Selected";
            }
        }

        if (selectAllCheckbox) {
            selectAllCheckbox.checked = fetchedRepositories.length > 0 && selectedCount === fetchedRepositories.length;
            selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < fetchedRepositories.length;
        }
    }

    /** Toggle Select All */
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener("change", (e) => {
            const isChecked = e.target.checked;
            // Apply only to visible cards
            document.querySelectorAll(".repo-card-item").forEach(cardCol => {
                if (cardCol.style.display !== "none") {
                    const idx = parseInt(cardCol.dataset.index, 10);
                    if (fetchedRepositories[idx]) {
                        fetchedRepositories[idx].selected = isChecked;
                        const cb = cardCol.querySelector(".repo-select-checkbox");
                        if (cb) cb.checked = isChecked;
                        const card = cardCol.querySelector(".glass-card");
                        if (card) card.classList.toggle("border-primary", isChecked);
                    }
                }
            });
            updateSelectionState();
        });
    }

    /** Live search filter across cards */
    if (filterKeyword) {
        filterKeyword.addEventListener("input", (e) => {
            const term = e.target.value.toLowerCase().trim();
            document.querySelectorAll(".repo-card-item").forEach(col => {
                const name = col.dataset.name || "";
                const lang = col.dataset.language || "";
                const desc = col.dataset.description || "";
                const matches = name.includes(term) || lang.includes(term) || desc.includes(term);
                col.style.display = matches ? "" : "none";
            });
        });
    }

    /** Open Edit / AI Polish Modal */
    function openEditModal(index) {
        const repo = fetchedRepositories[index];
        if (!repo || !editModal) return;

        currentEditIndex = index;
        modalRepoIndex.value = index;
        modalProjectTitle.value = repo.title || repo.name;
        modalLiveUrl.value = repo.live_url || "";
        modalTechStack.value = repo.technologies || "";
        modalDescription.value = repo.description || repo.rawDescription || "";
        modalGithubUrl.value = repo.html_url || "";

        editModal.show();
    }

    /** Generate AI Polish description inside Modal */
    if (btnModalAiPolish) {
        btnModalAiPolish.addEventListener("click", async () => {
            if (currentEditIndex === null || !fetchedRepositories[currentEditIndex]) return;
            const repo = fetchedRepositories[currentEditIndex];

            btnModalAiPolish.disabled = true;
            aiPolishSpinner.classList.remove("d-none");
            aiPolishIcon.classList.add("d-none");

            try {
                const response = await fetch("/github/generate-description", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: JSON.stringify({
                        name: repo.name,
                        description: modalDescription.value.trim() || repo.rawDescription,
                        language: repo.language,
                        topics: repo.topics,
                    }),
                });

                const data = await response.json();
                if (response.ok && data.success) {
                    modalDescription.value = data.generated_description;
                } else {
                    alert(data.error || "Failed to generate AI description.");
                }
            } catch (err) {
                alert("Network error while communicating with AI service.");
            } finally {
                btnModalAiPolish.disabled = false;
                aiPolishSpinner.classList.add("d-none");
                aiPolishIcon.classList.remove("d-none");
            }
        });
    }

    /** Save modal changes back to card & state */
    if (btnSaveModalChanges) {
        btnSaveModalChanges.addEventListener("click", () => {
            if (currentEditIndex === null || !fetchedRepositories[currentEditIndex]) return;

            const repo = fetchedRepositories[currentEditIndex];
            repo.title = modalProjectTitle.value.trim() || repo.name;
            repo.live_url = modalLiveUrl.value.trim();
            repo.technologies = modalTechStack.value.trim();
            repo.description = modalDescription.value.trim();

            // Auto-select when customized
            repo.selected = true;

            // Update card DOM
            const cardCol = document.querySelector(`.repo-card-item[data-index="${currentEditIndex}"]`);
            if (cardCol) {
                const titleEl = cardCol.querySelector("h5");
                if (titleEl) titleEl.textContent = repo.title;
                const descEl = cardCol.querySelector(".repo-desc-text");
                if (descEl) descEl.textContent = repo.description || "No description provided.";
                const cb = cardCol.querySelector(".repo-select-checkbox");
                if (cb) cb.checked = true;
                const card = cardCol.querySelector(".glass-card");
                if (card) card.classList.add("border-primary");
            }

            updateSelectionState();
            if (editModal) editModal.hide();
        });
    }

    /** Import Selected Projects */
    if (btnImportSelected) {
        btnImportSelected.addEventListener("click", () => {
            executeImport(false);
        });
    }

    async function executeImport(confirmOverwrite = false) {
        const selected = fetchedRepositories.filter(r => r.selected);
        if (selected.length === 0) {
            showAlert("Please select at least one project to import.", "warning");
            return;
        }

        const portfolioId = portfolioSelect ? portfolioSelect.value : null;
        if (!portfolioId) {
            showAlert("Please select a target portfolio destination.", "warning");
            return;
        }

        const payload = {
            portfolio_id: parseInt(portfolioId, 10),
            confirm_overwrite: confirmOverwrite,
            projects: selected.map(r => ({
                title: r.title || r.name,
                description: r.description,
                technologies: r.technologies,
                github_url: r.html_url,
                live_url: r.live_url || null,
                stars_count: r.stars || 0,
                forks_count: r.forks || 0,
            })),
        };

        pendingImportPayload = payload;

        // UI Loading
        btnImportSelected.disabled = true;
        importBtnSpinner.classList.remove("d-none");
        importBtnIcon.classList.add("d-none");
        hideAlert();

        try {
            const response = await fetch("/github/import", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (response.status === 409) {
                // Conflict detected! Show modal for user confirmation
                if (conflictModalMessage && data.conflicts && data.conflicts.length > 0) {
                    const titles = data.conflicts.map(c => `<strong>"${escapeHtml(c.title)}"</strong>`).join(", ");
                    conflictModalMessage.innerHTML = `Project ${titles} already exists in this portfolio. Would you like to overwrite it with updated repository details?`;
                }
                if (conflictModal) conflictModal.show();
                return;
            }

            if (!response.ok || !data.success) {
                showAlert(data.error || "Failed to import selected projects.", "danger");
                return;
            }

            // Success!
            showAlert(data.message, "success");

            // Mark imported items
            selected.forEach(r => {
                r.already_imported = true;
            });
            renderRepositoryCards(fetchedRepositories);
            updateSelectionState();

            // Auto-redirect to portfolio preview after 1.2s
            setTimeout(() => {
                window.location.href = `/portfolios/${portfolioId}`;
            }, 1200);

        } catch (err) {
            showAlert("Network error while saving imported projects.", "danger");
        } finally {
            btnImportSelected.disabled = false;
            importBtnSpinner.classList.add("d-none");
            importBtnIcon.classList.remove("d-none");
        }
    }

    /** Conflict confirmation */
    if (btnConfirmOverwrite) {
        btnConfirmOverwrite.addEventListener("click", () => {
            if (conflictModal) conflictModal.hide();
            executeImport(true);
        });
    }

    // Trigger fetch on button click or Enter key in username input
    if (btnFetchRepos) {
        btnFetchRepos.addEventListener("click", handleFetchRepositories);
    }
    if (githubUsername) {
        githubUsername.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                handleFetchRepositories();
            }
        });

        // If default username already pre-filled, allow quick auto-fetch if user clicks
        if (githubUsername.value.trim() && !reposContainer.classList.contains("d-none")) {
            handleFetchRepositories();
        }
    }

    /** Helper: HTML Escaping */
    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
