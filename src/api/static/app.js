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

  // Market Intelligence & Rate Optimizer Modal
  btnOpenMarket: document.getElementById("btn-open-market"),
  btnCloseMarket: document.getElementById("btn-close-market"),
  marketModal: document.getElementById("market-modal"),
  marketStatPipelineVal: document.getElementById("market-stat-pipeline-val"),
  marketStatAvgBudget: document.getElementById("market-stat-avg-budget"),
  marketStatTopSkill: document.getElementById("market-stat-top-skill"),
  subtabBtnSkillsRoi: document.getElementById("subtab-btn-skills-roi"),
  subtabBtnUpskill: document.getElementById("subtab-btn-upskill"),
  subtabBtnRateOpt: document.getElementById("subtab-btn-rate-opt"),
  sectionSkillsRoi: document.getElementById("section-skills-roi"),
  sectionUpskill: document.getElementById("section-upskill"),
  sectionRateOpt: document.getElementById("section-rate-opt"),
  skillsRoiTableContainer: document.getElementById("skills-roi-table-container"),
  upskillCardsContainer: document.getElementById("upskill-cards-container"),
  optProjectTitle: document.getElementById("opt-project-title"),
  optMatchScore: document.getElementById("opt-match-score"),
  optHours: document.getElementById("opt-hours"),
  optClientBudget: document.getElementById("opt-client-budget"),
  btnCalculateRateOpt: document.getElementById("btn-calculate-rate-opt"),
  rateOptOutputContainer: document.getElementById("rate-opt-output-container"),

  // Scope of Work (SOW) & Proposal Quality Auditor Modal
  btnOpenContracts: document.getElementById("btn-open-contracts"),
  btnCloseContracts: document.getElementById("btn-close-contracts"),
  contractsModal: document.getElementById("contracts-modal"),
  subtabBtnAudit: document.getElementById("subtab-btn-audit"),
  subtabBtnSow: document.getElementById("subtab-btn-sow"),
  subtabBtnClauses: document.getElementById("subtab-btn-clauses"),
  sectionAudit: document.getElementById("section-audit"),
  sectionSow: document.getElementById("section-sow"),
  sectionClauses: document.getElementById("section-clauses"),
  auditProjectTitle: document.getElementById("audit-project-title"),
  auditTargetSkills: document.getElementById("audit-target-skills"),
  auditProposalText: document.getElementById("audit-proposal-text"),
  btnRunProposalAudit: document.getElementById("btn-run-proposal-audit"),
  auditOutputContainer: document.getElementById("audit-output-container"),
  sowProjectTitle: document.getElementById("sow-project-title"),
  sowClientName: document.getElementById("sow-client-name"),
  sowBudget: document.getElementById("sow-budget"),
  sowSkills: document.getElementById("sow-skills"),
  btnGenerateSowContract: document.getElementById("btn-generate-sow-contract"),
  sowOutputContainer: document.getElementById("sow-output-container"),
  sowContractTitle: document.getElementById("sow-contract-title"),
  sowMarkdownView: document.getElementById("sow-markdown-view"),
  btnCopySowMarkdown: document.getElementById("btn-copy-sow-markdown"),
  clausesCardsContainer: document.getElementById("clauses-cards-container"),

  // Autonomous Outreach & A/B Studio
  btnOpenOutreach: document.getElementById("btn-open-outreach"),
  btnCloseOutreachModal: document.getElementById("btn-close-outreach-modal"),
  modalOutreach: document.getElementById("modal-outreach"),
  tabBtnOutreachCadences: document.getElementById("tab-btn-outreach-cadences"),
  tabBtnOutreachInbound: document.getElementById("tab-btn-outreach-inbound"),
  tabBtnOutreachAb: document.getElementById("tab-btn-outreach-ab"),
  sectionOutreachCadences: document.getElementById("section-outreach-cadences"),
  sectionOutreachInbound: document.getElementById("section-outreach-inbound"),
  sectionOutreachAb: document.getElementById("section-outreach-ab"),
  outreachAppId: document.getElementById("outreach-app-id"),
  outreachProjTitle: document.getElementById("outreach-proj-title"),
  outreachClientName: document.getElementById("outreach-client-name"),
  outreachPitchAngle: document.getElementById("outreach-pitch-angle"),
  btnCreateSequence: document.getElementById("btn-create-sequence"),
  outreachSequenceSummary: document.getElementById("outreach-sequence-summary"),
  outreachActionsBar: document.getElementById("outreach-actions-bar"),
  btnAdvanceSequence: document.getElementById("btn-advance-sequence"),
  btnPauseSequence: document.getElementById("btn-pause-sequence"),
  outreachStepsTimeline: document.getElementById("outreach-steps-timeline"),
  inboundMessageText: document.getElementById("inbound-message-text"),
  inboundProjTitle: document.getElementById("inbound-proj-title"),
  inboundClientName: document.getElementById("inbound-client-name"),
  btnAnalyzeInbound: document.getElementById("btn-analyze-inbound"),
  inboundAnalysisResults: document.getElementById("inbound-analysis-results"),
  inboundIntentBadge: document.getElementById("inbound-intent-badge"),
  inboundSentimentBadge: document.getElementById("inbound-sentiment-badge"),
  inboundStatusBadge: document.getElementById("inbound-status-badge"),
  inboundReplyDraft: document.getElementById("inbound-reply-draft"),
  btnCopyInboundDraft: document.getElementById("btn-copy-inbound-draft"),
  btnRefreshAb: document.getElementById("btn-refresh-ab"),
  abPitchCardsGrid: document.getElementById("ab-pitch-cards-grid"),
  abCategoryRoutingList: document.getElementById("ab-category-routing-list"),

  // Client Intelligence & Scam Sentinel
  btnOpenIntel: document.getElementById("btn-open-intel"),
  btnCloseIntel: document.getElementById("btn-close-intel"),
  modalIntel: document.getElementById("modal-intel"),
  tabIntelDossier: document.getElementById("tab-intel-dossier"),
  tabIntelScam: document.getElementById("tab-intel-scam"),
  tabIntelFeasibility: document.getElementById("tab-intel-feasibility"),
  sectionIntelDossier: document.getElementById("section-intel-dossier"),
  sectionIntelScam: document.getElementById("section-intel-scam"),
  sectionIntelFeasibility: document.getElementById("section-intel-feasibility"),
  intelClientName: document.getElementById("intel-client-name"),
  intelClientBudget: document.getElementById("intel-client-budget"),
  intelProjectTitle: document.getElementById("intel-project-title"),
  intelProjectDesc: document.getElementById("intel-project-desc"),
  btnRunDossier: document.getElementById("btn-run-dossier"),
  intelDossierOutput: document.getElementById("intel-dossier-output"),
  dossierScoreBadge: document.getElementById("dossier-score-badge"),
  dossierGradeBadge: document.getElementById("dossier-grade-badge"),
  dossierDomainBadge: document.getElementById("dossier-domain-badge"),
  dossierTechStack: document.getElementById("dossier-tech-stack"),
  dossierPositives: document.getElementById("dossier-positives"),
  dossierCautions: document.getElementById("dossier-cautions"),
  dossierPosture: document.getElementById("dossier-posture"),
  scamAuditText: document.getElementById("scam-audit-text"),
  scamProjectTitle: document.getElementById("scam-project-title"),
  scamProjectBudget: document.getElementById("scam-project-budget"),
  btnRunScamAudit: document.getElementById("btn-run-scam-audit"),
  intelScamOutput: document.getElementById("intel-scam-output"),
  scamScoreBadge: document.getElementById("scam-score-badge"),
  scamTierBadge: document.getElementById("scam-tier-badge"),
  scamSafetyBadge: document.getElementById("scam-safety-badge"),
  scamFlagsList: document.getElementById("scam-flags-list"),
  scamDefensiveRecs: document.getElementById("scam-defensive-recs"),
  feasProjectTitle: document.getElementById("feas-project-title"),
  feasProjectBudget: document.getElementById("feas-project-budget"),
  feasProjectDesc: document.getElementById("feas-project-desc"),
  btnRunFeasibility: document.getElementById("btn-run-feasibility"),
  intelFeasOutput: document.getElementById("intel-feas-output"),
  feasRatingBadge: document.getElementById("feas-rating-badge"),
  feasHoursBadge: document.getElementById("feas-hours-badge"),
  feasMarketBadge: document.getElementById("feas-market-badge"),
  feasCounterBadge: document.getElementById("feas-counter-badge"),
  feasSuggestions: document.getElementById("feas-suggestions"),

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

  // Market Intelligence & Rate Optimizer
  if (DOM.btnOpenMarket) DOM.btnOpenMarket.addEventListener("click", openMarketModal);
  if (DOM.btnCloseMarket) DOM.btnCloseMarket.addEventListener("click", closeMarketModal);
  if (DOM.subtabBtnSkillsRoi) DOM.subtabBtnSkillsRoi.addEventListener("click", () => switchMarketSubtab("skills-roi"));
  if (DOM.subtabBtnUpskill) DOM.subtabBtnUpskill.addEventListener("click", () => switchMarketSubtab("upskill"));
  if (DOM.subtabBtnRateOpt) DOM.subtabBtnRateOpt.addEventListener("click", () => switchMarketSubtab("rate-opt"));
  if (DOM.btnCalculateRateOpt) DOM.btnCalculateRateOpt.addEventListener("click", handleCalculateRateOpt);

  // SOW & Proposal Quality Auditor
  if (DOM.btnOpenContracts) DOM.btnOpenContracts.addEventListener("click", openContractsModal);
  if (DOM.btnCloseContracts) DOM.btnCloseContracts.addEventListener("click", closeContractsModal);
  if (DOM.subtabBtnAudit) DOM.subtabBtnAudit.addEventListener("click", () => switchContractsSubtab("audit"));
  if (DOM.subtabBtnSow) DOM.subtabBtnSow.addEventListener("click", () => switchContractsSubtab("sow"));
  if (DOM.subtabBtnClauses) DOM.subtabBtnClauses.addEventListener("click", () => switchContractsSubtab("clauses"));
  if (DOM.btnRunProposalAudit) DOM.btnRunProposalAudit.addEventListener("click", handleRunProposalAudit);
  if (DOM.btnGenerateSowContract) DOM.btnGenerateSowContract.addEventListener("click", handleGenerateSowContract);
  if (DOM.btnCopySowMarkdown) DOM.btnCopySowMarkdown.addEventListener("click", copySowMarkdown);

  // Autonomous Outreach & A/B Studio
  if (DOM.btnOpenOutreach) DOM.btnOpenOutreach.addEventListener("click", openOutreachModal);
  if (DOM.btnCloseOutreachModal) DOM.btnCloseOutreachModal.addEventListener("click", closeOutreachModal);
  if (DOM.tabBtnOutreachCadences) DOM.tabBtnOutreachCadences.addEventListener("click", () => switchOutreachTab("cadences"));
  if (DOM.tabBtnOutreachInbound) DOM.tabBtnOutreachInbound.addEventListener("click", () => switchOutreachTab("inbound"));
  if (DOM.tabBtnOutreachAb) DOM.tabBtnOutreachAb.addEventListener("click", () => switchOutreachTab("ab"));
  if (DOM.btnCreateSequence) DOM.btnCreateSequence.addEventListener("click", handleCreateSequence);
  if (DOM.btnAdvanceSequence) DOM.btnAdvanceSequence.addEventListener("click", handleAdvanceSequence);
  if (DOM.btnPauseSequence) DOM.btnPauseSequence.addEventListener("click", handlePauseSequence);
  if (DOM.btnAnalyzeInbound) DOM.btnAnalyzeInbound.addEventListener("click", handleAnalyzeInboundReply);
  if (DOM.btnCopyInboundDraft) DOM.btnCopyInboundDraft.addEventListener("click", copyInboundDraft);
  if (DOM.btnRefreshAb) DOM.btnRefreshAb.addEventListener("click", loadAbPitchStats);

  // Client Intelligence & Scam Sentinel
  if (DOM.btnOpenIntel) DOM.btnOpenIntel.addEventListener("click", openIntelModal);
  if (DOM.btnCloseIntel) DOM.btnCloseIntel.addEventListener("click", closeIntelModal);
  if (DOM.tabIntelDossier) DOM.tabIntelDossier.addEventListener("click", () => switchIntelTab("dossier"));
  if (DOM.tabIntelScam) DOM.tabIntelScam.addEventListener("click", () => switchIntelTab("scam"));
  if (DOM.tabIntelFeasibility) DOM.tabIntelFeasibility.addEventListener("click", () => switchIntelTab("feasibility"));
  if (DOM.btnRunDossier) DOM.btnRunDossier.addEventListener("click", handleRunDossier);
  if (DOM.btnRunScamAudit) DOM.btnRunScamAudit.addEventListener("click", handleRunScamAudit);
  if (DOM.btnRunFeasibility) DOM.btnRunFeasibility.addEventListener("click", handleRunFeasibility);
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
      </article >
    `;
    })
    .join("");
}

// 2. Multi-Source Collector Actions
async function triggerLiveHarvest() {
  const chosenSource = DOM.selectHarvestSource ? DOM.selectHarvestSource.value : "all";
  DOM.btnTriggerCollector.disabled = true;
  DOM.btnTriggerCollector.innerHTML = `< span >⏳ Harvesting...</span > `;
  showToast(`Harvesting live opportunities from ${ chosenSource }...`, "info");

  try {
    const res = await fetch(`/ api / collectors / collect ? collector_name = ${ encodeURIComponent(chosenSource) }& limit=10`, {
      method: "POST",
    });
    const data = await res.json();
    showToast(data.message || `Discovered ${ data.collected_count } opportunities!`, "success");
    fetchOpportunities();
    loadStats();
  } catch (err) {
    showToast("Error triggering feed harvester", "info");
  } finally {
    DOM.btnTriggerCollector.disabled = false;
    DOM.btnTriggerCollector.innerHTML = `< span class="btn-icon" >⚡</span > <span>Harvest Leads</span>`;
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
  DOM.sourcesListContainer.innerHTML = `< div class="loading-state" ><div class="spinner"></div><p>Loading source health...</p></div > `;

  try {
    const res = await fetch("/api/collectors/health");
    const sources = await res.json();

    DOM.sourcesListContainer.innerHTML = sources
      .map(
        (s) => `
    < div class="source-item-card" >
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
        </div >
      </div >
    `
      )
      .join("");
  } catch (err) {
    DOM.sourcesListContainer.innerHTML = `< p style = "color: var(--accent-rose);" > Failed to load sources health.</p > `;
  }
}

window.toggleSource = async function (sourceName) {
  try {
    const res = await fetch(`/ api / collectors / ${ encodeURIComponent(sourceName) }/toggle`, { method: "POST" });
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
            <div style="font-weight: 600; font-size: 13px; color: var(--text-primary); margin-bottom: 4px;">Q${idx + 1}: ${escapeHtml(q.question)}</div>
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

// ----------------------------------------------------
// Market Intelligence & Rate Optimizer Logic
// ----------------------------------------------------
function openMarketModal() {
  if (DOM.marketModal) {
    DOM.marketModal.style.display = "flex";
    loadMarketIntelligence();
  }
}

function closeMarketModal() {
  if (DOM.marketModal) {
    DOM.marketModal.style.display = "none";
  }
}

function switchMarketSubtab(tabName) {
  const tabs = [
    { name: "skills-roi", btn: DOM.subtabBtnSkillsRoi, sec: DOM.sectionSkillsRoi },
    { name: "upskill", btn: DOM.subtabBtnUpskill, sec: DOM.sectionUpskill },
    { name: "rate-opt", btn: DOM.subtabBtnRateOpt, sec: DOM.sectionRateOpt },
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

async function loadMarketIntelligence() {
  try {
    // 1. Overview
    const resOverview = await fetch("/api/market/overview");
    const overview = await resOverview.json();
    if (DOM.marketStatPipelineVal) {
      DOM.marketStatPipelineVal.textContent = `$${(overview.total_market_pipeline_value || 0).toLocaleString()}`;
    }
    if (DOM.marketStatAvgBudget) {
      DOM.marketStatAvgBudget.textContent = `$${(overview.average_project_value || 0).toLocaleString()}`;
    }
    if (DOM.marketStatTopSkill && overview.top_paying_skills && overview.top_paying_skills.length > 0) {
      const top = overview.top_paying_skills[0];
      DOM.marketStatTopSkill.textContent = `${top.skill} ($${top.hourly_rate_benchmark}/hr)`;
    }

    // 2. Skill ROI Table
    const resRoi = await fetch("/api/market/skills/roi");
    const skills = await resRoi.json();
    renderSkillsRoiTable(skills);

    // 3. Upskill Recommendations
    const resUpskill = await fetch("/api/market/recommendations/upskill");
    const upskills = await resUpskill.json();
    renderUpskillCards(upskills);
  } catch (err) {
    console.error("Failed to load market intelligence:", err);
  }
}

function renderSkillsRoiTable(skills) {
  if (!DOM.skillsRoiTableContainer) return;
  if (!skills || skills.length === 0) {
    DOM.skillsRoiTableContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No skill metrics collected yet.</div>`;
    return;
  }

  let html = `
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
      <thead>
        <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary);">
          <th style="padding: 8px;">Technology</th>
          <th style="padding: 8px;">Market Demand</th>
          <th style="padding: 8px;">Avg Project Value</th>
          <th style="padding: 8px;">Rate Benchmark</th>
          <th style="padding: 8px;">Growth Trend</th>
        </tr>
      </thead>
      <tbody>
  `;

  skills.forEach((s) => {
    html += `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
        <td style="padding: 8px; font-weight: 600; color: var(--text-primary);">${escapeHtml(s.skill)}</td>
        <td style="padding: 8px; color: var(--accent-indigo);">${s.demand_count} jobs (${s.demand_share_pct}%)</td>
        <td style="padding: 8px; color: var(--accent-emerald); font-weight: 600;">$${s.average_budget.toLocaleString()}</td>
        <td style="padding: 8px; color: var(--text-primary); font-weight: 600;">$${s.hourly_rate_benchmark}/hr</td>
        <td style="padding: 8px; color: var(--accent-purple);">+${s.growth_trend_pct}%</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  DOM.skillsRoiTableContainer.innerHTML = html;
}

function renderUpskillCards(upskills) {
  if (!DOM.upskillCardsContainer) return;
  if (!upskills || upskills.length === 0) {
    DOM.upskillCardsContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Profile skills fully optimized!</div>`;
    return;
  }

  let html = "";
  upskills.forEach((u) => {
    html += `
      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-weight: 700; font-size: 14px; color: var(--accent-indigo);">🚀 ${escapeHtml(u.target_skill)}</span>
          <span class="badge" style="background: rgba(16,185,129,0.15); color: var(--accent-emerald); font-weight: 600;">+${u.projected_rate_increase_pct}% Rate Premium</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.4;">${escapeHtml(u.rationale)}</div>
        <div style="font-size: 11px; color: var(--text-muted);">
          <strong>Synergy with your stack:</strong> ${escapeHtml(u.synergy_with_existing_stack.join(", "))} | 
          <strong>Difficulty:</strong> ${escapeHtml(u.difficulty_level)}
        </div>
      </div>
    `;
  });

  DOM.upskillCardsContainer.innerHTML = html;
}

async function handleCalculateRateOpt() {
  const payload = {
    project_title: DOM.optProjectTitle ? DOM.optProjectTitle.value || "Custom AI Development" : "Custom AI Development",
    match_score: DOM.optMatchScore ? parseFloat(DOM.optMatchScore.value) || 80 : 80,
    estimated_hours: DOM.optHours ? parseFloat(DOM.optHours.value) || 40 : 40,
    client_budget: DOM.optClientBudget && DOM.optClientBudget.value ? parseFloat(DOM.optClientBudget.value) : null,
    target_hourly_rate: STATE.profile && STATE.profile.target_hourly_rate ? STATE.profile.target_hourly_rate : 95,
  };

  DOM.btnCalculateRateOpt.disabled = true;
  DOM.btnCalculateRateOpt.textContent = "Simulating Expected Value Curves...";

  try {
    const res = await fetch("/api/market/optimize-rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (DOM.rateOptOutputContainer) {
      let html = `<div style="font-weight: 700; font-size: 14px; color: var(--accent-emerald); margin-bottom: 12px;">📊 Pricing Optimization Strategies:</div>`;
      html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">`;

      data.strategies.forEach((st) => {
        const isOptimal = st.hourly_rate === data.optimal_recommended_rate;
        html += `
          <div style="background: ${isOptimal ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.03)"}; border: 1px solid ${isOptimal ? "var(--accent-indigo)" : "var(--border-subtle)"}; border-radius: var(--radius-md); padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: ${isOptimal ? "var(--accent-indigo)" : "var(--text-muted)"}; text-transform: uppercase;">
              ${escapeHtml(st.strategy_name)} ${isOptimal ? "⭐ (OPTIMAL EV)" : ""}
            </div>
            <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin: 4px 0;">
              $${st.hourly_rate}/hr <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">($${st.total_project_estimate.toLocaleString()})</span>
            </div>
            <div style="font-size: 12px; color: var(--accent-emerald); margin-bottom: 6px;">
              Win Prob: <strong>${st.win_probability_pct}%</strong> | Expected Yield: <strong>$${st.expected_yield_value.toLocaleString()}</strong>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.3;">${escapeHtml(st.recommendation_summary)}</div>
          </div>
        `;
      });

      html += `</div>`;
      DOM.rateOptOutputContainer.innerHTML = html;
      DOM.rateOptOutputContainer.style.display = "block";
    }
    showToast("Pricing curve simulation complete!", "success");
  } catch (err) {
    showToast("Failed to optimize pricing rate", "info");
  } finally {
    DOM.btnCalculateRateOpt.disabled = false;
    DOM.btnCalculateRateOpt.textContent = "✨ Calculate Optimal Expected Value Quote";
  }
}

// ----------------------------------------------------
// SOW & Proposal Quality Auditor Logic
// ----------------------------------------------------
function openContractsModal() {
  if (DOM.contractsModal) {
    DOM.contractsModal.style.display = "flex";
    loadContractClauses();
  }
}

function closeContractsModal() {
  if (DOM.contractsModal) {
    DOM.contractsModal.style.display = "none";
  }
}

function switchContractsSubtab(tabName) {
  const tabs = [
    { name: "audit", btn: DOM.subtabBtnAudit, sec: DOM.sectionAudit },
    { name: "sow", btn: DOM.subtabBtnSow, sec: DOM.sectionSow },
    { name: "clauses", btn: DOM.subtabBtnClauses, sec: DOM.sectionClauses },
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

async function handleRunProposalAudit() {
  const text = DOM.auditProposalText ? DOM.auditProposalText.value.trim() : "";
  if (!text) {
    showToast("Please paste proposal text to audit", "info");
    return;
  }

  const rawSkills = DOM.auditTargetSkills ? DOM.auditTargetSkills.value : "";
  const skills = rawSkills.split(",").map((s) => s.trim()).filter(Boolean);

  const payload = {
    proposal_text: text,
    project_title: DOM.auditProjectTitle ? DOM.auditProjectTitle.value || "Software Project" : "Software Project",
    target_skills: skills.length > 0 ? skills : ["Python", "FastAPI", "PostgreSQL"],
  };

  DOM.btnRunProposalAudit.disabled = true;
  DOM.btnRunProposalAudit.textContent = "Auditing Conversion Heuristics...";

  try {
    const res = await fetch("/api/contracts/audit-proposal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (DOM.auditOutputContainer) {
      let html = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <span style="font-weight: 700; font-size: 16px; color: var(--accent-indigo);">Proposal Readiness Score:</span>
            <span style="font-size: 20px; font-weight: 800; color: ${data.overall_readiness_score >= 75 ? "var(--accent-emerald)" : "var(--accent-purple);"}; margin-left: 8px;">
              ${data.overall_readiness_score}/100 (${data.grade})
            </span>
          </div>
          <span style="font-size: 12px; color: var(--text-muted);">${data.word_count} words</span>
        </div>
      `;

      html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; margin-bottom: 12px;">`;
      data.dimensions.forEach((d) => {
        html += `
          <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; margin-bottom: 4px;">
              <span>${escapeHtml(d.dimension_name)}</span>
              <span style="color: ${d.passed ? "var(--accent-emerald)" : "var(--accent-purple)"};">${d.score}/100</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.3;">${escapeHtml(d.feedback)}</div>
          </div>
        `;
      });
      html += `</div>`;

      if (data.actionable_recommendations && data.actionable_recommendations.length > 0) {
        html += `<div style="font-weight: 600; font-size: 13px; color: var(--accent-purple); margin-bottom: 4px;">💡 Actionable Optimization Tips:</div>`;
        html += `<ul style="padding-left: 20px; font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">`;
        data.actionable_recommendations.forEach((r) => {
          html += `<li>${escapeHtml(r)}</li>`;
        });
        html += `</ul>`;
      }

      DOM.auditOutputContainer.innerHTML = html;
      DOM.auditOutputContainer.style.display = "block";
    }
    showToast("Proposal quality audit complete!", "success");
  } catch (err) {
    showToast("Failed to audit proposal", "info");
  } finally {
    DOM.btnRunProposalAudit.disabled = false;
    DOM.btnRunProposalAudit.textContent = "✨ Run Deep Conversion Quality Audit";
  }
}

async function handleGenerateSowContract() {
  const rawSkills = DOM.sowSkills ? DOM.sowSkills.value : "";
  const skills = rawSkills.split(",").map((s) => s.trim()).filter(Boolean);

  const payload = {
    project_title: DOM.sowProjectTitle ? DOM.sowProjectTitle.value || "Custom Software Implementation" : "Custom Software Implementation",
    client_name: DOM.sowClientName ? DOM.sowClientName.value || "Client" : "Client",
    total_budget: DOM.sowBudget ? parseFloat(DOM.sowBudget.value) || 5000 : 5000,
    skills: skills.length > 0 ? skills : ["Python", "FastAPI", "PostgreSQL"],
    include_ip_assignment: true,
    include_change_order_clause: true,
  };

  DOM.btnGenerateSowContract.disabled = true;
  DOM.btnGenerateSowContract.textContent = "Drafting SOW Contract...";

  try {
    const res = await fetch("/api/contracts/generate-sow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (DOM.sowContractTitle) DOM.sowContractTitle.textContent = data.contract_title;
    if (DOM.sowMarkdownView) DOM.sowMarkdownView.textContent = data.formatted_markdown_contract;
    if (DOM.sowOutputContainer) DOM.sowOutputContainer.style.display = "block";
    showToast("Milestone SOW contract generated!", "success");
  } catch (err) {
    showToast("Failed to generate SOW contract", "info");
  } finally {
    DOM.btnGenerateSowContract.disabled = false;
    DOM.btnGenerateSowContract.textContent = "✨ Generate Milestone SOW Contract";
  }
}

function copySowMarkdown() {
  if (DOM.sowMarkdownView) {
    navigator.clipboard.writeText(DOM.sowMarkdownView.textContent);
    showToast("SOW Markdown contract copied to clipboard!", "success");
  }
}

async function loadContractClauses() {
  if (!DOM.clausesCardsContainer) return;
  try {
    const res = await fetch("/api/contracts/clauses");
    const clauses = await res.json();
    let html = "";
    clauses.forEach((c) => {
      html += `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px;">
          <div style="font-weight: 700; font-size: 13px; color: var(--accent-indigo); margin-bottom: 4px;">🛡️ ${escapeHtml(c.clause_title)}</div>
          <div style="font-size: 12px; color: var(--text-primary); margin-bottom: 6px; line-height: 1.4; font-family: monospace; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;">${escapeHtml(c.clause_text)}</div>
          <div style="font-size: 11px; color: var(--accent-emerald);"><strong>Purpose:</strong> ${escapeHtml(c.purpose)}</div>
        </div>
      `;
    });
    DOM.clausesCardsContainer.innerHTML = html;
  } catch (err) {
    console.error("Failed to load contract clauses:", err);
  }
}

// ---------------------------------------------------------------------------
// Autonomous Lead Outreach & A/B Studio Functions
// ---------------------------------------------------------------------------

let ACTIVE_OUTREACH_SEQUENCE = null;

function openOutreachModal() {
  if (DOM.modalOutreach) {
    DOM.modalOutreach.style.display = "flex";
    loadAbPitchStats();
  }
}

function closeOutreachModal() {
  if (DOM.modalOutreach) {
    DOM.modalOutreach.style.display = "none";
  }
}

function switchOutreachTab(tabName) {
  if (!DOM.tabBtnOutreachCadences) return;

  const tabs = [
    { btn: DOM.tabBtnOutreachCadences, sec: DOM.sectionOutreachCadences },
    { btn: DOM.tabBtnOutreachInbound, sec: DOM.sectionOutreachInbound },
    { btn: DOM.tabBtnOutreachAb, sec: DOM.sectionOutreachAb },
  ];

  tabs.forEach((t) => {
    if (t.btn && t.sec) {
      t.btn.classList.remove("btn-primary");
      t.btn.classList.add("btn-ghost");
      t.sec.style.display = "none";
    }
  });

  if (tabName === "cadences" && DOM.tabBtnOutreachCadences && DOM.sectionOutreachCadences) {
    DOM.tabBtnOutreachCadences.classList.add("btn-primary");
    DOM.tabBtnOutreachCadences.classList.remove("btn-ghost");
    DOM.sectionOutreachCadences.style.display = "block";
  } else if (tabName === "inbound" && DOM.tabBtnOutreachInbound && DOM.sectionOutreachInbound) {
    DOM.tabBtnOutreachInbound.classList.add("btn-primary");
    DOM.tabBtnOutreachInbound.classList.remove("btn-ghost");
    DOM.sectionOutreachInbound.style.display = "block";
  } else if (tabName === "ab" && DOM.tabBtnOutreachAb && DOM.sectionOutreachAb) {
    DOM.tabBtnOutreachAb.classList.add("btn-primary");
    DOM.tabBtnOutreachAb.classList.remove("btn-ghost");
    DOM.sectionOutreachAb.style.display = "block";
    loadAbPitchStats();
  }
}

async function handleCreateSequence() {
  const appId = parseInt(DOM.outreachAppId?.value) || 1;
  const projTitle = DOM.outreachProjTitle?.value || "AI Workflow Implementation";
  const clientName = DOM.outreachClientName?.value || "Founders Tech";
  const pitchAngle = DOM.outreachPitchAngle?.value || "TECHNICAL_EXPERT";

  const payload = {
    application_id: appId,
    project_title: projTitle,
    client_name: clientName,
    pitch_angle: pitchAngle,
    target_skills: ["Python", "FastAPI", "PostgreSQL"],
    auto_start: true,
  };

  DOM.btnCreateSequence.disabled = true;
  DOM.btnCreateSequence.textContent = "Launching Cadence...";

  try {
    const res = await fetch("/api/outreach/sequences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const seq = await res.json();
    ACTIVE_OUTREACH_SEQUENCE = seq;
    renderSequenceTimeline(seq);
    showToast("Outreach sequence launched successfully!", "success");
  } catch (err) {
    showToast("Failed to create outreach sequence", "info");
  } finally {
    DOM.btnCreateSequence.disabled = false;
    DOM.btnCreateSequence.textContent = "🚀 Launch 5-Step Outreach Sequence";
  }
}

async function handleAdvanceSequence() {
  if (!ACTIVE_OUTREACH_SEQUENCE) return;
  try {
    const res = await fetch(`/api/outreach/sequences/${ACTIVE_OUTREACH_SEQUENCE.sequence_id}/advance`, {
      method: "POST",
    });
    const updated = await res.json();
    ACTIVE_OUTREACH_SEQUENCE = updated;
    renderSequenceTimeline(updated);
    showToast(`Advanced sequence to Step ${updated.current_step_index}!`, "success");
  } catch (err) {
    showToast("Failed to advance sequence", "info");
  }
}

async function handlePauseSequence() {
  if (!ACTIVE_OUTREACH_SEQUENCE) return;
  try {
    const res = await fetch(`/api/outreach/sequences/${ACTIVE_OUTREACH_SEQUENCE.sequence_id}/pause`, {
      method: "POST",
    });
    const updated = await res.json();
    ACTIVE_OUTREACH_SEQUENCE = updated;
    renderSequenceTimeline(updated);
    showToast("Sequence paused", "info");
  } catch (err) {
    showToast("Failed to pause sequence", "info");
  }
}

function renderSequenceTimeline(seq) {
  if (!DOM.outreachStepsTimeline || !DOM.outreachSequenceSummary) return;

  DOM.outreachSequenceSummary.innerHTML = `
    <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">ID: <code>${escapeHtml(seq.sequence_id)}</code></div>
    <div><strong>Target:</strong> ${escapeHtml(seq.project_title)} (${escapeHtml(seq.client_name)})</div>
    <div><strong>Pitch Angle:</strong> <span class="badge" style="background: rgba(99,102,241,0.2); color: #818cf8; padding: 2px 6px; border-radius: 4px;">${escapeHtml(seq.pitch_angle)}</span></div>
    <div><strong>Status:</strong> <span style="font-weight: 700; color: ${seq.status === "ACTIVE" ? "#10b981" : "#f59e0b"};">${escapeHtml(seq.status)}</span> (Step ${seq.current_step_index} of ${seq.total_steps})</div>
  `;

  if (DOM.outreachActionsBar) {
    DOM.outreachActionsBar.style.display = "flex";
  }

  let html = "";
  seq.steps.forEach((step) => {
    const isDone = step.status === "EXECUTED";
    const statusIcon = isDone ? "✅" : "⏳";
    const bg = isDone ? "rgba(16,185,129,0.06)" : "rgba(255,255,255,0.02)";
    const border = isDone ? "1px solid rgba(16,185,129,0.3)" : "1px solid var(--border-color)";

    html += `
      <div style="background: ${bg}; border: ${border}; border-radius: 8px; padding: 10px 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <div style="font-weight: 600; font-size: 13px;">
            ${statusIcon} Step ${step.step_index}: <strong>${escapeHtml(step.step_type)}</strong> (+${step.delay_days}d delay)
          </div>
          <span style="font-size: 11px; font-weight: 600; color: ${isDone ? "#10b981" : "#94a3b8"};">${escapeHtml(step.status)}</span>
        </div>
        <div style="font-size: 12px; color: var(--accent-indigo); font-weight: 500; margin-bottom: 4px;">Subject: ${escapeHtml(step.subject)}</div>
        <div style="font-size: 11px; color: var(--text-muted); font-family: monospace; white-space: pre-wrap; max-height: 80px; overflow-y: auto; background: rgba(0,0,0,0.25); padding: 6px; border-radius: 4px;">${escapeHtml(step.message_content)}</div>
      </div>
    `;
  });

  DOM.outreachStepsTimeline.innerHTML = html;
}

async function handleAnalyzeInboundReply() {
  const text = DOM.inboundMessageText?.value.trim();
  if (!text) {
    showToast("Please enter an inbound message to analyze", "info");
    return;
  }

  const payload = {
    message_text: text,
    project_title: DOM.inboundProjTitle?.value || "Target Project",
    client_name: DOM.inboundClientName?.value || "Client",
  };

  DOM.btnAnalyzeInbound.disabled = true;
  DOM.btnAnalyzeInbound.textContent = "Analyzing Intent...";

  try {
    const res = await fetch("/api/outreach/inbound/analyze?update_db=false", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (DOM.inboundIntentBadge) DOM.inboundIntentBadge.textContent = data.classified_intent;
    if (DOM.inboundSentimentBadge) {
      const s = data.sentiment_score;
      const label = s > 0.4 ? "Enthusiastic" : s < -0.2 ? "Hesitant / Critical" : "Neutral";
      DOM.inboundSentimentBadge.textContent = `${s > 0 ? "+" : ""}${s.toFixed(2)} (${label})`;
      DOM.inboundSentimentBadge.style.color = s > 0.2 ? "#10b981" : s < -0.2 ? "#ef4444" : "#f59e0b";
    }
    if (DOM.inboundStatusBadge) DOM.inboundStatusBadge.textContent = `➔ ${data.recommended_funnel_status}`;
    if (DOM.inboundReplyDraft) DOM.inboundReplyDraft.value = data.suggested_response_draft;
    if (DOM.inboundAnalysisResults) DOM.inboundAnalysisResults.style.display = "block";

    showToast(`Intent classified: ${data.classified_intent}`, "success");
  } catch (err) {
    showToast("Failed to analyze inbound message", "info");
  } finally {
    DOM.btnAnalyzeInbound.disabled = false;
    DOM.btnAnalyzeInbound.textContent = "🤖 Classify Intent & Synthesize Auto-Reply";
  }
}

function copyInboundDraft() {
  if (DOM.inboundReplyDraft) {
    navigator.clipboard.writeText(DOM.inboundReplyDraft.value);
    showToast("Response draft copied to clipboard!", "success");
  }
}

async function loadAbPitchStats() {
  if (!DOM.abPitchCardsGrid) return;
  try {
    const res = await fetch("/api/outreach/experiments/pitch-stats");
    const summary = await res.json();

    let cardsHtml = "";
    summary.pitch_metrics.forEach((m) => {
      const isSig = m.is_statistically_significant;
      cardsHtml += `
        <div class="card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; font-size: 13px; color: var(--accent-indigo);">${escapeHtml(m.pitch_angle)}</span>
            ${isSig ? '<span class="badge" style="background: rgba(16,185,129,0.2); color: #34d399; font-size: 10px; padding: 2px 6px; border-radius: 4px;">⭐ High Win</span>' : ""}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 12px; margin-bottom: 8px;">
            <div>Sent: <strong>${m.impressions_sent}</strong></div>
            <div>Replies: <strong>${m.replies_received}</strong> (${m.reply_rate_percent}%)</div>
            <div>Wins: <strong>${m.wins_recorded}</strong> (${m.win_rate_percent}%)</div>
            <div>Score: <strong>${m.conversion_score}</strong></div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted);">95% CI: [${m.confidence_interval_low}%, ${m.confidence_interval_high}%]</div>
        </div>
      `;
    });
    DOM.abPitchCardsGrid.innerHTML = cardsHtml;

    if (DOM.abCategoryRoutingList && summary.category_recommendations) {
      let routingHtml = "";
      for (const [cat, angle] of Object.entries(summary.category_recommendations)) {
        routingHtml += `
          <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 10px; display: flex; justify-content: space-between;">
            <span>${escapeHtml(cat)}</span>
            <span style="font-weight: 600; color: var(--accent-emerald);">➔ ${escapeHtml(angle)}</span>
          </div>
        `;
      }
      DOM.abCategoryRoutingList.innerHTML = routingHtml;
    }
  } catch (err) {
    console.error("Failed to load A/B stats:", err);
  }
}

// -------------------------------------------------------------
// Phase 19: Client Intelligence, Scam Sentinel & Feasibility Handlers
// -------------------------------------------------------------
function openIntelModal() {
  if (DOM.modalIntel) {
    DOM.modalIntel.style.display = "flex";
    switchIntelTab("dossier");
  }
}

function closeIntelModal() {
  if (DOM.modalIntel) DOM.modalIntel.style.display = "none";
}

function switchIntelTab(tab) {
  if (!DOM.tabIntelDossier || !DOM.tabIntelScam || !DOM.tabIntelFeasibility) return;
  DOM.tabIntelDossier.className = tab === "dossier" ? "btn btn-sm btn-primary" : "btn btn-sm btn-ghost";
  DOM.tabIntelScam.className = tab === "scam" ? "btn btn-sm btn-primary" : "btn btn-sm btn-ghost";
  DOM.tabIntelFeasibility.className = tab === "feasibility" ? "btn btn-sm btn-primary" : "btn btn-sm btn-ghost";

  DOM.sectionIntelDossier.style.display = tab === "dossier" ? "block" : "none";
  DOM.sectionIntelScam.style.display = tab === "scam" ? "block" : "none";
  DOM.sectionIntelFeasibility.style.display = tab === "feasibility" ? "block" : "none";
}

async function handleRunDossier() {
  const clientName = DOM.intelClientName.value.trim() || "Client";
  const projectTitle = DOM.intelProjectTitle.value.trim() || "Target Project";
  const projectDesc = DOM.intelProjectDesc.value.trim();
  const claimedBudget = parseFloat(DOM.intelClientBudget.value) || null;

  try {
    const res = await fetch("/api/intelligence/client-dossier", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_name: clientName,
        project_title: projectTitle,
        project_description: projectDesc,
        claimed_budget: claimedBudget,
      }),
    });
    if (!res.ok) throw new Error("Failed to generate dossier");
    const data = await res.json();

    DOM.intelDossierOutput.style.display = "block";
    DOM.dossierScoreBadge.textContent = `${data.overall_trust_score} / 100`;
    DOM.dossierGradeBadge.textContent = data.trust_grade;
    DOM.dossierDomainBadge.textContent = data.inferred_company_domain || "Unverified Domain";

    // Tech Stack
    DOM.dossierTechStack.innerHTML = data.detected_tech_stack.map(
      (s) => `<span class="badge badge-skill" style="font-size: 11px; padding: 2px 8px;">${escapeHtml(s)}</span>`
    ).join("");

    // Positives & Cautions
    DOM.dossierPositives.innerHTML = (data.positive_signals || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>None noted</li>";
    DOM.dossierCautions.innerHTML = (data.caution_warnings || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>None noted</li>";
    DOM.dossierPosture.textContent = data.recommended_commercial_posture;
    showToast("Client Intelligence Dossier generated!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleRunScamAudit() {
  const text = DOM.scamAuditText.value.trim();
  if (!text) {
    showToast("Please enter text or message to audit.", "warning");
    return;
  }
  const title = DOM.scamProjectTitle.value.trim() || "Opportunity Text";
  const budget = parseFloat(DOM.scamProjectBudget.value) || null;

  try {
    const res = await fetch("/api/intelligence/scam-audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_title: title,
        project_description: text,
        claimed_budget: budget,
      }),
    });
    if (!res.ok) throw new Error("Scam audit failed");
    const data = await res.json();

    DOM.intelScamOutput.style.display = "block";
    DOM.scamScoreBadge.textContent = `${data.scam_risk_score} / 100`;
    DOM.scamTierBadge.textContent = data.risk_tier;

    if (data.risk_tier === "CRITICAL" || data.risk_tier === "HIGH") {
      DOM.scamTierBadge.style.color = "#ef4444";
      DOM.scamScoreBadge.style.color = "#ef4444";
      DOM.scamSafetyBadge.innerHTML = "🚨 High Scam Risk";
      DOM.scamSafetyBadge.style.color = "#ef4444";
    } else {
      DOM.scamTierBadge.style.color = "#10b981";
      DOM.scamScoreBadge.style.color = "#10b981";
      DOM.scamSafetyBadge.innerHTML = "✅ Safe to Apply";
      DOM.scamSafetyBadge.style.color = "#10b981";
    }

    if (data.detected_red_flags && data.detected_red_flags.length > 0) {
      DOM.scamFlagsList.innerHTML = data.detected_red_flags.map((f) => `
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px; padding: 8px 10px;">
          <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700; color: #ef4444; margin-bottom: 2px;">
            <span>[${escapeHtml(f.severity)}] ${escapeHtml(f.pattern_type)}</span>
          </div>
          <div style="font-size: 11px; margin-bottom: 4px;"><strong>Evidence:</strong> ${escapeHtml(f.evidence_snippet)}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(f.risk_explanation)}</div>
          <div style="font-size: 11px; color: #f59e0b; margin-top: 4px;"><strong>Defensive Step:</strong> ${escapeHtml(f.defensive_action)}</div>
        </div>
      `).join("");
    } else {
      DOM.scamFlagsList.innerHTML = `<div style="font-size: 12px; color: #10b981;">No malicious patterns or fraud indicators detected.</div>`;
    }

    DOM.scamDefensiveRecs.innerHTML = (data.defensive_recommendations || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");
    showToast("Scam Sentinel audit complete!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleRunFeasibility() {
  const title = DOM.feasProjectTitle.value.trim() || "Project";
  const desc = DOM.feasProjectDesc.value.trim();
  const budget = parseFloat(DOM.feasProjectBudget.value) || 3000.0;

  try {
    const res = await fetch("/api/intelligence/budget-feasibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_title: title,
        project_description: desc,
        proposed_budget: budget,
      }),
    });
    if (!res.ok) throw new Error("Feasibility calculation failed");
    const data = await res.json();

    DOM.intelFeasOutput.style.display = "block";
    DOM.feasRatingBadge.textContent = data.feasibility_rating;
    DOM.feasHoursBadge.textContent = `${data.estimated_engineering_hours_min} - ${data.estimated_engineering_hours_max} hrs`;
    DOM.feasMarketBadge.textContent = `$${data.estimated_fair_market_budget.toLocaleString()}`;
    DOM.feasCounterBadge.textContent = `$${data.recommended_counter_budget.toLocaleString()}`;

    DOM.feasSuggestions.innerHTML = (data.scope_reduction_suggestions || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("");
    showToast("Scope feasibility evaluated!");
  } catch (err) {
    showToast(err.message, "error");
  }
}
