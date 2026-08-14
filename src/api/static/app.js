/**
 * CLIENT FINDER SVC - Interactive Dashboard Application
 */

const STATE = {
  projects: [],
  profile: null,
  activePitchAngle: "TECHNICAL_EXPERT",
  currentModalProject: null,
  searchDebounceTimer: null,
};

// DOM Elements
const DOM = {
  // Stats
  statTotalLeads: document.getElementById("stat-total-leads"),
  statHighPriority: document.getElementById("stat-high-priority"),
  statAvgScore: document.getElementById("stat-avg-score"),
  statDevRate: document.getElementById("stat-dev-rate"),
  resultsCount: document.getElementById("results-count"),

  // Filters
  searchInput: document.getElementById("search-input"),
  btnClearSearch: document.getElementById("btn-clear-search"),
  filterCategory: document.getElementById("filter-category"),
  filterStatus: document.getElementById("filter-status"),
  filterMinScore: document.getElementById("filter-min-score"),
  sliderVal: document.getElementById("slider-val"),
  btnRefresh: document.getElementById("btn-refresh"),

  // Containers
  opportunitiesContainer: document.getElementById("opportunities-container"),

  // Buttons
  btnTriggerCollector: document.getElementById("btn-trigger-collector"),
  btnOpenProfile: document.getElementById("btn-open-profile"),

  // Modal
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
  btnCloseModal: document.getElementById("btn-close-modal"),

  // Drawer
  profileDrawer: document.getElementById("profile-drawer"),
  btnCloseDrawer: document.getElementById("btn-close-drawer"),
  profileName: document.getElementById("profile-name"),
  profileTitle: document.getElementById("profile-title"),
  profileTargetRate: document.getElementById("profile-target-rate"),
  profileMinRate: document.getElementById("profile-min-rate"),
  profileBio: document.getElementById("profile-bio"),
  profileSkillsList: document.getElementById("profile-skills-list"),
  btnSaveProfile: document.getElementById("btn-save-profile"),

  // Toast
  toastContainer: document.getElementById("toast-container"),
};

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadProfile();
  loadStats();
  fetchOpportunities();
});

function initEventListeners() {
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

  DOM.filterCategory.addEventListener("change", fetchOpportunities);
  DOM.filterStatus.addEventListener("change", fetchOpportunities);

  DOM.filterMinScore.addEventListener("input", (e) => {
    DOM.sliderVal.textContent = e.target.value;
  });
  DOM.filterMinScore.addEventListener("change", fetchOpportunities);

  DOM.btnRefresh.addEventListener("click", () => {
    fetchOpportunities();
    loadStats();
    showToast("Feed refreshed", "info");
  });

  // Collector Trigger
  DOM.btnTriggerCollector.addEventListener("click", triggerLiveHarvest);

  // Pitch Angle Chips
  DOM.pitchChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      DOM.pitchChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      STATE.activePitchAngle = chip.dataset.angle;
    });
  });

  // Proposal Generation
  DOM.btnGenerateProposal.addEventListener("click", executeProposalGeneration);
  DOM.btnCopyProposal.addEventListener("click", copyProposalToClipboard);
  DOM.btnCloseModal.addEventListener("click", closeModal);

  // Profile Drawer
  DOM.btnOpenProfile.addEventListener("click", openProfileDrawer);
  DOM.btnCloseDrawer.addEventListener("click", closeProfileDrawer);
  DOM.btnSaveProfile.addEventListener("click", saveProfileChanges);
}

// API Functions
async function loadStats() {
  try {
    const res = await fetch("/api/opportunities/stats");
    if (!res.ok) return;
    const data = await res.json();
    DOM.statTotalLeads.textContent = data.total_projects;
    DOM.statHighPriority.textContent = data.high_priority_count;
    DOM.statAvgScore.textContent = data.average_score;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    if (!res.ok) return;
    STATE.profile = await res.json();
    DOM.statDevRate.textContent = `$${STATE.profile.target_hourly_rate}/hr`;
  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function fetchOpportunities() {
  const query = DOM.searchInput.value.trim();
  const category = DOM.filterCategory.value;
  const status = DOM.filterStatus.value;
  const minScore = DOM.filterMinScore.value;

  let url = `/api/projects?limit=50`;
  if (category) url += `&category=${encodeURIComponent(category)}`;
  if (status) url += `&status=${encodeURIComponent(status)}`;
  if (minScore > 0) url += `&min_score=${minScore}`;

  if (query) {
    url = `/api/search?q=${encodeURIComponent(query)}&limit=50`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (minScore > 0) url += `&min_score=${minScore}`;
  }

  try {
    DOM.opportunitiesContainer.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Scanning opportunities and calculating real-time match scores...</p>
      </div>
    `;

    const res = await fetch(url);
    const data = await res.json();
    STATE.projects = data.items || [];
    DOM.resultsCount.textContent = STATE.projects.length;
    renderOpportunities(STATE.projects);
  } catch (err) {
    console.error("Failed to fetch opportunities:", err);
    DOM.opportunitiesContainer.innerHTML = `
      <div class="empty-state">
        <p>⚠️ Unable to reach service API. Please check your server connection.</p>
      </div>
    `;
  }
}

function renderOpportunities(projects) {
  if (!projects.length) {
    DOM.opportunitiesContainer.innerHTML = `
      <div class="empty-state">
        <p>🔍 No opportunities match your active filters.</p>
        <button class="btn btn-sm btn-primary" onclick="resetFilters()" style="margin-top: 12px;">Reset Filters</button>
      </div>
    `;
    return;
  }

  DOM.opportunitiesContainer.innerHTML = projects.map(renderCardHtml).join("");
}

function renderCardHtml(p) {
  const score = p.score != null ? p.score.toFixed(1) : "N/A";
  let scoreClass = "score-low";
  if (p.score >= 75) scoreClass = "score-high";
  else if (p.score >= 50) scoreClass = "score-med";

  const skillsHtml = (p.skills || [])
    .slice(0, 6)
    .map((s) => `<span class="skill-pill">${escapeHtml(s)}</span>`)
    .join("");

  const budgetDisplay = p.budget
    ? `$${p.budget.toLocaleString()} ${escapeHtml(p.currency || "USD")}`
    : "Unstated Budget";

  const breakdown = p.score_breakdown || {};
  const skillScore = breakdown.skill_score != null ? breakdown.skill_score.toFixed(0) : "-";
  const budgetScore = breakdown.budget_score != null ? breakdown.budget_score.toFixed(0) : "-";
  const winProb = breakdown.win_probability != null ? breakdown.win_probability.toFixed(0) : "-";

  return `
    <div class="opp-card" data-id="${p.id}">
      <div>
        <div class="opp-card-top">
          <h3 class="opp-title">
            <a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener noreferrer">
              ${escapeHtml(p.title)} ↗
            </a>
          </h3>
          <div class="score-badge ${scoreClass}">
            <span>★</span> ${score}
          </div>
        </div>

        <div class="opp-meta">
          <span class="meta-tag">🏢 ${escapeHtml(p.source)}</span>
          <span class="meta-tag">🏷️ ${escapeHtml(p.category || "General")}</span>
          <span class="meta-tag">💰 ${budgetDisplay}</span>
        </div>

        <p class="opp-desc">${escapeHtml(p.description)}</p>

        <div class="opp-skills">${skillsHtml}</div>

        <div class="opp-breakdown-bar">
          <div class="breakdown-item">
            <span class="breakdown-label">Skill Fit</span>
            <span class="breakdown-val">${skillScore}%</span>
          </div>
          <div class="breakdown-item">
            <span class="breakdown-label">Budget Fit</span>
            <span class="breakdown-val">${budgetScore}%</span>
          </div>
          <div class="breakdown-item">
            <span class="breakdown-label">Win Prob</span>
            <span class="breakdown-val">${winProb}%</span>
          </div>
          <div class="breakdown-item">
            <span class="breakdown-label">Status</span>
            <span class="breakdown-val">${escapeHtml(p.status)}</span>
          </div>
        </div>
      </div>

      <div class="opp-card-actions">
        <button class="btn btn-sm btn-primary" onclick="openProposalModal(${p.id})">
          🪄 Generate Proposal
        </button>
        <button class="btn btn-sm btn-ghost" onclick="quickAutoPitch(${p.id})">
          ⚡ Auto-Pitch
        </button>
      </div>
    </div>
  `;
}

// Live Lead Harvest
async function triggerLiveHarvest() {
  DOM.btnTriggerCollector.disabled = true;
  DOM.btnTriggerCollector.innerHTML = `
    <div class="spinner" style="width: 16px; height: 16px; border-width: 2px; margin: 0;"></div>
    <span>Harvesting Leads...</span>
  `;

  try {
    const res = await fetch("/api/collectors/trigger?limit=5", { method: "POST" });
    const data = await res.json();
    showToast(`Harvested ${data.collected_count} items & scored ${data.scored_count} leads!`, "success");
    await loadStats();
    await fetchOpportunities();
  } catch (err) {
    showToast("Error triggering collector", "info");
    console.error(err);
  } finally {
    DOM.btnTriggerCollector.disabled = false;
    DOM.btnTriggerCollector.innerHTML = `
      <span class="btn-icon">⚡</span>
      <span>Harvest Live Leads</span>
    `;
  }
}

// Proposal Modal Actions
window.openProposalModal = function (projectId) {
  const p = STATE.projects.find((item) => item.id === projectId);
  if (!p) return;

  STATE.currentModalProject = p;
  DOM.modalProjectTitle.textContent = p.title;
  DOM.proposalOutputContainer.style.display = "none";
  DOM.proposalModal.style.display = "flex";
};

window.quickAutoPitch = async function (projectId) {
  showToast("Synthesizing optimal AI proposal...", "info");
  try {
    const res = await fetch("/api/proposals/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    const result = await res.json();

    // Open modal directly with generated content
    const p = STATE.projects.find((item) => item.id === projectId);
    if (p) STATE.currentModalProject = p;
    DOM.modalProjectTitle.textContent = p ? p.title : "Custom Proposal";
    displayProposalResult(result);
    DOM.proposalModal.style.display = "flex";
  } catch (err) {
    showToast("Failed to auto-generate proposal", "info");
  }
};

async function executeProposalGeneration() {
  if (!STATE.currentModalProject) return;

  DOM.btnGenerateProposal.disabled = true;
  DOM.btnGenerateProposal.innerHTML = `<span>✨ Synthesizing Proposal...</span>`;

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
    displayProposalResult(result);
  } catch (err) {
    showToast("Error generating proposal", "info");
    console.error(err);
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

function closeModal() {
  DOM.proposalModal.style.display = "none";
}

// Profile Drawer Actions
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
    DOM.statDevRate.textContent = `$${STATE.profile.target_hourly_rate}/hr`;
    showToast("Profile updated & scores recalculated!", "success");
    closeProfileDrawer();
    fetchOpportunities();
    loadStats();
  } catch (err) {
    showToast("Error updating profile", "info");
  }
}

// Helper Utilities
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
  DOM.filterCategory.value = "";
  DOM.filterStatus.value = "";
  DOM.filterMinScore.value = "0";
  DOM.sliderVal.textContent = "0";
  fetchOpportunities();
};
