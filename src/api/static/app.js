/**
 * CLIENT FINDER SVC - Interactive Dashboard & Outcome Tracking Application
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
  btnTrackApplication: document.getElementById("btn-track-application"),
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

  if (DOM.btnRefreshApps) {
    DOM.btnRefreshApps.addEventListener("click", fetchApplications);
  }

  if (DOM.btnRefreshAnalytics) {
    DOM.btnRefreshAnalytics.addEventListener("click", fetchAnalytics);
  }

  // Live Scraper
  DOM.btnTriggerCollector.addEventListener("click", triggerCollector);

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

  DOM.btnGenerateProposal.addEventListener("click", generateProposal);
  DOM.btnCopyProposal.addEventListener("click", copyProposalToClipboard);
  if (DOM.btnTrackApplication) {
    DOM.btnTrackApplication.addEventListener("click", trackCurrentProposal);
  }
}

// 1. Data Fetching
async function loadStats() {
  try {
    const res = await fetch("/api/opportunities/stats");
    const data = await res.json();
    DOM.statTotalLeads.textContent = data.total_opportunities || 0;
    DOM.statHighPriority.textContent = data.tier_distribution?.EXCELLENT || 0;

    // Load revenue & win rates from analytics
    const revRes = await fetch("/api/analytics/revenue");
    const revData = await revRes.json();
    DOM.statRealizedRev.textContent = `$${(revData.realized_revenue || 0).toLocaleString()}`;

    const funRes = await fetch("/api/analytics/funnel");
    const funData = await funRes.json();
    DOM.statWinRate.textContent = `${funData.won_count || 0} (${funData.win_rate || 0}%)`;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    STATE.profile = await res.json();
  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function fetchOpportunities() {
  const query = DOM.searchInput.value.trim();
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
    STATE.projects = data.items || data || [];

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
        <p>Try adjusting your search criteria, minimum score slider, or trigger a live feed harvest.</p>
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
      <article class="opportunity-card">
        <div class="card-header">
          <span class="source-badge">🔗 ${escapeHtml(p.source)}</span>
          <div class="score-badge ${badgeClass}">${score.toFixed(1)} Match</div>
        </div>

        <h3 class="card-title">
          <a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(p.title)}</a>
        </h3>

        <div class="card-meta">
          <span class="meta-item">💰 ${budgetDisplay}</span>
          <span class="meta-item">📅 ${postedTime}</span>
          ${p.client_name ? `<span class="meta-item">👤 ${escapeHtml(p.client_name)}</span>` : ""}
        </div>

        <p class="card-desc">${escapeHtml(p.description)}</p>

        <div class="skills-wrap">${skillsHtml}</div>

        <div class="card-footer">
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

// 2. Applications Pipeline View
async function fetchApplications() {
  DOM.applicationsContainer.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading application pipeline...</p>
    </div>
  `;

  try {
    const res = await fetch("/api/applications?limit=100");
    STATE.applications = await res.json();
    renderApplications(STATE.applications);
  } catch (err) {
    DOM.applicationsContainer.innerHTML = `
      <div class="empty-state">
        <p>⚠️ Failed to load applications.</p>
      </div>
    `;
  }
}

function renderApplications(apps) {
  if (DOM.appsCount) DOM.appsCount.textContent = apps.length;

  if (apps.length === 0) {
    DOM.applicationsContainer.innerHTML = `
      <div class="empty-state">
        <div style="font-size: 3rem; margin-bottom: 12px;">📋</div>
        <h3>No applications tracked yet</h3>
        <p>Generate a proposal and click "Track in Pipeline" or track submissions from terminal.</p>
      </div>
    `;
    return;
  }

  DOM.applicationsContainer.innerHTML = apps
    .map((a) => {
      const budgetDisplay = a.proposed_budget ? `${a.currency} ${a.proposed_budget.toLocaleString()}` : "Budget Unstated";
      const appliedDate = new Date(a.applied_at).toLocaleDateString();

      return `
      <div class="app-card">
        <div class="app-card-header">
          <span class="app-status-badge status-${a.status}">${a.status.replace("_", " ")}</span>
          <span style="font-size: 12px; color: var(--text-muted);">ID #${a.id}</span>
        </div>

        <h4 class="app-title">${escapeHtml(a.project_title || "Project Opportunity #" + a.project_id)}</h4>

        <div class="app-meta-row">
          <span>Proposed: <strong>${budgetDisplay}</strong></span>
          <span>Applied: ${appliedDate}</span>
        </div>

        ${a.final_revenue ? `<div style="font-size: 13px; color: var(--accent-emerald);">🎉 Realized Revenue: <strong>${a.currency} ${a.final_revenue.toLocaleString()}</strong></div>` : ""}

        <div class="app-actions">
          <button class="btn btn-sm btn-secondary" onclick="updateAppStatus(${a.id}, 'CLIENT_REPLIED')">💬 Replied</button>
          <button class="btn btn-sm btn-secondary" onclick="updateAppStatus(${a.id}, 'INTERVIEW')">🎙️ Interview</button>
          <button class="btn btn-sm btn-primary" onclick="markAppWon(${a.id}, ${a.proposed_budget || 0})">🏆 Won</button>
          <button class="btn btn-sm btn-ghost" onclick="updateAppStatus(${a.id}, 'LOST')">❌ Lost</button>
        </div>
      </div>
    `;
    })
    .join("");
}

async function updateAppStatus(appId, newStatus, revenue = null) {
  try {
    const payload = { status: newStatus, final_revenue: revenue };
    const res = await fetch(`/api/applications/${appId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      showToast(`Application #${appId} moved to ${newStatus}!`, "success");
      fetchApplications();
      loadStats();
    }
  } catch (err) {
    showToast("Error updating application status", "info");
  }
}

window.updateAppStatus = updateAppStatus;

window.markAppWon = function (appId, defaultBudget) {
  const rev = prompt("Enter realized revenue contract value ($):", defaultBudget);
  if (rev !== null) {
    const parsed = parseFloat(rev) || defaultBudget;
    updateAppStatus(appId, "WON", parsed);
  }
};

// 3. Conversion Analytics View
async function fetchAnalytics() {
  try {
    const [funnelRes, pitchRes, skillsRes, insightsRes] = await Promise.all([
      fetch("/api/analytics/funnel"),
      fetch("/api/analytics/pitch-angles"),
      fetch("/api/analytics/skills?min_applications=1"),
      fetch("/api/analytics/insights"),
    ]);

    const funnel = await funnelRes.json();
    const pitches = await pitchRes.json();
    const skills = await skillsRes.json();
    const insights = await insightsRes.json();

    renderFunnel(funnel);
    renderPitchAngles(pitches);
    renderSkillsAnalytics(skills);
    renderInsights(insights);
  } catch (err) {
    console.error("Failed to load analytics:", err);
  }
}

function renderFunnel(funnel) {
  const total = funnel.total_applications || 1;
  const stages = [
    { label: "Submitted", count: funnel.total_applications, pct: 100 },
    { label: "Client Replied", count: funnel.replied_count, pct: funnel.response_rate || 0 },
    { label: "Interviewed", count: funnel.interview_count, pct: funnel.interview_rate || 0 },
    { label: "Negotiation", count: funnel.negotiation_count, pct: Math.round((funnel.negotiation_count / total) * 100) },
    { label: "Contracts Won", count: funnel.won_count, pct: funnel.win_rate || 0 },
  ];

  DOM.funnelContainer.innerHTML = stages
    .map(
      (s) => `
    <div class="funnel-stage">
      <div class="funnel-label">${s.label}</div>
      <div class="funnel-bar-bg">
        <div class="funnel-bar-fill" style="width: ${Math.max(s.pct, 4)}%;"></div>
      </div>
      <div class="funnel-count">${s.count} (${s.pct}%)</div>
    </div>
  `
    )
    .join("");
}

function renderPitchAngles(pitches) {
  DOM.pitchAnglesContainer.innerHTML = `
    <table class="analytics-table">
      <thead>
        <tr>
          <th>Pitch Angle</th>
          <th>Sent</th>
          <th>Replied</th>
          <th>Won</th>
          <th>Win Rate</th>
          <th>Revenue</th>
        </tr>
      </thead>
      <tbody>
        ${pitches
          .map(
            (p) => `
          <tr>
            <td><strong>${p.pitch_angle.replace("_", " ")}</strong></td>
            <td>${p.total_sent}</td>
            <td>${p.replied}</td>
            <td>${p.won}</td>
            <td><span class="score-val-badge">${p.win_rate}%</span></td>
            <td>$${p.total_revenue.toLocaleString()}</td>
          </tr>
        `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderSkillsAnalytics(skills) {
  if (skills.length === 0) {
    DOM.skillsAnalyticsContainer.innerHTML = `<p style="color: var(--text-muted);">No skill outcome data yet.</p>`;
    return;
  }

  DOM.skillsAnalyticsContainer.innerHTML = skills
    .slice(0, 6)
    .map(
      (s) => `
    <div class="skill-rank-row">
      <span><strong>${escapeHtml(s.skill)}</strong> (${s.applications_count} apps)</span>
      <span>Win Rate: <strong>${s.win_rate}%</strong> | Rev: <strong style="color: var(--accent-emerald);">$${s.total_revenue.toLocaleString()}</strong></span>
    </div>
  `
    )
    .join("");
}

function renderInsights(insights) {
  if (!insights.recommendations || insights.recommendations.length === 0) {
    DOM.insightsContainer.innerHTML = `<div class="insight-item">💡 Tracking more application outcomes unlocks automated win probability calibration.</div>`;
    return;
  }

  DOM.insightsContainer.innerHTML = insights.recommendations
    .map((r) => `<div class="insight-item">💡 ${escapeHtml(r)}</div>`)
    .join("");
}

// 4. Scraper Actions
async function triggerCollector() {
  DOM.btnTriggerCollector.disabled = true;
  DOM.btnTriggerCollector.innerHTML = `<span>⏳ Harvesting...</span>`;
  showToast("Scanning live feeds across Hacker News...", "info");

  try {
    const res = await fetch("/api/collectors/collect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collector_name: "Hacker News", limit: 5 }),
    });
    const data = await res.json();
    showToast(`Harvest complete: Discovered ${data.collected_count} leads!`, "success");
    fetchOpportunities();
    loadStats();
  } catch (err) {
    showToast("Error triggering feed scraper", "info");
  } finally {
    DOM.btnTriggerCollector.disabled = false;
    DOM.btnTriggerCollector.innerHTML = `<span class="btn-icon">⚡</span><span>Harvest Live Leads</span>`;
  }
}

// 5. Proposal Modal Actions
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
  DOM.btnGenerateProposal.innerHTML = `<span>⚡ Generating Proposal...</span>`;

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

// 6. Profile Drawer Actions
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
  DOM.filterCategory.value = "";
  DOM.filterStatus.value = "";
  DOM.filterMinScore.value = "0";
  DOM.sliderVal.textContent = "0";
  fetchOpportunities();
};
