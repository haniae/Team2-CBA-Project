const API_BASE = window.API_BASE || "";
const STORAGE_KEY = "benchmarkos.chatHistory.v1";

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const statusDot = document.getElementById("api-status");
const statusMessage = document.getElementById("status-message");
const conversationList = document.getElementById("conversation-list");
const navItems = document.querySelectorAll(".nav-item");
const chatSearchContainer = document.getElementById("chat-search");
const chatSearchInput = document.getElementById("chat-search-input");
const chatSearchClear = document.getElementById("chat-search-clear");
const utilityPanel = document.getElementById("utility-panel");
const utilityTitle = document.getElementById("utility-title");
const utilityContent = document.getElementById("utility-content");
const introPanel = document.getElementById("chat-intro");
const chatPanel = document.querySelector(".chat-panel");
const chatFormContainer = document.getElementById("chat-form");
const savedSearchTrigger = document.querySelector("[data-action='search-saved']");
const archivedToggleButton = document.querySelector("[data-action='toggle-archived']");

const TICKER_STOPWORDS = new Set([
  "THE",
  "AND",
  "WITH",
  "KPI",
  "EPS",
  "ROE",
  "FCF",
  "PE",
  "TSR",
  "LTM",
  "FY",
  "API",
  "DATA",
  "THIS",
  "THAT",
  "YOY",
  "TTM",
  "GROWTH",
  "METRIC",
  "METRICS",
  "SUMMARY",
  "REPORT",
  "SCENARIO",
  "K",
]);

let reportMenu = null;
let projectMenu = null;
let activeMenuConversationId = null;
let activeMenuAnchor = null;
let shareModalBackdrop = null;
let shareModalElement = null;
let shareToggleInput = null;
let shareStatusTextEl = null;
let shareStatusSubTextEl = null;
let shareLinkInput = null;
let shareCopyButton = null;
let sharePrimaryButton = null;
let shareCancelButton = null;
let shareModalConversationId = null;
let toastContainer = null;
const toastTimeouts = new Map();
let companyUniverseData = [];
let filteredCompanyData = [];
let companyUniverseMetrics = null;
let companyUniverseTable = null;
let companyUniverseEmpty = null;
let companySearchInput = null;
let companySectorSelect = null;
let companyCoverageSelect = null;
let companyUniverseMetaUniverse = null;
let companyUniverseMetaSectors = null;
let companyUniverseMetaLatest = null;
let companyUniverseMetaCoverage = null;

const KPI_LIBRARY_PATH = "/static/data/kpi_library.json";
const COMPANY_UNIVERSE_PATH = "/static/data/company_universe.json";
const SETTINGS_STORAGE_KEY = "benchmarkos.userSettings.v1";
let kpiLibraryCache = null;
let kpiLibraryLoadPromise = null;
let companyUniversePromise = null;

const METRIC_KEYWORD_MAP = [
  { regex: /\bgrowth|cagr|yoy\b/i, label: "Growth" },
  { regex: /\brevenue\b/i, label: "Revenue" },
  { regex: /\bmargin\b/i, label: "Margin" },
  { regex: /\bearnings|\beps\b/i, label: "Earnings" },
  { regex: /\bcash\s*flow|\bcf\b/i, label: "Cash Flow" },
  { regex: /\bvaluation|\bp\/?e\b|\bmultiple\b/i, label: "Valuation" },
  { regex: /\bleverage|\bdebt\b/i, label: "Leverage" },
  { regex: /\bsummary|\bmovers|\bmarket\b/i, label: "Market" },
  { regex: /\bfact|\bsnapshot\b/i, label: "Snapshot" },
  { regex: /\bmetric|\bkpi\b/i, label: "KPI" },
];

const RECENT_PROJECTS = ["Benchmark Coverage", "AI Research Notes", "Sector Watchlist"];
const INTENT_LABELS = {
  compare: "Comparison",
  metric: "KPI Report",
  fact: "Fact Sheet",
  summarize: "Market Summary",
  scenario: "Scenario Analysis",
  insight: "Insight",
};

const DEFAULT_USER_SETTINGS = {
  apiKey: "",
  dataSources: {
    edgar: true,
    yahoo: true,
    bloomberg: false,
  },
  refreshSchedule: "daily",
  aiModel: "gpt-4o-mini",
  exportFormats: {
    pdf: true,
    excel: true,
    markdown: false,
  },
  locale: "en-US",
  timezone: "UTC",
  currency: "USD",
  compliance: "standard",
};

function loadUserSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) {
      return JSON.parse(JSON.stringify(DEFAULT_USER_SETTINGS));
    }
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_USER_SETTINGS,
      ...parsed,
      dataSources: {
        ...DEFAULT_USER_SETTINGS.dataSources,
        ...(parsed?.dataSources || {}),
      },
      exportFormats: {
        ...DEFAULT_USER_SETTINGS.exportFormats,
        ...(parsed?.exportFormats || {}),
      },
    };
  } catch (error) {
    console.warn("Unable to load user settings from storage", error);
    return JSON.parse(JSON.stringify(DEFAULT_USER_SETTINGS));
  }
}

function saveUserSettings(settings) {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error("Unable to persist user settings", error);
    throw error;
  }
}

async function renderCompanyUniverseSection({ container } = {}) {
  if (!container) {
    return;
  }

  companyUniverseMetrics = null;
  companyUniverseTable = null;
  companyUniverseEmpty = null;
  companySearchInput = null;
  companySectorSelect = null;
  companyCoverageSelect = null;
  companyUniverseMetaUniverse = null;
  companyUniverseMetaSectors = null;
  companyUniverseMetaLatest = null;
  companyUniverseMetaCoverage = null;

  container.innerHTML = `
    <div class="company-universe" role="region" aria-live="polite">
      <section class="company-universe__hero">
        <div class="company-universe__badge" aria-hidden="true">CU</div>
        <div class="company-universe__hero-copy">
          <h3 class="company-universe__title">Company Universe</h3>
          <p class="company-universe__subtitle">
            Explore coverage across every tracked company, segment results, and monitor ingestion progress.
          </p>
          <ul class="company-universe__meta">
            <li class="company-universe__meta-item">
              <span class="company-universe__meta-label">Universe</span>
              <span class="company-universe__meta-value" data-role="company-universe-meta-universe">Loading...</span>
            </li>
            <li class="company-universe__meta-item">
              <span class="company-universe__meta-label">Sectors</span>
              <span class="company-universe__meta-value" data-role="company-universe-meta-sectors">Loading...</span>
            </li>
            <li class="company-universe__meta-item">
              <span class="company-universe__meta-label">Latest filing</span>
              <span class="company-universe__meta-value" data-role="company-universe-meta-latest">Loading...</span>
            </li>
            <li class="company-universe__meta-item">
              <span class="company-universe__meta-label">Coverage mix</span>
              <span class="company-universe__meta-value" data-role="company-universe-meta-coverage">Loading...</span>
            </li>
          </ul>
        </div>
      </section>
      <div class="company-universe__controls">
        <label class="sr-only" for="company-universe-search-input">Search companies</label>
        <input
          type="search"
          id="company-universe-search-input"
          data-role="company-universe-search"
          placeholder="Search by company, ticker, or sector"
          autocomplete="off"
        />
        <label class="sr-only" for="company-universe-sector-filter">Filter by sector</label>
        <select id="company-universe-sector-filter" data-role="company-universe-sector">
          <option value="">All sectors</option>
        </select>
        <label class="sr-only" for="company-universe-coverage-filter">Filter by coverage</label>
        <select id="company-universe-coverage-filter" data-role="company-universe-coverage">
          <option value="">All coverage</option>
          <option value="complete">Complete coverage</option>
          <option value="partial">Partial coverage</option>
          <option value="missing">Missing coverage</option>
        </select>
      </div>
      <div class="company-universe__metrics" data-role="company-universe-metrics">
        <div class="utility-loading">Loading coverage snapshot...</div>
      </div>
      <div class="company-universe__table-wrapper">
        <table class="company-universe__table hidden" data-role="company-universe-table">
          <thead>
            <tr>
              <th scope="col">Company</th>
              <th scope="col">Ticker</th>
              <th scope="col">Sector</th>
              <th scope="col">Market cap</th>
              <th scope="col">Latest filing</th>
              <th scope="col">Coverage</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
        <p class="company-universe__empty hidden" data-role="company-universe-empty">
          No companies match the current filters.
        </p>
      </div>
    </div>
  `;

  companySearchInput = container.querySelector("[data-role='company-universe-search']");
  companySectorSelect = container.querySelector("[data-role='company-universe-sector']");
  companyCoverageSelect = container.querySelector("[data-role='company-universe-coverage']");
  companyUniverseMetrics = container.querySelector("[data-role='company-universe-metrics']");
  companyUniverseTable = container.querySelector("[data-role='company-universe-table']");
  companyUniverseEmpty = container.querySelector("[data-role='company-universe-empty']");
  companyUniverseMetaUniverse = container.querySelector("[data-role='company-universe-meta-universe']");
  companyUniverseMetaSectors = container.querySelector("[data-role='company-universe-meta-sectors']");
  companyUniverseMetaLatest = container.querySelector("[data-role='company-universe-meta-latest']");
  companyUniverseMetaCoverage = container.querySelector("[data-role='company-universe-meta-coverage']");

  if (companySearchInput) {
    companySearchInput.value = "";
    companySearchInput.addEventListener("input", applyCompanyUniverseFilters);
  }
  if (companySectorSelect) {
    companySectorSelect.value = "";
    companySectorSelect.addEventListener("change", applyCompanyUniverseFilters);
  }
  if (companyCoverageSelect) {
    companyCoverageSelect.value = "";
    companyCoverageSelect.addEventListener("change", applyCompanyUniverseFilters);
  }
  if (companyUniverseMetrics) {
    companyUniverseMetrics.innerHTML = `<div class="utility-loading">Loading coverage snapshot...</div>`;
  }
  if (companyUniverseTable) {
    companyUniverseTable.classList.add("hidden");
  }
  if (companyUniverseEmpty) {
    companyUniverseEmpty.classList.add("hidden");
  }

  try {
    await loadCompanyUniverseData();
    if (!container.isConnected) {
      return;
    }
    applyCompanyUniverseFilters();
    if (companySearchInput) {
      companySearchInput.focus();
      companySearchInput.select();
    }
  } catch (error) {
    companyUniverseMetrics = null;
    companyUniverseTable = null;
    companyUniverseEmpty = null;
    companySearchInput = null;
    companySectorSelect = null;
    companyCoverageSelect = null;
    companyUniverseMetaUniverse = null;
    companyUniverseMetaSectors = null;
    companyUniverseMetaLatest = null;
    companyUniverseMetaCoverage = null;
    if (!container.isConnected) {
      return;
    }
    container.innerHTML = `
      <div class="utility-error">
        <p>Unable to load the company universe right now. Please try again.</p>
        <button type="button" class="utility-error__retry" data-action="retry-company-universe">Retry</button>
      </div>
    `;
    const retryButton = container.querySelector("[data-action='retry-company-universe']");
    if (retryButton) {
      retryButton.addEventListener("click", () => {
        renderCompanyUniverseSection({ container });
      });
    }
  }
}


const HELP_PROMPTS = [
  "Show Apple KPIs for 2022–2024",
  "Compare Microsoft and Amazon in FY2023",
  "What was Tesla’s 2022 revenue?",
];

const HELP_SECTIONS = [
  {
    icon: "📊",
    title: "KPI & Comparisons",
    command: "Metrics TICKER [YEAR | YEAR–YEAR] [+ peers]",
    purpose: "Summarise a company’s finance snapshot or line up peers on one table.",
    example: "Metrics AAPL 2023 vs MSFT",
    delivers: "Revenue, profitability, free cash flow, ROE, valuation ratios.",
  },
  {
    icon: "🧾",
    title: "Facts from SEC Filings",
    command: "Fact TICKER YEAR [metric]",
    purpose: "Retrieve exactly what was reported in 10-K/10-Q filings.",
    example: "Fact TSLA 2022 revenue",
    delivers: "Original value, adjustment notes, and source reference.",
  },
  {
    icon: "🧮",
    title: "Scenario Modelling",
    command: "Scenario TICKER NAME rev=+X% margin=+Y% mult=+Z",
    purpose: "Run what-if cases for growth, margin shifts, or valuation moves.",
    example: "Scenario NVDA Bull rev=+8% margin=+1.5% mult=+0.5",
    delivers: "Projected revenue, margins, EPS/FCF change, implied valuation.",
  },
  {
    icon: "⚙️",
    title: "Data Management",
    command: ["Ingest TICKER [years]", "Ingest status TICKER", "Audit TICKER [year]"],
    purpose: "Refresh data, track ingestion progress, or review the audit log.",
    examples: [
      "Ingest META 5 — refreshes five fiscal years of filings and quotes.",
      "Audit META 2023 — lists the latest import activity and KPI updates.",
    ],
  },
];

function getHelpContent() {
  return {
    prompts: HELP_PROMPTS,
    sections: HELP_SECTIONS,
    tips: HELP_TIPS,
  };
}

let HELP_TIPS = [
  // Intentionally empty; tips section removed.
];

let HELP_TEXT = composeHelpText(getHelpContent());
let HELP_GUIDE_HTML = renderHelpGuide(getHelpContent()).outerHTML;

function composeHelpText(content) {
  const lines = [];
  lines.push("📘 BenchmarkOS Copilot — Quick Reference", "", "How to ask:");
  content.prompts.forEach((prompt) => lines.push(`• ${prompt}`));
  lines.push("", "──────────────────────────────────────");

  content.sections.forEach((section, index) => {
    lines.push(`${section.icon} ${section.title.toUpperCase()}`);
    if (Array.isArray(section.command)) {
      section.command.forEach((entry, entryIndex) => {
        const prefix = entryIndex === 0 ? "Command:" : "         ";
        lines.push(`${prefix} ${entry}`);
      });
    } else {
      lines.push(`Command: ${section.command}`);
    }
    if (section.purpose) {
      lines.push(`Purpose: ${section.purpose}`);
    }
    if (section.example) {
      lines.push(`Example: ${section.example}`);
    }
    if (section.delivers) {
      lines.push(`Delivers: ${section.delivers}`);
    }
    if (section.examples && section.examples.length) {
      lines.push("Examples:");
      section.examples.forEach((example) => lines.push(`• ${example}`));
    }
    lines.push("");
    if (index !== content.sections.length - 1) {
      lines.push("──────────────────────────────────────");
    }
  });

  if (content.tips && content.tips.length) {
    lines.push("──────────────────────────────────────", "💡 Tips");
    content.tips.forEach((tip) => lines.push(`• ${tip}`));
  }

  return lines.join("\n");
}

function renderHelpGuide(content) {
  const article = document.createElement("article");
  article.className = "help-guide";

  const hero = document.createElement("header");
  hero.className = "help-guide__hero";

  const badge = document.createElement("span");
  badge.className = "help-guide__badge";
  badge.textContent = "📘";

  const heroCopy = document.createElement("div");
  heroCopy.className = "help-guide__hero-copy";

  const title = document.createElement("h2");
  title.className = "help-guide__title";
  title.textContent = "BenchmarkOS Copilot — Quick Reference";

  const subtitle = document.createElement("p");
  subtitle.className = "help-guide__subtitle";
  subtitle.textContent = "Ask natural prompts and I will translate them into institutional-grade analysis.";

  const promptList = document.createElement("ul");
  promptList.className = "help-guide__prompts";
  content.prompts.forEach((prompt) => {
    const item = document.createElement("li");
    item.className = "help-guide__prompt";
    item.textContent = prompt;
    promptList.append(item);
  });

  heroCopy.append(title, subtitle, promptList);
  hero.append(badge, heroCopy);
  article.append(hero);

  const sectionGrid = document.createElement("div");
  sectionGrid.className = "help-guide__grid";

  content.sections.forEach((section) => {
    const card = document.createElement("section");
    card.className = "help-guide__card";

    const cardHeader = document.createElement("div");
    cardHeader.className = "help-guide__card-header";

    const icon = document.createElement("span");
    icon.className = "help-guide__card-icon";
    icon.textContent = section.icon;

    const heading = document.createElement("h3");
    heading.className = "help-guide__card-title";
    heading.textContent = section.title;

    cardHeader.append(icon, heading);
    card.append(cardHeader);

    appendHelpLine(card, "Command", section.command, { tokens: true });
    appendHelpLine(card, "Purpose", section.purpose);
    appendHelpLine(card, "Example", section.example);
    appendHelpLine(card, "Delivers", section.delivers);

    if (section.examples && section.examples.length) {
      const examplesLabel = document.createElement("p");
      examplesLabel.className = "help-guide__label help-guide__label--stack";
      examplesLabel.textContent = "Examples";
      card.append(examplesLabel);

      const exampleList = document.createElement("ul");
      exampleList.className = "help-guide__list";
      section.examples.forEach((example) => {
        const li = document.createElement("li");
        li.textContent = example;
        exampleList.append(li);
      });
      card.append(exampleList);
    }

    sectionGrid.append(card);
  });

  article.append(sectionGrid);

  if (content.tips && content.tips.length) {
    const tipsSection = document.createElement("section");
    tipsSection.className = "help-guide__tips";

    const tipsHeading = document.createElement("h3");
    tipsHeading.className = "help-guide__tips-title";
    tipsHeading.textContent = "💡 Tips";

    const tipsList = document.createElement("ul");
    tipsList.className = "help-guide__tips-list";
    content.tips.forEach((tip) => {
      const li = document.createElement("li");
      li.textContent = tip;
      tipsList.append(li);
    });

    tipsSection.append(tipsHeading, tipsList);
    article.append(tipsSection);
  }

  return article;
}

function appendHelpLine(container, label, value, { tokens = false } = {}) {
  if (!value) {
    return;
  }

  const line = document.createElement("p");
  line.className = "help-guide__line";

  const labelEl = document.createElement("span");
  labelEl.className = "help-guide__label";
  labelEl.textContent = `${label}`;
  line.append(labelEl);

  if (Array.isArray(value) || tokens) {
    const values = Array.isArray(value) ? value : [value];
    const tokenGroup = document.createElement("div");
    tokenGroup.className = "help-guide__tokens";
    values.forEach((token) => {
      const pill = document.createElement("span");
      pill.className = "help-guide__token";
      pill.textContent = token;
      tokenGroup.append(pill);
    });
    line.append(tokenGroup);
  } else {
    const valueEl = document.createElement("span");
    valueEl.className = "help-guide__value";
    valueEl.textContent = value;
    line.append(valueEl);
  }

  container.append(line);
}

function refreshHelpArtifacts() {
  HELP_TEXT = composeHelpText(getHelpContent());
  HELP_GUIDE_HTML = renderHelpGuide(getHelpContent()).outerHTML;
  if (UTILITY_SECTIONS.help) {
    UTILITY_SECTIONS.help.html = HELP_GUIDE_HTML;
  }
  if (currentUtilityKey === "help" && utilityContent) {
    utilityContent.innerHTML = HELP_GUIDE_HTML;
  }
}

async function loadHelpContentOverrides() {
  try {
    const response = await fetch(`${API_BASE}/help-content`);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data?.tips) && data.tips.length) {
      const customTips = data.tips.map((tip) => `${tip}`.trim()).filter(Boolean);
      if (customTips.length) {
        HELP_TIPS = customTips;
        refreshHelpArtifacts();
      }
    }
  } catch (error) {
    console.warn("Failed to load help tip overrides:", error);
  }
}



function formatDisplayDate(value) {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return `${value}`;
  }
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function humaniseLabel(value) {
  if (!value) {
    return "";
  }
  return `${value}`
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function createList(items, className = "kpi-library__doc-list") {
  const list = document.createElement("ul");
  list.className = className;
  (items || [])
    .map((item) => (typeof item === "string" ? item.trim() : item))
    .filter(Boolean)
    .forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item}`;
      list.append(li);
    });
  return list;
}

function formatDirectionality(value) {
  if (!value) {
    return "";
  }
  const mapping = {
    higher_is_better: "Higher is better",
    lower_is_better: "Lower is better",
    depends: "Depends",
  };
  return mapping[value] || humaniseLabel(value);
}

function formatPeriodLabel(value) {
  if (!value) {
    return "";
  }
  return `${value}`
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTagName(tag) {
  if (!tag) {
    return "";
  }
  return `${tag}`
    .replace(/[_-]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatFriendlyInput(input) {
  if (!input || typeof input !== "object") {
    return "";
  }
  const label = input.tag ? formatTagName(input.tag) : formatTagName(input.source);
  const statement = input.statement ? humaniseLabel(input.statement) : "";
  const derived = input.source === "derived" ? " (Derived)" : "";
  const base = label ? `${label}${derived}` : statement;
  if (base && statement) {
    return `${base} (${statement})`;
  }
  return base || statement || "";
}

function formatTechnicalInput(input) {
  if (!input || typeof input !== "object") {
    return "";
  }
  const segments = [];
  if (input.source) {
    segments.push(`[${input.source}]`);
  }
  if (input.tag) {
    segments.push(input.tag);
  }
  if (input.statement) {
    segments.push(`(${input.statement})`);
  }
  if (Array.isArray(input.components) && input.components.length) {
    segments.push(`components: ${input.components.join(", ")}`);
  }
  if (Array.isArray(input.fallbacks) && input.fallbacks.length) {
    segments.push(`fallbacks: ${input.fallbacks.join(", ")}`);
  }
  return segments.join(" ").trim();
}

function createMetaBadge(label, value) {
  if (!value) {
    return null;
  }
  const badge = document.createElement("span");
  badge.className = "kpi-library__meta-pill";
  badge.textContent = `${label}: ${value}`;
  return badge;
}

function createDocSection(label, content, options = {}) {
  if (
    content === undefined ||
    content === null ||
    (typeof content === "string" && !content.trim())
  ) {
    return null;
  }
  if (Array.isArray(content)) {
    const filtered = content.map((entry) => (entry ? `${entry}`.trim() : "")).filter(Boolean);
    if (!filtered.length) {
      return null;
    }
    content = filtered;
  }

  const section = document.createElement("section");
  section.className = "kpi-library__doc-section";

  const heading = document.createElement("h6");
  heading.className = "kpi-library__doc-label";
  heading.textContent = label;
  section.append(heading);

  if (options.type === "code") {
    const block = document.createElement("pre");
    block.className = "kpi-library__formula";
    const code = document.createElement("code");
    code.textContent = `${content}`;
    block.append(code);
    section.append(block);
    return section;
  }

  if (Array.isArray(content)) {
    section.append(createList(content, options.listClass || "kpi-library__doc-list"));
    return section;
  }

  if (typeof content === "object") {
    const entries = Object.entries(content).map(
      ([key, value]) => `${humaniseLabel(key)}: ${value}`
    );
    section.append(createList(entries, options.listClass || "kpi-library__doc-list"));
    return section;
  }

  const paragraph = document.createElement("p");
  paragraph.className = "kpi-library__doc-text";
  paragraph.textContent = `${content}`;
  section.append(paragraph);
  return section;
}

function buildTechnicalDetails(kpi) {
  const lines = [];
  (kpi.inputs || []).forEach((input) => {
    const descriptor = formatTechnicalInput(input);
    if (descriptor) {
      lines.push(`Input: ${descriptor}`);
    }
  });

  if (kpi.parameters && Object.keys(kpi.parameters).length) {
    lines.push(`Parameters: ${JSON.stringify(kpi.parameters)}`);
  }
  if (kpi.presentation && Object.keys(kpi.presentation).length) {
    lines.push(`Presentation: ${JSON.stringify(kpi.presentation)}`);
  }
  if (Array.isArray(kpi.dimensions_supported) && kpi.dimensions_supported.length) {
    lines.push(`Dimensions: ${kpi.dimensions_supported.join(", ")}`);
  }
  if (kpi.quality_notes) {
    lines.push(`Quality notes: ${kpi.quality_notes}`);
  }

  const detailLines = lines.filter(Boolean);
  if (!detailLines.length) {
    return null;
  }

  const container = document.createElement("div");
  container.className = "kpi-library__tech";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "kpi-library__tech-toggle";
  toggle.textContent = "Show technical tags ▸";

  const body = document.createElement("div");
  body.className = "kpi-library__tech-body";
  body.hidden = true;
  body.append(createList(detailLines, "kpi-library__tech-list"));

  toggle.addEventListener("click", () => {
    const isOpen = !body.hidden;
    if (isOpen) {
      body.hidden = true;
      toggle.textContent = "Show technical tags ▸";
      toggle.classList.remove("is-open");
    } else {
      body.hidden = false;
      toggle.textContent = "Hide technical tags ▾";
      toggle.classList.add("is-open");
    }
  });

  container.append(toggle);
  container.append(body);
  return container;
}

async function loadKpiLibraryData() {
  if (kpiLibraryCache) {
    return kpiLibraryCache;
  }
  if (kpiLibraryLoadPromise) {
    return kpiLibraryLoadPromise;
  }
  kpiLibraryLoadPromise = fetch(KPI_LIBRARY_PATH, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`KPI library fetch failed (${response.status})`);
      }
      return response.json();
    })
    .then((data) => {
      kpiLibraryCache = data;
      return data;
    })
    .finally(() => {
      kpiLibraryLoadPromise = null;
    });
  return kpiLibraryLoadPromise;
}

function buildKpiLibraryHero(data) {
  const hero = document.createElement("section");
  hero.className = "kpi-library__hero";

  const badge = document.createElement("div");
  badge.className = "kpi-library__badge";
  badge.textContent = "📊";

  const copy = document.createElement("div");
  copy.className = "kpi-library__hero-copy";

  const title = document.createElement("h3");
  title.className = "kpi-library__title";
  title.textContent = data.library_name || "KPI Library";

  const subtitle = document.createElement("p");
  subtitle.className = "kpi-library__subtitle";
  subtitle.textContent =
    "Standardised KPI definitions, formulas, and data lineage policies.";

  const metaList = document.createElement("ul");
  metaList.className = "kpi-library__meta";

  copy.append(title);
  copy.append(subtitle);

  hero.append(badge);
  hero.append(copy);
  return hero;
}

function buildKpiCard(kpi) {
  const card = document.createElement("article");
  card.className = "kpi-library__doc-card";

  const header = document.createElement("header");
  header.className = "kpi-library__doc-header";

  const title = document.createElement("h5");
  title.className = "kpi-library__doc-title";
  title.textContent = kpi.display_name || formatTagName(kpi.kpi_id);
  header.append(title);

  if (kpi.kpi_id) {
    const code = document.createElement("span");
    code.className = "kpi-library__doc-code";
    code.textContent = kpi.kpi_id;
    header.append(code);
  }

  const meta = document.createElement("div");
  meta.className = "kpi-library__doc-meta";
  const unitsBadge = createMetaBadge("Units", humaniseLabel(kpi.units));
  const directionBadge = createMetaBadge("Direction", formatDirectionality(kpi.directionality));
  if (unitsBadge) {
    meta.append(unitsBadge);
  }
  if (directionBadge) {
    meta.append(directionBadge);
  }
  if (meta.children.length) {
    header.append(meta);
  }

  card.append(header);

  const body = document.createElement("div");
  body.className = "kpi-library__doc-body";

  const definitionSection = createDocSection("Definition", kpi.definition_short || kpi.definition_long);
  if (definitionSection) {
    body.append(definitionSection);
  }

  const categorySection = createDocSection("Category", kpi.category);
  if (categorySection) {
    body.append(categorySection);
  }

  const formulaSection = createDocSection("Formula", kpi.formula_text, { type: "code" });
  if (formulaSection) {
    body.append(formulaSection);
  }

  const friendlyInputs = (kpi.inputs || [])
    .map(formatFriendlyInput)
    .filter(Boolean);
  const inputsSection = createDocSection("Inputs", friendlyInputs);
  if (inputsSection) {
    body.append(inputsSection);
  }

  const computationSection = createDocSection("Computation Notes", kpi.computation || []);
  if (computationSection) {
    body.append(computationSection);
  }

  const periods = (kpi.supports_periods || []).map(formatPeriodLabel);
  const periodsSection = createDocSection("Supported Periods", periods);
  if (periodsSection) {
    body.append(periodsSection);
  }

  const interpretationSource =
    (kpi.definition_long && kpi.definition_long !== kpi.definition_short
      ? kpi.definition_long
      : null) || kpi.notes;
  const interpretationSection = createDocSection("Interpretation", interpretationSource);
  if (interpretationSection) {
    body.append(interpretationSection);
  }

  if (Array.isArray(kpi.edge_cases) && kpi.edge_cases.length) {
    const edgeSection = createDocSection("Edge Cases", kpi.edge_cases);
    if (edgeSection) {
      body.append(edgeSection);
    }
  }

  if (kpi.quality_notes && !interpretationSource) {
    const qualitySection = createDocSection("Quality Notes", kpi.quality_notes);
    if (qualitySection) {
      body.append(qualitySection);
    }
  }

  card.append(body);

  const technicalDetails = buildTechnicalDetails(kpi);
  if (technicalDetails) {
    card.append(technicalDetails);
  }

  return card;
}

function buildCategoriesSection(kpis) {
  if (!Array.isArray(kpis) || !kpis.length) {
    return null;
  }
  const byCategory = new Map();
  kpis.forEach((kpi) => {
    const category = kpi.category || "Other";
    if (!byCategory.has(category)) {
      byCategory.set(category, []);
    }
    byCategory.get(category).push(kpi);
  });

  const categories = Array.from(byCategory.entries()).sort(([a], [b]) =>
    a.localeCompare(b)
  );

  const wrapper = document.createElement("div");
  wrapper.className = "kpi-library__categories";

  categories.forEach(([category, items]) => {
    const section = document.createElement("section");
    section.className = "kpi-library__category";

    const heading = document.createElement("h4");
    heading.className = "kpi-library__category-title";
    heading.textContent = category;

    const grid = document.createElement("div");
    grid.className = "kpi-library__grid";

    items
      .slice()
      .sort((a, b) => {
        const left = a.display_name || a.kpi_id || "";
        const right = b.display_name || b.kpi_id || "";
        return left.localeCompare(right);
      })
      .forEach((kpi) => {
        grid.append(buildKpiCard(kpi));
      });

    section.append(heading);
    section.append(grid);
    wrapper.append(section);
  });

  return wrapper;
}

function buildKpiLibraryView(data) {
  const container = document.createElement("div");
  container.className = "kpi-library";
  container.append(buildKpiLibraryHero(data));

  const state = {
    all: Array.isArray(data?.kpis) ? data.kpis.slice() : [],
    filtered: [],
    search: "",
    category: "",
    direction: "",
  };

  const controls = document.createElement("div");
  controls.className = "kpi-library__filters";

  const searchGroup = document.createElement("div");
  searchGroup.className = "kpi-library__filter kpi-library__filter--search";
  const searchInput = document.createElement("input");
  searchInput.type = "search";
  searchInput.placeholder = "Search KPI by name, formula, or ID";
  searchInput.autocomplete = "off";
  searchInput.className = "kpi-library__search";
  searchGroup.append(searchInput);
  controls.append(searchGroup);

  const categoryGroup = document.createElement("div");
  categoryGroup.className = "kpi-library__filter";
  const categorySelect = document.createElement("select");
  categorySelect.className = "kpi-library__select";
  categorySelect.innerHTML = `<option value="">All categories</option>`;
  const categories = Array.from(
    new Set(state.all.map((kpi) => kpi.category || "").filter(Boolean))
  ).sort((a, b) => a.localeCompare(b));
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.append(option);
  });
  categoryGroup.append(categorySelect);
  controls.append(categoryGroup);

  const directionGroup = document.createElement("div");
  directionGroup.className = "kpi-library__filter";
  const directionSelect = document.createElement("select");
  directionSelect.className = "kpi-library__select";
  directionSelect.innerHTML = `<option value="">Any direction</option>`;
  const directions = Array.from(
    new Set(state.all.map((kpi) => kpi.directionality || "").filter(Boolean))
  );
  directions
    .map((direction) => ({ raw: direction, label: formatDirectionality(direction) }))
    .sort((a, b) => a.label.localeCompare(b.label))
    .forEach(({ raw, label }) => {
      const option = document.createElement("option");
      option.value = raw;
      option.textContent = label;
      directionSelect.append(option);
    });
  directionGroup.append(directionSelect);
  controls.append(directionGroup);

  container.append(controls);

  const content = document.createElement("div");
  content.className = "kpi-library__content";
  container.append(content);

  const emptyState = document.createElement("div");
  emptyState.className = "kpi-library__empty hidden";
  emptyState.textContent = "No KPIs match your filters.";
  container.append(emptyState);

  function applyFilters() {
    const term = state.search;
    const category = state.category;
    const direction = state.direction;

    state.filtered = state.all.filter((kpi) => {
      const matchesTerm =
        !term ||
        [kpi.display_name, kpi.kpi_id, kpi.category, kpi.formula_text]
          .filter(Boolean)
          .some((field) => field.toLowerCase().includes(term));
      const matchesCategory = !category || kpi.category === category;
      const matchesDirection = !direction || kpi.directionality === direction;
      return matchesTerm && matchesCategory && matchesDirection;
    });

    renderContent();
  }

  function renderContent() {
    content.innerHTML = "";
    if (!state.filtered.length) {
      emptyState.classList.remove("hidden");
      return;
    }
    emptyState.classList.add("hidden");
    const section = buildCategoriesSection(state.filtered);
    if (section) {
      content.append(section);
    }
  }

  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    applyFilters();
  });

  categorySelect.addEventListener("change", (event) => {
    state.category = event.target.value;
    applyFilters();
  });

  directionSelect.addEventListener("change", (event) => {
    state.direction = event.target.value;
    applyFilters();
  });

  // initial render
  applyFilters();

  return container;
}

async function renderKpiLibrarySection({ container } = {}) {
  if (!container) {
    return;
  }
  container.innerHTML = `<div class="utility-loading">Loading KPI library…</div>`;
  try {
    const data = await loadKpiLibraryData();
    if (!container.isConnected) {
      return;
    }
    container.innerHTML = "";
    container.append(buildKpiLibraryView(data));
  } catch (error) {
    console.warn("Unable to load KPI library:", error);
    if (!container.isConnected) {
      return;
    }
    container.innerHTML = `
      <div class="utility-error">
        <p>Không thể tải KPI Library. Vui lòng thử lại.</p>
        <button type="button" class="utility-error__retry" data-action="retry-kpi-library">Thử lại</button>
      </div>
    `;
    const retry = container.querySelector("[data-action='retry-kpi-library']");
    if (retry) {
      retry.addEventListener("click", () => {
        renderKpiLibrarySection({ container });
      });
    }
  }
}







async function fetchFilingFacts({ ticker, metric, fiscalYear, startYear, endYear, limit = 250 }) {
  const params = new URLSearchParams();
  params.set("ticker", ticker);
  if (metric) {
    params.set("metric", metric);
  }
  if (typeof fiscalYear === "number" && Number.isFinite(fiscalYear)) {
    params.set("fiscal_year", String(fiscalYear));
  }
  if (typeof startYear === "number" && Number.isFinite(startYear)) {
    params.set("start_year", String(startYear));
  }
  if (typeof endYear === "number" && Number.isFinite(endYear)) {
    params.set("end_year", String(endYear));
  }
  if (limit) {
    params.set("limit", String(limit));
  }

  const response = await fetch(`${API_BASE}/filings?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch (error) {
      // ignore JSON parsing errors
    }
    throw new Error(detail);
  }
  return response.json();
}

function formatFactValueDisplay(value, unit) {
  if (value === null || value === undefined) {
    return "—";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  const abs = Math.abs(numeric);
  let formatted;
  if (abs >= 1e12) {
    formatted = `${(numeric / 1e12).toFixed(2)}T`;
  } else if (abs >= 1e9) {
    formatted = `${(numeric / 1e9).toFixed(2)}B`;
  } else if (abs >= 1e6) {
    formatted = `${(numeric / 1e6).toFixed(2)}M`;
  } else if (abs >= 1) {
    formatted = numeric.toLocaleString(undefined, { maximumFractionDigits: 2 });
  } else if (abs >= 1e3) {
    formatted = `${(numeric / 1e3).toFixed(2)}K`;
  } else {
    formatted = numeric.toPrecision(3);
  }
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatFilingDate(dateString) {
  if (!dateString) {
    return "—";
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

async function renderFilingViewerSection({ container } = {}) {
  if (!container) {
    return;
  }

  container.innerHTML = `
    <div class="filing-viewer">
      <section class="filing-viewer__hero">
        <div class="filing-viewer__badge">FS</div>
        <div class="filing-viewer__hero-copy">
          <h3 class="filing-viewer__title">Filing Source Viewer</h3>
          <p class="filing-viewer__subtitle">
            Trace capital-market KPIs back to their source filings — built for audit-ready analytics.
          </p>
          <div class="filing-viewer__meta">
            <div class="filing-viewer__meta-item">
              <span class="filing-viewer__meta-label">Records</span>
              <span class="filing-viewer__meta-value" data-role="filing-meta-records">—</span>
            </div>
            <div class="filing-viewer__meta-item">
              <span class="filing-viewer__meta-label">Fiscal years</span>
              <span class="filing-viewer__meta-value" data-role="filing-meta-years">—</span>
            </div>
            <div class="filing-viewer__meta-item">
              <span class="filing-viewer__meta-label">Metrics</span>
              <span class="filing-viewer__meta-value" data-role="filing-meta-metrics">—</span>
            </div>
          </div>
        </div>
      </section>
      <div class="filing-viewer__status" data-role="filing-status" aria-live="polite"></div>
      <form class="filing-viewer__form" data-role="filing-viewer-form">
        <div class="filing-viewer__form-group">
          <label for="filing-viewer-ticker">Ticker</label>
          <input id="filing-viewer-ticker" name="ticker" type="text" placeholder="e.g. TSLA" required />
        </div>
        <div class="filing-viewer__form-group">
          <label for="filing-viewer-metric">Metric (optional)</label>
          <input id="filing-viewer-metric" name="metric" type="text" placeholder="e.g. revenue" />
        </div>
        <div class="filing-viewer__form-group">
          <label for="filing-viewer-year">Fiscal year (optional)</label>
          <input id="filing-viewer-year" name="year" type="number" inputmode="numeric" placeholder="e.g. 2023" />
        </div>
        <div class="filing-viewer__form-group">
          <label for="filing-viewer-start">Start year (range)</label>
          <input id="filing-viewer-start" name="start" type="number" inputmode="numeric" placeholder="e.g. 2021" />
        </div>
        <div class="filing-viewer__form-group">
          <label for="filing-viewer-end">End year (range)</label>
          <input id="filing-viewer-end" name="end" type="number" inputmode="numeric" placeholder="e.g. 2023" />
        </div>
        <div class="filing-viewer__form-actions">
          <button type="submit">Fetch filings</button>
        </div>
      </form>
      <div class="filing-viewer__notice">
        <p>Pull SEC-backed facts to validate every KPI. Supply a ticker, then refine by metric or year.</p>
      </div>
      <div class="filing-viewer__table-wrapper">
        <table class="filing-viewer__table">
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Fiscal period</th>
              <th scope="col">Value</th>
              <th scope="col">Filing</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody data-role="filing-table-body"></tbody>
        </table>
        <p class="filing-viewer__empty hidden" data-role="filing-empty">No filings match your filters yet.</p>
      </div>
    </div>
  `;

  const form = container.querySelector("[data-role='filing-viewer-form']");
  const tickerInput = container.querySelector("#filing-viewer-ticker");
  const metricInput = container.querySelector("#filing-viewer-metric");
  const yearInput = container.querySelector("#filing-viewer-year");
  const startInput = container.querySelector("#filing-viewer-start");
  const endInput = container.querySelector("#filing-viewer-end");
  const statusBox = container.querySelector("[data-role='filing-status']");
  const metaRecords = container.querySelector("[data-role='filing-meta-records']");
  const metaYears = container.querySelector("[data-role='filing-meta-years']");
  const metaMetrics = container.querySelector("[data-role='filing-meta-metrics']");
  const tableBody = container.querySelector("[data-role='filing-table-body']");
  const emptyState = container.querySelector("[data-role='filing-empty']");
  const submitButton = form?.querySelector("button[type='submit']");

  if (tickerInput) {
    tickerInput.value = "TSLA";
  }
  if (startInput) {
    startInput.value = String(new Date().getFullYear() - 2);
  }
  if (endInput) {
    endInput.value = String(new Date().getFullYear());
  }

  const resetStatus = () => {
    if (statusBox) {
      statusBox.textContent = "";
      statusBox.classList.remove("error");
    }
  };

  const setStatus = (message, tone = "info") => {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.classList.toggle("error", tone === "error");
  };

  const setLoading = (isLoading) => {
    if (submitButton) {
      submitButton.disabled = isLoading;
      submitButton.textContent = isLoading ? "Fetching…" : "Fetch filings";
    }
    if (isLoading) {
      setStatus("Loading filings…", "info");
    } else {
      resetStatus();
    }
  };

  const renderSummary = (summary) => {
    if (metaRecords) {
      metaRecords.textContent = summary && typeof summary.count === "number" ? summary.count.toLocaleString() : "—";
    }
    if (metaYears) {
      metaYears.textContent = summary?.fiscal_years?.length ? summary.fiscal_years.join(", ") : "—";
    }
    if (metaMetrics) {
      metaMetrics.textContent = summary?.metrics?.length ? summary.metrics.join(", ") : "—";
    }
  };

  const renderRows = (items) => {
    if (!tableBody || !emptyState) {
      return;
    }
    tableBody.innerHTML = "";
    if (!Array.isArray(items) || !items.length) {
      emptyState.classList.remove("hidden");
      return;
    }
    emptyState.classList.add("hidden");
    items.forEach((item) => {
      const row = document.createElement("tr");
      const valueDisplay = formatFactValueDisplay(item.value, item.unit);
      const periodText = item.period || [item.fiscal_year, item.fiscal_period].filter(Boolean).join(" ") || "—";
      const filedText = formatFilingDate(item.filed_at);
      const links = [];
      if (item.sec_url) {
        links.push(`<a href="${item.sec_url}" target="_blank" rel="noopener noreferrer">Inline</a>`);
      }
      if (item.archive_url) {
        links.push(`<a href="${item.archive_url}" target="_blank" rel="noopener noreferrer">Archive</a>`);
      }
      const linkHtml = links.length ? `<div class="filing-viewer__links">${links.join(" · ")}</div>` : "";
      const badges = [];
      if (item.adjusted) {
        badges.push('<span class="filing-viewer__badge">Adjusted</span>');
      }
      const detailLines = [];
      if (item.period_start || item.period_end) {
        detailLines.push(
          `Period: ${item.period_start ? formatFilingDate(item.period_start) : "?"} → ${item.period_end ? formatFilingDate(item.period_end) : "?"}`
        );
      }
      if (item.adjustment_note) {
        detailLines.push(`Note: ${item.adjustment_note}`);
      }
      row.innerHTML = `
        <td data-label="Metric">
          <div class="filing-viewer__metric">${item.metric || "—"}</div>
          ${badges.join(" ")}
        </td>
        <td data-label="Fiscal period">
          <div>${periodText}</div>
          ${filedText !== "—" ? `<div class="filing-viewer__filed">Filed ${filedText}</div>` : ""}
        </td>
        <td data-label="Value">
          <div>${valueDisplay}</div>
        </td>
        <td data-label="Filing">
          <div>${item.form || "—"}</div>
          <div class="filing-viewer__accession">${item.source_filing || item.accession || "—"}</div>
          ${linkHtml}
        </td>
        <td data-label="Source">
          <div>${item.source || "—"}</div>
          ${detailLines.length ? `<div class="filing-viewer__details">${detailLines.join("<br />")}</div>` : ""}
        </td>
      `;
      tableBody.append(row);
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form || !tickerInput) {
      return;
    }
    resetStatus();

    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) {
      setStatus("Ticker is required.", "error");
      tickerInput.focus();
      return;
    }

    const metricValue = metricInput?.value.trim();
    const yearValue = yearInput?.value.trim();
    const startValue = startInput?.value.trim();
    const endValue = endInput?.value.trim();

    const payload = {
      ticker,
      metric: metricValue || undefined,
      fiscalYear: yearValue ? Number(yearValue) : undefined,
      startYear: startValue ? Number(startValue) : undefined,
      endYear: endValue ? Number(endValue) : undefined,
      limit: 250,
    };

    if (payload.startYear && payload.endYear && payload.startYear > payload.endYear) {
      const tmp = payload.startYear;
      payload.startYear = payload.endYear;
      payload.endYear = tmp;
      if (startInput) {
        startInput.value = String(payload.startYear);
      }
      if (endInput) {
        endInput.value = String(payload.endYear);
      }
    }

    try {
      setLoading(true);
      renderSummary(null);
      renderRows([]);
      const data = await fetchFilingFacts(payload);
      renderSummary(data.summary || null);
      renderRows(data.items || []);
      setStatus(`Loaded ${data.summary?.count ?? data.items?.length ?? 0} filings for ${data.ticker}.`, "info");
    } catch (error) {
      console.error("Unable to load filing facts:", error);
      renderSummary(null);
      renderRows([]);
      setStatus(error?.message || "Unable to load filings. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  };

  if (form) {
    form.addEventListener("submit", handleSubmit);
    window.queueMicrotask(() => {
      if (tickerInput) {
        tickerInput.focus();
      }
      form.requestSubmit();
    });
  } else if (tickerInput) {
    window.queueMicrotask(() => tickerInput.focus());
  }
}

function renderSettingsSection({ container } = {}) {
  if (!container) {
    return;
  }

  const root = container.querySelector("[data-role='settings-root']") || container;
  const settings = loadUserSettings();

  root.innerHTML = `
    <form class="settings-form" data-role="settings-form">
      <section class="settings-section">
        <h3>AI preferences</h3>
        <p class="settings-hint">
          The values below are stored locally in your browser so you can experiment without touching
          the backend configuration.
        </p>
        <label class="settings-field">
          <span class="settings-label">Preferred model</span>
          <input name="aiModel" type="text" autocomplete="off" spellcheck="false" />
        </label>
        <label class="settings-field">
          <span class="settings-label">Local API key (optional)</span>
          <input name="apiKey" type="password" autocomplete="off" placeholder="Stored in this browser only" />
        </label>
        <label class="settings-field">
          <span class="settings-label">Refresh cadence</span>
          <select name="refreshSchedule">
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </label>
      </section>
      <section class="settings-section">
        <h3>Data sources</h3>
        <label class="settings-toggle">
          <input type="checkbox" name="dataSources.edgar" />
          <span>SEC EDGAR filings</span>
        </label>
        <label class="settings-toggle">
          <input type="checkbox" name="dataSources.yahoo" />
          <span>Yahoo Finance market data</span>
        </label>
        <label class="settings-toggle">
          <input type="checkbox" name="dataSources.bloomberg" />
          <span>Bloomberg real-time quotes</span>
        </label>
      </section>
      <section class="settings-section">
        <h3>Output preferences</h3>
        <label class="settings-field">
          <span class="settings-label">Timezone</span>
          <input name="timezone" type="text" autocomplete="off" placeholder="e.g. UTC" />
        </label>
        <label class="settings-field">
          <span class="settings-label">Primary currency</span>
          <input name="currency" type="text" autocomplete="off" placeholder="e.g. USD" />
        </label>
        <label class="settings-field">
          <span class="settings-label">Compliance mode</span>
          <select name="compliance">
            <option value="standard">Standard</option>
            <option value="restricted">Restricted</option>
            <option value="audit">Audit</option>
          </select>
        </label>
        <fieldset class="settings-checkbox-group">
          <legend>Enable exports</legend>
          <label class="settings-toggle">
            <input type="checkbox" name="exportFormats.pdf" />
            <span>PDF</span>
          </label>
          <label class="settings-toggle">
            <input type="checkbox" name="exportFormats.excel" />
            <span>Excel</span>
          </label>
          <label class="settings-toggle">
            <input type="checkbox" name="exportFormats.markdown" />
            <span>Markdown</span>
          </label>
        </fieldset>
      </section>
      <div class="settings-actions">
        <button type="submit">Save settings</button>
        <button type="button" data-role="settings-reset">Reset to defaults</button>
      </div>
      <p class="settings-status" data-role="settings-status" aria-live="polite"></p>
    </form>
  `;

  const form = root.querySelector("[data-role='settings-form']");
  if (!form) {
    return;
  }
  const statusEl = root.querySelector("[data-role='settings-status']");
  const resetButton = root.querySelector("[data-role='settings-reset']");

  const fields = {
    aiModel: form.elements.aiModel,
    apiKey: form.elements.apiKey,
    refreshSchedule: form.elements.refreshSchedule,
    timezone: form.elements.timezone,
    currency: form.elements.currency,
    compliance: form.elements.compliance,
    edgar: form.querySelector("[name='dataSources.edgar']"),
    yahoo: form.querySelector("[name='dataSources.yahoo']"),
    bloomberg: form.querySelector("[name='dataSources.bloomberg']"),
    exportPdf: form.querySelector("[name='exportFormats.pdf']"),
    exportExcel: form.querySelector("[name='exportFormats.excel']"),
    exportMarkdown: form.querySelector("[name='exportFormats.markdown']"),
  };

  const applySettings = (values) => {
    if (!values) {
      return;
    }
    fields.aiModel.value = values.aiModel || "";
    fields.apiKey.value = values.apiKey || "";
    fields.refreshSchedule.value = values.refreshSchedule || "daily";
    fields.timezone.value = values.timezone || "UTC";
    fields.currency.value = values.currency || "USD";
    fields.compliance.value = values.compliance || "standard";
    fields.edgar.checked = Boolean(values?.dataSources?.edgar);
    fields.yahoo.checked = Boolean(values?.dataSources?.yahoo);
    fields.bloomberg.checked = Boolean(values?.dataSources?.bloomberg);
    fields.exportPdf.checked = Boolean(values?.exportFormats?.pdf);
    fields.exportExcel.checked = Boolean(values?.exportFormats?.excel);
    fields.exportMarkdown.checked = Boolean(values?.exportFormats?.markdown);
  };

  const showStatus = (message, type = "info") => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = message;
    statusEl.dataset.state = type;
    if (statusEl.dataset.timeoutId) {
      window.clearTimeout(Number(statusEl.dataset.timeoutId));
    }
    const id = window.setTimeout(() => {
      statusEl.textContent = "";
      delete statusEl.dataset.state;
    }, 3000);
    statusEl.dataset.timeoutId = String(id);
  };

  applySettings(settings);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const nextSettings = {
      ...settings,
      apiKey: fields.apiKey.value.trim(),
      aiModel: fields.aiModel.value.trim() || DEFAULT_USER_SETTINGS.aiModel,
      refreshSchedule: fields.refreshSchedule.value || DEFAULT_USER_SETTINGS.refreshSchedule,
      timezone: fields.timezone.value.trim() || DEFAULT_USER_SETTINGS.timezone,
      currency: fields.currency.value.trim() || DEFAULT_USER_SETTINGS.currency,
      compliance: fields.compliance.value || DEFAULT_USER_SETTINGS.compliance,
      dataSources: {
        ...settings.dataSources,
        edgar: fields.edgar.checked,
        yahoo: fields.yahoo.checked,
        bloomberg: fields.bloomberg.checked,
      },
      exportFormats: {
        ...settings.exportFormats,
        pdf: fields.exportPdf.checked,
        excel: fields.exportExcel.checked,
        markdown: fields.exportMarkdown.checked,
      },
    };
    saveUserSettings(nextSettings);
    showStatus("Settings saved locally.", "success");
  });

  if (resetButton) {
    resetButton.addEventListener("click", () => {
      const defaults = JSON.parse(JSON.stringify(DEFAULT_USER_SETTINGS));
      saveUserSettings(defaults);
      applySettings(defaults);
      showStatus("Settings reset to defaults.", "success");
    });
  }
}

let isSending = false;
let conversations = loadStoredConversations();
let activeConversation = null;
let conversationSearch = "";
let currentUtilityKey = null;

const UTILITY_SECTIONS = {
  help: {
    title: "Copilot Quick Reference",
    html: HELP_GUIDE_HTML,
  },
  "kpi-library": {
    title: "KPI Library",
    html: `<div class="utility-loading">Đang tải KPI library…</div>`,
    render: renderKpiLibrarySection,
  },
  "company-universe": {
    title: "Company Universe",
    html: `<div class="utility-loading">Loading company universe…</div>`,
    render: renderCompanyUniverseSection,
  },
  "filing-viewer": {
    title: "Filing Source Viewer",
    html: `<div class="filing-viewer" data-role="filing-viewer-root"></div>`,
    render: renderFilingViewerSection,
  },
  projects: {
    title: "Projects",
    html: `
      <p>Quản lý các bộ phân tích theo nhóm, khách hàng, hoặc chủ đề.</p>
      <ul>
        <li>📊 Big 5 Tech Benchmark 2025</li>
        <li>🏭 AI Semiconductor Peer Set Analysis</li>
        <li>📈 Dividend Portfolio Comparison</li>
      </ul>
      <p class="panel-note">Liên kết phân tích với dashboard hoặc notebook để chia sẻ với đội ngũ nội bộ.</p>
    `,
  },
  settings: {
    title: "Settings",
    html: `<div class="settings-panel" data-role="settings-root"></div>`,
    render: renderSettingsSection,
  },
};

function normaliseArtifacts(response) {
  if (!response || typeof response !== "object") {
    return null;
  }
  const artifacts = {
    highlights: Array.isArray(response.highlights) ? response.highlights : [],
    trends: Array.isArray(response.trends) ? response.trends : [],
    comparisonTable: response.comparison_table || response.comparisonTable || null,
    citations: Array.isArray(response.citations) ? response.citations : [],
    exports: Array.isArray(response.exports) ? response.exports : [],
  };
  if (
    !artifacts.highlights.length &&
    !artifacts.trends.length &&
    !artifacts.comparisonTable &&
    !artifacts.citations.length &&
    !artifacts.exports.length
  ) {
    return null;
  }
  return artifacts;
}

function appendMessage(
  role,
  text,
  {
    smooth = true,
    forceScroll = false,
    isPlaceholder = false,
    animate = true,
    artifacts = null,
  } = {}
) {
  if (!chatLog) {
    return null;
  }

  hideIntroPanel();

  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}${isPlaceholder ? " typing" : ""}`;
  wrapper.dataset.role = role;

  if (animate) {
    wrapper.classList.add("incoming");
    wrapper.addEventListener(
      "animationend",
      () => wrapper.classList.remove("incoming"),
      { once: true }
    );
  }

  const header = document.createElement("div");
  header.className = "message-header";

  const avatar = document.createElement("span");
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === "user" ? "You" : role === "assistant" ? "BO" : "SYS";

  const label = document.createElement("span");
  label.className = "message-role";
  label.textContent = role === "user" ? "You" : role === "assistant" ? "BenchmarkOS" : "System";

  header.append(avatar, label);
  wrapper.append(header);

  const body = document.createElement("div");
  body.className = "message-body";

  if (isPlaceholder) {
    body.append(createTypingIndicator());
  } else if (text === HELP_TEXT) {
    wrapper.classList.add("message-help");
    body.innerHTML = HELP_GUIDE_HTML;
  } else {
    wrapper.classList.remove("message-help");
    const fragments = buildMessageBlocks(text);
    fragments.forEach((node) => body.append(node));
  }
  wrapper.append(body);

  if (!isPlaceholder) {
    renderMessageArtifacts(wrapper, artifacts);
  }

  chatLog.append(wrapper);
  scrollChatToBottom({ smooth, force: forceScroll });
  return wrapper;
}

function createTypingIndicator() {
  const container = document.createElement("div");
  container.className = "typing-indicator";

  const srLabel = document.createElement("span");
  srLabel.className = "sr-only";
  srLabel.textContent = "BenchmarkOS is typing";
  container.append(srLabel);

  for (let index = 0; index < 3; index += 1) {
    const dot = document.createElement("span");
    dot.className = "typing-dot";
    dot.style.animationDelay = `${index * 0.2}s`;
    container.append(dot);
  }

  return container;
}

function updateMessageRole(wrapper, role) {
  if (!wrapper) {
    return;
  }
  wrapper.className = `message ${role}`;
  wrapper.dataset.role = role;

  const avatar = wrapper.querySelector(".avatar");
  if (avatar) {
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === "user" ? "You" : role === "assistant" ? "BO" : "SYS";
  }

  const roleLabel = wrapper.querySelector(".message-role");
  if (roleLabel) {
    roleLabel.textContent =
      role === "user" ? "You" : role === "assistant" ? "BenchmarkOS" : "System";
  }
}

function setMessageBody(wrapper, text) {
  if (!wrapper) {
    return;
  }
  const body = wrapper.querySelector(".message-body");
  if (!body) {
    return;
  }
  body.innerHTML = "";
  if (text === HELP_TEXT) {
    wrapper.classList.add("message-help");
    body.innerHTML = HELP_GUIDE_HTML;
  } else {
    wrapper.classList.remove("message-help");
    const fragments = buildMessageBlocks(text);
    fragments.forEach((node) => body.append(node));
  }
}

function renderMessageArtifacts(wrapper, artifacts) {
  const existing = wrapper.querySelector(".message-artifacts");
  if (existing) {
    existing.remove();
  }
  if (!artifacts) {
    return;
  }
  const body = wrapper.querySelector(".message-body");
  if (!body) {
    return;
  }
  const sections = [];
  const highlightsSection = createHighlightsSection(artifacts.highlights);
  if (highlightsSection) {
    sections.push(highlightsSection);
  }
  const tableSection = createComparisonTableSection(artifacts.comparisonTable);
  if (tableSection) {
    sections.push(tableSection);
  }
  const trendsSection = createTrendSection(artifacts.trends);
  if (trendsSection) {
    sections.push(trendsSection);
  }
  const citationsSection = createCitationSection(artifacts.citations);
  if (citationsSection) {
    sections.push(citationsSection);
  }
  const exportsSection = createExportSection(artifacts.exports);
  if (exportsSection) {
    sections.push(exportsSection);
  }
  if (!sections.length) {
    return;
  }
  const container = document.createElement("div");
  container.className = "message-artifacts";
  sections.forEach((section) => container.append(section));
  body.append(container);
}

function createHighlightsSection(highlights) {
  if (!Array.isArray(highlights) || !highlights.length) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-highlights";
  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = "Highlights";
  wrapper.append(title);
  const list = document.createElement("ul");
  list.className = "artifact-list";
  highlights.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.append(item);
  });
  wrapper.append(list);
  return wrapper;
}

function createComparisonTableSection(table) {
  if (
    !table ||
    table.render === false ||
    table.render_hint === "hidden" ||
    !Array.isArray(table.headers) ||
    !table.headers.length
  ) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-table";
  if (table.title || table.descriptor) {
    const title = document.createElement("h4");
    title.className = "artifact-title";
    title.textContent = table.title || "Comparison table";
    wrapper.append(title);
    if (table.descriptor) {
      const subtitle = document.createElement("div");
      subtitle.className = "artifact-subtitle";
      subtitle.textContent = table.descriptor;
      wrapper.append(subtitle);
    }
  }
  const tableEl = document.createElement("table");
  tableEl.className = "artifact-table__grid";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  table.headers.forEach((header) => {
    const cell = document.createElement("th");
    cell.textContent = header;
    headerRow.append(cell);
  });
  thead.append(headerRow);
  tableEl.append(thead);
  const tbody = document.createElement("tbody");
  (table.rows || []).forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((value, index) => {
      const cell = document.createElement(index === 0 ? "th" : "td");
      if (index === 0) {
        cell.scope = "row";
      }
      cell.textContent = value;
      tr.append(cell);
    });
    tbody.append(tr);
  });
  tableEl.append(tbody);
  wrapper.append(tableEl);
  return wrapper;
}

function createTrendSection(trends) {
  if (!Array.isArray(trends) || !trends.length) {
    return null;
  }
  const validSeries = trends.filter(
    (series) => Array.isArray(series.points) && series.points.length >= 2
  );
  if (!validSeries.length) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-trends";
  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = "Trend visualisations";
  wrapper.append(title);
  const grid = document.createElement("div");
  grid.className = "trend-grid";
  validSeries.forEach((series) => {
    const card = createTrendCard(series);
    if (card) {
      grid.append(card);
    }
  });
  wrapper.append(grid);
  return wrapper;
}

function createTrendCard(series) {
  const points = (series.points || []).filter(
    (point) => point && typeof point.value === "number"
  );
  if (points.length < 2) {
    return null;
  }
  const card = document.createElement("div");
  card.className = "trend-card";
  const header = document.createElement("div");
  header.className = "trend-card__header";
  header.textContent = `${series.ticker} · ${series.label}`;
  card.append(header);
  const chartContainer = document.createElement("div");
  chartContainer.className = "trend-card__chart";
  const chart = createTrendSparkline(points);
  if (chart) {
    chartContainer.append(chart);
  }
  card.append(chartContainer);
  const footer = document.createElement("div");
  footer.className = "trend-card__footer";
  const latest = points[points.length - 1];
  footer.textContent = `${latest.period}: ${latest.formatted_value || latest.value}`;
  card.append(footer);
  return card;
}

function createTrendSparkline(points) {
  const svgNS = "http://www.w3.org/2000/svg";
  const width = 240;
  const height = 80;
  const padding = 10;
  const values = points.map((point) => Number(point.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = (width - padding * 2) / (points.length - 1 || 1);
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.classList.add("trend-chart");
  const polyline = document.createElementNS(svgNS, "polyline");
  const coords = points.map((point, index) => {
    const x = padding + index * step;
    const normalized = range === 0 ? 0.5 : (point.value - min) / range;
    const y = height - padding - normalized * (height - padding * 2);
    return `${x},${y}`;
  });
  polyline.setAttribute("points", coords.join(" "));
  polyline.classList.add("trend-chart__line");
  svg.appendChild(polyline);
  const baseline = document.createElementNS(svgNS, "line");
  baseline.setAttribute("x1", String(padding));
  baseline.setAttribute("y1", String(height - padding));
  baseline.setAttribute("x2", String(width - padding));
  baseline.setAttribute("y2", String(height - padding));
  baseline.classList.add("trend-chart__baseline");
  svg.appendChild(baseline);
  const finalPoint = points[points.length - 1];
  const finalX = padding + (points.length - 1) * step;
  const finalNormalized = range === 0 ? 0.5 : (finalPoint.value - min) / range;
  const finalY = height - padding - finalNormalized * (height - padding * 2);
  const marker = document.createElementNS(svgNS, "circle");
  marker.setAttribute("cx", String(finalX));
  marker.setAttribute("cy", String(finalY));
  marker.setAttribute("r", "3.5");
  marker.classList.add("trend-chart__marker");
  svg.appendChild(marker);
  return svg;
}

function createCitationSection(citations) {
  if (!Array.isArray(citations) || !citations.length) {
    return null;
  }
  const details = document.createElement("details");
  details.className = "artifact-section artifact-citations";
  const summary = document.createElement("summary");
  summary.textContent = `Sources (${citations.length})`;
  details.append(summary);
  const list = document.createElement("ul");
  list.className = "citation-list";
  citations.forEach((citation) => {
    const item = document.createElement("li");
    const parts = [
      `${citation.ticker} • ${citation.label}`,
      citation.period ? citation.period : null,
      citation.formatted_value || (typeof citation.value === "number" ? citation.value : null),
    ].filter(Boolean);
    const text = document.createElement("span");
    text.textContent = parts.join(" · ");
    item.append(text);
    if (citation.form) {
      const formTag = document.createElement("span");
      formTag.className = "citation-form";
      formTag.textContent = citation.form;
      item.append(formTag);
    }
    if (citation.urls && citation.urls.detail) {
      const link = document.createElement("a");
      link.href = citation.urls.detail;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "View filing";
      item.append(link);
    } else if (citation.urls && citation.urls.interactive) {
      const link = document.createElement("a");
      link.href = citation.urls.interactive;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "View filing";
      item.append(link);
    }
    list.append(item);
  });
  details.append(list);
  return details;
}

function createExportSection(exports) {
  if (!Array.isArray(exports) || !exports.length) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-exports";
  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = "Export";
  wrapper.append(title);
  const buttonRow = document.createElement("div");
  buttonRow.className = "artifact-export-buttons";
  exports.forEach((entry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "artifact-export-button";
    button.textContent = entry.label || entry.type.toUpperCase();
    button.addEventListener("click", () => handleExport(entry));
    buttonRow.append(button);
  });
  wrapper.append(buttonRow);
  return wrapper;
}

function handleExport(payload) {
  if (!payload || typeof payload !== "object") {
    return;
  }
  if (payload.type === "csv") {
    downloadCsv(payload);
    return;
  }
  if (payload.type === "pdf") {
    openPdfPreview(payload);
  }
}

function downloadCsv(payload) {
  const headers = Array.isArray(payload.headers) ? payload.headers : [];
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  if (!headers.length || !rows.length) {
    return;
  }
  const lines = [];
  lines.push(headers.map(formatCsvValue).join(","));
  rows.forEach((row) => {
    const safeRow = Array.isArray(row) ? row : [];
    lines.push(safeRow.map(formatCsvValue).join(","));
  });
  if (payload.descriptor) {
    lines.unshift(`# ${payload.descriptor}`);
  }
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = payload.filename || `benchmarkos-export-${Date.now()}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function formatCsvValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  const stringValue = String(value);
  if (/[",\n]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

function openPdfPreview(payload) {
  const headers = Array.isArray(payload.headers) ? payload.headers : [];
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  if (!headers.length || !rows.length) {
    alert("Nothing to export yet.");
    return;
  }
  const win = window.open("", "_blank");
  if (!win) {
    alert("Unable to open preview window. Allow pop-ups and try again.");
    return;
  }
  const title = payload.title || "BenchmarkOS export";
  const descriptor = payload.descriptor ? `<p><strong>Period:</strong> ${payload.descriptor}</p>` : "";
  const highlights = Array.isArray(payload.highlights) && payload.highlights.length
    ? `<ul>${payload.highlights.map((line) => `<li>${line}</li>`).join("")}</ul>`
    : "";
  const tableRows = rows
    .map(
      (row) =>
        `<tr>${row
          .map((value, index) =>
            index === 0
              ? `<th scope="row">${value}</th>`
              : `<td>${value}</td>`
          )
          .join("")}</tr>`
    )
    .join("");
  const html = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${title}</title>
    <style>
      body { font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #0f172a; }
      h1 { font-size: 20px; margin-bottom: 8px; }
      table { border-collapse: collapse; width: 100%; margin-top: 16px; }
      th, td { border: 1px solid #cbd5f5; padding: 6px 10px; text-align: right; font-size: 13px; }
      th:first-child, td:first-child { text-align: left; }
      th { background: #eff6ff; }
      ul { margin: 12px 0; padding-left: 18px; }
      .meta { font-size: 12px; color: #475569; margin-top: 4px; }
    </style>
  </head>
  <body>
    <h1>${title}</h1>
    ${descriptor}
    ${highlights}
    <table>
      <thead>
        <tr>${headers.map((header, index) => `<${index === 0 ? "th scope=\"col\"" : "th"}>${header}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${tableRows}
      </tbody>
    </table>
    <p class="meta">Generated ${new Date().toLocaleString()}</p>
  </body>
</html>`;
  win.document.write(html);
  win.document.close();
  win.focus();
  try {
    win.print();
  } catch (error) {
    // noop
  }
}

function showAssistantTyping() {
  return appendMessage("assistant", "", { isPlaceholder: true, animate: false });
}

function resolvePendingMessage(
  wrapper,
  role,
  text,
  { forceScroll = false, artifacts = null } = {}
) {
  if (!wrapper) {
    appendMessage(role, text, { forceScroll, smooth: true, artifacts });
    return null;
  }
  updateMessageRole(wrapper, role);
  wrapper.classList.remove("typing");
  setMessageBody(wrapper, text);
  renderMessageArtifacts(wrapper, artifacts);
  scrollChatToBottom({ smooth: true, force: forceScroll });
  return wrapper;
}

function buildMessageBlocks(text) {
  const fragments = [];
  const blocks = splitBlocks(text);

  blocks.forEach((block) => {
    if (block.type === "table") {
      fragments.push(renderTable(block.lines));
    } else {
      const div = document.createElement("div");
      div.className = "message-content";
      div.textContent = block.text;
      fragments.push(div);
    }
  });

  if (!blocks.length) {
    const div = document.createElement("div");
    div.className = "message-content";
    div.textContent = text;
    fragments.push(div);
  }

  return fragments;
}

function splitBlocks(text) {
  const lines = text.split(/\r?\n/);
  const blocks = [];
  let buffer = [];

  const flush = () => {
    if (!buffer.length) {
      return;
    }
    const trimmedLines = buffer.map((line) => line);
    if (looksLikeTable(trimmedLines)) {
      blocks.push({ type: "table", lines: trimmedLines });
    } else {
      blocks.push({ type: "text", text: buffer.join("\n") });
    }
    buffer = [];
  };

  lines.forEach((line) => {
    const normalized = line.replace(/\r/g, "");
    if (!normalized.trim()) {
      flush();
    } else {
      buffer.push(normalized);
    }
  });
  flush();

  return blocks;
}

function looksLikeTable(lines) {
  if (lines.length < 2) {
    return false;
  }
  if (!lines[0].includes("|")) {
    return false;
  }
  const hasSeparator = lines.some((line, index) => {
    if (index === 0) return false;
    return /^[\s\-\+=|]+$/.test(line);
  });
  if (!hasSeparator) {
    return false;
  }
  const rowCount = lines.filter((line) => line.includes("|")).length;
  return rowCount >= 2;
}

function renderTable(lines) {
  const wrapper = document.createElement("div");
  wrapper.className = "message-table";

  const table = document.createElement("table");
  table.className = "ascii-table";

  const compact = lines.filter((line) => line.trim().length);
  if (!compact.length) {
    return wrapper;
  }

  const headerCells = parseRow(compact[0]);
  let rowIndex = 1;
  while (rowIndex < compact.length && /^[\s\-\+=|]+$/.test(compact[rowIndex])) {
    rowIndex += 1;
  }

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  headerCells.forEach((cell) => {
    const th = document.createElement("th");
    th.textContent = cell;
    headRow.append(th);
  });
  thead.append(headRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  for (let i = rowIndex; i < compact.length; i += 1) {
    const cells = parseRow(compact[i]);
    if (!cells.length) {
      continue;
    }
    const row = document.createElement("tr");
    cells.forEach((cell, idx) => {
      const td = document.createElement("td");
      const parsed = parseNumericCell(cell);
      if (parsed.isNumeric) {
        td.classList.add("numeric");
        const value = document.createElement("span");
        value.className = "cell-value";
        value.textContent = parsed.value;
        td.append(value);
        if (parsed.suffix) {
          const suffix = document.createElement("span");
          suffix.className = "cell-suffix";
          suffix.textContent = parsed.suffix;
          td.append(suffix);
        }
      } else {
        td.textContent = parsed.value;
      }
      if (idx === 0) {
        td.scope = "row";
      }
      row.append(td);
    });
    tbody.append(row);
  }
  table.append(tbody);
  wrapper.append(table);
  return wrapper;
}

function parseRow(line) {
  return line
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}

function parseNumericCell(rawValue) {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return { isNumeric: false, value: "", suffix: "" };
  }

  const match = trimmed.match(/^([+-]?\$?[\d,]+(?:\.\d+)?)(%?)(.*)$/);
  if (!match) {
    return { isNumeric: false, value: trimmed, suffix: "" };
  }

  const [, numericPart, percentPart, rest] = match;
  const numericMatch = numericPart.match(/^([+-]?)(\$?)([\d,]+(?:\.\d+)?)/);
  if (!numericMatch) {
    return { isNumeric: false, value: trimmed, suffix: "" };
  }

  const [, sign, currency, digits] = numericMatch;
  const numericValue = Number(digits.replace(/,/g, ""));
  if (Number.isNaN(numericValue)) {
    return { isNumeric: false, value: trimmed, suffix: "" };
  }

  const absValue = Math.abs(numericValue);
  let decimals = 0;
  if (absValue < 1) {
    decimals = 3;
  } else if (absValue < 1000) {
    decimals = 2;
  }

  const formatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  let valueText = formatter.format(absValue);
  if (currency) {
    valueText = currency + valueText;
  }
  if (numericValue < 0 && sign !== "+") {
    valueText = "-" + valueText;
  }
  if (percentPart) {
    valueText += percentPart;
  }

  const suffix = rest.trim();
  return { isNumeric: true, value: valueText, suffix };
}

function scrollChatToBottom({ smooth = true } = {}) {
  if (!chatLog) {
    return;
  }
  const behavior = smooth ? "smooth" : "auto";
  const schedule = window.requestAnimationFrame || ((fn) => setTimeout(fn, 16));
  schedule(() => {
    chatLog.scrollTo({ top: chatLog.scrollHeight, behavior });
  });
}

function hideIntroPanel() {
  if (!introPanel) {
    return;
  }
  introPanel.classList.add("hidden");
}

function showIntroPanel() {
  if (!introPanel) {
    return;
  }
  introPanel.classList.remove("hidden");
}

function setupReportMenus() {
  if (reportMenu) {
    return;
  }

  reportMenu = document.createElement("div");
  reportMenu.className = "report-menu hidden";
  reportMenu.setAttribute("role", "menu");
  reportMenu.innerHTML = `
    <button class="menu-item" data-action="share" role="menuitem">Share</button>
    <button class="menu-item" data-action="rename" role="menuitem">Rename</button>
    <button class="menu-item has-submenu" data-action="move" role="menuitem">
      <span>Move to Project</span>
      <span class="submenu-indicator">›</span>
    </button>
    <button class="menu-item" data-action="export" role="menuitem">Export…</button>
    <button class="menu-item" data-action="duplicate" role="menuitem">Duplicate</button>
    <button class="menu-item" data-action="copy-link" role="menuitem">Copy Link</button>
    <button class="menu-item" data-action="archive" role="menuitem">Archive</button>
    <div class="menu-divider" role="separator"></div>
    <button class="menu-item danger" data-action="delete" role="menuitem">Delete</button>
  `;
  reportMenu.tabIndex = -1;

  projectMenu = document.createElement("div");
  projectMenu.className = "report-menu report-submenu hidden";
  projectMenu.setAttribute("role", "menu");

  document.body.append(reportMenu, projectMenu);

  reportMenu.addEventListener("click", handleReportMenuClick);
  reportMenu.addEventListener("keydown", handleReportMenuKeyDown);
  projectMenu.addEventListener("click", handleProjectMenuClick);
  projectMenu.addEventListener("keydown", handleProjectMenuKeyDown);

  document.addEventListener("mousedown", handleGlobalPointerDown);
  document.addEventListener("keydown", handleGlobalKeyDown);
  window.addEventListener("resize", closeReportMenu);
}

function handleGlobalPointerDown(event) {
  if (
    reportMenu &&
    !reportMenu.classList.contains("hidden") &&
    !reportMenu.contains(event.target) &&
    !(activeMenuAnchor && activeMenuAnchor.contains(event.target)) &&
    !(projectMenu && !projectMenu.classList.contains("hidden") && projectMenu.contains(event.target))
  ) {
    closeReportMenu();
  }
  if (
    shareModalBackdrop &&
    !shareModalBackdrop.classList.contains("hidden") &&
    !shareModalBackdrop.querySelector(".share-modal").contains(event.target)
  ) {
    closeShareModal();
  }
}

function handleGlobalKeyDown(event) {
  if (event.key === "Escape") {
    if (shareModalBackdrop && !shareModalBackdrop.classList.contains("hidden")) {
      closeShareModal();
      return;
    }
    closeReportMenu();
  }
}

function handleReportMenuClick(event) {
  const target = event.target.closest(".menu-item");
  if (!target || !reportMenu) {
    return;
  }
  event.preventDefault();
  const action = target.dataset.action;
  if (!action) {
    return;
  }
  if (action === "move") {
    openProjectSubmenu(activeMenuConversationId, target);
    return;
  }
  closeProjectMenu();
  closeReportMenu();
  if (activeMenuConversationId) {
    handleReportAction(action, activeMenuConversationId);
  }
}

function handleReportAction(action, conversationId) {
  const conversation = conversations.find((entry) => entry.id === conversationId);
  if (!conversation) {
    return;
  }
  if (action === "delete") {
    deleteConversation(conversationId);
  }
}

function handleReportMenuKeyDown(event) {
  if (!reportMenu) {
    return;
  }
  const items = Array.from(reportMenu.querySelectorAll(".menu-item"));
  if (!items.length) {
    return;
  }
  const currentIndex = items.indexOf(document.activeElement);

  if (event.key === "ArrowDown") {
    event.preventDefault();
    const next = items[(currentIndex + 1) % items.length];
    focusMenuItem(next, items);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    const next = items[(currentIndex - 1 + items.length) % items.length];
    focusMenuItem(next, items);
  } else if (event.key === "ArrowRight") {
    const action = document.activeElement?.dataset.action;
    if (action === "move" && activeMenuConversationId) {
      event.preventDefault();
      openProjectSubmenu(activeMenuConversationId, document.activeElement);
    }
  } else if (event.key === "ArrowLeft") {
    if (projectMenu && !projectMenu.classList.contains("hidden")) {
      event.preventDefault();
      closeProjectMenu();
      focusMenuItem(document.activeElement, items);
    }
  } else if (event.key === "Enter" || event.key === " ") {
    document.activeElement?.click();
  } else if (event.key === "Escape") {
    closeReportMenu();
  }
}

function focusMenuItem(target, items) {
  if (!target) {
    return;
  }
  items.forEach((item) => {
    item.tabIndex = -1;
  });
  target.tabIndex = 0;
  target.focus();
}

function openReportMenu(conversation, anchor, coords) {
  setupReportMenus();

  closeProjectMenu();

  activeMenuConversationId = conversation.id;
  if (activeMenuAnchor && activeMenuAnchor !== anchor) {
    activeMenuAnchor.setAttribute("aria-expanded", "false");
  }
  activeMenuAnchor = anchor || null;
  if (activeMenuAnchor) {
    activeMenuAnchor.setAttribute("aria-expanded", "true");
  }

  reportMenu.dataset.conversationId = conversation.id;
  reportMenu.classList.remove("hidden");
  reportMenu.style.visibility = "hidden";
  reportMenu.style.left = "0px";
  reportMenu.style.top = "0px";

  requestAnimationFrame(() => {
    const menuRect = reportMenu.getBoundingClientRect();
    let left;
    let top;
    if (coords) {
      left = coords.x;
      top = coords.y;
    } else if (anchor) {
      const rect = anchor.getBoundingClientRect();
      left = rect.right + 8;
      top = rect.top;
    } else {
      left = window.innerWidth / 2 - menuRect.width / 2;
      top = window.innerHeight / 2 - menuRect.height / 2;
    }
    if (left + menuRect.width > window.innerWidth - 12) {
      left = window.innerWidth - menuRect.width - 12;
    }
    if (top + menuRect.height > window.innerHeight - 12) {
      top = window.innerHeight - menuRect.height - 12;
    }
    reportMenu.style.left = `${Math.max(12, left)}px`;
    reportMenu.style.top = `${Math.max(12, top)}px`;
    reportMenu.style.visibility = "visible";
    const items = Array.from(reportMenu.querySelectorAll(".menu-item"));
    focusMenuItem(items[0], items);
  });
}

function closeProjectMenu() {
  if (projectMenu) {
    projectMenu.classList.add("hidden");
  }
}

function openProjectSubmenu(conversationId, anchor) {
  if (!projectMenu || !reportMenu) {
    return;
  }
  projectMenu.innerHTML = `
    ${RECENT_PROJECTS.map(
      (name, idx) =>
        `<button class="menu-item" data-project-index="${idx}" data-project-name="${name}" role="menuitem">${name}</button>`
    ).join("")}
    <div class="menu-divider" role="separator"></div>
    <button class="menu-item" data-project-action="browse" role="menuitem">Browse all projects…</button>
  `;
  projectMenu.dataset.conversationId = conversationId;
  projectMenu.classList.remove("hidden");
  projectMenu.style.visibility = "hidden";
  const menuRect = projectMenu.getBoundingClientRect();
  const anchorRect = anchor.getBoundingClientRect();
  const reportRect = reportMenu.getBoundingClientRect();
  let left = reportRect.right + 8;
  let top = anchorRect.top;
  if (left + menuRect.width > window.innerWidth - 12) {
    left = reportRect.left - menuRect.width - 8;
  }
  if (top + menuRect.height > window.innerHeight - 12) {
    top = window.innerHeight - menuRect.height - 12;
  }
  projectMenu.style.left = `${Math.max(12, left)}px`;
  projectMenu.style.top = `${Math.max(12, top)}px`;
  projectMenu.style.visibility = "visible";
  const items = Array.from(projectMenu.querySelectorAll(".menu-item"));
  focusMenuItem(items[0], items);
}

function handleProjectMenuClick(event) {
  const button = event.target.closest(".menu-item");
  if (!button) {
    return;
  }
  event.preventDefault();
  const conversationId = projectMenu.dataset.conversationId;
  const conversation = conversations.find((entry) => entry.id === conversationId);
  if (!conversation) {
    closeProjectMenu();
    closeReportMenu();
    return;
  }
  if (button.dataset.projectAction === "browse") {
    const chosen = window.prompt("Enter project name to move this report into:", conversation.projectName || "");
    if (chosen) {
      conversation.projectName = chosen;
      conversation.projectId = `proj-${chosen.toLowerCase().replace(/\s+/g, "-")}`;
      conversation.updatedAt = new Date().toISOString();
      saveConversations();
      renderConversationList();
      showToast(`Moved to ${chosen}`, "success");
    }
    closeProjectMenu();
    closeReportMenu();
    return;
  }
  const index = Number(button.dataset.projectIndex);
  const name = RECENT_PROJECTS[index];
  if (name) {
    conversation.projectName = name;
    conversation.projectId = `recent-${index}`;
    conversation.updatedAt = new Date().toISOString();
    saveConversations();
    renderConversationList();
    showToast(`Moved to ${name}`, "success");
  }
  closeProjectMenu();
  closeReportMenu();
}

function handleProjectMenuKeyDown(event) {
  const items = Array.from(projectMenu?.querySelectorAll(".menu-item") || []);
  if (!items.length) {
    return;
  }
  const currentIndex = items.indexOf(document.activeElement);
  if (event.key === "ArrowDown") {
    event.preventDefault();
    const next = items[(currentIndex + 1) % items.length];
    focusMenuItem(next, items);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    const next = items[(currentIndex - 1 + items.length) % items.length];
    focusMenuItem(next, items);
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    closeProjectMenu();
    const itemsMain = Array.from(reportMenu?.querySelectorAll(".menu-item") || []);
    const moveButton = itemsMain.find((item) => item.dataset.action === "move");
    if (moveButton) {
      focusMenuItem(moveButton, itemsMain);
    }
  } else if (event.key === "Enter" || event.key === " ") {
    document.activeElement?.click();
  } else if (event.key === "Escape") {
    closeProjectMenu();
    closeReportMenu();
  }
}

function closeReportMenu() {
  if (reportMenu) {
    reportMenu.classList.add("hidden");
  }
  closeProjectMenu();
  if (activeMenuAnchor) {
    activeMenuAnchor.setAttribute("aria-expanded", "false");
  }
  activeMenuConversationId = null;
  activeMenuAnchor = null;
}

function ensureShareModal() {
  if (shareModalBackdrop) {
    return;
  }
  shareModalBackdrop = document.createElement("div");
  shareModalBackdrop.className = "share-modal-backdrop hidden";
  shareModalBackdrop.innerHTML = `
    <div class="share-modal" role="dialog" aria-modal="true" aria-labelledby="share-modal-title">
      <header>
        <h2 id="share-modal-title">Share saved report</h2>
        <button type="button" class="close" aria-label="Close share dialog">×</button>
      </header>
      <div class="share-toggle">
        <label>
          <span class="share-status-text"></span>
          <span class="share-status-subtext"></span>
        </label>
        <input type="checkbox" aria-label="Enable public link" />
      </div>
      <div class="share-link-row">
        <input type="text" readonly />
        <button type="button" class="copy-link">Copy link</button>
      </div>
      <footer>
        <button type="button" class="secondary">Cancel</button>
        <button type="button" class="primary">Save</button>
      </footer>
    </div>
  `;
  document.body.append(shareModalBackdrop);

  shareModalElement = shareModalBackdrop.querySelector(".share-modal");
  shareToggleInput = shareModalBackdrop.querySelector(".share-toggle input");
  shareStatusTextEl = shareModalBackdrop.querySelector(".share-status-text");
  shareStatusSubTextEl = shareModalBackdrop.querySelector(".share-status-subtext");
  shareLinkInput = shareModalBackdrop.querySelector(".share-link-row input");
  shareCopyButton = shareModalBackdrop.querySelector(".share-link-row .copy-link");
  shareCancelButton = shareModalBackdrop.querySelector("footer .secondary");
  sharePrimaryButton = shareModalBackdrop.querySelector("footer .primary");
  const closeButton = shareModalBackdrop.querySelector("header .close");

  shareModalBackdrop.addEventListener("mousedown", (event) => {
    if (event.target === shareModalBackdrop) {
      closeShareModal();
    }
  });
  closeButton.addEventListener("click", closeShareModal);
  shareCancelButton.addEventListener("click", closeShareModal);
  sharePrimaryButton.addEventListener("click", applyShareModal);
  shareCopyButton.addEventListener("click", copyShareLink);
  shareToggleInput.addEventListener("change", handleShareToggleChange);
}

function openShareModal(conversation) {
  ensureShareModal();
  if (!shareModalBackdrop || !shareToggleInput) {
    return;
  }
  shareModalConversationId = conversation.id;
  const share = ensureShareRecord(conversation);
  shareToggleInput.checked = Boolean(share.isPublic);
  updateShareModalDisplay(conversation);
  shareModalBackdrop.classList.remove("hidden");
  requestAnimationFrame(() => {
    shareToggleInput.focus();
  });
}

function closeShareModal() {
  if (shareModalBackdrop) {
    shareModalBackdrop.classList.add("hidden");
  }
  shareModalConversationId = null;
}

function updateShareModalDisplay(conversation) {
  if (!shareToggleInput || !shareStatusTextEl || !shareStatusSubTextEl || !shareLinkInput || !shareCopyButton) {
    return;
  }
  const share = ensureShareRecord(conversation);
  const enabled = Boolean(shareToggleInput.checked);
  shareStatusTextEl.textContent = enabled ? "Public link is enabled" : "Public link is disabled";
  shareStatusSubTextEl.textContent = enabled
    ? "Anyone with the link can view this report."
    : "Only you can access this report.";
  if (enabled) {
    const url = buildShareUrl(conversation);
    shareLinkInput.value = url;
    shareLinkInput.disabled = false;
    shareCopyButton.disabled = false;
  } else {
    shareLinkInput.value = "Enable sharing to generate a link.";
    shareLinkInput.disabled = true;
    shareCopyButton.disabled = true;
  }
  sharePrimaryButton.textContent = "Save";
}

function handleShareToggleChange() {
  const conversation = conversations.find((entry) => entry.id === shareModalConversationId);
  if (!conversation) {
    return;
  }
  updateShareModalDisplay(conversation);
}

function applyShareModal() {
  const conversation = conversations.find((entry) => entry.id === shareModalConversationId);
  if (!conversation) {
    closeShareModal();
    return;
  }
  const share = ensureShareRecord(conversation);
  const enabled = Boolean(shareToggleInput?.checked);
  share.isPublic = enabled;
  if (enabled) {
    ensureShareToken(conversation);
    showToast("Public link enabled", "success");
  } else {
    showToast("Sharing disabled");
  }
  saveConversations();
  renderConversationList();
  closeShareModal();
}

function copyShareLink() {
  const conversation = conversations.find((entry) => entry.id === shareModalConversationId);
  if (!conversation) {
    return;
  }
  const share = ensureShareRecord(conversation);
  if (!share.isPublic) {
    showToast("Enable sharing before copying link");
    return;
  }
  const url = buildShareUrl(conversation);
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(url).then(
      () => showToast("Link copied", "success"),
      () => window.prompt("Copy link:", url)
    );
  } else {
    window.prompt("Copy link:", url);
    showToast("Copy the link shown and share manually.");
  }
}


function setSending(state) {
  isSending = state;
  sendButton.disabled = state;
  chatInput.disabled = state;
  sendButton.textContent = state ? "Sending..." : "Send";
}

function loadStoredConversations() {
  try {
    if (!window.localStorage) {
      return [];
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((entry) => entry && entry.id)
      .map((entry) => ({
        id: entry.id,
        remoteId: entry.remoteId || null,
        title: entry.title || "",
        createdAt: entry.createdAt || entry.updatedAt || new Date().toISOString(),
        updatedAt: entry.updatedAt || entry.createdAt || new Date().toISOString(),
        messages: Array.isArray(entry.messages) ? entry.messages : [],
        previewPrompt:
          entry.previewPrompt ||
          entry.firstPrompt ||
          (Array.isArray(entry.messages)
            ? (entry.messages.find((msg) => msg && msg.role === "user" && typeof msg.text === "string") || {})
                .text || ""
            : ""),
        intent: entry.intent || "insight",
        tickers: Array.isArray(entry.tickers) ? entry.tickers : [],
        period: entry.period || "",
        metricLabel: entry.metricLabel || "",
        archived: Boolean(entry.archived),
        projectId: entry.projectId || null,
        projectName: entry.projectName || entry.project || "",
        share:
          entry.share && typeof entry.share === "object"
            ? { isPublic: Boolean(entry.share.isPublic), token: entry.share.token || null }
            : { isPublic: false, token: null },
      }))
      .map((conversation) => {
        const summary = buildSemanticSummary(conversation.previewPrompt || conversation.title || "");
        conversation.title = summary.title;
        conversation.intent = summary.intent;
        conversation.tickers = summary.tickers;
        conversation.period = summary.period;
        conversation.metricLabel = summary.metric;
        return conversation;
      })
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  } catch (error) {
    console.warn("Failed to load stored conversations", error);
    return [];
  }
}

function saveConversations() {
  try {
    if (!window.localStorage) {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (error) {
    console.warn("Unable to persist conversations", error);
  }
}

function generateLocalId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function extractTickers(text) {
  const matches = text.match(/\b[A-Za-z]{1,5}(?:-[A-Za-z]{1,2})?\b/g) || [];
  const tickers = [];
  matches.forEach((token) => {
    const upper = token.toUpperCase();
    if (upper.length < 2 || upper.length > 6) {
      return;
    }
    if (!/^[A-Z]+(?:-[A-Z]+)?$/.test(upper)) {
      return;
    }
    if (TICKER_STOPWORDS.has(upper)) {
      return;
    }
    if (!tickers.includes(upper)) {
      tickers.push(upper);
    }
  });
  return tickers.slice(0, 3);
}

function extractPeriod(text) {
  const periodMatchers = [
    { regex: /\bLTM\b/i, format: () => "LTM" },
    {
      regex: /\bFY\s*(\d{4})\b/i,
      format: (match) => `FY${match[1]}`,
    },
    {
      regex: /\bQ([1-4])\s*(?:FY)?\s*(\d{4})\b/i,
      format: (match) => `Q${match[1]} ${match[2]}`,
    },
    {
      regex: /\b(20\d{2})\s*[-–]\s*(20\d{2})\b/,
      format: (match) => `${match[1]}-${match[2]}`,
    },
    {
      regex: /\blast\s+(\d+)\s+(?:quarters?|qtrs?)\b/i,
      format: (match) => `Last ${match[1]} Quarters`,
    },
    {
      regex: /\b(20\d{2})\b/,
      format: (match) => match[1],
    },
  ];

  for (const matcher of periodMatchers) {
    const result = matcher.regex.exec(text);
    if (result) {
      return matcher.format(result);
    }
  }
  return "";
}

function detectIntentMeta(text, tickers) {
  const lower = text.toLowerCase();
  if (/^\/?compare\b/.test(lower) || (lower.includes("compare") && lower.includes(" vs ")) || tickers.length >= 2) {
    return { intent: "compare", label: "Analysis" };
  }
  if (/scenario|what if|impact if/.test(lower)) {
    return { intent: "scenario", label: "Scenario Analysis" };
  }
  if (/^\/?fact\b|\bfact sheet\b|\bsec\b.*line item\b/.test(lower)) {
    return { intent: "fact", label: "Fact Sheet" };
  }
  if (/summari[sz]e\b|\btoday\b.*market\b|\bmovers\b|\bdaily\b/.test(lower)) {
    return { intent: "summarize", label: "Market Summary" };
  }
  if (
    /metric\b|\bkpi\b|\beps\b|\broe\b|\bfcf\b|\bpe\b|\btsr\b|\brevenue\b|\bmargin\b|\bgrowth\b/.test(
      lower
    )
  ) {
    return { intent: "metric", label: "KPI Report" };
  }
  return { intent: "insight", label: "Insight" };
}

function detectMetricLabel(text, intent) {
  for (const entry of METRIC_KEYWORD_MAP) {
    if (entry.regex.test(text)) {
      return entry.label;
    }
  }
  if (intent === "summarize") {
    return "Market";
  }
  if (intent === "scenario") {
    return "Scenario";
  }
  return "";
}

function formatWord(word) {
  if (!word) {
    return "";
  }
  if (word === "vs") {
    return "vs";
  }
  if (/^FY\d{4}$/i.test(word)) {
    return word.toUpperCase();
  }
  if (/^Q[1-4]$/.test(word)) {
    return word.toUpperCase();
  }
  if (/^[A-Z0-9-]{2,}$/.test(word)) {
    return word.toUpperCase();
  }
  const lower = word.toLowerCase();
  return lower.replace(/^\w/, (char) => char.toUpperCase());
}

function composeTitleComponents({ tickers, period, metricLabel, intentInfo }) {
  const words = [];
  const seen = new Set();

  const pushWord = (value) => {
    if (!value) return;
    const cleaned = value.trim();
    if (!cleaned) return;
    cleaned.split(/\s+/).forEach((w) => {
      if (!w) {
        return;
      }
      const key = w.toLowerCase();
      if (!seen.has(key)) {
        words.push(w);
        seen.add(key);
      }
    });
  };

  if (tickers.length >= 2) {
    pushWord(tickers[0]);
    pushWord("vs");
    pushWord(tickers[1]);
    if (tickers.length > 2) {
      pushWord("Peers");
    }
  } else if (tickers.length === 1) {
    pushWord(tickers[0]);
  }

  if (period) {
    pushWord(period);
  }

  const descriptor = [];
  const metricKey = metricLabel && metricLabel !== "KPI" && metricLabel !== "Market" ? metricLabel : "";

  switch (intentInfo.intent) {
    case "compare":
      if (metricKey) descriptor.push(metricKey);
      descriptor.push("Analysis");
      break;
    case "metric":
      if (metricKey) descriptor.push(metricKey);
      descriptor.push("KPI");
      descriptor.push("Report");
      break;
    case "fact":
      if (metricKey) descriptor.push(metricKey);
      descriptor.push(metricKey && metricKey !== "Snapshot" ? "Snapshot" : "Fact");
      break;
    case "summarize":
      if (metricKey && metricKey !== "Market") descriptor.push(metricKey);
      descriptor.push("Market");
      descriptor.push("Summary");
      break;
    case "scenario":
      if (metricKey) descriptor.push(metricKey);
      descriptor.push("Scenario");
      descriptor.push("Analysis");
      break;
    default:
      if (metricKey) descriptor.push(metricKey);
      descriptor.push("Insight");
      break;
  }

  descriptor.forEach((part) => pushWord(part));

  const fallbackWords = ["Insight", "Report", "Overview", "Brief"];
  let fallbackIndex = 0;
  while (words.length < 4 && fallbackIndex < fallbackWords.length) {
    pushWord(fallbackWords[fallbackIndex]);
    fallbackIndex += 1;
  }

  if (words.length > 6) {
    words.length = 6;
  }

  const formatted = words.map((word) => formatWord(word));
  let title = formatted.join(" ");

  while (title.length > 42 && formatted.length > 1) {
    formatted.pop();
    title = formatted.join(" ");
  }

  if (title.length > 42) {
    title = `${title.slice(0, 41).trimEnd()}…`;
  }

  return title;
}

function buildSemanticSummary(prompt) {
  const trimmed = (prompt || "").trim();
  if (!trimmed) {
    return { title: "Untitled Chat", intent: "insight", tickers: [], period: "", metric: "" };
  }
  const tickers = extractTickers(trimmed);
  const period = extractPeriod(trimmed);
  const intentInfo = detectIntentMeta(trimmed, tickers);
  const metricLabel = detectMetricLabel(trimmed, intentInfo.intent);
  const title = composeTitleComponents({ tickers, period, metricLabel, intentInfo });
  return {
    title: title || "Untitled Chat",
    intent: intentInfo.intent,
    tickers,
    period,
    metric: metricLabel,
  };
}

function ensureShareRecord(conversation) {
  if (!conversation.share || typeof conversation.share !== "object") {
    conversation.share = { isPublic: false, token: null };
  }
  return conversation.share;
}

function ensureShareToken(conversation) {
  const share = ensureShareRecord(conversation);
  if (!share.token) {
    share.token = `${conversation.id}-${Math.random().toString(36).slice(2, 8)}`;
  }
  return share.token;
}

function buildShareUrl(conversation) {
  const token = ensureShareToken(conversation);
  return `${window.location.origin.replace(/\/$/, "")}/reports/${token}`;
}

function generateTitle(text) {
  return buildSemanticSummary(text).title;
}

function ensureActiveConversation() {
  if (activeConversation) {
    return activeConversation;
  }
  const timestamp = new Date().toISOString();
  activeConversation = {
    id: generateLocalId(),
    remoteId: null,
    title: "",
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: [],
    previewPrompt: "",
    intent: "insight",
    tickers: [],
    period: "",
    metricLabel: "",
    archived: false,
    projectId: null,
    projectName: "",
    share: { isPublic: false, token: null },
  };
  return activeConversation;
}

function promoteConversation(conversation) {
  conversations = [conversation, ...conversations.filter((entry) => entry.id !== conversation.id)];
}

function recordMessage(role, text, metadata = null) {
  const conversation = ensureActiveConversation();
  const timestamp = new Date().toISOString();
  if (!conversations.find((entry) => entry.id === conversation.id)) {
    conversations = [conversation, ...conversations];
  }
  if (role === "user" && !conversation.previewPrompt) {
    conversation.previewPrompt = text;
    const summary = buildSemanticSummary(text);
    conversation.title = summary.title;
    conversation.intent = summary.intent;
    conversation.tickers = summary.tickers;
    conversation.period = summary.period;
    conversation.metricLabel = summary.metric;
    conversation.archived = false;
  }
  const messageEntry = { role, text, timestamp };
  if (metadata) {
    try {
      messageEntry.metadata = JSON.parse(JSON.stringify(metadata));
    } catch (error) {
      messageEntry.metadata = metadata;
    }
  }
  conversation.messages.push(messageEntry);
  if (!conversation.title && conversation.previewPrompt) {
    const summary = buildSemanticSummary(conversation.previewPrompt);
    conversation.title = summary.title;
    conversation.intent = summary.intent;
    conversation.tickers = summary.tickers;
    conversation.period = summary.period;
    conversation.metricLabel = summary.metric;
  }
  if (!conversation.title) {
    conversation.title = "Untitled Chat";
  }
  conversation.updatedAt = timestamp;
  promoteConversation(conversation);
  saveConversations();
  renderConversationList();
}

function formatRelativeTime(isoString) {
  if (!isoString) {
    return "";
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const diff = Date.now() - date.getTime();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diff < minute) {
    return "Just now";
  }
  if (diff < hour) {
    const value = Math.floor(diff / minute);
    return `${value} min${value === 1 ? "" : "s"} ago`;
  }
  if (diff < day) {
    const value = Math.floor(diff / hour);
    return `${value} hr${value === 1 ? "" : "s"} ago`;
  }
  if (diff < 7 * day) {
    const value = Math.floor(diff / day);
    return `${value} day${value === 1 ? "" : "s"} ago`;
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function getFilteredConversations() {
  if (!conversationSearch) {
    return conversations;
  }
  const query = conversationSearch.toLowerCase();
  return conversations.filter((conversation) => {
    const title = (conversation.title || "").toLowerCase();
    if (title.includes(query)) {
      return true;
    }
    return conversation.messages.some(
      (message) =>
        typeof message.text === "string" && message.text.toLowerCase().includes(query)
    );
  });
}

function renderConversationList() {
  if (!conversationList) {
    return;
  }

  conversationList.innerHTML = "";

  const items = getFilteredConversations().filter((conversation) => !conversation.archived);

  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = conversationSearch
      ? "No reports match your filter yet."
      : "Saved analyses will appear here.";
    conversationList.append(empty);
    return;
  }

  items.forEach((conversation) => {
    const item = document.createElement("div");
    item.className = "conversation-item";
    item.setAttribute("role", "listitem");
    if (activeConversation && conversation.id === activeConversation.id) {
      item.classList.add("active");
    }

    const linkButton = document.createElement("button");
    linkButton.type = "button";
    linkButton.className = "conversation-link";
    linkButton.dataset.id = conversation.id;

    const title = document.createElement("span");
    title.className = "conversation-title";
    title.textContent = conversation.title || "Untitled Chat";
    title.title = conversation.previewPrompt || conversation.title || "Untitled Chat";
    linkButton.title = title.title;

    const timestamp = document.createElement("span");
    timestamp.className = "conversation-timestamp";
    timestamp.textContent = formatRelativeTime(conversation.updatedAt);

    linkButton.append(title, timestamp);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "conversation-delete";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteConversation(conversation.id);
    });

    item.append(linkButton, deleteButton);
    conversationList.append(item);
  });
}

function loadConversation(conversationId) {
  const conversation = conversations.find((entry) => entry.id === conversationId);
  if (!conversation) {
    return;
  }
  activeConversation = conversation;

  closeReportMenu();

  if (currentUtilityKey) {
    closeUtilityPanel();
    resetNavActive();
  }

  if (chatLog) {
    chatLog.innerHTML = "";
  }

  if (conversation.messages.length) {
    hideIntroPanel();
  } else {
    showIntroPanel();
  }

  conversation.messages.forEach((message) => {
    appendMessage(message.role, message.text, {
      smooth: false,
      animate: false,
      artifacts: message.metadata || null,
    });
  });

  scrollChatToBottom({ smooth: false, force: true });
  renderConversationList();
  chatInput.focus();
}

function startNewConversation({ focusInput = true } = {}) {
  activeConversation = null;
  if (currentUtilityKey) {
    closeUtilityPanel();
    resetNavActive();
  }
  closeReportMenu();
  if (chatLog) {
    chatLog.innerHTML = "";
  }
  showIntroPanel();
  chatInput.value = "";
  if (focusInput) {
    chatInput.focus();
  }
  renderConversationList();
}

function deleteConversation(conversationId) {
  const index = conversations.findIndex((entry) => entry.id === conversationId);
  if (index === -1) {
    return;
  }

  const [removed] = conversations.splice(index, 1);
  saveConversations();

  if (activeConversation && removed.id === activeConversation.id) {
    const nextActive =
      conversations.find((entry) => !entry.archived) ||
      conversations.find((entry) => entry.archived) ||
      null;
    if (nextActive) {
      loadConversation(nextActive.id);
    } else {
      activeConversation = null;
      startNewConversation({ focusInput: false });
    }
    renderConversationList();
    return;
  }

  renderConversationList();
}

function setActiveNav(action) {
  if (!navItems || !navItems.length) {
    return;
  }
  navItems.forEach((item) => {
    const itemAction = item.dataset.action || "";
    item.classList.toggle("active", Boolean(action && itemAction === action));
  });
}

function resetNavActive() {
  setActiveNav(null);
}

function openUtilityPanel(key) {
  if (!utilityPanel || !utilityTitle || !utilityContent) {
    return;
  }
  const section = UTILITY_SECTIONS[key];
  if (!section) {
    return;
  }
  currentUtilityKey = key;
  utilityPanel.classList.remove("hidden");
  utilityTitle.textContent = section.title;
  utilityContent.innerHTML = section.html;
  if (typeof section.render === "function") {
    try {
      const maybePromise = section.render({ container: utilityContent, key });
      if (maybePromise && typeof maybePromise.then === "function") {
        maybePromise.catch((error) =>
          console.warn(`Utility panel "${key}" render error:`, error)
        );
      }
    } catch (error) {
      console.warn(`Utility panel "${key}" render error:`, error);
    }
  }
  setActiveNav(`open-${key}`);
  if (["help", "kpi-library", "company-universe", "filing-viewer"].includes(key)) {
    if (chatPanel) {
      chatPanel.classList.add("chat-panel--collapsed");
    }
    if (chatLog) {
      chatLog.classList.add("hidden");
    }
    if (chatFormContainer) {
      chatFormContainer.classList.add("chat-form--collapsed");
    }
  }
}

function closeUtilityPanel() {
  if (!utilityPanel || !utilityTitle || !utilityContent) {
    return;
  }
  utilityPanel.classList.add("hidden");
  utilityTitle.textContent = "";
  utilityContent.innerHTML = "";
  currentUtilityKey = null;
  if (chatPanel) {
    chatPanel.classList.remove("chat-panel--collapsed");
  }
  if (chatLog) {
    chatLog.classList.remove("hidden");
  }
  if (chatFormContainer) {
    chatFormContainer.classList.remove("chat-form--collapsed");
  }
}

function showChatSearch({ focus = true, source = "saved-reports" } = {}) {
  if (!chatSearchContainer) {
    return;
  }
  chatSearchContainer.classList.remove("hidden");
  setActiveNav(source);
  if (focus && chatSearchInput) {
    chatSearchInput.focus();
    chatSearchInput.select();
  }
}

function clearConversationSearch({ hide = false } = {}) {
  conversationSearch = "";
  if (chatSearchInput) {
    chatSearchInput.value = "";
  }
  if (hide && chatSearchContainer) {
    chatSearchContainer.classList.add("hidden");
  }
  renderConversationList();
}

function handleNavAction(action) {
  if (!action) {
    return;
  }
  if (action === "new-analysis") {
    closeUtilityPanel();
    clearConversationSearch({ hide: true });
    resetNavActive();
    startNewConversation();
    return;
  }
  if (action === "saved-reports" || action === "search-saved") {
    closeUtilityPanel();
    if (!chatSearchContainer) {
      return;
    }
    const isHidden = chatSearchContainer.classList.contains("hidden");
    if (isHidden) {
      showChatSearch({ focus: true, source: "saved-reports" });
      return;
    }
    if (conversationSearch) {
      showChatSearch({ focus: true, source: "saved-reports" });
      return;
    }
    clearConversationSearch({ hide: true });
    resetNavActive();
    return;
  }
  if (action === "open-company-universe") {
    const key = "company-universe";
    if (currentUtilityKey === key) {
      closeUtilityPanel();
      resetNavActive();
      return;
    }
    clearConversationSearch({ hide: true });
    openUtilityPanel(key);
    return;
  }
  if (action.startsWith("open-")) {
    const key = action.replace("open-", "");
    if (currentUtilityKey === key) {
      closeUtilityPanel();
      resetNavActive();
      return;
    }
    clearConversationSearch({ hide: true });
    openUtilityPanel(key);
    return;
  }
}

async function loadCompanyUniverseData() {
  if (companyUniverseData.length) {
    return companyUniverseData;
  }
  if (companyUniversePromise) {
    return companyUniversePromise;
  }
  companyUniversePromise = fetch(COMPANY_UNIVERSE_PATH, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Company universe fetch failed (${response.status})`);
      }
      return response.json();
    })
    .then((data) => {
      const normalised = Array.isArray(data) ? data : [];
      companyUniverseData = normalised.map((record) => {
        const coverage = (record.coverage || "complete").toLowerCase();
        const marketCap = Number.isFinite(record.market_cap) ? record.market_cap : null;
        return {
          ...record,
          coverage,
          market_cap: marketCap,
          market_cap_display: record.market_cap_display || record.marketCapDisplay || null,
          latest_filing: record.latest_filing || record.latestFiling || null,
          sector: record.sector || "Uncategorised",
        };
      });
      populateCompanyUniverseFilters(companyUniverseData);
      applyCompanyUniverseFilters();
      return companyUniverseData;
    })
    .catch((error) => {
      console.warn("Company universe load failed:", error);
      showToast("Unable to load company universe data. Please try again later.", "error");
      companyUniverseData = [];
      throw error;
    })
    .finally(() => {
      companyUniversePromise = null;
    });
  return companyUniversePromise;
}

function populateCompanyUniverseFilters(data) {
  if (!companySectorSelect) {
    return;
  }
  while (companySectorSelect.options.length > 1) {
    companySectorSelect.remove(1);
  }
  const sectors = Array.from(
    new Set(
      data
        .map((item) => item.sector || "")
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
  sectors.forEach((sector) => {
    const option = document.createElement("option");
    option.value = sector;
    option.textContent = sector;
    companySectorSelect.append(option);
  });
}

function getMostRecentCompanyRecord(records) {
  if (!Array.isArray(records) || !records.length) {
    return null;
  }
  return records
    .filter((entry) => entry.latest_filing)
    .sort((a, b) => Date.parse(b.latest_filing) - Date.parse(a.latest_filing))[0] || null;
}

function updateCompanyUniverseMeta({
  filteredCount = 0,
  totalCount = 0,
  sectorsCount = 0,
  latestRecord = null,
  coverage = null,
} = {}) {
  if (companyUniverseMetaUniverse) {
    if (totalCount > 0) {
      const displayFiltered = typeof filteredCount === "number" ? filteredCount : totalCount;
      if (displayFiltered === totalCount) {
        companyUniverseMetaUniverse.textContent = `${totalCount.toLocaleString()} companies tracked`;
      } else {
        companyUniverseMetaUniverse.textContent = `${displayFiltered.toLocaleString()} of ${totalCount.toLocaleString()} companies`;
      }
    } else if (typeof filteredCount === "number" && filteredCount > 0) {
      companyUniverseMetaUniverse.textContent = `${filteredCount.toLocaleString()} companies`;
    } else {
      companyUniverseMetaUniverse.textContent = "No companies loaded";
    }
  }

  if (companyUniverseMetaSectors) {
    if (typeof sectorsCount === "number" && sectorsCount > 0) {
      companyUniverseMetaSectors.textContent = `${sectorsCount} sector${sectorsCount === 1 ? "" : "s"} in view`;
    } else {
      companyUniverseMetaSectors.textContent = "No sectors";
    }
  }

  if (companyUniverseMetaLatest) {
    if (latestRecord && latestRecord.latest_filing) {
      const dateLabel = formatDateHuman(latestRecord.latest_filing);
      const ticker = latestRecord.ticker ? ` | ${latestRecord.ticker}` : "";
      companyUniverseMetaLatest.textContent = `${dateLabel}${ticker}`;
    } else {
      companyUniverseMetaLatest.textContent = "No filings ingested";
    }
  }

  if (companyUniverseMetaCoverage) {
    const complete = coverage && typeof coverage.complete === "number" ? coverage.complete : 0;
    const partial = coverage && typeof coverage.partial === "number" ? coverage.partial : 0;
    const missing = coverage && typeof coverage.missing === "number" ? coverage.missing : 0;
    const total = complete + partial + missing;
    const detail = `${complete} complete | ${partial} partial | ${missing} missing`;
    if (total > 0) {
      const percent = Math.round((complete / total) * 100);
      companyUniverseMetaCoverage.textContent = `${percent}% complete (${detail})`;
    } else if (totalCount > 0) {
      companyUniverseMetaCoverage.textContent = `No coverage for current filters (${detail})`;
    } else {
      companyUniverseMetaCoverage.textContent = "Coverage data unavailable";
    }
  }
}

function renderCompanyUniverseMetrics(data) {
  if (!companyUniverseMetrics) {
    return;
  }

  const rows = Array.isArray(data) ? data : [];
  const filteredCount = rows.length;
  const totalTracked = companyUniverseData.length;

  const complete = rows.filter((entry) => entry.coverage === "complete").length;
  const partial = rows.filter((entry) => entry.coverage === "partial").length;
  const missing = rows.filter((entry) => entry.coverage === "missing").length;
  const sectors = new Set(rows.map((entry) => entry.sector).filter(Boolean));
  const referenceForLatest = rows.length ? rows : companyUniverseData;
  const mostRecent = getMostRecentCompanyRecord(referenceForLatest);

  updateCompanyUniverseMeta({
    filteredCount,
    totalCount: totalTracked,
    sectorsCount: sectors.size,
    latestRecord: mostRecent,
    coverage: { complete, partial, missing },
  });

  companyUniverseMetrics.innerHTML = "";
  companyUniverseMetrics.classList.add("hidden");
}
function formatMarketCap(rawValue, displayValue) {
  if (displayValue) {
    return displayValue;
  }
  if (!Number.isFinite(rawValue)) {
    return "—";
  }
  const absValue = Math.abs(rawValue);
  if (absValue >= 1e12) {
    return `${(rawValue / 1e12).toFixed(2)}T`;
  }
  if (absValue >= 1e9) {
    return `${(rawValue / 1e9).toFixed(2)}B`;
  }
  if (absValue >= 1e6) {
    return `${(rawValue / 1e6).toFixed(2)}M`;
  }
  return rawValue.toLocaleString();
}

function formatDateHuman(dateInput) {
  if (!dateInput) {
    return "—";
  }
  const parsed = new Date(dateInput);
  if (Number.isNaN(parsed.getTime())) {
    return dateInput;
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed);
}

function createCoverageBadge(coverage) {
  const span = document.createElement("span");
  span.className = `badge ${coverage}`;
  span.textContent =
    coverage === "complete"
      ? "Complete"
      : coverage === "partial"
      ? "Partial"
      : coverage === "missing"
      ? "Missing"
      : coverage;
  return span;
}

function renderCompanyUniverseTable(data) {
  if (!companyUniverseTable) {
    return;
  }
  const tbody = companyUniverseTable.querySelector("tbody");
  if (!tbody) {
    return;
  }
  tbody.innerHTML = "";
  if (!data.length) {
    companyUniverseTable.classList.add("hidden");
    if (companyUniverseEmpty) {
      companyUniverseEmpty.classList.remove("hidden");
    }
    return;
  }
  companyUniverseTable.classList.remove("hidden");
  if (companyUniverseEmpty) {
    companyUniverseEmpty.classList.add("hidden");
  }

  const sorted = [...data].sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0));
  sorted.forEach((company) => {
    const row = document.createElement("tr");

    const companyCell = document.createElement("td");
    const companyWrap = document.createElement("div");
    companyWrap.className = "company-cell";
    const companyName = document.createElement("span");
    companyName.className = "company-name";
    companyName.textContent = company.company || company.ticker;
    companyWrap.append(companyName);
    if (company.hq) {
      const meta = document.createElement("span");
      meta.className = "company-meta";
      meta.textContent = company.hq;
      companyWrap.append(meta);
    }
    companyCell.append(companyWrap);

    const tickerCell = document.createElement("td");
    const tickerBadge = document.createElement("span");
    tickerBadge.className = "ticker-badge";
    tickerBadge.textContent = company.ticker || "—";
    tickerCell.append(tickerBadge);

    const sectorCell = document.createElement("td");
    sectorCell.textContent = company.sector || "—";

    const marketCapCell = document.createElement("td");
    marketCapCell.textContent = formatMarketCap(company.market_cap, company.market_cap_display);

    const filingCell = document.createElement("td");
    filingCell.textContent = formatDateHuman(company.latest_filing);

    const coverageCell = document.createElement("td");
    coverageCell.append(createCoverageBadge(company.coverage || "complete"));

    row.append(companyCell);
    row.append(tickerCell);
    row.append(sectorCell);
    row.append(marketCapCell);
    row.append(filingCell);
    row.append(coverageCell);
    tbody.append(row);
  });
}

function applyCompanyUniverseFilters() {
  if (!companyUniverseData.length) {
    return;
  }
  const term = (companySearchInput?.value || "").trim().toLowerCase();
  const sectorFilter = companySectorSelect?.value || "";
  const coverageFilter = companyCoverageSelect?.value || "";

  filteredCompanyData = companyUniverseData.filter((entry) => {
    const matchesTerm =
      !term ||
      [entry.company, entry.ticker, entry.sector]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(term));
    const matchesSector = !sectorFilter || entry.sector === sectorFilter;
    const matchesCoverage = !coverageFilter || entry.coverage === coverageFilter;
    return matchesTerm && matchesSector && matchesCoverage;
  });

  renderCompanyUniverseMetrics(filteredCompanyData);
  renderCompanyUniverseTable(filteredCompanyData);
}

async function sendPrompt(prompt) {
  const payload = { prompt };
  if (activeConversation && activeConversation.remoteId) {
    payload.conversation_id = activeConversation.remoteId;
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API ${response.status}: ${errorText || "Unknown error"}`);
  }

  const data = await response.json();
  if (activeConversation && data.conversation_id) {
    activeConversation.remoteId = data.conversation_id;
    promoteConversation(activeConversation);
    saveConversations();
    renderConversationList();
  }
  return data;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSending) {
    return;
  }

  const prompt = chatInput.value.trim();
  if (!prompt) {
    return;
  }

  recordMessage("user", prompt);
  appendMessage("user", prompt, { forceScroll: true });
  chatInput.value = "";

  if (prompt.toLowerCase() === "help") {
    recordMessage("assistant", HELP_TEXT);
    appendMessage("assistant", HELP_TEXT, { forceScroll: true, animate: false });
    chatInput.focus();
    return;
  }

  setSending(true);
  const pendingMessage = showAssistantTyping();

  try {
    const response = await sendPrompt(prompt);
    const cleanReply = typeof response?.reply === "string" ? response.reply.trim() : "";
    const messageText = cleanReply || "(no content)";
    const artifacts = normaliseArtifacts(response);
    recordMessage("assistant", messageText, artifacts);
    resolvePendingMessage(pendingMessage, "assistant", messageText, {
      forceScroll: true,
      artifacts,
    });
  } catch (error) {
    const fallback = error && error.message ? error.message : "Something went wrong. Please try again.";
    recordMessage("system", fallback);
    resolvePendingMessage(pendingMessage, "system", fallback, { forceScroll: true });
  } finally {
    setSending(false);
    chatInput.focus();
  }
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

function wirePromptChips() {
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (!prompt) {
        return;
      }
      chatInput.value = prompt;
      chatForm.requestSubmit();
    });
  });
}

if (navItems && navItems.length) {
  navItems.forEach((item) => {
    item.addEventListener("click", () => handleNavAction(item.dataset.action));
  });
}

if (savedSearchTrigger) {
  savedSearchTrigger.addEventListener("click", () => handleNavAction("search-saved"));
}

if (chatSearchInput) {
  chatSearchInput.addEventListener("input", (event) => {
    conversationSearch = event.target.value.trim();
    renderConversationList();
    if (conversationSearch) {
      showChatSearch({ focus: false, source: "saved-reports" });
    }
  });
}

if (chatSearchClear) {
  chatSearchClear.addEventListener("click", () => {
    if (conversationSearch) {
      clearConversationSearch({ hide: false });
      showChatSearch({ focus: true, source: "saved-reports" });
      return;
    }
    clearConversationSearch({ hide: true });
    resetNavActive();
  });
}

if (conversationList) {
  conversationList.addEventListener("click", (event) => {
    const target = event.target?.closest(".conversation-link");
    if (!target) {
      return;
    }
    loadConversation(target.dataset.id);
  });
}

wirePromptChips();

function ensureToastContainer() {
  if (toastContainer) {
    return;
  }
  toastContainer = document.createElement("div");
  toastContainer.className = "toast-container";
  document.body.append(toastContainer);
}

function showToast(message, tone = "info", duration = 3200) {
  ensureToastContainer();
  if (!toastContainer) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = `toast ${tone}`;
  toast.setAttribute("role", "status");
  toast.innerHTML = `<span>${message}</span><button class="toast-close" aria-label="Dismiss">×</button>`;
  const closeButton = toast.querySelector(".toast-close");
  closeButton.addEventListener("click", () => removeToast(toast));
  toastContainer.append(toast);
  const timeout = window.setTimeout(() => removeToast(toast), duration);
  toastTimeouts.set(toast, timeout);
}

function removeToast(toast) {
  if (!toastContainer || !toast) {
    return;
  }
  const timeout = toastTimeouts.get(toast);
  if (timeout) {
    clearTimeout(timeout);
    toastTimeouts.delete(toast);
  }
  if (toast.parentElement === toastContainer) {
    toastContainer.removeChild(toast);
  }
}

renderConversationList();

if (conversations.length) {
  loadConversation(conversations[0].id);
} else {
  startNewConversation({ focusInput: false });
}

async function checkHealth() {
  try {
    const url = `${API_BASE}/health?ts=${Date.now()}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error();
    statusDot.classList.remove("offline");
    statusDot.classList.add("online");
    statusMessage.textContent = "API online";
  } catch (error) {
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
    statusMessage.textContent = "Cannot reach API";
  }
}

checkHealth();
setInterval(checkHealth, 30000);

loadHelpContentOverrides();

if (chatInput) {
  chatInput.focus();
}

