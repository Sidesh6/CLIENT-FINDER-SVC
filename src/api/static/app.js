/**
 * CLIENT FINDER SVC - Multi-Source Opportunity Discovery & Proposal Application
 */

const STATE = {
  projects: [],
  applications: [],
  profile: null,
  activePitchAngle: "TECHNICAL_EXPERT",
  currentModalProject: null,
  lastGeneratedProposal: null,
  searchDebounceTimer: null,
};

// DOM Elements
const DOM = {
  // Stats
  statTotalLeads: document.getElementById("stat-total-leads"),
  statHighPriority: document.getElementById("stat-high-priority"),
  statWinRate: document.getElementById("stat-win-rate"),
  statRealizedRev: document.getElementById("stat-realized-rev"),
  resultsCount: document.getElementById("results-count"),
  appsCount: document.getElementById("apps-count"),

  // Navigation Tabs
  navTabs: document.querySelectorAll(".nav-tab"),
  tabPanes: document.querySelectorAll(".tab-pane"),

  // Filters
  searchInput: document.getElementById("search-input"),
  btnClearSearch: document.getElementById("btn-clear-search"),
  filterSource: document.getElementById("filter-source"),
  filterCategory: document.getElementById("filter-category"),
  filterStatus: document.getElementById("filter-status"),
  filterMinScore: document.getElementById("filter-min-score"),
  sliderVal: document.getElementById("slider-val"),
  btnRefresh: document.getElementById("btn-refresh"),
  btnRefreshApps: document.getElementById("btn-refresh-apps"),
  btnRefreshAnalytics: document.getElementById("btn-refresh-analytics"),

  // Containers
  opportunitiesContainer: document.getElementById("opportunities-container"),
  applicationsContainer: document.getElementById("applications-container"),
  funnelContainer: document.getElementById("funnel-container"),
  pitchAnglesContainer: document.getElementById("pitch-angles-container"),
  skillsAnalyticsContainer: document.getElementById("skills-analytics-container"),
  insightsContainer: document.getElementById("insights-container"),

  // Live Stream & Export
  wsStatusBadge: document.getElementById("ws-status-badge"),
  btnExportCsv: document.getElementById("btn-export-csv"),
  btnExportJson: document.getElementById("btn-export-json"),

  // Sources Modal & Custom Feed
  selectHarvestSource: document.getElementById("select-harvest-source"),
  btnTriggerCollector: document.getElementById("btn-trigger-collector"),
  btnOpenSources: document.getElementById("btn-open-sources"),
  btnCloseSources: document.getElementById("btn-close-sources"),
  sourcesModal: document.getElementById("sources-modal"),
  sourcesListContainer: document.getElementById("sources-list-container"),
  inputCustomFeedName: document.getElementById("input-custom-feed-name"),
  inputCustomFeedUrl: document.getElementById("input-custom-feed-url"),
  btnAddCustomFeed: document.getElementById("btn-add-custom-feed"),

  // Closing & Negotiation Studio Modal
  btnOpenNegotiation: document.getElementById("btn-open-negotiation"),
  btnCloseNegotiation: document.getElementById("btn-close-negotiation"),
  negotiationModal: document.getElementById("negotiation-modal"),
  subtabBtnObjection: document.getElementById("subtab-btn-objection"),
  subtabBtnFollowup: document.getElementById("subtab-btn-followup"),
  subtabBtnInterview: document.getElementById("subtab-btn-interview"),
  sectionObjection: document.getElementById("section-objection-studio"),
  sectionFollowup: document.getElementById("section-followup-studio"),
  sectionInterview: document.getElementById("section-interview-studio"),
  negObjectionType: document.getElementById("neg-objection-type"),
  negStrategy: document.getElementById("neg-strategy"),
  negProjectTitle: document.getElementById("neg-project-title"),
  negTargetRate: document.getElementById("neg-target-rate"),
  negClientBudget: document.getElementById("neg-client-budget"),
  btnGenerateNegotiation: document.getElementById("btn-generate-negotiation"),
  negOutputBox: document.getElementById("neg-output-box"),
  negResponseText: document.getElementById("neg-response-text"),
  negCounterOfferText: document.getElementById("neg-counter-offer-text"),
  btnCopyNegotiation: document.getElementById("btn-copy-negotiation"),
  followupStage: document.getElementById("followup-stage"),
  followupClientName: document.getElementById("followup-client-name"),
  btnGenerateFollowup: document.getElementById("btn-generate-followup"),
  followupOutputBox: document.getElementById("followup-output-box"),
  followupSubjectDisplay: document.getElementById("followup-subject-display"),
  followupBodyText: document.getElementById("followup-body-text"),
  followupTimingText: document.getElementById("followup-timing-text"),
  btnCopyFollowup: document.getElementById("btn-copy-followup"),
  interviewProjectTitle: document.getElementById("interview-project-title"),
  btnGenerateInterview: document.getElementById("btn-generate-interview"),
  interviewOutputBox: document.getElementById("interview-output-box"),
  interviewContentContainer: document.getElementById("interview-content-container"),

  // Profile Drawer
  btnOpenProfile: document.getElementById("btn-open-profile"),
  profileDrawer: document.getElementById("profile-drawer"),
  btnCloseDrawer: document.getElementById("btn-close-drawer"),
  profileName: document.getElementById("profile-name"),
  profileTitle: document.getElementById("profile-title"),
  profileTargetRate: document.getElementById("profile-target-rate"),
  profileMinRate: document.getElementById("profile-min-rate"),
  profileBio: document.getElementById("profile-bio"),
  profileSkillsList: document.getElementById("profile-skills-list"),
  profilePortfolioList: document.getElementById("profile-portfolio-list"),
  btnSaveProfile: document.getElementById("btn-save-profile"),

  // Proposal Modal
  proposalModal: document.getElementById("proposal-modal"),
  modalProjectTitle: document.getElementById("modal-project-title"),
  pitchChips: document.querySelectorAll(".pitch-chip"),
  proposalTone: document.getElementById("proposal-tone"),
  chkIncludePricing: document.getElementById("chk-include-pricing"),
  customInstructions: document.getElementById("custom-instructions"),
  btnGenerateProposal: document.getElementById("btn-generate-proposal"),
  proposalOutputContainer: document.getElementById("proposal-output-container"),
  proposalQualityBadge: document.getElementById("proposal-quality-badge"),
  proposalSubjectBox: document.getElementById("proposal-subject-box"),
  proposalTextBox: document.getElementById("proposal-text-box"),
  btnCopyProposal: document.getElementById("btn-copy-proposal"),
  btnTrackApplication: document.getElementById("btn-track-application"),
  btnCloseModal: document.getElementById("btn-close-modal"),

  // Toast
  toastContainer: document.getElementById("toast-container"),
};

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadProfile();
  loadStats();
  fetchOpportunities();
  initWebSocket();
});

function initEventListeners() {
  // Tab Switching
  DOM.navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      DOM.navTabs.forEach((t) => t.classList.remove("active"));
      DOM.tabPanes.forEach((p) => {
        p.classList.remove("active");
        p.style.display = "none";
      });

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
        targetPane.style.display = "block";
      }

      if (targetId === "tab-pipeline") fetchApplications();
      if (targetId === "tab-analytics") fetchAnalytics();
    });
  });

  // Filters & Search
  DOM.searchInput.addEventListener("input", (e) => {
    DOM.btnClearSearch.style.display = e.target.value ? "block" : "none";
    clearTimeout(STATE.searchDebounceTimer);
    STATE.searchDebounceTimer = setTimeout(fetchOpportunities, 300);
  });

  DOM.btnClearSearch.addEventListener("click", () => {
    DOM.searchInput.value = "";
    DOM.btnClearSearch.style.display = "none";
    fetchOpportunities();
  });

  if (DOM.filterSource) DOM.filterSource.addEventListener("change", fetchOpportunities);
  DOM.filterCategory.addEventListener("change", fetchOpportunities);
  DOM.filterStatus.addEventListener("change", fetchOpportunities);

  DOM.filterMinScore.addEventListener("input", (e) => {
    DOM.sliderVal.textContent = e.target.value;
  });
  DOM.filterMinScore.addEventListener("change", fetchOpportunities);

  DOM.btnRefresh.addEventListener("click", () => {
    fetchOpportunities();
    loadStats();
  });

  // Collector Harvest & Sources Modal
  DOM.btnTriggerCollector.addEventListener("click", triggerLiveHarvest);
  if (DOM.btnOpenSources) DOM.btnOpenSources.addEventListener("click", openSourcesModal);
  if (DOM.btnCloseSources) DOM.btnCloseSources.addEventListener("click", closeSourcesModal);
  if (DOM.btnAddCustomFeed) DOM.btnAddCustomFeed.addEventListener("click", handleAddCustomFeed);

  // Data Export Buttons
  if (DOM.btnExportCsv) {
    DOM.btnExportCsv.addEventListener("click", () => {
      window.open("/api/export/csv", "_blank");
      showToast("Downloading CSV spreadsheet...", "info");
    });
  }
  if (DOM.btnExportJson) {
    DOM.btnExportJson.addEventListener("click", () => {
      window.open("/api/export/json", "_blank");
      showToast("Downloading JSON export...", "info");
    });
  }

  // Profile Drawer
  DOM.btnOpenProfile.addEventListener("click", openProfileDrawer);
  DOM.btnCloseDrawer.addEventListener("click", closeProfileDrawer);
  DOM.btnSaveProfile.addEventListener("click", saveProfileChanges);

  // Proposal Modal
  DOM.btnCloseModal.addEventListener("click", closeModal);
  DOM.pitchChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      DOM.pitchChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      STATE.activePitchAngle = chip.getAttribute("data-angle");
    });
  });

  // Proposal Generation
  DOM.btnGenerateProposal.addEventListener("click", generateProposal);
  DOM.btnCopyProposal.addEventListener("click", copyProposalToClipboard);
  DOM.btnCloseModal.addEventListener("click", closeModal);

  // Closing & Negotiation Studio
  if (DOM.btnOpenNegotiation) DOM.btnOpenNegotiation.addEventListener("click", openNegotiationModal);
  if (DOM.btnCloseNegotiation) DOM.btnCloseNegotiation.addEventListener("click", closeNegotiationModal);
  if (DOM.subtabBtnObjection) DOM.subtabBtnObjection.addEventListener("click", () => switchNegotiationSubtab("objection"));
  if (DOM.subtabBtnFollowup) DOM.subtabBtnFollowup.addEventListener("click", () => switchNegotiationSubtab("followup"));
  if (DOM.subtabBtnInterview) DOM.subtabBtnInterview.addEventListener("click", () => switchNegotiationSubtab("interview"));
  if (DOM.btnGenerateNegotiation) DOM.btnGenerateNegotiation.addEventListener("click", handleGenerateNegotiation);
  if (DOM.btnGenerateFollowup) DOM.btnGenerateFollowup.addEventListener("click", handleGenerateFollowup);
  if (DOM.btnGenerateInterview) DOM.btnGenerateInterview.addEventListener("click", handleGenerateInterview);
  if (DOM.btnCopyNegotiation) DOM.btnCopyNegotiation.addEventListener("click", copyNegotiationResponse);
  if (DOM.btnCopyFollowup) DOM.btnCopyFollowup.addEventListener("click", copyFollowupResponse);
}

// 1. Data Fetching
async function loadStats() {
  try {
    const res = await fetch("/api/opportunities/stats");
    const data = await res.json();
    DOM.statTotalLeads.textContent = data.total_opportunities || 0;
    DOM.statHighPriority.textContent = data.tier_distribution?.EXCELLENT || 0;
    DOM.statAvgScore.textContent = (data.average_score || 0).toFixed(1);
    if (STATE.profile) {
      DOM.statDevRate.textContent = `$${STATE.profile.target_hourly_rate || 95}/hr`;
    }
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    STATE.profile = await res.json();
    if (STATE.profile && STATE.profile.target_hourly_rate) {
      DOM.statDevRate.textContent = `$${STATE.profile.target_hourly_rate}/hr`;
    }
  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function fetchOpportunities() {
  const query = DOM.searchInput.value.trim();
  const source = DOM.filterSource ? DOM.filterSource.value : "";
  const category = DOM.filterCategory.value;
  const status = DOM.filterStatus.value;
  const minScore = DOM.filterMinScore.value;

  DOM.opportunitiesContainer.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Scanning opportunities and calculating real-time match scores...</p>
    </div>
  `;

  try {
    let url = `/api/projects?limit=50&min_score=${minScore}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;

    if (query) {
      url = `/api/search?q=${encodeURIComponent(query)}&limit=50`;
    }

    const res = await fetch(url);
    const data = await res.json();
    let projects = data.items || data || [];

    // Client-side source filter if applicable
    if (source) {
      projects = projects.filter((p) => (p.source || "").toLowerCase() === source.toLowerCase());
    }

    STATE.projects = projects;
    renderOpportunities(STATE.projects);
  } catch (err) {
    DOM.opportunitiesContainer.innerHTML = `
      <div class="empty-state">
        <p>⚠️ Failed to load opportunities. Ensure server is running.</p>
      </div>
    `;
  }
}

function renderOpportunities(projects) {
  DOM.resultsCount.textContent = projects.length;

  if (projects.length === 0) {
    DOM.opportunitiesContainer.innerHTML = `
      <div class="empty-state">
        <div style="font-size: 3rem; margin-bottom: 12px;">🔍</div>
        <h3>No matching opportunities found</h3>
        <p>Try adjusting your search criteria, source filter, or trigger a live feed harvest.</p>
        <button class="btn btn-secondary" style="margin-top: 16px;" onclick="resetFilters()">Reset Filters</button>
      </div>
    `;
    return;
  }

  DOM.opportunitiesContainer.innerHTML = projects
    .map((p) => {
      const score = p.score || 0;
      let badgeClass = "score-low";
      if (score >= 80) badgeClass = "score-high";
      else if (score >= 60) badgeClass = "score-med";

      const budgetDisplay = p.budget ? `${p.currency} ${p.budget.toLocaleString()}` : "Budget Unstated";
      const postedTime = p.posted_at ? new Date(p.posted_at).toLocaleDateString() : "Recent";
      const skillsHtml = (p.skills || [])
        .slice(0, 5)
        .map((s) => `<span class="skill-tag">${escapeHtml(s)}</span>`)
        .join("");

      return `
      <article class="opp-card">
        <div class="opp-card-top">
          <span class="source-badge">🔗 ${escapeHtml(p.source)}</span>
          <div class="score-badge ${badgeClass}">${score.toFixed(1)} Match</div>
        </div>
      </article>
    `;
    })
    .join("");
}

// 2. Applications Pipeline View
async function fetchApplications() {
  DOM.applicationsContainer.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading application pipeline...</p>
    </div>
  `;

        <h3 class="opp-title">
          <a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(p.title)}</a>
        </h3>

        <div class="opp-meta">
          <span class="meta-item">💰 ${budgetDisplay}</span>
          <span class="meta-item">📅 ${postedTime}</span>
          ${p.client_name ? `<span class="meta-item">👤 ${escapeHtml(p.client_name)}</span>` : ""}
        </div>

        <h4 class="app-title">${escapeHtml(a.project_title || "Project Opportunity #" + a.project_id)}</h4>

        <div class="skills-wrap">${skillsHtml}</div>

        <div class="opp-card-footer">
          <div class="status-indicator">
            <span class="status-dot status-${p.status}"></span>
            <span class="status-text">${p.status}</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-sm btn-primary" onclick="openProposalModal(${p.id})">
              ✨ Craft Proposal
            </button>
            <a href="${escapeHtml(p.source_url)}" target="_blank" class="btn btn-sm btn-ghost">
              Source ↗
            </a>
          </div>
        </div>
      </article>
    `;
    })
    .join("");
}

// 2. Multi-Source Collector Actions
async function triggerLiveHarvest() {
  const chosenSource = DOM.selectHarvestSource ? DOM.selectHarvestSource.value : "all";
  DOM.btnTriggerCollector.disabled = true;
  DOM.btnTriggerCollector.innerHTML = `<span>⏳ Harvesting...</span>`;
  showToast(`Harvesting live opportunities from ${chosenSource}...`, "info");

  try {
    const res = await fetch(`/api/collectors/collect?collector_name=${encodeURIComponent(chosenSource)}&limit=10`, {
      method: "POST",
    });
    const data = await res.json();
    showToast(data.message || `Discovered ${data.collected_count} opportunities!`, "success");
    fetchOpportunities();
    loadStats();
  } catch (err) {
    showToast("Error triggering feed harvester", "info");
  } finally {
    DOM.btnTriggerCollector.disabled = false;
    DOM.btnTriggerCollector.innerHTML = `<span class="btn-icon">⚡</span><span>Harvest Leads</span>`;
  }
}

async function openSourcesModal() {
  if (!DOM.sourcesModal) return;
  DOM.sourcesModal.style.display = "flex";
  loadSourcesHealth();
}

function closeSourcesModal() {
  if (DOM.sourcesModal) DOM.sourcesModal.style.display = "none";
}

async function loadSourcesHealth() {
  if (!DOM.sourcesListContainer) return;
  DOM.sourcesListContainer.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Loading source health...</p></div>`;

  try {
    const res = await fetch("/api/collectors/health");
    const sources = await res.json();

    DOM.sourcesListContainer.innerHTML = sources
      .map(
        (s) => `
      <div class="source-item-card">
        <div>
          <div class="source-name-header">
            <span>${escapeHtml(s.source_name)}</span>
            ${s.circuit_broken ? `<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: var(--accent-rose);">⚠️ Circuit Tripped</span>` : s.enabled ? `<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">Active</span>` : `<span class="badge" style="background: rgba(148, 163, 184, 0.2); color: var(--text-secondary);">Disabled</span>`}
          </div>
          <div class="source-meta-row">
            <span>Success Rate: <strong>${s.success_rate}%</strong></span>
            <span>Items Harvested: <strong>${s.total_items_collected}</strong></span>
            ${s.last_scrape_at ? `<span>Last Scrape: ${new Date(s.last_scrape_at).toLocaleTimeString()}</span>` : ""}
          </div>
          ${s.last_error ? `<div style="font-size: 11px; color: var(--accent-rose); margin-top: 4px;">Last Error: ${escapeHtml(s.last_error)}</div>` : ""}
        </div>
        <div style="display: flex; gap: 8px;">
          ${s.circuit_broken ? `<button class="btn btn-sm btn-accent" onclick="resetCircuit('${escapeHtml(s.source_name)}')">Reset Circuit</button>` : ""}
          <button class="btn btn-sm ${s.enabled ? "btn-secondary" : "btn-primary"}" onclick="toggleSource('${escapeHtml(s.source_name)}')">
            ${s.enabled ? "Disable" : "Enable"}
          </button>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    DOM.sourcesListContainer.innerHTML = `<p style="color: var(--accent-rose);">Failed to load sources health.</p>`;
  }
}

window.toggleSource = async function (sourceName) {
  try {
    const res = await fetch(`/api/collectors/${encodeURIComponent(sourceName)}/toggle`, { method: "POST" });
    if (res.ok) {
      showToast(`Toggled ${sourceName}`, "success");
      loadSourcesHealth();
    }
  } catch (err) {
    showToast("Failed to toggle source", "info");
  }
};

window.resetCircuit = async function (sourceName) {
  try {
    const res = await fetch(`/api/collectors/${encodeURIComponent(sourceName)}/reset-circuit`, { method: "POST" });
    if (res.ok) {
      showToast(`Reset circuit breaker for ${sourceName}`, "success");
      loadSourcesHealth();
    }
  } catch (err) {
    showToast("Failed to reset circuit breaker", "info");
  }
};

// 3. Proposal Modal Actions
window.openProposalModal = function (projectId) {
  const project = STATE.projects.find((p) => p.id === projectId);
  if (!project) return;

  STATE.currentModalProject = project;
  DOM.modalProjectTitle.textContent = project.title;
  DOM.proposalOutputContainer.style.display = "none";
  DOM.proposalModal.style.display = "flex";
};

async function generateProposal() {
  if (!STATE.currentModalProject) return;

  DOM.btnGenerateProposal.disabled = true;
  DOM.btnGenerateProposal.innerHTML = `<span>⚡ Generating Proposal with Portfolio RAG...</span>`;

  const payload = {
    project_id: STATE.currentModalProject.id,
    pitch_angle: STATE.activePitchAngle,
    tone: DOM.proposalTone.value,
    include_pricing: DOM.chkIncludePricing.checked,
    custom_instructions: DOM.customInstructions.value.trim() || null,
  };

  try {
    const res = await fetch("/api/proposals/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    STATE.lastGeneratedProposal = result;
    displayProposalResult(result);
  } catch (err) {
    showToast("Error generating proposal", "info");
  } finally {
    DOM.btnGenerateProposal.disabled = false;
    DOM.btnGenerateProposal.innerHTML = `<span>✨ Synthesize Customized Proposal</span>`;
  }
}

function displayProposalResult(result) {
  DOM.proposalQualityBadge.textContent = `${result.quality_score}/100`;
  DOM.proposalSubjectBox.textContent = `Subject: ${result.subject_line}`;
  DOM.proposalTextBox.textContent = result.full_proposal_text;
  DOM.proposalOutputContainer.style.display = "block";
}

function copyProposalToClipboard() {
  const fullText = `${DOM.proposalSubjectBox.textContent}\n\n${DOM.proposalTextBox.textContent}`;
  navigator.clipboard.writeText(fullText).then(() => {
    showToast("Proposal copied to clipboard! 📋", "success");
  });
}

async function trackCurrentProposal() {
  if (!STATE.currentModalProject || !STATE.lastGeneratedProposal) return;

  try {
    const payload = {
      project_id: STATE.currentModalProject.id,
      status: "APPLIED",
      proposed_budget: STATE.lastGeneratedProposal.suggested_rate || 0,
      currency: "USD",
      proposal_text: STATE.lastGeneratedProposal.full_proposal_text,
      pitch_angle: STATE.lastGeneratedProposal.pitch_angle,
      notes: `Proposal generated with quality score ${STATE.lastGeneratedProposal.quality_score}`,
    };

    const res = await fetch("/api/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      showToast("Application tracked into live pipeline! 🚀", "success");
      closeModal();
      loadStats();
    }
  } catch (err) {
    showToast("Error tracking application", "info");
  }
}

function closeModal() {
  DOM.proposalModal.style.display = "none";
}

// 4. Profile Drawer Actions
function openProfileDrawer() {
  if (!STATE.profile) return;
  DOM.profileName.value = STATE.profile.name;
  DOM.profileTitle.value = STATE.profile.title;
  DOM.profileTargetRate.value = STATE.profile.target_hourly_rate;
  DOM.profileMinRate.value = STATE.profile.minimum_hourly_rate;
  DOM.profileBio.value = STATE.profile.bio || "";

  DOM.profileSkillsList.innerHTML = (STATE.profile.skills || [])
    .map(
      (s) => `
      <div class="skill-row">
        <span style="flex: 1; font-weight: 500;">${escapeHtml(s.name)}</span>
        <span class="score-val-badge">${s.proficiency}/10</span>
      </div>
    `
    )
    .join("");

  if (DOM.profilePortfolioList) {
    DOM.profilePortfolioList.innerHTML = (STATE.profile.portfolio || [])
      .map(
        (p) => `
      <div class="portfolio-card">
        <div class="portfolio-card-title">${escapeHtml(p.title)}</div>
        <div class="portfolio-card-desc">${escapeHtml(p.description)}</div>
        <div class="portfolio-tags">
          ${(p.technologies || []).map((t) => `<span class="skill-tag">${escapeHtml(t)}</span>`).join("")}
        </div>
      </div>
    `
      )
      .join("");
  }

  DOM.profileDrawer.style.display = "flex";
}

function closeProfileDrawer() {
  DOM.profileDrawer.style.display = "none";
}

async function saveProfileChanges() {
  const payload = {
    name: DOM.profileName.value,
    title: DOM.profileTitle.value,
    target_hourly_rate: parseFloat(DOM.profileTargetRate.value),
    minimum_hourly_rate: parseFloat(DOM.profileMinRate.value),
    bio: DOM.profileBio.value,
  };

  try {
    const res = await fetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    STATE.profile = await res.json();
    showToast("Profile updated & scores recalculated!", "success");
    closeProfileDrawer();
    fetchOpportunities();
    loadStats();
  } catch (err) {
    showToast("Error updating profile", "info");
  }
}

// Utilities
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  DOM.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.resetFilters = function () {
  DOM.searchInput.value = "";
  if (DOM.filterSource) DOM.filterSource.value = "";
  DOM.filterCategory.value = "";
  DOM.filterStatus.value = "";
  DOM.filterMinScore.value = "0";
  DOM.sliderVal.textContent = "0";
  fetchOpportunities();
};

// Custom Feed Registration Handler
async function handleAddCustomFeed() {
  const name = DOM.inputCustomFeedName ? DOM.inputCustomFeedName.value.trim() : "";
  const feedUrl = DOM.inputCustomFeedUrl ? DOM.inputCustomFeedUrl.value.trim() : "";

  if (!name || !feedUrl) {
    showToast("Please provide both feed name and valid URL", "info");
    return;
  }

  DOM.btnAddCustomFeed.disabled = true;
  DOM.btnAddCustomFeed.textContent = "Verifying XML...";

  try {
    const res = await fetch("/api/collectors/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, feed_url: feedUrl, enabled: true }),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Failed to register feed");
    }

    const data = await res.json();
    showToast(data.message || `Feed '${name}' verified & registered!`, "success");
    DOM.inputCustomFeedName.value = "";
    DOM.inputCustomFeedUrl.value = "";
    loadSourcesHealth();
  } catch (err) {
    showToast(err.message, "info");
  } finally {
    DOM.btnAddCustomFeed.disabled = false;
    DOM.btnAddCustomFeed.textContent = "Verify & Register Feed";
  }
}

// Real-Time WebSocket Streaming Client
let wsConnection = null;

function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/api/ws/events`;

  try {
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onopen = () => {
      if (DOM.wsStatusBadge) {
        DOM.wsStatusBadge.textContent = "🟢 LIVE";
        DOM.wsStatusBadge.style.display = "inline-block";
      }
    };

    wsConnection.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        handleLiveEvent(payload);
      } catch (err) {
        console.warn("Invalid WebSocket message payload:", evt.data);
      }
    };

    wsConnection.onclose = () => {
      if (DOM.wsStatusBadge) {
        DOM.wsStatusBadge.textContent = "🟡 CONNECTING...";
      }
      // Attempt reconnection after 5s
      setTimeout(initWebSocket, 5000);
    };

    wsConnection.onerror = () => {
      if (wsConnection) wsConnection.close();
    };
  } catch (err) {
    console.warn("WebSocket initialization error:", err);
  }
}

function handleLiveEvent(event) {
  const type = event.event_type;
  const data = event.data || {};

  if (type === "NEW_OPPORTUNITY") {
    showToast(`⚡ New Opportunity Discovered: ${data.title} (${data.score ? data.score.toFixed(0) : "New"})`, "success");
    fetchOpportunities();
    loadStats();
  } else if (type === "CYCLE_COMPLETED") {
    showToast(`🔄 Harvest Cycle Completed: Found ${data.collected_count} leads across ${data.sources?.length || 0} sources`, "info");
    loadStats();
  } else if (type === "APPLICATION_UPDATED") {
    fetchApplications();
    fetchAnalytics();
  } else if (type === "COLLECTOR_STATUS_CHANGED") {
    loadSourcesHealth();
  }
}

// ----------------------------------------------------
// Closing & Negotiation Studio Logic
// ----------------------------------------------------
function openNegotiationModal() {
  if (DOM.negotiationModal) {
    DOM.negotiationModal.style.display = "flex";
    if (STATE.profile && DOM.negTargetRate) {
      DOM.negTargetRate.value = STATE.profile.target_hourly_rate || 95;
    }
  }
}

function closeNegotiationModal() {
  if (DOM.negotiationModal) {
    DOM.negotiationModal.style.display = "none";
  }
}

function switchNegotiationSubtab(tabName) {
  const tabs = [
    { name: "objection", btn: DOM.subtabBtnObjection, sec: DOM.sectionObjection },
    { name: "followup", btn: DOM.subtabBtnFollowup, sec: DOM.sectionFollowup },
    { name: "interview", btn: DOM.subtabBtnInterview, sec: DOM.sectionInterview },
  ];

  tabs.forEach((t) => {
    if (t.name === tabName) {
      t.btn.classList.add("btn-primary");
      t.btn.classList.remove("btn-ghost");
      t.sec.style.display = "block";
    } else {
      t.btn.classList.remove("btn-primary");
      t.btn.classList.add("btn-ghost");
      t.sec.style.display = "none";
    }
  });
}

async function handleGenerateNegotiation() {
  const payload = {
    project_title: DOM.negProjectTitle ? DOM.negProjectTitle.value || "Senior Engineering Lead" : "Senior Engineering Lead",
    project_description: "Project scope and deliverables",
    objection_type: DOM.negObjectionType ? DOM.negObjectionType.value : "RATE_TOO_HIGH",
    strategy: DOM.negStrategy ? DOM.negStrategy.value : "VALUE_ANCHORING",
    target_hourly_rate: DOM.negTargetRate ? parseFloat(DOM.negTargetRate.value) || 95 : 95,
    client_budget: DOM.negClientBudget && DOM.negClientBudget.value ? parseFloat(DOM.negClientBudget.value) : null,
  };

  DOM.btnGenerateNegotiation.disabled = true;
  DOM.btnGenerateNegotiation.textContent = "Analyzing Objection Strategy...";

  try {
    const res = await fetch("/api/closing/negotiate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (DOM.negResponseText) DOM.negResponseText.textContent = data.recommended_response;
    if (DOM.negCounterOfferText) DOM.negCounterOfferText.textContent = `💡 Alternative Offer: ${data.alternative_counter_offer}`;
    if (DOM.negOutputBox) DOM.negOutputBox.style.display = "block";
    showToast("Strategic response script synthesized!", "success");
  } catch (err) {
    showToast("Failed to generate negotiation script", "info");
  } finally {
    DOM.btnGenerateNegotiation.disabled = false;
    DOM.btnGenerateNegotiation.textContent = "✨ Generate Strategic Response Script";
  }
}

async function handleGenerateFollowup() {
  const payload = {
    project_title: DOM.negProjectTitle ? DOM.negProjectTitle.value || "Software Development Project" : "Software Development Project",
    project_description: "Project architecture and milestone delivery",
    client_name: DOM.followupClientName ? DOM.followupClientName.value || null : null,
    stage: DOM.followupStage ? DOM.followupStage.value : "DAY_3_CHECKIN",
  };

  DOM.btnGenerateFollowup.disabled = true;
  DOM.btnGenerateFollowup.textContent = "Drafting Follow-up...";

  try {
    const res = await fetch("/api/closing/followup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (DOM.followupSubjectDisplay) DOM.followupSubjectDisplay.textContent = `Subject: ${data.subject_line}`;
    if (DOM.followupBodyText) DOM.followupBodyText.textContent = data.body_text;
    if (DOM.followupTimingText) DOM.followupTimingText.textContent = `📅 Best Timing: ${data.recommended_send_timing}`;
    if (DOM.followupOutputBox) DOM.followupOutputBox.style.display = "block";
    showToast("Follow-up draft ready!", "success");
  } catch (err) {
    showToast("Failed to generate follow-up", "info");
  } finally {
    DOM.btnGenerateFollowup.disabled = false;
    DOM.btnGenerateFollowup.textContent = "✨ Draft Follow-Up Message";
  }
}

async function handleGenerateInterview() {
  const title = DOM.interviewProjectTitle ? DOM.interviewProjectTitle.value.trim() || "Full-Stack AI Architecture Lead" : "Full-Stack AI Architecture Lead";

  DOM.btnGenerateInterview.disabled = true;
  DOM.btnGenerateInterview.textContent = "Preparing Architectural Cheatsheet...";

  try {
    const res = await fetch("/api/closing/interview-prep", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_title: title,
        project_description: "Core distributed microservice architecture and data pipelines",
        skills: ["Python", "FastAPI", "PostgreSQL", "RAG"],
      }),
    });

    const data = await res.json();
    if (DOM.interviewContentContainer) {
      let html = `<div style="margin-bottom: 12px; font-weight: 600; color: var(--accent-indigo);">📌 ${escapeHtml(data.architecture_overview)}</div>`;
      html += `<div style="font-weight: 600; margin-bottom: 8px; color: var(--accent-emerald);">🎯 Anticipated Technical Questions & Model Answers:</div>`;

      data.likely_questions.forEach((q, idx) => {
        html += `
          <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 10px; margin-bottom: 8px;">
            <div style="font-weight: 600; font-size: 13px; color: var(--text-primary); margin-bottom: 4px;">Q${idx+1}: ${escapeHtml(q.question)}</div>
            <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">${escapeHtml(q.model_answer)}</div>
          </div>
        `;
      });

      html += `<div style="font-weight: 600; margin: 12px 0 6px 0; color: var(--accent-purple);">❓ Strategic Reverse Questions to Ask Client:</div>`;
      html += `<ul style="padding-left: 20px; font-size: 12px; color: var(--text-secondary);">`;
      data.reverse_questions_to_ask_client.forEach((rq) => {
        html += `<li>${escapeHtml(rq)}</li>`;
      });
      html += `</ul>`;

      DOM.interviewContentContainer.innerHTML = html;
    }
    if (DOM.interviewOutputBox) DOM.interviewOutputBox.style.display = "block";
    showToast("Interview prep guide generated!", "success");
  } catch (err) {
    showToast("Failed to generate interview prep", "info");
  } finally {
    DOM.btnGenerateInterview.disabled = false;
    DOM.btnGenerateInterview.textContent = "✨ Generate Interview Cheatsheet";
  }
}

function copyNegotiationResponse() {
  if (DOM.negResponseText) {
    navigator.clipboard.writeText(DOM.negResponseText.textContent);
    showToast("Negotiation script copied to clipboard!", "success");
  }
}

function copyFollowupResponse() {
  if (DOM.followupBodyText) {
    navigator.clipboard.writeText(DOM.followupBodyText.textContent);
    showToast("Follow-up message copied to clipboard!", "success");
  }
}
