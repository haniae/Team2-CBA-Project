// ============================================
// FILE UPLOAD INITIALIZATION - RUNS IMMEDIATELY
// ============================================
console.log("🚀🚀🚀 [Upload] SCRIPT LOADED - FILE UPLOAD CODE IS RUNNING! 🚀🚀🚀");

const API_BASE = window.API_BASE || "";
const STORAGE_KEY = "finanlyzeos.chatHistory.v2";
const LEGACY_STORAGE_KEYS = ["finanlyzeos.chatHistory.v1"];
const ACTIVE_CONVERSATION_KEY = "finanlyzeos.activeConversationId";
const CHAT_FILE_INPUT_ID = "chat-file-upload";
const CHAT_FILE_BUTTON_ID = "chat-file-upload-btn";
const LEGACY_BUTTON_ID = "upload-button";

let chatUploadHandlersBound = false;

function resolveChatUploadButton() {
  return (
    document.getElementById(CHAT_FILE_BUTTON_ID) ||
    document.getElementById(LEGACY_BUTTON_ID) ||
    document.querySelector(".chat-file-upload-btn")
  );
}

function ensureChatUploadInput() {
  let input = document.getElementById(CHAT_FILE_INPUT_ID);
  if (input) {
    return input;
  }
  if (!document.body) {
    return null;
  }
  input = document.createElement("input");
  input.type = "file";
  input.accept = "*/*";
  input.id = CHAT_FILE_INPUT_ID;
  input.style.position = "fixed";
  input.style.left = "-10000px";
  input.style.top = "auto";
  input.style.opacity = "0";
  input.style.pointerEvents = "none";
  input.style.width = "1px";
  input.style.height = "1px";
  document.body.appendChild(input);
  return input;
}

function getChatUploadElements() {
  const button = resolveChatUploadButton();
  const input = button ? ensureChatUploadInput() : null;
  return { input, button };
}

function bindChatUploadHandlers(reason = "unspecified") {
  if (chatUploadHandlersBound) {
    return true;
  }

  const { input, button } = getChatUploadElements();

  if (!input || !button) {
    console.warn("[Upload] Chat upload elements missing during bind", {
      reason,
      inputFound: !!input,
      buttonFound: !!button,
    });
    return false;
  }

  const triggerPicker = (event) => {
    if (!input) {
      console.error("[Upload] Cannot trigger file picker: input not available");
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    console.log("[Upload] Upload control activated", {
      type: event.type,
      key: event.key,
    });
    try {
      input.click();
      console.log("[Upload] File picker opened successfully");
    } catch (error) {
      console.error("[Upload] Failed to open file picker", error);
    }
  };

  const handleButtonKeydown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      triggerPicker(event);
    }
  };

  button.addEventListener("click", triggerPicker);
  button.addEventListener("keydown", handleButtonKeydown);

  if (!input.dataset.chatUploadChangeBound) {
    input.addEventListener("change", onChatFileSelected);
    input.dataset.chatUploadChangeBound = "true";
  }

  console.log("[Upload] Chat upload handlers bound", { reason });
  chatUploadHandlersBound = true;
  return true;
}

// Attempt to bind immediately so pointer events work even before DOMContentLoaded
if (!bindChatUploadHandlers("initial")) {
  const retryBind = (reason) => bindChatUploadHandlers(reason);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => retryBind("domcontentloaded"));
  } else {
    setTimeout(() => retryBind("post-timeout"), 100);
  }
  window.addEventListener("load", () => retryBind("window-load"));
}

(function cleanupLegacyStorage() {
  try {
    if (!window || !window.localStorage) {
      return;
    }
    LEGACY_STORAGE_KEYS.forEach((key) => window.localStorage.removeItem(key));
  } catch (error) {
    console.warn("Unable to clear legacy chat storage", error);
  }
})();

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const scrollBtn = document.getElementById("scrollBtn");
const statusDot = document.getElementById("api-status");
const statusMessage = document.getElementById("status-message");
const conversationList = document.getElementById("conversation-list");
const navItems = document.querySelectorAll(".nav-item");
const promptSuggestionsContainer = document.getElementById("prompt-suggestions");
const conversationExportButtons = document.querySelectorAll(".chat-export-btn");
const auditDrawer = document.getElementById("audit-drawer");
const auditDrawerList = document.getElementById("audit-drawer-list");
const auditDrawerStatus = document.getElementById("audit-drawer-status");
const auditDrawerTitle = document.getElementById("audit-drawer-title");
const auditDrawerDetail = document.getElementById("audit-drawer-detail");
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

const STREAM_STEP_MS = 18;
const STREAM_MIN_SLICE = 2;
const STREAM_MAX_SLICE = 24;
const DEFAULT_PROMPT_SUGGESTIONS = [
  "Summarise Q3 performance for AAPL, MSFT, and NVDA with key KPIs.",
  "Show revenue CAGR, ROIC, and FCF margin trends for semiconductor peers.",
  "Which tracked tickers triggered alerts in the past week and why?"
];

/**
 * Convert markdown text to HTML
 * @param {string} text - Raw markdown text
 * @returns {string} HTML string
 */
function renderMarkdown(text) {
  if (!text) {
    return "";
  }

  const escapeHtml = (value) =>
    value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const escapeAttribute = (value) =>
    value.replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const processInline = (value) => {
    if (!value) {
      return "";
    }

    let working = value;

    const codeTokens = [];
    working = working.replace(/`([^`]+)`/g, (match, code) => {
      codeTokens.push(code);
      return `\uE000${codeTokens.length - 1}\uE000`;
    });

    working = working.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, textValue, urlValue) => {
      const rawUrl = urlValue.trim();
      if (!rawUrl) {
        return textValue;
      }
      const safeUrl = escapeAttribute(rawUrl);
      const href = /^([a-z][a-z\d+\-.]*:|\/\/)/i.test(safeUrl) ? safeUrl : `https://${safeUrl}`;
      return `<a href="${href}" target="_blank" rel="noopener noreferrer">${textValue}</a>`;
    });

    working = working.replace(
      /(^|[\s>])((?:https?:\/\/|www\.)[^\s<]+)(?=$|[\s<])/gi,
      (match, prefix, urlValue) => {
        const safeUrl = escapeAttribute(urlValue);
        const href = /^https?:\/\//i.test(safeUrl) ? safeUrl : `https://${safeUrl}`;
        return `${prefix}<a href="${href}" target="_blank" rel="noopener noreferrer">${urlValue}</a>`;
      }
    );

    working = working.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    working = working.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    working = working.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    working = working.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    working = working.replace(/_([^_]+)_/g, "<em>$1</em>");

    working = working.replace(/\uE000(\d+)\uE000/g, (match, indexValue) => {
      const idx = Number(indexValue);
      const codeText = codeTokens[idx] || "";
      return `<code>${codeText}</code>`;
    });

    return working;
  };

  const lines = escapeHtml(text).split(/\r?\n/);

  const html = [];
  const listStack = [];

  let inParagraph = false;
  let paragraphHasContent = false;
  let inBlockquote = false;
  let inCodeBlock = false;
  let codeLang = "";
  const codeBuffer = [];

  const closeParagraph = () => {
    if (inParagraph) {
      html.push("</p>");
      inParagraph = false;
      paragraphHasContent = false;
    }
  };

  const closeListsToIndent = (indent) => {
    while (listStack.length && listStack[listStack.length - 1].indent > indent) {
      const { type } = listStack.pop();
      html.push(`</${type}>`);
    }
  };

  const closeAllLists = () => {
    closeListsToIndent(-1);
  };

  const ensureList = (type, indent) => {
    const current = listStack[listStack.length - 1];
    if (!current || current.indent < indent) {
      html.push(`<${type}>`);
      listStack.push({ type, indent });
      return;
    }
    if (current.indent === indent && current.type !== type) {
      html.push(`</${current.type}>`);
      listStack.pop();
      html.push(`<${type}>`);
      listStack.push({ type, indent });
    }
  };

  const flushCodeBlock = () => {
    const code = codeBuffer.join("\n");
    const languageClass = codeLang ? ` class="language-${codeLang}"` : "";
    html.push(`<pre><code${languageClass}>${code}</code></pre>`);
    codeBuffer.length = 0;
    codeLang = "";
  };

  for (let index = 0; index < lines.length; index += 1) {
    let line = lines[index];

    if (inCodeBlock) {
      if (/^\s*```/.test(line)) {
        flushCodeBlock();
        inCodeBlock = false;
      } else {
        codeBuffer.push(line);
      }
      continue;
    }

    const fenceMatch = line.match(/^\s*```(\w+)?\s*$/);
    if (fenceMatch) {
      closeParagraph();
      closeAllLists();
      const language = fenceMatch[1] ? fenceMatch[1].trim().toLowerCase() : "";
      inCodeBlock = true;
      codeLang = language;
      continue;
    }

    if (line.trim() === "") {
      closeParagraph();
      continue;
    }

    const blockquoteMatch = line.match(/^\s*> ?(.*)$/);
    if (blockquoteMatch) {
      if (!inBlockquote) {
        closeParagraph();
        closeAllLists();
        html.push("<blockquote>");
        inBlockquote = true;
      }
      line = blockquoteMatch[1];
    } else if (inBlockquote) {
      closeParagraph();
      closeAllLists();
      html.push("</blockquote>");
      inBlockquote = false;
      index -= 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      closeParagraph();
      closeAllLists();
      const level = headingMatch[1].length;
      html.push(`<h${level}>${processInline(headingMatch[2].trim())}</h${level}>`);
      continue;
    }

    const hrMatch = line.trim().match(/^([-*_])(?:\s*\1){2,}$/);
    if (hrMatch) {
      closeParagraph();
      closeAllLists();
      html.push("<hr />");
      continue;
    }

    const listMatch = line.match(/^(\s*)([-+*]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      const indent = listMatch[1].replace(/\t/g, "    ").length;
      const marker = listMatch[2];
      const content = listMatch[3];

      closeParagraph();
      closeListsToIndent(indent);

      const type = marker.endsWith(".") ? "ol" : "ul";
      ensureList(type, indent);

      html.push("<li>");
      html.push(processInline(content.trim()));
      html.push("</li>");
      continue;
    }

    if (listStack.length) {
      closeParagraph();
      closeAllLists();
    }

    if (!inParagraph) {
      html.push("<p>");
      inParagraph = true;
      paragraphHasContent = false;
    }

    const content = processInline(line.trim());
    if (paragraphHasContent && content) {
      html.push(" ");
    }
    if (content) {
      html.push(content);
      paragraphHasContent = true;
    }
  }

  if (inCodeBlock) {
    flushCodeBlock();
  }

  closeParagraph();
  closeAllLists();
  if (inBlockquote) {
    closeParagraph();
    closeAllLists();
    html.push("</blockquote>");
  }

  return html.join("");
}
let activePromptSuggestions = [...DEFAULT_PROMPT_SUGGESTIONS];
const FOLLOW_UP_SUGGESTION_LIBRARY = {
  Growth: "Which peers are pacing the fastest quarter-over-quarter growth versus consensus?",
  Revenue: "Break revenue down by segment with multi-year CAGR for each tracked ticker.",
  Margin: "Compare gross and operating margins against peers over the trailing four quarters.",
  Earnings: "Summarise EPS surprises and guidance changes across the peer set.",
  "Cash Flow": "Analyse free-cash-flow conversion and working capital movements this year.",
  Valuation: "Benchmark valuation multiples versus sector medians and the three-year average.",
  Leverage: "Show leverage ratios and interest coverage versus covenant targets.",
  Market: "Highlight market share shifts and relative price performance over the last month.",
  Snapshot: "Generate a KPI snapshot that I can paste into an investment memo.",
  KPI: "List the KPI definitions and calculation lineage referenced in this analysis."
};
const MAX_PROMPT_SUGGESTIONS = 5;
const ALERT_PREFS_KEY = "finanlyzeos.alertPreferences";
const DEFAULT_ALERT_PREFERENCES = {
  digest: "immediate",
  quietHours: {
    enabled: false,
    start: "22:00",
    end: "07:00",
  },
  types: {
    filings: { enabled: true, mandatory: true },
    metricDelta: { enabled: true, threshold: 10 },
    dataQuality: { enabled: true },
  },
  channels: {
    email: { enabled: true, address: "" },
    slack: { enabled: false, webhook: "" },
  },
};
const PREFERS_REDUCED_MOTION = (() => {
  try {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  } catch (error) {
    return false;
  }
})();

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
const PROMPT_CACHE_LIMIT = 32;
const PROMPT_CACHE_TTL_MS = 3 * 60 * 1000;
const promptCache = new Map();
const topBar = document.querySelector(".top-bar");
const PROGRESS_POLL_INTERVAL_MS = 750;
const progressTrackers = new Map();

// Rotating placeholder for hero (no chips)
const PLACEHOLDERS = [
  "Ask anything about tickers or metrics…",
  "Compare two companies…",
  "Request a KPI table or explain a metric…",
];
let placeholderTimer = null;
let placeholderIndex = 0;
let hasNewSinceScroll = false;
let lastFocusedBeforeAudit = null;
let auditAbortController = null;
let auditDrawerEvents = [];
let auditActiveEventIndex = -1;

function startPlaceholderRotation() {
  stopPlaceholderRotation();
  if (!chatInput) {
    return;
  }
  chatInput.placeholder = PLACEHOLDERS[0];
  placeholderTimer = window.setInterval(() => {
    if (!chatInput) {
      return;
    }
    if (document.activeElement === chatInput) {
      return; // don't rotate while typing/focused
    }
    if (chatInput.value && chatInput.value.trim().length > 0) {
      return; // keep when user has typed
    }
    placeholderIndex = (placeholderIndex + 1) % PLACEHOLDERS.length;
    chatInput.placeholder = PLACEHOLDERS[placeholderIndex];
  }, 5000);
}

function stopPlaceholderRotation() {
  if (placeholderTimer) {
    window.clearInterval(placeholderTimer);
    placeholderTimer = null;
  }
}

// Textarea auto-grow: up to 4 lines, cap at 6 lines then scroll
function autoResizeTextarea() {
  if (!chatInput) return;
  const style = window.getComputedStyle(chatInput);
  const lineHeight = parseFloat(style.lineHeight) || 22;
  const paddingY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
  const minHeight = 48;
  const maxAutoLines = 4;
  const maxLines = 6;
  chatInput.style.height = "auto";
  const content = chatInput.scrollHeight;
  const maxAuto = maxAutoLines * lineHeight + paddingY;
  const hardMax = maxLines * lineHeight + paddingY;
  const next = Math.min(Math.max(content, minHeight), hardMax);
  chatInput.style.height = `${next}px`;
  chatInput.style.overflowY = next >= hardMax ? "auto" : "hidden";
}
const COMPLETE_STAGE_HINTS = [
  "_complete",
  "_ready",
  "cache_hit",
  "cache_miss",
  "cache_store",
  "cache_skip",
  "summary_cache_hit",
  "summary_build_complete",
  "context_sources_ready",
  "context_sources_empty",
  "summary_unavailable",
  "finalize",
  "help_complete",
  "complete",
];
const PROGRESS_BLUEPRINT = [
  {
    key: "intent",
    label: "Understand request",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("intent") ||
        stage === "help_lookup" ||
        stage === "help_complete"
      );
    },
  },
  {
    key: "cache",
    label: "Check recent answers",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return stage.startsWith("cache");
    },
  },
  {
    key: "context",
    label: "Gather context",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("context") ||
        stage.startsWith("summary") ||
        stage.startsWith("metrics") ||
        stage.startsWith("ticker")
      );
    },
  },
  {
    key: "compose",
    label: "Compose explanation",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("llm") ||
        stage === "fallback" ||
        stage === "finalize" ||
        stage === "complete"
      );
    },
  },
];
let companyUniverseData = [];
let filteredCompanyData = [];
let companyUniverseMetrics = null;
let companyUniverseTable = null;
let companyUniverseEmpty = null;
let companyUniverseSkeleton = null;
let companySearchInput = null;
let companySectorSelect = null;
let companyCoverageSelect = null;
let companyUniverseMetaUniverse = null;
let companyUniverseMetaSectors = null;
let companyUniverseMetaLatest = null;
let companyUniverseMetaCoverage = null;

const KPI_LIBRARY_PATH = "/static/data/kpi_library.json";
const COMPANY_UNIVERSE_PATH = "/static/data/company_universe.json";
const SETTINGS_STORAGE_KEY = "finanlyzeos.userSettings.v1";
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

function cloneAlertDefaults() {
  try {
    // structuredClone is not available in older browsers, fall back to JSON copy.
    return typeof structuredClone === "function"
      ? structuredClone(DEFAULT_ALERT_PREFERENCES)
      : JSON.parse(JSON.stringify(DEFAULT_ALERT_PREFERENCES));
  } catch (error) {
    return JSON.parse(JSON.stringify(DEFAULT_ALERT_PREFERENCES));
  }
}

function loadAlertPreferences() {
  try {
    const raw = localStorage.getItem(ALERT_PREFS_KEY);
    if (!raw) {
      return cloneAlertDefaults();
    }
    const parsed = JSON.parse(raw);
    const defaults = cloneAlertDefaults();
    return {
      ...defaults,
      ...parsed,
      digest: parsed?.digest || defaults.digest,
      quietHours: {
        ...defaults.quietHours,
        ...(parsed?.quietHours || {}),
      },
      types: {
        ...defaults.types,
        ...(parsed?.types || {}),
      },
      channels: {
        ...defaults.channels,
        ...(parsed?.channels || {}),
      },
    };
  } catch (error) {
    console.warn("Unable to load alert preferences from storage", error);
    return cloneAlertDefaults();
  }
}

function saveAlertPreferences(preferences) {
  try {
    localStorage.setItem(ALERT_PREFS_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.error("Unable to persist alert preferences", error);
    throw error;
  }
}
function renderAlertPreview(previewEl, preferences) {
  if (!previewEl) {
    return;
  }
  const prefs = preferences || cloneAlertDefaults();
  previewEl.innerHTML = "";

  const heading = document.createElement("strong");
  heading.textContent = "What you'll receive";
  previewEl.append(heading);

  const items = document.createElement("ul");
  const activeTypes = [];
  if (prefs.types.filings?.enabled) {
    activeTypes.push("New SEC filing events for tracked tickers.");
  }
  if (prefs.types.metricDelta?.enabled) {
    const threshold = Number(prefs.types.metricDelta.threshold) || DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold;
    activeTypes.push(`Metric change alerts above ${threshold}% delta.`);
  }
  if (prefs.types.dataQuality?.enabled) {
    activeTypes.push("Data quality failures or ingestion retries.");
  }
  if (!activeTypes.length) {
    activeTypes.push("No proactive alerts are currently enabled.");
  }
  activeTypes.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    items.append(li);
  });
  previewEl.append(items);

  const channels = [];
  if (prefs.channels.email?.enabled) {
    const address = prefs.channels.email.address || "Add an email address";
    channels.push(`Email → ${address}`);
  }
  if (prefs.channels.slack?.enabled) {
    channels.push("Slack webhook");
  }
  if (!channels.length) {
    channels.push("No delivery channels enabled.");
  }
  const channelLine = document.createElement("p");
  channelLine.textContent = `Channels: ${channels.join(", ")}`;
  previewEl.append(channelLine);

  const digestLabel = {
    immediate: "Deliver immediately",
    daily: "Daily digest (8:00 AM)",
    weekly: "Weekly digest (Monday 8:00 AM)",
  }[prefs.digest] || "Deliver immediately";

  const digestLine = document.createElement("p");
  digestLine.textContent = `Cadence: ${digestLabel}`;
  previewEl.append(digestLine);

  const quietLine = document.createElement("p");
  quietLine.textContent = prefs.quietHours?.enabled
    ? `Quiet hours: ${prefs.quietHours.start || "22:00"} – ${prefs.quietHours.end || "07:00"}`
    : "Quiet hours disabled.";
  previewEl.append(quietLine);
}

function renderAlertSettingsSection({ container } = {}) {
  if (!container) {
    return;
  }

  const preferences = loadAlertPreferences();
  container.innerHTML = `
    <form class="alert-settings" data-role="alert-settings-form" novalidate>
      <fieldset class="alert-settings__section">
        <legend>Alert types</legend>
        <p class="alert-settings__description">Choose which events raise notifications for your workspace.</p>
        <div class="alert-settings__grid">
          <label class="alert-settings__toggle" data-role="alert-type-filings">
            <input type="checkbox" name="alerts.filings" disabled />
            <span>New SEC filing ingested</span>
            <small>Mandatory for audit coverage.</small>
          </label>
          <label class="alert-settings__toggle">
            <input type="checkbox" name="alerts.metricDelta" />
            <span>Metric change above threshold</span>
            <small>Triggered when KPI delta exceeds your configured limit.</small>
          </label>
          <label class="alert-settings__toggle">
            <input type="checkbox" name="alerts.dataQuality" />
            <span>Data quality issue detected</span>
            <small>Heads-up when ingestion or QA checks fail.</small>
          </label>
        </div>
        <div class="alert-settings__field">
          <span>Metric delta threshold (%)</span>
          <input
            type="number"
            name="alerts.metricDeltaThreshold"
            min="1"
            max="100"
            step="1"
            inputmode="numeric"
            aria-describedby="metric-threshold-help"
          />
          <small id="metric-threshold-help" class="alert-settings__description">Alerts fire when absolute change exceeds this value.</small>
        </div>
      </fieldset>
      <fieldset class="alert-settings__section">
        <legend>Delivery channels</legend>
        <p class="alert-settings__description">Route alerts to your preferred communication channels.</p>
        <div class="alert-settings__channels">
          <div class="alert-settings__channel" data-channel="email">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="channel.email.enabled" />
              <span>Email (SES)</span>
              <small>Distribute alerts to analysts or coverage aliases.</small>
            </label>
            <div class="alert-settings__field">
              <span>Email address</span>
              <input type="email" name="channel.email.address" placeholder="name@company.com" autocomplete="email" />
            </div>
          </div>
          <div class="alert-settings__channel" data-channel="slack">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="channel.slack.enabled" />
              <span>Slack webhook</span>
              <small>Post alerts into a shared #finalyze channel.</small>
            </label>
            <div class="alert-settings__field">
              <span>Webhook URL</span>
              <input type="url" name="channel.slack.webhook" placeholder="https://hooks.slack.com/..." inputmode="url" />
            </div>
          </div>
        </div>
      </fieldset>
      <fieldset class="alert-settings__section">
        <legend>Cadence & quiet hours</legend>
        <div class="alert-settings__grid">
          <div class="alert-settings__field">
            <span>Digest cadence</span>
            <select name="alerts.digest">
              <option value="immediate">Send immediately</option>
              <option value="daily">Daily summary</option>
              <option value="weekly">Weekly digest</option>
            </select>
          </div>
          <div class="alert-settings__field">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="alerts.quiet.enabled" />
              <span>Respect quiet hours</span>
              <small>Pause notifications between the times below.</small>
            </label>
            <div class="alert-settings__grid">
              <div class="alert-settings__field">
                <span>Quiet hours start</span>
                <input type="time" name="alerts.quiet.start" />
              </div>
              <div class="alert-settings__field">
                <span>Quiet hours end</span>
                <input type="time" name="alerts.quiet.end" />
              </div>
            </div>
          </div>
        </div>
      </fieldset>
      <div class="alert-settings__actions">
        <button type="submit">Save preferences</button>
        <button type="button" data-role="alert-reset">Reset to defaults</button>
      </div>
      <p class="alert-settings__status" data-role="alert-status" aria-live="polite"></p>
      <div class="alert-settings__preview" data-role="alert-preview"></div>
    </form>
  `;

  const form = container.querySelector("[data-role='alert-settings-form']");
  if (!form) {
    return;
  }

  const statusEl = form.querySelector("[data-role='alert-status']");
  const resetButton = form.querySelector("[data-role='alert-reset']");
  const previewEl = form.querySelector("[data-role='alert-preview']");
  const channelContainers = {
    email: form.querySelector("[data-channel='email']"),
    slack: form.querySelector("[data-channel='slack']"),
  };

  const controls = {
    filings: form.querySelector("[name='alerts.filings']"),
    metricDelta: form.querySelector("[name='alerts.metricDelta']"),
    metricDeltaThreshold: form.querySelector("[name='alerts.metricDeltaThreshold']"),
    dataQuality: form.querySelector("[name='alerts.dataQuality']"),
    digest: form.querySelector("[name='alerts.digest']"),
    quietEnabled: form.querySelector("[name='alerts.quiet.enabled']"),
    quietStart: form.querySelector("[name='alerts.quiet.start']"),
    quietEnd: form.querySelector("[name='alerts.quiet.end']"),
    emailEnabled: form.querySelector("[name='channel.email.enabled']"),
    emailAddress: form.querySelector("[name='channel.email.address']"),
    slackEnabled: form.querySelector("[name='channel.slack.enabled']"),
    slackWebhook: form.querySelector("[name='channel.slack.webhook']"),
  };

  const applyPreferences = (prefs) => {
    controls.filings.checked = true;
    controls.metricDelta.checked = Boolean(prefs.types.metricDelta?.enabled);
    controls.metricDeltaThreshold.value = Number(prefs.types.metricDelta?.threshold ?? DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold);
    controls.dataQuality.checked = Boolean(prefs.types.dataQuality?.enabled);
    controls.digest.value = prefs.digest || DEFAULT_ALERT_PREFERENCES.digest;
    controls.quietEnabled.checked = Boolean(prefs.quietHours?.enabled);
    controls.quietStart.value = prefs.quietHours?.start || DEFAULT_ALERT_PREFERENCES.quietHours.start;
    controls.quietEnd.value = prefs.quietHours?.end || DEFAULT_ALERT_PREFERENCES.quietHours.end;
    controls.emailEnabled.checked = Boolean(prefs.channels.email?.enabled);
    controls.emailAddress.value = prefs.channels.email?.address || "";
    controls.slackEnabled.checked = Boolean(prefs.channels.slack?.enabled);
    controls.slackWebhook.value = prefs.channels.slack?.webhook || "";
    syncQuietHours();
    syncChannelState();
    syncMetricThresholdState();
    renderAlertPreview(previewEl, prefs);
  };

  const clampThreshold = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold;
    }
    return Math.min(100, Math.max(1, Math.round(numeric)));
  };

  const collectPreferences = () => {
    const next = cloneAlertDefaults();
    next.types.metricDelta.enabled = Boolean(controls.metricDelta.checked);
    next.types.metricDelta.threshold = clampThreshold(controls.metricDeltaThreshold.value);
    next.types.dataQuality.enabled = Boolean(controls.dataQuality.checked);
    next.digest = controls.digest.value || DEFAULT_ALERT_PREFERENCES.digest;
    next.quietHours.enabled = Boolean(controls.quietEnabled.checked);
    next.quietHours.start = controls.quietStart.value || DEFAULT_ALERT_PREFERENCES.quietHours.start;
    next.quietHours.end = controls.quietEnd.value || DEFAULT_ALERT_PREFERENCES.quietHours.end;
    next.channels.email.enabled = Boolean(controls.emailEnabled.checked);
    next.channels.email.address = controls.emailAddress.value.trim();
    next.channels.slack.enabled = Boolean(controls.slackEnabled.checked);
    next.channels.slack.webhook = controls.slackWebhook.value.trim();
    controls.metricDeltaThreshold.value = next.types.metricDelta.threshold;
    return next;
  };

  const showStatus = (message, tone = "info") => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = message;
    statusEl.dataset.tone = tone;
  };

  const syncChannelState = () => {
    const emailEnabled = Boolean(controls.emailEnabled?.checked);
    const slackEnabled = Boolean(controls.slackEnabled?.checked);
    if (controls.emailAddress) {
      controls.emailAddress.disabled = !emailEnabled;
    }
    if (controls.slackWebhook) {
      controls.slackWebhook.disabled = !slackEnabled;
    }
    if (channelContainers.email) {
      channelContainers.email.classList.toggle("alert-settings__channel-disabled", !emailEnabled);
    }
    if (channelContainers.slack) {
      channelContainers.slack.classList.toggle("alert-settings__channel-disabled", !slackEnabled);
    }
  };

  const syncQuietHours = () => {
    const enabled = Boolean(controls.quietEnabled?.checked);
    if (controls.quietStart) {
      controls.quietStart.disabled = !enabled;
    }
    if (controls.quietEnd) {
      controls.quietEnd.disabled = !enabled;
    }
  };

  const syncMetricThresholdState = () => {
    if (!controls.metricDeltaThreshold) {
      return;
    }
    const enabled = Boolean(controls.metricDelta?.checked);
    controls.metricDeltaThreshold.disabled = !enabled;
  };

  applyPreferences(preferences);

  controls.emailEnabled?.addEventListener("change", () => {
    syncChannelState();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.slackEnabled?.addEventListener("change", () => {
    syncChannelState();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.quietEnabled?.addEventListener("change", () => {
    syncQuietHours();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.metricDelta?.addEventListener("change", () => {
    syncMetricThresholdState();
    renderAlertPreview(previewEl, collectPreferences());
  });

  form.addEventListener("input", (event) => {
    if (event.target === controls.metricDeltaThreshold) {
      controls.metricDeltaThreshold.value = controls.metricDeltaThreshold.value.slice(0, 3);
    }
    if (statusEl) {
      statusEl.textContent = "";
      delete statusEl.dataset.tone;
    }
    renderAlertPreview(previewEl, collectPreferences());
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = collectPreferences();
    try {
      saveAlertPreferences(next);
      showStatus("Alert preferences saved.", "success");
      renderAlertPreview(previewEl, next);
    } catch (error) {
      showStatus("Unable to save alert preferences. Try again.", "error");
    }
  });

  resetButton?.addEventListener("click", (event) => {
    event.preventDefault();
    const defaults = cloneAlertDefaults();
    applyPreferences(defaults);
    try {
      saveAlertPreferences(defaults);
      showStatus("Alert preferences reset to defaults.", "success");
    } catch (error) {
      showStatus("Unable to reset alert preferences.", "error");
    }
    renderAlertPreview(previewEl, defaults);
  });
}

function generateRequestId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `req_${Date.now().toString(16)}_${Math.random().toString(16).slice(2, 10)}`;
}

function formatElapsed(milliseconds) {
  if (typeof milliseconds !== "number" || Number.isNaN(milliseconds)) {
    return null;
  }
  if (milliseconds < 1000) {
    return `${Math.max(0, milliseconds).toFixed(0)} ms`;
  }
  if (milliseconds < 10000) {
    return `${(milliseconds / 1000).toFixed(1)} s`;
  }
  return `${Math.round(milliseconds / 1000)} s`;
}

function createProgressSteps() {
  return PROGRESS_BLUEPRINT.map(({ key, label }) => ({
    key,
    label,
    status: "pending",
    detail: "",
    messages: [],
  }));
}

function stepStatusFromStage(stage) {
  if (!stage) {
    return "pending";
  }
  if (stage === "error") {
    return "error";
  }
  if (stage === "complete" || COMPLETE_STAGE_HINTS.some((hint) => stage.includes(hint))) {
    return "complete";
  }
  return "active";
}

function findStepKeyForStage(stage) {
  if (!stage) {
    return null;
  }
  const match = PROGRESS_BLUEPRINT.find((entry) => entry.matches(stage));
  return match ? match.key : null;
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
      <div class="company-universe__legend" role="note" aria-label="Dataset cues">
        <span class="company-universe__legend-title">Data cues</span>
        <span class="company-universe__legend-item" title="Market cap benchmark"> 
          <span class="company-universe__legend-dot company-universe__legend-dot--mega" aria-hidden="true"></span>
          Market cap ≥ $1T
        </span>
        <span class="company-universe__legend-item" title="Filing recency benchmark">
          <span class="company-universe__legend-dot company-universe__legend-dot--stale" aria-hidden="true"></span>
          Filing > 180 days
        </span>
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
        <div class="company-universe__skeleton" data-role="company-universe-skeleton">
          ${Array.from({ length: 6 })
            .map(
              () => `
                <div class=\"company-universe__skeleton-row\">
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                </div>`
            )
            .join("")}
        </div>
        <p class="company-universe__empty hidden" data-role="company-universe-empty">
          <span class="company-universe__empty-icon" aria-hidden="true">📊</span>
          <span>No companies match your search. Adjust filters and try again.</span>
        </p>
      </div>
    </div>
  `;

  const companyUniverseDiv = container.querySelector(".company-universe");
  if (companyUniverseDiv) {
    const hero = buildCompanyUniverseHero();
    companyUniverseDiv.insertBefore(hero, companyUniverseDiv.firstChild);
  }

  companySearchInput = container.querySelector("[data-role='company-universe-search']");
  companySectorSelect = container.querySelector("[data-role='company-universe-sector']");
  companyCoverageSelect = container.querySelector("[data-role='company-universe-coverage']");
  companyUniverseMetrics = container.querySelector("[data-role='company-universe-metrics']");
  companyUniverseTable = container.querySelector("[data-role='company-universe-table']");
  companyUniverseEmpty = container.querySelector("[data-role='company-universe-empty']");
  companyUniverseSkeleton = container.querySelector("[data-role='company-universe-skeleton']");
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
  if (companyUniverseSkeleton) {
    companyUniverseSkeleton.classList.remove("hidden");
  }
  if (companyUniverseEmpty) {
    companyUniverseEmpty.classList.add("hidden");
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
  "What is Apple's revenue?",
  "Show Microsoft's EBITDA margin",
  "Why is Tesla's margin declining?",
  "Compare AAPL and MSFT profitability",
  "Is Tesla overvalued?",
  "What's my portfolio exposure?",
  "Show me a dashboard for Apple",
  "What are the key risks for Tesla?",
];
const HELP_SECTIONS = [
  {
    icon: "📊",
    title: "Company Metrics & Analysis",
    command: "What is [TICKER]'s [metric]?",
    purpose: "Get single metrics, trends, or comprehensive company analysis.",
    examples: [
      "What is Apple's revenue?",
      "Show Microsoft's EBITDA margin",
      "What's Tesla's free cash flow?",
      "What is Google's net income?",
      "Show NVDA's gross margin",
      "What is META's return on equity?",
      "Tell me about Amazon's balance sheet",
      "What's Microsoft's P/E ratio?",
    ],
    delivers: "Direct answers, YoY growth, 3-5 year CAGRs, business drivers, SEC sources.",
  },
  {
    icon: "🔍",
    title: "Why Questions (Deep Analysis)",
    command: "Why is [TICKER]'s [metric] [trend]?",
    purpose: "Get multi-factor explanations for changes in financial metrics.",
    examples: [
      "Why is Tesla's margin declining?",
      "Why is Apple's revenue growing?",
      "Why is Microsoft more profitable?",
      "Why did NVDA's stock price increase?",
      "Why is Amazon investing more in CapEx?",
      "Why is Google's margin expanding?",
    ],
    delivers: "Multi-factor analysis (3-5 reasons), quantified impacts, business context, forward outlook.",
  },
  {
    icon: "⚖️",
    title: "Comparisons",
    command: "Compare [TICKER1] and [TICKER2] [metric]",
    purpose: "Side-by-side analysis of companies, metrics, or performance.",
    examples: [
      "Compare AAPL and MSFT profitability",
      "Is Apple more profitable than Microsoft?",
      "Compare Tesla and Ford margins",
      "Which is better: Apple or Microsoft?",
      "Compare FAANG revenue growth",
      "Compare valuation metrics for AAPL, MSFT, GOOGL",
    ],
    delivers: "Side-by-side metrics, percentage differences, rankings, performance indicators.",
  },
  {
    icon: "💎",
    title: "Valuation & Multiples",
    command: "What's [TICKER]'s [valuation metric]?",
    purpose: "Analyze valuation multiples, P/E ratios, and relative valuation.",
    examples: [
      "What's Apple's P/E ratio?",
      "Is Tesla overvalued?",
      "What multiples is Microsoft trading at?",
      "Compare Apple's P/E to the S&P 500",
      "What's Amazon's PEG ratio?",
      "How does Tesla's valuation compare to Ford?",
      "Compare valuation metrics for FAANG stocks",
      "Which is cheaper: Apple or Microsoft?",
    ],
    delivers: "Valuation metrics, peer comparison, analyst target prices, historical multiples.",
  },
  {
    icon: "💪",
    title: "Financial Health & Risk",
    command: "What's [TICKER]'s [risk/health metric]?",
    purpose: "Assess balance sheet strength, leverage, and risk factors.",
    examples: [
      "What's Tesla's debt-to-equity ratio?",
      "How leveraged is Apple?",
      "What's Microsoft's net debt?",
      "What are the key risks for Tesla?",
      "Is Amazon's balance sheet strong?",
      "How much cash does Apple have?",
      "What's Apple's interest coverage ratio?",
      "What could go wrong with Apple's business?",
    ],
    delivers: "Balance sheet metrics, leverage ratios, credit analysis, risk factors from 10-K.",
  },
  {
    icon: "📈",
    title: "Profitability & Margins",
    command: "What's [TICKER]'s [margin metric]?",
    purpose: "Analyze margins, profitability trends, and operating efficiency.",
    examples: [
      "What's Apple's gross margin?",
      "What's Apple's gross margin trend?",
      "Which is more profitable: Microsoft or Google?",
      "What's driving Tesla's margin compression?",
      "Compare EBITDA margins across FAANG",
      "Show me Microsoft's operating margin",
      "What's Amazon's profit margin?",
    ],
    delivers: "Margin breakdown, multi-year trends, peer comparison, drivers of margin changes.",
  },
  {
    icon: "🚀",
    title: "Growth & Performance",
    command: "What's [TICKER]'s [growth metric]?",
    purpose: "Analyze revenue growth, earnings growth, and growth outlook.",
    examples: [
      "Is Apple growing faster than Microsoft?",
      "What's Tesla's revenue CAGR?",
      "How fast is Amazon growing?",
      "What's Apple's earnings growth?",
      "What's the revenue forecast for Microsoft?",
      "Which tech stock has the best growth trajectory?",
      "Show me NVDA's 3-year revenue CAGR",
    ],
    delivers: "Historical growth rates (3-5 years), segment breakdown, growth drivers, analyst forecasts.",
  },
  {
    icon: "💵",
    title: "Cash Flow & Capital Allocation",
    command: "What's [TICKER]'s [cash flow metric]?",
    purpose: "Analyze cash generation, capital allocation, and shareholder returns.",
    examples: [
      "What's Apple's free cash flow?",
      "How much cash does Microsoft generate?",
      "How is Amazon allocating capital?",
      "What's Microsoft's dividend yield?",
      "Is Apple doing share buybacks?",
      "Compare ROI across mega-cap tech",
      "What's Tesla's cash burn rate?",
    ],
    delivers: "Cash flow statements, FCF trends, capex plans, dividend history, buyback programs.",
  },
  {
    icon: "🎯",
    title: "Investment Analysis",
    command: "Should I invest in [TICKER]?",
    purpose: "Get investment thesis, bull/bear cases, and recommendations.",
    examples: [
      "Should I invest in Apple or Microsoft?",
      "What's the bull case for Tesla?",
      "What's the bear case for Amazon?",
      "Should I buy Apple stock?",
      "What's the investment thesis for NVDA?",
      "Is Microsoft a good investment?",
    ],
    delivers: "Bull/bear cases, investment thesis, analyst consensus, target prices, risk factors.",
  },
  {
    icon: "📦",
    title: "Portfolio Management",
    command: "What's my portfolio [metric]?",
    purpose: "Analyze portfolio holdings, exposure, and optimization.",
    examples: [
      "What's my portfolio exposure?",
      "Show my portfolio holdings",
      "Optimize my portfolio to maximize Sharpe",
      "What if the market drops 20%?",
      "Show my portfolio performance",
      "Analyze my portfolio risk",
      "What's my portfolio's sector allocation?",
    ],
    delivers: "Portfolio analysis, holdings breakdown, risk metrics, optimization suggestions.",
  },
  {
    icon: "📊",
    title: "Dashboards",
    command: "Show me a dashboard for [TICKER]",
    purpose: "Get interactive visualizations and comprehensive financial tables.",
    examples: [
      "Show me a dashboard for Apple",
      "Dashboard AAPL",
      "Show dashboard for Microsoft",
      "Create a dashboard for Tesla",
    ],
    delivers: "Interactive charts, multi-year comparisons, comprehensive metrics table, downloadable data.",
  },
  {
    icon: "🏭",
    title: "Market Position & Competition",
    command: "Who are [TICKER]'s competitors?",
    purpose: "Analyze competitive landscape and market position.",
    examples: [
      "Who are Apple's main competitors?",
      "Is Apple losing market share to Samsung?",
      "What's Microsoft's competitive advantage?",
      "Compare Tesla to traditional automakers",
      "What's Amazon's market share?",
    ],
    delivers: "Competitor analysis, market share data, competitive advantages, industry positioning.",
  },
  {
    icon: "📋",
    title: "Sector & Industry Analysis",
    command: "Compare [TICKER] to [sector/industry]",
    purpose: "Benchmark companies against sector averages and industry peers.",
    examples: [
      "How does Apple compare to the technology sector?",
      "Compare Tesla to the automotive sector",
      "What's Microsoft's position in cloud computing?",
      "Show me tech sector benchmarks",
    ],
    delivers: "Sector benchmarks, percentile rankings, industry averages, peer comparisons.",
  },
  {
    icon: "🧾",
    title: "SEC Filing Facts",
    command: "Fact [TICKER] [YEAR] [metric]",
    purpose: "Retrieve exactly what was reported in 10-K/10-Q filings.",
    example: "Fact TSLA 2022 revenue",
    delivers: "Original value, adjustment notes, and source reference.",
  },
  {
    icon: "🧮",
    title: "Scenario Modelling",
    command: "Scenario [TICKER] [NAME] rev=+X% margin=+Y% mult=+Z",
    purpose: "Run what-if cases for growth, margin shifts, or valuation moves.",
    example: "Scenario NVDA Bull rev=+8% margin=+1.5% mult=+0.5",
    delivers: "Projected revenue, margins, EPS/FCF change, implied valuation.",
  },
  {
    icon: "⚙️",
    title: "Data Management",
    command: ["Ingest [TICKER] [years]", "Ingest status [TICKER]", "Audit [TICKER] [year]"],
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
  lines.push("📘 Finalyze Copilot — Quick Reference", "", "How to ask:");
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

  // Hero box (summary card)
  const hero = document.createElement("section");
  hero.className = "help-guide__hero";

  const badge = document.createElement("div");
  badge.className = "help-guide__badge";
  badge.textContent = "📘";

  const heroCopy = document.createElement("div");
  heroCopy.className = "help-guide__hero-copy";

  const title = document.createElement("h3");
  title.className = "help-guide__title";
  title.textContent = "Finalyze Copilot — Quick Reference";

  const subtitle = document.createElement("p");
  subtitle.className = "help-guide__subtitle";
  subtitle.textContent = "Ask natural prompts and I will translate them into institutional-grade analysis.";

  heroCopy.append(title, subtitle);
  hero.append(badge, heroCopy);

  // Search Form (similar to KPI Library)
  const controls = document.createElement("div");
  controls.className = "help-guide__filters";
  
  const searchGroup = document.createElement("div");
  searchGroup.className = "help-guide__filter help-guide__filter--search";
  const searchInput = document.createElement("input");
  searchInput.type = "search";
  searchInput.placeholder = "Search by command, purpose, or example";
  searchInput.autocomplete = "off";
  searchInput.className = "help-guide__search";
  searchGroup.append(searchInput);
  controls.append(searchGroup);

  const categoryGroup = document.createElement("div");
  categoryGroup.className = "help-guide__filter";
  const categorySelect = document.createElement("select");
  categorySelect.className = "help-guide__select";
  categorySelect.innerHTML = `<option value="">All categories</option>`;
  const categories = Array.from(
    new Set(content.sections.map((section) => section.title || "").filter(Boolean))
  ).sort((a, b) => a.localeCompare(b));
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.append(option);
  });
  categoryGroup.append(categorySelect);
  controls.append(categoryGroup);

  // Create sticky container for hero + filters
  const stickyContainer = document.createElement("div");
  stickyContainer.className = "help-guide__sticky-container";
  stickyContainer.append(hero);
  stickyContainer.append(controls);
  article.append(stickyContainer);

  const sectionGrid = document.createElement("div");
  sectionGrid.className = "help-guide__grid";

  // Filter function
  const filterCards = () => {
    const searchTerm = searchInput.value.toLowerCase().trim();
    const selectedCategory = categorySelect.value;

    const cards = sectionGrid.querySelectorAll(".help-guide__card");
    let visibleCount = 0;

    cards.forEach((card) => {
      const title = card.querySelector(".help-guide__card-title")?.textContent || "";
      const command = card.querySelector(".help-guide__value")?.textContent || "";
      const purpose = Array.from(card.querySelectorAll(".help-guide__value")).map(el => el.textContent).join(" ") || "";
      const examples = Array.from(card.querySelectorAll(".help-guide__list li")).map(el => el.textContent).join(" ") || "";
      
      const matchesSearch = !searchTerm || 
        title.toLowerCase().includes(searchTerm) ||
        command.toLowerCase().includes(searchTerm) ||
        purpose.toLowerCase().includes(searchTerm) ||
        examples.toLowerCase().includes(searchTerm);
      
      const matchesCategory = !selectedCategory || title === selectedCategory;

      if (matchesSearch && matchesCategory) {
        card.style.display = "";
        visibleCount++;
      } else {
        card.style.display = "none";
      }
    });

    // Show empty state if no cards visible
    let emptyState = sectionGrid.querySelector(".help-guide__empty");
    if (visibleCount === 0) {
      if (!emptyState) {
        emptyState = document.createElement("div");
        emptyState.className = "help-guide__empty";
        emptyState.textContent = "No results match your search.";
        sectionGrid.append(emptyState);
      }
      emptyState.style.display = "";
    } else if (emptyState) {
      emptyState.style.display = "none";
    }
  };

  searchInput.addEventListener("input", filterCards);
  categorySelect.addEventListener("change", filterCards);

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
      pill.setAttribute("role", "button");
      pill.setAttribute("tabindex", "0");
      pill.setAttribute("aria-label", `Use command: ${token}`);
      pill.title = `Click to copy: ${token}`;
      // Add click handler to copy command
      pill.addEventListener("click", () => {
        navigator.clipboard.writeText(token).then(() => {
          const originalText = pill.textContent;
          pill.textContent = "✓ Copied!";
          pill.style.color = "#16a34a";
          setTimeout(() => {
            pill.textContent = originalText;
            pill.style.color = "";
          }, 1500);
        }).catch(() => {
          // Fallback: insert into chat input if available
          const chatInput = document.querySelector("#chat-input, .chat-input, textarea[placeholder*='Ask']");
          if (chatInput) {
            chatInput.value = token;
            chatInput.focus();
            chatInput.dispatchEvent(new Event("input", { bubbles: true }));
          }
        });
      });
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

function createMetaBadge(label, value, directionality = null) {
  if (!value) {
    return null;
  }
  const badge = document.createElement("span");
  badge.className = "kpi-library__meta-pill";
  
  // Add color coding for directionality
  if (label === "Direction" && directionality) {
    const colorClass = getDirectionalityColor(directionality);
    badge.classList.add(colorClass);
  }
  
  badge.textContent = `${label}: ${value}`;
  return badge;
}

function getDirectionalityColor(directionality) {
  switch (directionality) {
    case "higher_is_better":
      return "kpi-library__meta-pill--positive";
    case "lower_is_better":
      return "kpi-library__meta-pill--negative";
    case "depends":
      return "kpi-library__meta-pill--neutral";
    case "neutral":
      return "kpi-library__meta-pill--neutral";
    default:
      return "";
  }
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
  title.textContent = "KPI Library";

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

// ============================================
// FILE UPLOAD INITIALIZATION - RUNS IMMEDIATELY
// ============================================
console.log("🚀🚀🚀 [Upload] SCRIPT LOADED - FILE UPLOAD CODE IS RUNNING! 🚀🚀🚀");
const API_BASE = window.API_BASE || "";
const STORAGE_KEY = "finanlyzeos.chatHistory.v2";
const LEGACY_STORAGE_KEYS = ["finanlyzeos.chatHistory.v1"];
const ACTIVE_CONVERSATION_KEY = "finanlyzeos.activeConversationId";

// Initialize file upload handler immediately - run at top level
(function initFileUploadImmediate() {
  console.log("🚀 [Upload] TOP LEVEL: Starting file upload initialization...");
  console.log("🚀 [Upload] TOP LEVEL: Document ready state:", document.readyState);
  
  function tryInit() {
    const { input, button } = getChatUploadElements();
    console.log("🚀 [Upload] TOP LEVEL: Element check:", {
      input: !!input,
      button: !!button,
      inputEl: input,
      buttonEl: button
    });
    
    if (input && button) {
      console.log("🚀 [Upload] TOP LEVEL: ✅ Elements found! Setting up click handler...");
      bindChatUploadHandlers("top-level");
      
      input.addEventListener("change", function(e) {
        console.log("🚀 [Upload] TOP LEVEL: File selected:", e.target.files?.[0]?.name);
        // The main handler will process this
      });
      
      return true;
    }
    return false;
  }
  
  // Try immediately
  if (!tryInit()) {
    // Retry on DOM ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        console.log("🚀 [Upload] TOP LEVEL: DOMContentLoaded, retrying...");
        tryInit();
      });
    } else {
      setTimeout(function() {
        console.log("🚀 [Upload] TOP LEVEL: Retrying after delay...");
        tryInit();
      }, 100);
    }
  }
  
  // Also try on window load
  window.addEventListener('load', function() {
    console.log("🚀 [Upload] TOP LEVEL: Window load, retrying...");
    tryInit();
  });
})();

(function cleanupLegacyStorage() {
  try {
    if (!window || !window.localStorage) {
      return;
    }
    LEGACY_STORAGE_KEYS.forEach((key) => window.localStorage.removeItem(key));
  } catch (error) {
    console.warn("Unable to clear legacy chat storage", error);
  }
})();

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const scrollBtn = document.getElementById("scrollBtn");
const statusDot = document.getElementById("api-status");
const statusMessage = document.getElementById("status-message");
const conversationList = document.getElementById("conversation-list");
const navItems = document.querySelectorAll(".nav-item");
const promptSuggestionsContainer = document.getElementById("prompt-suggestions");
const conversationExportButtons = document.querySelectorAll(".chat-export-btn");
const auditDrawer = document.getElementById("audit-drawer");
const auditDrawerList = document.getElementById("audit-drawer-list");
const auditDrawerStatus = document.getElementById("audit-drawer-status");
const auditDrawerTitle = document.getElementById("audit-drawer-title");
const auditDrawerDetail = document.getElementById("audit-drawer-detail");
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

const STREAM_STEP_MS = 18;
const STREAM_MIN_SLICE = 2;
const STREAM_MAX_SLICE = 24;
const DEFAULT_PROMPT_SUGGESTIONS = [
  "Summarise Q3 performance for AAPL, MSFT, and NVDA with key KPIs.",
  "Show revenue CAGR, ROIC, and FCF margin trends for semiconductor peers.",
  "Which tracked tickers triggered alerts in the past week and why?"
];

/**
 * Convert markdown text to HTML
 * @param {string} text - Raw markdown text
 * @returns {string} HTML string
 */
function renderMarkdown(text) {
  if (!text) {
    return "";
  }

  const escapeHtml = (value) =>
    value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const escapeAttribute = (value) =>
    value.replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const processInline = (value) => {
    if (!value) {
      return "";
    }

    let working = value;

    const codeTokens = [];
    working = working.replace(/`([^`]+)`/g, (match, code) => {
      codeTokens.push(code);
      return `\uE000${codeTokens.length - 1}\uE000`;
    });

    working = working.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, textValue, urlValue) => {
      const rawUrl = urlValue.trim();
      if (!rawUrl) {
        return textValue;
      }
      const safeUrl = escapeAttribute(rawUrl);
      const href = /^([a-z][a-z\d+\-.]*:|\/\/)/i.test(safeUrl) ? safeUrl : `https://${safeUrl}`;
      return `<a href="${href}" target="_blank" rel="noopener noreferrer">${textValue}</a>`;
    });

    working = working.replace(
      /(^|[\s>])((?:https?:\/\/|www\.)[^\s<]+)(?=$|[\s<])/gi,
      (match, prefix, urlValue) => {
        const safeUrl = escapeAttribute(urlValue);
        const href = /^https?:\/\//i.test(safeUrl) ? safeUrl : `https://${safeUrl}`;
        return `${prefix}<a href="${href}" target="_blank" rel="noopener noreferrer">${urlValue}</a>`;
      }
    );

    working = working.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    working = working.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    working = working.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    working = working.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    working = working.replace(/_([^_]+)_/g, "<em>$1</em>");

    working = working.replace(/\uE000(\d+)\uE000/g, (match, indexValue) => {
      const idx = Number(indexValue);
      const codeText = codeTokens[idx] || "";
      return `<code>${codeText}</code>`;
    });

    return working;
  };

  const lines = escapeHtml(text).split(/\r?\n/);

  const html = [];
  const listStack = [];

  let inParagraph = false;
  let paragraphHasContent = false;
  let inBlockquote = false;
  let inCodeBlock = false;
  let codeLang = "";
  const codeBuffer = [];

  const closeParagraph = () => {
    if (inParagraph) {
      html.push("</p>");
      inParagraph = false;
      paragraphHasContent = false;
    }
  };

  const closeListsToIndent = (indent) => {
    while (listStack.length && listStack[listStack.length - 1].indent > indent) {
      const { type } = listStack.pop();
      html.push(`</${type}>`);
    }
  };

  const closeAllLists = () => {
    closeListsToIndent(-1);
  };

  const ensureList = (type, indent) => {
    const current = listStack[listStack.length - 1];
    if (!current || current.indent < indent) {
      html.push(`<${type}>`);
      listStack.push({ type, indent });
      return;
    }
    if (current.indent === indent && current.type !== type) {
      html.push(`</${current.type}>`);
      listStack.pop();
      html.push(`<${type}>`);
      listStack.push({ type, indent });
    }
  };

  const flushCodeBlock = () => {
    const code = codeBuffer.join("\n");
    const languageClass = codeLang ? ` class="language-${codeLang}"` : "";
    html.push(`<pre><code${languageClass}>${code}</code></pre>`);
    codeBuffer.length = 0;
    codeLang = "";
  };

  for (let index = 0; index < lines.length; index += 1) {
    let line = lines[index];

    if (inCodeBlock) {
      if (/^\s*```/.test(line)) {
        flushCodeBlock();
        inCodeBlock = false;
      } else {
        codeBuffer.push(line);
      }
      continue;
    }

    const fenceMatch = line.match(/^\s*```(\w+)?\s*$/);
    if (fenceMatch) {
      closeParagraph();
      closeAllLists();
      const language = fenceMatch[1] ? fenceMatch[1].trim().toLowerCase() : "";
      inCodeBlock = true;
      codeLang = language;
      continue;
    }

    if (line.trim() === "") {
      closeParagraph();
      continue;
    }

    const blockquoteMatch = line.match(/^\s*> ?(.*)$/);
    if (blockquoteMatch) {
      if (!inBlockquote) {
        closeParagraph();
        closeAllLists();
        html.push("<blockquote>");
        inBlockquote = true;
      }
      line = blockquoteMatch[1];
    } else if (inBlockquote) {
      closeParagraph();
      closeAllLists();
      html.push("</blockquote>");
      inBlockquote = false;
      index -= 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      closeParagraph();
      closeAllLists();
      const level = headingMatch[1].length;
      html.push(`<h${level}>${processInline(headingMatch[2].trim())}</h${level}>`);
      continue;
    }

    const hrMatch = line.trim().match(/^([-*_])(?:\s*\1){2,}$/);
    if (hrMatch) {
      closeParagraph();
      closeAllLists();
      html.push("<hr />");
      continue;
    }

    const listMatch = line.match(/^(\s*)([-+*]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      const indent = listMatch[1].replace(/\t/g, "    ").length;
      const marker = listMatch[2];
      const content = listMatch[3];

      closeParagraph();
      closeListsToIndent(indent);

      const type = marker.endsWith(".") ? "ol" : "ul";
      ensureList(type, indent);

      html.push("<li>");
      html.push(processInline(content.trim()));
      html.push("</li>");
      continue;
    }

    if (listStack.length) {
      closeParagraph();
      closeAllLists();
    }

    if (!inParagraph) {
      html.push("<p>");
      inParagraph = true;
      paragraphHasContent = false;
    }

    const content = processInline(line.trim());
    if (paragraphHasContent && content) {
      html.push(" ");
    }
    if (content) {
      html.push(content);
      paragraphHasContent = true;
    }
  }

  if (inCodeBlock) {
    flushCodeBlock();
  }

  closeParagraph();
  closeAllLists();
  if (inBlockquote) {
    closeParagraph();
    closeAllLists();
    html.push("</blockquote>");
  }

  return html.join("");
}
let activePromptSuggestions = [...DEFAULT_PROMPT_SUGGESTIONS];
const FOLLOW_UP_SUGGESTION_LIBRARY = {
  Growth: "Which peers are pacing the fastest quarter-over-quarter growth versus consensus?",
  Revenue: "Break revenue down by segment with multi-year CAGR for each tracked ticker.",
  Margin: "Compare gross and operating margins against peers over the trailing four quarters.",
  Earnings: "Summarise EPS surprises and guidance changes across the peer set.",
  "Cash Flow": "Analyse free-cash-flow conversion and working capital movements this year.",
  Valuation: "Benchmark valuation multiples versus sector medians and the three-year average.",
  Leverage: "Show leverage ratios and interest coverage versus covenant targets.",
  Market: "Highlight market share shifts and relative price performance over the last month.",
  Snapshot: "Generate a KPI snapshot that I can paste into an investment memo.",
  KPI: "List the KPI definitions and calculation lineage referenced in this analysis."
};
const MAX_PROMPT_SUGGESTIONS = 5;
const ALERT_PREFS_KEY = "finanlyzeos.alertPreferences";
const DEFAULT_ALERT_PREFERENCES = {
  digest: "immediate",
  quietHours: {
    enabled: false,
    start: "22:00",
    end: "07:00",
  },
  types: {
    filings: { enabled: true, mandatory: true },
    metricDelta: { enabled: true, threshold: 10 },
    dataQuality: { enabled: true },
  },
  channels: {
    email: { enabled: true, address: "" },
    slack: { enabled: false, webhook: "" },
  },
};
const PREFERS_REDUCED_MOTION = (() => {
  try {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  } catch (error) {
    return false;
  }
})();

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
const PROMPT_CACHE_LIMIT = 32;
const PROMPT_CACHE_TTL_MS = 3 * 60 * 1000;
const promptCache = new Map();
const topBar = document.querySelector(".top-bar");
const PROGRESS_POLL_INTERVAL_MS = 750;
const progressTrackers = new Map();

// Rotating placeholder for hero (no chips)
const PLACEHOLDERS = [
  "Ask anything about tickers or metrics…",
  "Compare two companies…",
  "Request a KPI table or explain a metric…",
];
let placeholderTimer = null;
let placeholderIndex = 0;
let hasNewSinceScroll = false;
let lastFocusedBeforeAudit = null;
let auditAbortController = null;
let auditDrawerEvents = [];
let auditActiveEventIndex = -1;

function startPlaceholderRotation() {
  stopPlaceholderRotation();
  if (!chatInput) {
    return;
  }
  chatInput.placeholder = PLACEHOLDERS[0];
  placeholderTimer = window.setInterval(() => {
    if (!chatInput) {
      return;
    }
    if (document.activeElement === chatInput) {
      return; // don't rotate while typing/focused
    }
    if (chatInput.value && chatInput.value.trim().length > 0) {
      return; // keep when user has typed
    }
    placeholderIndex = (placeholderIndex + 1) % PLACEHOLDERS.length;
    chatInput.placeholder = PLACEHOLDERS[placeholderIndex];
  }, 5000);
}

function stopPlaceholderRotation() {
  if (placeholderTimer) {
    window.clearInterval(placeholderTimer);
    placeholderTimer = null;
  }
}

// Textarea auto-grow: up to 4 lines, cap at 6 lines then scroll
function autoResizeTextarea() {
  if (!chatInput) return;
  const style = window.getComputedStyle(chatInput);
  const lineHeight = parseFloat(style.lineHeight) || 22;
  const paddingY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
  const minHeight = 48;
  const maxAutoLines = 4;
  const maxLines = 6;
  chatInput.style.height = "auto";
  const content = chatInput.scrollHeight;
  const maxAuto = maxAutoLines * lineHeight + paddingY;
  const hardMax = maxLines * lineHeight + paddingY;
  const next = Math.min(Math.max(content, minHeight), hardMax);
  chatInput.style.height = `${next}px`;
  chatInput.style.overflowY = next >= hardMax ? "auto" : "hidden";
}
const COMPLETE_STAGE_HINTS = [
  "_complete",
  "_ready",
  "cache_hit",
  "cache_miss",
  "cache_store",
  "cache_skip",
  "summary_cache_hit",
  "summary_build_complete",
  "context_sources_ready",
  "context_sources_empty",
  "summary_unavailable",
  "finalize",
  "help_complete",
  "complete",
];
const PROGRESS_BLUEPRINT = [
  {
    key: "intent",
    label: "Understand request",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("intent") ||
        stage === "help_lookup" ||
        stage === "help_complete"
      );
    },
  },
  {
    key: "cache",
    label: "Check recent answers",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return stage.startsWith("cache");
    },
  },
  {
    key: "context",
    label: "Gather context",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("context") ||
        stage.startsWith("summary") ||
        stage.startsWith("metrics") ||
        stage.startsWith("ticker")
      );
    },
  },
  {
    key: "compose",
    label: "Compose explanation",
    matches(stage) {
      if (!stage) {
        return false;
      }
      return (
        stage.startsWith("llm") ||
        stage === "fallback" ||
        stage === "finalize" ||
        stage === "complete"
      );
    },
  },
];
let companyUniverseData = [];
let filteredCompanyData = [];
let companyUniverseMetrics = null;
let companyUniverseTable = null;
let companyUniverseEmpty = null;
let companyUniverseSkeleton = null;
let companySearchInput = null;
let companySectorSelect = null;
let companyCoverageSelect = null;
let companyUniverseMetaUniverse = null;
let companyUniverseMetaSectors = null;
let companyUniverseMetaLatest = null;
let companyUniverseMetaCoverage = null;

const KPI_LIBRARY_PATH = "/static/data/kpi_library.json";
const COMPANY_UNIVERSE_PATH = "/static/data/company_universe.json";
const SETTINGS_STORAGE_KEY = "finanlyzeos.userSettings.v1";
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

function cloneAlertDefaults() {
  try {
    // structuredClone is not available in older browsers, fall back to JSON copy.
    return typeof structuredClone === "function"
      ? structuredClone(DEFAULT_ALERT_PREFERENCES)
      : JSON.parse(JSON.stringify(DEFAULT_ALERT_PREFERENCES));
  } catch (error) {
    return JSON.parse(JSON.stringify(DEFAULT_ALERT_PREFERENCES));
  }
}

function loadAlertPreferences() {
  try {
    const raw = localStorage.getItem(ALERT_PREFS_KEY);
    if (!raw) {
      return cloneAlertDefaults();
    }
    const parsed = JSON.parse(raw);
    const defaults = cloneAlertDefaults();
    return {
      ...defaults,
      ...parsed,
      digest: parsed?.digest || defaults.digest,
      quietHours: {
        ...defaults.quietHours,
        ...(parsed?.quietHours || {}),
      },
      types: {
        ...defaults.types,
        ...(parsed?.types || {}),
      },
      channels: {
        ...defaults.channels,
        ...(parsed?.channels || {}),
      },
    };
  } catch (error) {
    console.warn("Unable to load alert preferences from storage", error);
    return cloneAlertDefaults();
  }
}

function saveAlertPreferences(preferences) {
  try {
    localStorage.setItem(ALERT_PREFS_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.error("Unable to persist alert preferences", error);
    throw error;
  }
}

function renderAlertPreview(previewEl, preferences) {
  if (!previewEl) {
    return;
  }
  const prefs = preferences || cloneAlertDefaults();
  previewEl.innerHTML = "";

  const heading = document.createElement("strong");
  heading.textContent = "What you'll receive";
  previewEl.append(heading);

  const items = document.createElement("ul");
  const activeTypes = [];
  if (prefs.types.filings?.enabled) {
    activeTypes.push("New SEC filing events for tracked tickers.");
  }
  if (prefs.types.metricDelta?.enabled) {
    const threshold = Number(prefs.types.metricDelta.threshold) || DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold;
    activeTypes.push(`Metric change alerts above ${threshold}% delta.`);
  }
  if (prefs.types.dataQuality?.enabled) {
    activeTypes.push("Data quality failures or ingestion retries.");
  }
  if (!activeTypes.length) {
    activeTypes.push("No proactive alerts are currently enabled.");
  }
  activeTypes.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    items.append(li);
  });
  previewEl.append(items);

  const channels = [];
  if (prefs.channels.email?.enabled) {
    const address = prefs.channels.email.address || "Add an email address";
    channels.push(`Email → ${address}`);
  }
  if (prefs.channels.slack?.enabled) {
    channels.push("Slack webhook");
  }
  if (!channels.length) {
    channels.push("No delivery channels enabled.");
  }
  const channelLine = document.createElement("p");
  channelLine.textContent = `Channels: ${channels.join(", ")}`;
  previewEl.append(channelLine);

  const digestLabel = {
    immediate: "Deliver immediately",
    daily: "Daily digest (8:00 AM)",
    weekly: "Weekly digest (Monday 8:00 AM)",
  }[prefs.digest] || "Deliver immediately";

  const digestLine = document.createElement("p");
  digestLine.textContent = `Cadence: ${digestLabel}`;
  previewEl.append(digestLine);

  const quietLine = document.createElement("p");
  quietLine.textContent = prefs.quietHours?.enabled
    ? `Quiet hours: ${prefs.quietHours.start || "22:00"} – ${prefs.quietHours.end || "07:00"}`
    : "Quiet hours disabled.";
  previewEl.append(quietLine);
}
function renderAlertSettingsSection({ container } = {}) {
  if (!container) {
    return;
  }

  const preferences = loadAlertPreferences();
  container.innerHTML = `
    <form class="alert-settings" data-role="alert-settings-form" novalidate>
      <fieldset class="alert-settings__section">
        <legend>Alert types</legend>
        <p class="alert-settings__description">Choose which events raise notifications for your workspace.</p>
        <div class="alert-settings__grid">
          <label class="alert-settings__toggle" data-role="alert-type-filings">
            <input type="checkbox" name="alerts.filings" disabled />
            <span>New SEC filing ingested</span>
            <small>Mandatory for audit coverage.</small>
          </label>
          <label class="alert-settings__toggle">
            <input type="checkbox" name="alerts.metricDelta" />
            <span>Metric change above threshold</span>
            <small>Triggered when KPI delta exceeds your configured limit.</small>
          </label>
          <label class="alert-settings__toggle">
            <input type="checkbox" name="alerts.dataQuality" />
            <span>Data quality issue detected</span>
            <small>Heads-up when ingestion or QA checks fail.</small>
          </label>
        </div>
        <div class="alert-settings__field">
          <span>Metric delta threshold (%)</span>
          <input
            type="number"
            name="alerts.metricDeltaThreshold"
            min="1"
            max="100"
            step="1"
            inputmode="numeric"
            aria-describedby="metric-threshold-help"
          />
          <small id="metric-threshold-help" class="alert-settings__description">Alerts fire when absolute change exceeds this value.</small>
        </div>
      </fieldset>
      <fieldset class="alert-settings__section">
        <legend>Delivery channels</legend>
        <p class="alert-settings__description">Route alerts to your preferred communication channels.</p>
        <div class="alert-settings__channels">
          <div class="alert-settings__channel" data-channel="email">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="channel.email.enabled" />
              <span>Email (SES)</span>
              <small>Distribute alerts to analysts or coverage aliases.</small>
            </label>
            <div class="alert-settings__field">
              <span>Email address</span>
              <input type="email" name="channel.email.address" placeholder="name@company.com" autocomplete="email" />
            </div>
          </div>
          <div class="alert-settings__channel" data-channel="slack">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="channel.slack.enabled" />
              <span>Slack webhook</span>
              <small>Post alerts into a shared #finalyze channel.</small>
            </label>
            <div class="alert-settings__field">
              <span>Webhook URL</span>
              <input type="url" name="channel.slack.webhook" placeholder="https://hooks.slack.com/..." inputmode="url" />
            </div>
          </div>
        </div>
      </fieldset>
      <fieldset class="alert-settings__section">
        <legend>Cadence & quiet hours</legend>
        <div class="alert-settings__grid">
          <div class="alert-settings__field">
            <span>Digest cadence</span>
            <select name="alerts.digest">
              <option value="immediate">Send immediately</option>
              <option value="daily">Daily summary</option>
              <option value="weekly">Weekly digest</option>
            </select>
          </div>
          <div class="alert-settings__field">
            <label class="alert-settings__toggle">
              <input type="checkbox" name="alerts.quiet.enabled" />
              <span>Respect quiet hours</span>
              <small>Pause notifications between the times below.</small>
            </label>
            <div class="alert-settings__grid">
              <div class="alert-settings__field">
                <span>Quiet hours start</span>
                <input type="time" name="alerts.quiet.start" />
              </div>
              <div class="alert-settings__field">
                <span>Quiet hours end</span>
                <input type="time" name="alerts.quiet.end" />
              </div>
            </div>
          </div>
        </div>
      </fieldset>
      <div class="alert-settings__actions">
        <button type="submit">Save preferences</button>
        <button type="button" data-role="alert-reset">Reset to defaults</button>
      </div>
      <p class="alert-settings__status" data-role="alert-status" aria-live="polite"></p>
      <div class="alert-settings__preview" data-role="alert-preview"></div>
    </form>
  `;

  const form = container.querySelector("[data-role='alert-settings-form']");
  if (!form) {
    return;
  }

  const statusEl = form.querySelector("[data-role='alert-status']");
  const resetButton = form.querySelector("[data-role='alert-reset']");
  const previewEl = form.querySelector("[data-role='alert-preview']");
  const channelContainers = {
    email: form.querySelector("[data-channel='email']"),
    slack: form.querySelector("[data-channel='slack']"),
  };

  const controls = {
    filings: form.querySelector("[name='alerts.filings']"),
    metricDelta: form.querySelector("[name='alerts.metricDelta']"),
    metricDeltaThreshold: form.querySelector("[name='alerts.metricDeltaThreshold']"),
    dataQuality: form.querySelector("[name='alerts.dataQuality']"),
    digest: form.querySelector("[name='alerts.digest']"),
    quietEnabled: form.querySelector("[name='alerts.quiet.enabled']"),
    quietStart: form.querySelector("[name='alerts.quiet.start']"),
    quietEnd: form.querySelector("[name='alerts.quiet.end']"),
    emailEnabled: form.querySelector("[name='channel.email.enabled']"),
    emailAddress: form.querySelector("[name='channel.email.address']"),
    slackEnabled: form.querySelector("[name='channel.slack.enabled']"),
    slackWebhook: form.querySelector("[name='channel.slack.webhook']"),
  };

  const applyPreferences = (prefs) => {
    controls.filings.checked = true;
    controls.metricDelta.checked = Boolean(prefs.types.metricDelta?.enabled);
    controls.metricDeltaThreshold.value = Number(prefs.types.metricDelta?.threshold ?? DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold);
    controls.dataQuality.checked = Boolean(prefs.types.dataQuality?.enabled);
    controls.digest.value = prefs.digest || DEFAULT_ALERT_PREFERENCES.digest;
    controls.quietEnabled.checked = Boolean(prefs.quietHours?.enabled);
    controls.quietStart.value = prefs.quietHours?.start || DEFAULT_ALERT_PREFERENCES.quietHours.start;
    controls.quietEnd.value = prefs.quietHours?.end || DEFAULT_ALERT_PREFERENCES.quietHours.end;
    controls.emailEnabled.checked = Boolean(prefs.channels.email?.enabled);
    controls.emailAddress.value = prefs.channels.email?.address || "";
    controls.slackEnabled.checked = Boolean(prefs.channels.slack?.enabled);
    controls.slackWebhook.value = prefs.channels.slack?.webhook || "";
    syncQuietHours();
    syncChannelState();
    syncMetricThresholdState();
    renderAlertPreview(previewEl, prefs);
  };

  const clampThreshold = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return DEFAULT_ALERT_PREFERENCES.types.metricDelta.threshold;
    }
    return Math.min(100, Math.max(1, Math.round(numeric)));
  };

  const collectPreferences = () => {
    const next = cloneAlertDefaults();
    next.types.metricDelta.enabled = Boolean(controls.metricDelta.checked);
    next.types.metricDelta.threshold = clampThreshold(controls.metricDeltaThreshold.value);
    next.types.dataQuality.enabled = Boolean(controls.dataQuality.checked);
    next.digest = controls.digest.value || DEFAULT_ALERT_PREFERENCES.digest;
    next.quietHours.enabled = Boolean(controls.quietEnabled.checked);
    next.quietHours.start = controls.quietStart.value || DEFAULT_ALERT_PREFERENCES.quietHours.start;
    next.quietHours.end = controls.quietEnd.value || DEFAULT_ALERT_PREFERENCES.quietHours.end;
    next.channels.email.enabled = Boolean(controls.emailEnabled.checked);
    next.channels.email.address = controls.emailAddress.value.trim();
    next.channels.slack.enabled = Boolean(controls.slackEnabled.checked);
    next.channels.slack.webhook = controls.slackWebhook.value.trim();
    controls.metricDeltaThreshold.value = next.types.metricDelta.threshold;
    return next;
  };

  const showStatus = (message, tone = "info") => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = message;
    statusEl.dataset.tone = tone;
  };

  const syncChannelState = () => {
    const emailEnabled = Boolean(controls.emailEnabled?.checked);
    const slackEnabled = Boolean(controls.slackEnabled?.checked);
    if (controls.emailAddress) {
      controls.emailAddress.disabled = !emailEnabled;
    }
    if (controls.slackWebhook) {
      controls.slackWebhook.disabled = !slackEnabled;
    }
    if (channelContainers.email) {
      channelContainers.email.classList.toggle("alert-settings__channel-disabled", !emailEnabled);
    }
    if (channelContainers.slack) {
      channelContainers.slack.classList.toggle("alert-settings__channel-disabled", !slackEnabled);
    }
  };

  const syncQuietHours = () => {
    const enabled = Boolean(controls.quietEnabled?.checked);
    if (controls.quietStart) {
      controls.quietStart.disabled = !enabled;
    }
    if (controls.quietEnd) {
      controls.quietEnd.disabled = !enabled;
    }
  };

  const syncMetricThresholdState = () => {
    if (!controls.metricDeltaThreshold) {
      return;
    }
    const enabled = Boolean(controls.metricDelta?.checked);
    controls.metricDeltaThreshold.disabled = !enabled;
  };

  applyPreferences(preferences);

  controls.emailEnabled?.addEventListener("change", () => {
    syncChannelState();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.slackEnabled?.addEventListener("change", () => {
    syncChannelState();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.quietEnabled?.addEventListener("change", () => {
    syncQuietHours();
    renderAlertPreview(previewEl, collectPreferences());
  });
  controls.metricDelta?.addEventListener("change", () => {
    syncMetricThresholdState();
    renderAlertPreview(previewEl, collectPreferences());
  });

  form.addEventListener("input", (event) => {
    if (event.target === controls.metricDeltaThreshold) {
      controls.metricDeltaThreshold.value = controls.metricDeltaThreshold.value.slice(0, 3);
    }
    if (statusEl) {
      statusEl.textContent = "";
      delete statusEl.dataset.tone;
    }
    renderAlertPreview(previewEl, collectPreferences());
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = collectPreferences();
    try {
      saveAlertPreferences(next);
      showStatus("Alert preferences saved.", "success");
      renderAlertPreview(previewEl, next);
    } catch (error) {
      showStatus("Unable to save alert preferences. Try again.", "error");
    }
  });

  resetButton?.addEventListener("click", (event) => {
    event.preventDefault();
    const defaults = cloneAlertDefaults();
    applyPreferences(defaults);
    try {
      saveAlertPreferences(defaults);
      showStatus("Alert preferences reset to defaults.", "success");
    } catch (error) {
      showStatus("Unable to reset alert preferences.", "error");
    }
    renderAlertPreview(previewEl, defaults);
  });
}

function generateRequestId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `req_${Date.now().toString(16)}_${Math.random().toString(16).slice(2, 10)}`;
}

function formatElapsed(milliseconds) {
  if (typeof milliseconds !== "number" || Number.isNaN(milliseconds)) {
    return null;
  }
  if (milliseconds < 1000) {
    return `${Math.max(0, milliseconds).toFixed(0)} ms`;
  }
  if (milliseconds < 10000) {
    return `${(milliseconds / 1000).toFixed(1)} s`;
  }
  return `${Math.round(milliseconds / 1000)} s`;
}

function createProgressSteps() {
  return PROGRESS_BLUEPRINT.map(({ key, label }) => ({
    key,
    label,
    status: "pending",
    detail: "",
    messages: [],
  }));
}

function stepStatusFromStage(stage) {
  if (!stage) {
    return "pending";
  }
  if (stage === "error") {
    return "error";
  }
  if (stage === "complete" || COMPLETE_STAGE_HINTS.some((hint) => stage.includes(hint))) {
    return "complete";
  }
  return "active";
}

function findStepKeyForStage(stage) {
  if (!stage) {
    return null;
  }
  const match = PROGRESS_BLUEPRINT.find((entry) => entry.matches(stage));
  return match ? match.key : null;
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
      <div class="company-universe__legend" role="note" aria-label="Dataset cues">
        <span class="company-universe__legend-title">Data cues</span>
        <span class="company-universe__legend-item" title="Market cap benchmark"> 
          <span class="company-universe__legend-dot company-universe__legend-dot--mega" aria-hidden="true"></span>
          Market cap ≥ $1T
        </span>
        <span class="company-universe__legend-item" title="Filing recency benchmark">
          <span class="company-universe__legend-dot company-universe__legend-dot--stale" aria-hidden="true"></span>
          Filing > 180 days
        </span>
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
        <div class="company-universe__skeleton" data-role="company-universe-skeleton">
          ${Array.from({ length: 6 })
            .map(
              () => `
                <div class=\"company-universe__skeleton-row\">
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                  <span class=\"company-universe__skeleton-col\"></span>
                </div>`
            )
            .join("")}
        </div>
        <p class="company-universe__empty hidden" data-role="company-universe-empty">
          <span class="company-universe__empty-icon" aria-hidden="true">📊</span>
          <span>No companies match your search. Adjust filters and try again.</span>
        </p>
      </div>
    </div>
  `;

  const companyUniverseDiv = container.querySelector(".company-universe");
  if (companyUniverseDiv) {
    const hero = buildCompanyUniverseHero();
    companyUniverseDiv.insertBefore(hero, companyUniverseDiv.firstChild);
  }

  companySearchInput = container.querySelector("[data-role='company-universe-search']");
  companySectorSelect = container.querySelector("[data-role='company-universe-sector']");
  companyCoverageSelect = container.querySelector("[data-role='company-universe-coverage']");
  companyUniverseMetrics = container.querySelector("[data-role='company-universe-metrics']");
  companyUniverseTable = container.querySelector("[data-role='company-universe-table']");
  companyUniverseEmpty = container.querySelector("[data-role='company-universe-empty']");
  companyUniverseSkeleton = container.querySelector("[data-role='company-universe-skeleton']");
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
  if (companyUniverseSkeleton) {
    companyUniverseSkeleton.classList.remove("hidden");
  }
  if (companyUniverseEmpty) {
    companyUniverseEmpty.classList.add("hidden");
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
  "What was Tesla's 2022 revenue?",
];

const HELP_SECTIONS = [
  {
    icon: "📊",
    title: "KPI & Comparisons",
    command: "Metrics TICKER [YEAR | YEAR–YEAR] [+ peers]",
    purpose: "Summarise a company's finance snapshot or line up peers on one table.",
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
  lines.push("📘 Finalyze Copilot — Quick Reference", "", "How to ask:");
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

  // Hero box (summary card)
  const hero = document.createElement("section");
  hero.className = "help-guide__hero";

  const badge = document.createElement("div");
  badge.className = "help-guide__badge";
  badge.textContent = "📘";

  const heroCopy = document.createElement("div");
  heroCopy.className = "help-guide__hero-copy";

  const title = document.createElement("h3");
  title.className = "help-guide__title";
  title.textContent = "Finalyze Copilot — Quick Reference";

  const subtitle = document.createElement("p");
  subtitle.className = "help-guide__subtitle";
  subtitle.textContent = "Ask natural prompts and I will translate them into institutional-grade analysis.";

  heroCopy.append(title, subtitle);
  hero.append(badge, heroCopy);

  // Search Form (similar to KPI Library)
  const controls = document.createElement("div");
  controls.className = "help-guide__filters";
  
  const searchGroup = document.createElement("div");
  searchGroup.className = "help-guide__filter help-guide__filter--search";
  const searchInput = document.createElement("input");
  searchInput.type = "search";
  searchInput.placeholder = "Search by command, purpose, or example";
  searchInput.autocomplete = "off";
  searchInput.className = "help-guide__search";
  searchGroup.append(searchInput);
  controls.append(searchGroup);

  const categoryGroup = document.createElement("div");
  categoryGroup.className = "help-guide__filter";
  const categorySelect = document.createElement("select");
  categorySelect.className = "help-guide__select";
  categorySelect.innerHTML = `<option value="">All categories</option>`;
  const categories = Array.from(
    new Set(content.sections.map((section) => section.title || "").filter(Boolean))
  ).sort((a, b) => a.localeCompare(b));
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.append(option);
  });
  categoryGroup.append(categorySelect);
  controls.append(categoryGroup);

  // Create sticky container for hero + filters
  const stickyContainer = document.createElement("div");
  stickyContainer.className = "help-guide__sticky-container";
  stickyContainer.append(hero);
  stickyContainer.append(controls);
  article.append(stickyContainer);

  const sectionGrid = document.createElement("div");
  sectionGrid.className = "help-guide__grid";

  // Filter function
  const filterCards = () => {
    const searchTerm = searchInput.value.toLowerCase().trim();
    const selectedCategory = categorySelect.value;

    const cards = sectionGrid.querySelectorAll(".help-guide__card");
    let visibleCount = 0;

    cards.forEach((card) => {
      const title = card.querySelector(".help-guide__card-title")?.textContent || "";
      const command = card.querySelector(".help-guide__value")?.textContent || "";
      const purpose = Array.from(card.querySelectorAll(".help-guide__value")).map(el => el.textContent).join(" ") || "";
      const examples = Array.from(card.querySelectorAll(".help-guide__list li")).map(el => el.textContent).join(" ") || "";
      
      const matchesSearch = !searchTerm || 
        title.toLowerCase().includes(searchTerm) ||
        command.toLowerCase().includes(searchTerm) ||
        purpose.toLowerCase().includes(searchTerm) ||
        examples.toLowerCase().includes(searchTerm);
      
      const matchesCategory = !selectedCategory || title === selectedCategory;

      if (matchesSearch && matchesCategory) {
        card.style.display = "";
        visibleCount++;
      } else {
        card.style.display = "none";
      }
    });

    // Show empty state if no cards visible
    let emptyState = sectionGrid.querySelector(".help-guide__empty");
    if (visibleCount === 0) {
      if (!emptyState) {
        emptyState = document.createElement("div");
        emptyState.className = "help-guide__empty";
        emptyState.textContent = "No results match your search.";
        sectionGrid.append(emptyState);
      }
      emptyState.style.display = "";
    } else if (emptyState) {
      emptyState.style.display = "none";
    }
  };

  searchInput.addEventListener("input", filterCards);
  categorySelect.addEventListener("change", filterCards);

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
      pill.setAttribute("role", "button");
      pill.setAttribute("tabindex", "0");
      pill.setAttribute("aria-label", `Use command: ${token}`);
      pill.title = `Click to copy: ${token}`;
      // Add click handler to copy command
      pill.addEventListener("click", () => {
        navigator.clipboard.writeText(token).then(() => {
          const originalText = pill.textContent;
          pill.textContent = "✓ Copied!";
          pill.style.color = "#16a34a";
          setTimeout(() => {
            pill.textContent = originalText;
            pill.style.color = "";
          }, 1500);
        }).catch(() => {
          // Fallback: insert into chat input if available
          const chatInput = document.querySelector("#chat-input, .chat-input, textarea[placeholder*='Ask']");
          if (chatInput) {
            chatInput.value = token;
            chatInput.focus();
            chatInput.dispatchEvent(new Event("input", { bubbles: true }));
          }
        });
      });
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

function createMetaBadge(label, value, directionality = null) {
  if (!value) {
    return null;
  }
  const badge = document.createElement("span");
  badge.className = "kpi-library__meta-pill";
  
  // Add color coding for directionality
  if (label === "Direction" && directionality) {
    const colorClass = getDirectionalityColor(directionality);
    badge.classList.add(colorClass);
  }
  
  badge.textContent = `${label}: ${value}`;
  return badge;
}

function getDirectionalityColor(directionality) {
  switch (directionality) {
    case "higher_is_better":
      return "kpi-library__meta-pill--positive";
    case "lower_is_better":
      return "kpi-library__meta-pill--negative";
    case "depends":
      return "kpi-library__meta-pill--neutral";
    case "neutral":
      return "kpi-library__meta-pill--neutral";
    default:
      return "";
  }
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
  title.textContent = "KPI Library";

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

function buildCompanyUniverseHero() {
  const hero = document.createElement("section");
  hero.className = "company-universe__hero";

  const badge = document.createElement("div");
  badge.className = "company-universe__badge";
  badge.textContent = "🏢";

  const copy = document.createElement("div");
  copy.className = "company-universe__hero-copy";

  const title = document.createElement("h3");
  title.className = "company-universe__title";
  title.textContent = "Company Universe";

  const subtitle = document.createElement("p");
  subtitle.className = "company-universe__subtitle";
  subtitle.textContent =
    "Explore coverage across every tracked company, segment results, and monitor ingestion progress inside this financial dataset view. The database contains 2.88M+ rows of financial data across 1,505 companies.";

  const context = document.createElement("p");
  context.className = "company-universe__context";
  context.textContent = "Coverage includes all S&P 500 firms and major tech leaders, refreshed weekly.";

  const status = document.createElement("div");
  status.className = "company-universe__status";

  // Universe status card
  const universeCard = document.createElement("div");
  universeCard.className = "company-universe__status-card";
  universeCard.setAttribute("role", "status");
  universeCard.innerHTML = `
    <span class="company-universe__status-icon" aria-hidden="true">📈</span>
    <div class="company-universe__status-text">
      <span class="company-universe__status-label">Universe</span>
      <span class="company-universe__status-value" data-role="company-universe-meta-universe">Loading...</span>
    </div>
  `;

  // Sectors status card
  const sectorsCard = document.createElement("div");
  sectorsCard.className = "company-universe__status-card";
  sectorsCard.setAttribute("role", "status");
  sectorsCard.innerHTML = `
    <span class="company-universe__status-icon" aria-hidden="true">🏭</span>
    <div class="company-universe__status-text">
      <span class="company-universe__status-label">Sectors</span>
      <span class="company-universe__status-value" data-role="company-universe-meta-sectors">Loading...</span>
    </div>
  `;

  // Latest filing status card
  const latestCard = document.createElement("div");
  latestCard.className = "company-universe__status-card";
  latestCard.setAttribute("role", "status");
  latestCard.innerHTML = `
    <span class="company-universe__status-icon" aria-hidden="true">🗓</span>
    <div class="company-universe__status-text">
      <span class="company-universe__status-label">Latest filing</span>
      <span class="company-universe__status-value" data-role="company-universe-meta-latest">Loading...</span>
    </div>
  `;

  // Coverage mix status card
  const coverageCard = document.createElement("div");
  coverageCard.className = "company-universe__status-card";
  coverageCard.setAttribute("role", "status");
  coverageCard.innerHTML = `
    <span class="company-universe__status-icon" aria-hidden="true">✅</span>
    <div class="company-universe__status-text">
      <span class="company-universe__status-label">Coverage mix</span>
      <span class="company-universe__status-value" data-role="company-universe-meta-coverage">Loading...</span>
    </div>
  `;

  status.append(universeCard, sectorsCard, latestCard, coverageCard);

  copy.append(title);
  copy.append(subtitle);
  copy.append(context);
  copy.append(status);

  hero.append(badge);
  hero.append(copy);
  return hero;
}

function buildKpiCard(kpi) {
  const card = document.createElement("article");
  card.className = "kpi-library__doc-card";

  // Header with title and meta
  const header = document.createElement("header");
  header.className = "kpi-library__doc-header";

  const title = document.createElement("h5");
  title.className = "kpi-library__doc-title";
  
  // Add category icon
  const categoryIcon = getCategoryIcon(kpi.category);
  if (categoryIcon) {
    title.innerHTML = `<span class="category-icon">${categoryIcon}</span> ${kpi.display_name || formatTagName(kpi.kpi_id)}`;
  } else {
    title.textContent = kpi.display_name || formatTagName(kpi.kpi_id);
  }
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
  const directionBadge = createMetaBadge("Direction", formatDirectionality(kpi.directionality), kpi.directionality);
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

  // Basic info (always visible)
  const body = document.createElement("div");
  body.className = "kpi-library__doc-body";

  // Definition (short)
  if (kpi.definition_short) {
    const definitionSection = createDocSection("📘 Definition", kpi.definition_short);
    body.append(definitionSection);
  }

  // Formula
  if (kpi.formula_text) {
    const formulaSection = createDocSection("📊 Formula", kpi.formula_text, { type: "code" });
    body.append(formulaSection);
  }

  // Interpretation
  if (kpi.interpretation) {
    const interpretationSection = createDocSection("✅ Interpretation", kpi.interpretation);
    body.append(interpretationSection);
  }

  card.append(body);

  // Advanced info (collapsible)
  const hasAdvancedInfo = kpi.view_more && (
    kpi.view_more.related_metrics?.length ||
    kpi.view_more.data_source_hint?.length ||
    kpi.view_more.natural_language_examples?.length ||
    kpi.view_more.limitations
  );

  if (hasAdvancedInfo) {
    const advancedSection = buildAdvancedInfo(kpi);
    card.append(advancedSection);
  }

  return card;
}

function getCategoryIcon(category) {
  const icons = {
    "Growth Metrics": "📈",
    "Profitability Metrics": "💰", 
    "Valuation Metrics": "📊",
    "Leverage Metrics": "⚖️",
    "Liquidity Metrics": "💧",
    "Dividend Metrics": "💸",
    "Share Metrics": "📋",
    "Balance Sheet Metrics": "📄",
    "Income Statement Metrics": "📋",
    "Cash Flow Metrics": "💸",
    "Per-Share Metrics": "📊"
  };
  return icons[category] || "";
}

function buildAdvancedInfo(kpi) {
  const advancedSection = document.createElement("div");
  advancedSection.className = "kpi-library__advanced";

  const toggle = document.createElement("button");
  toggle.className = "kpi-library__advanced-toggle";
  toggle.innerHTML = "🔽 <span>View More</span>";
  toggle.addEventListener("click", () => {
    const isOpen = toggle.classList.contains("is-open");
    const content = advancedSection.querySelector(".kpi-library__advanced-content");
    
    if (isOpen) {
      toggle.classList.remove("is-open");
      toggle.innerHTML = "🔽 <span>View More</span>";
      content.style.display = "none";
    } else {
      toggle.classList.add("is-open");
      toggle.innerHTML = "🔼 <span>View Less</span>";
      content.style.display = "block";
    }
  });

  const content = document.createElement("div");
  content.className = "kpi-library__advanced-content";
  content.style.display = "none";

  if (kpi.view_more?.related_metrics?.length) {
    const relatedSection = createDocSection("🔗 Related Metrics", kpi.view_more.related_metrics.join(", "));
    content.append(relatedSection);
  }

  if (kpi.view_more?.data_source_hint?.length) {
    const sourceSection = createDocSection("📂 Data Sources", kpi.view_more.data_source_hint.join(", "));
    content.append(sourceSection);
  }

  if (kpi.view_more?.natural_language_examples?.length) {
    const examplesSection = createDocSection("💬 Example Queries", kpi.view_more.natural_language_examples.join(", "));
    content.append(examplesSection);
  }

  if (kpi.view_more?.limitations) {
    const limitationsSection = createDocSection("⚠️ Limitations", kpi.view_more.limitations);
    content.append(limitationsSection);
  }

  advancedSection.append(toggle);
  advancedSection.append(content);

  return advancedSection;
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
      <div class="filing-viewer__sticky-container">
      <section class="filing-viewer__hero">
        <div class="filing-viewer__badge">📄</div>
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
      </div>
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
    title: "",
    html: `<div class="utility-loading">Đang tải KPI library…</div>`,
    render: renderKpiLibrarySection,
  },
  "company-universe": {
    title: "",
    html: `<div class="utility-loading">Loading company universe…</div>`,
    render: renderCompanyUniverseSection,
  },
  "filing-viewer": {
    title: "",
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
  alerts: {
    title: "Alert Settings",
    html: `<div class="alert-settings__skeleton">Loading alert preferences…</div>`,
    render: renderAlertSettingsSection,
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
  // CRITICAL: Strictly validate dashboard - if null/undefined/empty, treat as no dashboard
  let dashboard = response.dashboard || response.Dashboard || null;
  
  // Extra validation: ensure dashboard is not empty object or invalid
  if (dashboard !== null && typeof dashboard === 'object') {
    // If dashboard is an empty object {}, treat as null
    if (Object.keys(dashboard).length === 0) {
      dashboard = null;
    }
    // If dashboard has no kind or payload, treat as null
    if (!dashboard.kind && !dashboard.payload && !dashboard.dashboards) {
      dashboard = null;
    }
  }
  
  const artifacts = {
    highlights: Array.isArray(response.highlights) ? response.highlights : [],
    trends: Array.isArray(response.trends) ? response.trends : [],
    comparisonTable: response.comparison_table || response.comparisonTable || null,
    citations: Array.isArray(response.citations) ? response.citations : [],
    exports: Array.isArray(response.exports) ? response.exports : [],
    conclusion: "",
    dashboard: dashboard,  // Use validated dashboard (null if invalid)
  };
  if (
    !artifacts.highlights.length &&
    !artifacts.trends.length &&
    !artifacts.comparisonTable &&
    !artifacts.citations.length &&
    !artifacts.exports.length &&
    !artifacts.dashboard
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
  avatar.textContent = role === "user" ? "You" : role === "assistant" ? "FZ" : "SYS";

  const label = document.createElement("span");
  label.className = "message-role";
  label.textContent = role === "user" ? "You" : role === "assistant" ? "Finalyze" : "System";

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
  if (forceScroll || isNearBottom(120)) {
    scrollChatToBottom({ smooth });
    hasNewSinceScroll = false;
  } else {
    hasNewSinceScroll = true;
  }
  return wrapper;
}

function createTypingIndicator() {
  const container = document.createElement("div");
  container.className = "typing-indicator";

  const srLabel = document.createElement("span");
  srLabel.className = "sr-only";
  srLabel.textContent = "Finalyze is typing";
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
    avatar.textContent = role === "user" ? "You" : role === "assistant" ? "FZ" : "SYS";
  }

  const roleLabel = wrapper.querySelector(".message-role");
  if (roleLabel) {
    roleLabel.textContent =
      role === "user" ? "You" : role === "assistant" ? "Finalyze" : "System";
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
  wrapper.querySelectorAll(".message-dashboard").forEach((node) => node.remove());
  const existing = wrapper.querySelector(".message-artifacts");
  if (existing) {
    existing.remove();
  }
  if (!artifacts) {
    wrapper.classList.remove("message--has-dashboard");
    return;
  }
  const body = wrapper.querySelector(".message-body");
  if (!body) {
    wrapper.classList.remove("message--has-dashboard");
    return;
  }
  let hasDashboard = false;
  const inlineDashboard = renderDashboardArtifact(artifacts.dashboard);
  const dashboardKind = artifacts.dashboard?.kind || "";
  const isInlineClassic =
    inlineDashboard && (dashboardKind === "cfi-classic" || dashboardKind === "cfi-compare" || dashboardKind === "multi-classic" || dashboardKind === "multi-cfi-classic");
  if (inlineDashboard) {
    hasDashboard = true;
    body.append(inlineDashboard);
    if (!isInlineClassic) {
      wrapper.classList.toggle("message--has-dashboard", hasDashboard);
      return;
    }
  }
  const dashboard = createDashboardLayout(artifacts);
  if (dashboard && dashboardKind !== "cfi-classic" && dashboardKind !== "multi-classic" && dashboardKind !== "multi-cfi-classic") {
    hasDashboard = true;
    body.append(dashboard);
    if (artifacts.comparisonTable) {
      body.querySelectorAll(".message-table").forEach((tableNode) => tableNode.remove());
    }
    wrapper.classList.toggle("message--has-dashboard", hasDashboard);
    return;
  }
  const sections = [];
  if (!isInlineClassic) {
    const highlightsSection = createHighlightsSection(artifacts.highlights);
    if (highlightsSection) {
      sections.push(highlightsSection);
    }
    const tableSection = createComparisonTableSection(artifacts.comparisonTable);
    if (tableSection) {
      sections.push(tableSection);
    }
    const conclusionSection = createConclusionSection(artifacts.conclusion);
    if (conclusionSection) {
      sections.push(conclusionSection);
    }
    const trendsSection = createTrendSection(artifacts.trends);
    if (trendsSection) {
      sections.push(trendsSection);
    }
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
    wrapper.classList.toggle("message--has-dashboard", hasDashboard);
    return;
  }
  const container = document.createElement("div");
  container.className = "message-artifacts";
  sections.forEach((section) => container.append(section));
  body.append(container);
  if (artifacts.comparisonTable) {
    body.querySelectorAll(".message-table").forEach((tableNode) => tableNode.remove());
  }
  wrapper.classList.toggle("message--has-dashboard", hasDashboard);
}
function createDashboardLayout(artifacts) {
  const hasComparison =
    artifacts?.comparisonTable &&
    Array.isArray(artifacts.comparisonTable.rows) &&
    artifacts.comparisonTable.rows.length > 0;
  const hasHighlights = Array.isArray(artifacts?.highlights) && artifacts.highlights.length > 0;
  const hasTrends = Array.isArray(artifacts?.trends) && artifacts.trends.length > 0;
  const hasConclusion = typeof artifacts?.conclusion === "string" && artifacts.conclusion.trim();
  const hasCitations = Array.isArray(artifacts?.citations) && artifacts.citations.length > 0;
  const hasExports = Array.isArray(artifacts?.exports) && artifacts.exports.length > 0;
  if (!(hasComparison || hasHighlights || hasTrends)) {
    return null;
  }
  const wrapper = document.createElement("section");
  wrapper.className = "financial-dashboard";
  if (hasComparison) {
    const header = createDashboardHeader(artifacts.comparisonTable);
    if (header) {
      wrapper.append(header);
    }
    const ribbon = createDashboardRibbon(artifacts);
    if (ribbon) {
      wrapper.append(ribbon);
    }
  } else {
    const header = document.createElement("header");
    header.className = "financial-dashboard__header";
    const title = document.createElement("h3");
    title.className = "financial-dashboard__title";
    title.textContent = "Financial model dashboard";
    header.append(title);
    wrapper.append(header);
  }
  if (hasHighlights) {
    const highlightsSection = createDashboardHighlights(artifacts.highlights);
    if (highlightsSection) {
      wrapper.append(highlightsSection);
    }
  }
  if (hasComparison) {
    const summary = createDashboardSummary(artifacts.comparisonTable);
    if (summary) {
      wrapper.append(summary);
    }
    const comparison = createDashboardTable(artifacts.comparisonTable);
    if (comparison) {
      wrapper.append(comparison);
    }
  }
  if (hasTrends) {
    const charts = createDashboardTrends(artifacts.trends);
    if (charts) {
      wrapper.append(charts);
    }
  }
  if (hasConclusion || hasCitations || hasExports) {
    const footer = createDashboardFooter({
      conclusion: artifacts.conclusion,
      citations: artifacts.citations,
      exports: artifacts.exports,
    });
    if (footer) {
      wrapper.append(footer);
    }
  }
  return wrapper;
}


// Helper function to make all IDs unique within a dashboard instance
function makeIdsUnique(container, uniqueSuffix) {
  if (!container) return;
  
  // Find all elements with IDs and make them unique
  const elementsWithIds = container.querySelectorAll('[id]');
  const idMap = new Map(); // Track old ID -> new ID mappings
  
  elementsWithIds.forEach(element => {
    const oldId = element.id;
    const newId = `${oldId}-${uniqueSuffix}`;
    element.id = newId;
    idMap.set(oldId, newId);
  });
  
  // Update all 'for' attributes in labels to match new IDs
  const labels = container.querySelectorAll('label[for]');
  labels.forEach(label => {
    const oldFor = label.getAttribute('for');
    const newFor = idMap.get(oldFor);
    if (newFor) {
      label.setAttribute('for', newFor);
    }
  });
  
  // Update all aria-labelledby and aria-describedby references
  const elementsWithAria = container.querySelectorAll('[aria-labelledby], [aria-describedby]');
  elementsWithAria.forEach(element => {
    ['aria-labelledby', 'aria-describedby'].forEach(attr => {
      const oldValue = element.getAttribute(attr);
      if (oldValue) {
        const ids = oldValue.split(/\s+/);
        const newIds = ids.map(id => idMap.get(id) || id);
        element.setAttribute(attr, newIds.join(' '));
      }
    });
  });
}

function renderDashboardArtifact(descriptor) {
  // CRITICAL: Strict null/undefined/invalid dashboard check
  if (!descriptor || descriptor === null || descriptor === undefined) {
    console.log('[Dashboard] Dashboard is null/undefined - skipping render');
    return null;
  }
  // Extra validation: ensure descriptor is a valid object with required properties
  if (typeof descriptor !== 'object' || Object.keys(descriptor).length === 0) {
    console.log('[Dashboard] Dashboard is invalid object - skipping render');
    return null;
  }
  const kind = descriptor.kind || "cfi-classic";
  const container = document.createElement("div");
  container.className = "message-dashboard";
  if (kind === "cfi-classic" || kind === "cfi-compare" || kind === "multi-classic" || kind === "multi-cfi-classic") {
    container.classList.add("message-dashboard--cfi");
  }
  
  // Handle multi-classic and multi-cfi-classic: render multiple single-company dashboards with company switcher
  if ((kind === "multi-classic" || kind === "multi-cfi-classic") && descriptor.dashboards && Array.isArray(descriptor.dashboards)) {
    const multiContainer = document.createElement("div");
    multiContainer.className = "message-dashboard__multi";
    
    // Create selector for companies
    const selectorWrapper = document.createElement("div");
    selectorWrapper.className = "message-dashboard__selector";
    
    const selectorLabel = document.createElement("div");
    selectorLabel.className = "message-dashboard__selector-label";
    selectorLabel.textContent = `Compare Companies (${descriptor.dashboards.length}):`;
    
    // Determine if we should use buttons (small number) or dropdown (large number)
    const useDropdown = descriptor.dashboards.length > 10;
    
    if (useDropdown) {
      // Create searchable dropdown for large lists
      const dropdownContainer = document.createElement("div");
      dropdownContainer.className = "message-dashboard__dropdown-container";
      
      const searchInput = document.createElement("input");
      searchInput.type = "text";
      searchInput.className = "message-dashboard__company-search";
      searchInput.placeholder = "Search companies by name or ticker...";
      searchInput.setAttribute("autocomplete", "off");
      
      const selectElement = document.createElement("select");
      selectElement.className = "message-dashboard__company-select";
      selectElement.size = 1;
      
      // Populate select options
      descriptor.dashboards.forEach((dashboardItem, index) => {
        const companyName = dashboardItem.payload?.meta?.company || dashboardItem.ticker || `Company ${index + 1}`;
        const ticker = dashboardItem.ticker || dashboardItem.payload?.meta?.ticker || '';
        const option = document.createElement("option");
        option.value = index;
        option.textContent = ticker ? `${ticker} - ${companyName}` : companyName;
        option.dataset.ticker = ticker;
        option.dataset.company = companyName;
        selectElement.appendChild(option);
      });
      
      dropdownContainer.appendChild(searchInput);
      dropdownContainer.appendChild(selectElement);
      selectorWrapper.appendChild(selectorLabel);
      selectorWrapper.appendChild(dropdownContainer);
      
      // Setup search filtering
      let allOptions = Array.from(selectElement.options);
      searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        
        // Clear existing options
        selectElement.innerHTML = "";
        
        // Filter and re-add matching options
        const matchingOptions = allOptions.filter(option => {
          const ticker = (option.dataset.ticker || "").toLowerCase();
          const company = (option.dataset.company || "").toLowerCase();
          return ticker.includes(query) || company.includes(query);
        });
        
        matchingOptions.forEach(option => selectElement.appendChild(option));
        
        // Show count in label
        selectorLabel.textContent = `Compare Companies (${matchingOptions.length} of ${descriptor.dashboards.length}):`;
      });
    } else {
      // Use button group for small lists (original behavior)
      const buttonGroup = document.createElement("div");
      buttonGroup.className = "message-dashboard__button-group";
      
      // Create buttons for each company
      descriptor.dashboards.forEach((dashboardItem, index) => {
        const button = document.createElement("button");
        button.className = "message-dashboard__company-btn";
        button.dataset.companyIndex = index;
        
        // Extract company name and ticker
        const companyName = dashboardItem.payload?.meta?.company || dashboardItem.ticker || `Company ${index + 1}`;
        const ticker = dashboardItem.ticker || dashboardItem.payload?.meta?.ticker || '';
        
        // Button content
        const nameSpan = document.createElement("span");
        nameSpan.className = "company-btn-name";
        nameSpan.textContent = companyName;
        
        if (ticker) {
          const tickerSpan = document.createElement("span");
          tickerSpan.className = "company-btn-ticker";
          tickerSpan.textContent = ticker;
          button.appendChild(nameSpan);
          button.appendChild(tickerSpan);
        } else {
          button.appendChild(nameSpan);
        }
        
        // First button is active by default
        if (index === 0) {
          button.classList.add('active');
        }
        
        buttonGroup.appendChild(button);
      });
      
      selectorWrapper.appendChild(selectorLabel);
      selectorWrapper.appendChild(buttonGroup);
    }
    
    multiContainer.appendChild(selectorWrapper);
    
    // Create container for dashboard (only one visible at a time)
    const dashboardContainer = document.createElement("div");
    dashboardContainer.className = "message-dashboard__switchable";
    
    // Create all dashboard hosts but hide all except first
    const dashboardHosts = descriptor.dashboards.map((dashboardItem, index) => {
      const host = document.createElement("div");
      host.className = "message-dashboard__surface";
      host.style.display = index === 0 ? "block" : "none"; // Show first, hide others
      host.dataset.dashboardIndex = index;
      
      // Add unique identifier to avoid duplicate IDs across dashboards
      const uniqueId = `dash-${Date.now()}-${index}`;
      host.dataset.dashboardId = uniqueId;
      
      // Debug logging
      console.log(`Multi-dashboard item ${index}:`, {
        ticker: dashboardItem.ticker,
        hasPayload: !!dashboardItem.payload,
        payloadKeys: dashboardItem.payload ? Object.keys(dashboardItem.payload) : []
      });
      
      // Ensure payload exists before rendering
      if (!dashboardItem.payload) {
        console.error(`No payload for ${dashboardItem.ticker}`);
        host.innerHTML = `<div class="cfi-error">No data available for ${dashboardItem.ticker}.</div>`;
        dashboardContainer.appendChild(host);
        return host;
      }
      
      // Add to container FIRST before rendering
      dashboardContainer.appendChild(host);
      
      // Store render function for this dashboard
      host.renderDashboard = async () => {
        try {
          const options = { 
            container: host,
            payload: dashboardItem.payload,
            ticker: dashboardItem.ticker,
            isMultiTicker: true  // Flag to indicate this is part of a multi-ticker dashboard
          };
          await showCfiDashboard(options);
          
          // Fix duplicate IDs by making them unique per dashboard
          makeIdsUnique(host, uniqueId);
        } catch (error) {
          console.error(`Failed to render dashboard for ${dashboardItem.ticker}:`, error);
          host.innerHTML = `<div class="cfi-error">Unable to render dashboard for ${dashboardItem.ticker}.</div>`;
        }
      };
      
      return host;
    });
    
    multiContainer.appendChild(dashboardContainer);
    container.appendChild(multiContainer);
    
    // NOW render dashboards after everything is in the DOM
    setTimeout(() => {
      dashboardHosts.forEach((host, index) => {
        if (host.renderDashboard) {
          // Only render the first dashboard initially for better performance
          if (index === 0) {
            host.dataset.rendered = "true";
            host.renderDashboard();
          }
        }
      });
    }, 100);
    
    // Setup switching logic based on UI type
    const switchToDashboard = (selectedIndex) => {
      // Switch dashboards
      dashboardHosts.forEach((host, index) => {
        if (index === selectedIndex) {
          host.style.display = "block";
          // Render on-demand if not already rendered
          if (host.renderDashboard && !host.dataset.rendered) {
            host.dataset.rendered = "true";
            host.renderDashboard();
          }
        } else {
          host.style.display = "none";
        }
      });
    };
    
    if (useDropdown) {
      // Dropdown event handler
      const selectElement = selectorWrapper.querySelector(".message-dashboard__company-select");
      if (selectElement) {
        selectElement.addEventListener("change", (e) => {
          const selectedIndex = parseInt(e.target.value, 10);
          switchToDashboard(selectedIndex);
        });
        
        // Set initial selection
        selectElement.selectedIndex = 0;
      }
    } else {
      // Button event handlers (original behavior)
      // Need to query after DOM is ready
      setTimeout(() => {
        const companyButtons = selectorWrapper.querySelectorAll(".message-dashboard__company-btn");
        companyButtons.forEach((button) => {
          button.addEventListener("click", () => {
            const selectedIndex = parseInt(button.dataset.companyIndex, 10);
            
            // Update active button state
            companyButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            switchToDashboard(selectedIndex);
          });
        });
      }, 0);
    }
    
    return container;
  }
  
  // Standard single dashboard rendering
  const host = document.createElement("div");
  host.className = "message-dashboard__surface";
  container.append(host);
  const options = { container: host };
  if (descriptor.payload) {
    options.payload = descriptor.payload;
  }
  if (descriptor.ticker) {
    options.ticker = descriptor.ticker;
  }
  if (descriptor.tickers) {
    options.tickers = descriptor.tickers;
  }
  if (descriptor.benchmark) {
    options.benchmark = descriptor.benchmark;
  }
  const previousContainer = window.__cfiActiveContainer;
  window.__cfiActiveContainer = host;
  const finalizeContainer = () => {
    if (window.__cfiActiveContainer === host) {
      window.__cfiActiveContainer = previousContainer;
    }
  };
  let renderPromise;
  try {
    if (kind === "cfi-compare") {
      renderPromise = showCfiCompareDashboard(options);
    } else if (kind === "cfi-dense") {
      renderPromise = showCfiDenseDashboard(options);
    } else {
      renderPromise = showCfiDashboard(options);
    }
  } catch (error) {
    console.error(error);
    host.innerHTML = '<div class="cfi-error">Unable to render dashboard. Check console for details.</div>';
    finalizeContainer();
    return container;
  }
  if (renderPromise && typeof renderPromise.catch === "function") {
    renderPromise.catch((error) => {
      console.error(error);
      host.innerHTML = '<div class="cfi-error">Unable to render dashboard. Check console for details.</div>';
      finalizeContainer();
    });
    if (typeof renderPromise.finally === "function") {
      renderPromise.finally(finalizeContainer);
    } else {
      finalizeContainer();
    }
  } else {
    finalizeContainer();
  }
  return container;
}

function createDashboardHeader(table) {
  if (!table) {
    return null;
  }
  const header = document.createElement("header");
  header.className = "financial-dashboard__header";
  const title = document.createElement("h3");
  title.className = "financial-dashboard__title";
  title.textContent = table.title || "Financial model dashboard";
  header.append(title);
  if (table.descriptor) {
    const descriptor = document.createElement("p");
    descriptor.className = "financial-dashboard__descriptor";
    descriptor.textContent = table.descriptor;
    header.append(descriptor);
  }
  if (Array.isArray(table.tickers) && table.tickers.length) {
    const tickers = document.createElement("div");
    tickers.className = "financial-dashboard__tickers";
    table.tickers.forEach((ticker) => {
      const badge = document.createElement("span");
      badge.className = "financial-dashboard__ticker";
      badge.textContent = ticker;
      tickers.append(badge);
    });
    header.append(tickers);
  }
  return header;
}

function createDashboardRibbon(artifacts) {
  const items = deriveRibbonItems(artifacts);
  if (!items.length) {
    return null;
  }
  const ribbon = document.createElement("section");
  ribbon.className = "financial-dashboard__ribbon";
  items.forEach((item) => {
    const entry = document.createElement("article");
    entry.className = "financial-dashboard__ribbon-item";
    const label = document.createElement("span");
    label.className = "financial-dashboard__ribbon-label";
    label.textContent = item.label;
    const value = document.createElement("span");
    value.className = "financial-dashboard__ribbon-value";
    value.textContent = item.value;
    entry.append(label, value);
    ribbon.append(entry);
  });
  return ribbon;
}

function deriveRibbonItems({ highlights, comparisonTable, conclusion }) {
  const items = [];
  if (comparisonTable?.tickers?.length) {
    items.push({
      label: comparisonTable.tickers.length > 1 ? "Peer set" : "Company",
      value: comparisonTable.tickers.join(" vs "),
    });
  }
  if (comparisonTable?.descriptor) {
    items.push({
      label: "Coverage window",
      value: comparisonTable.descriptor,
    });
  }
  if (Array.isArray(highlights)) {
    highlights.forEach((entry) => {
      if (items.length >= 5) {
        return;
      }
      const parsed = parseHighlightPair(entry);
      if (parsed) {
        items.push(parsed);
      }
    });
  }
  if (items.length < 4 && typeof conclusion === "string" && conclusion.trim()) {
    items.push({
      label: "Narrative",
      value: truncateText(conclusion.trim(), 90),
    });
  }
  return items.slice(0, 5);
}

function parseHighlightPair(text) {
  if (typeof text !== "string") {
    return null;
  }
  const colonIndex = text.indexOf(":");
  if (colonIndex > -1) {
    return {
      label: text.slice(0, colonIndex).trim(),
      value: text.slice(colonIndex + 1).trim(),
    };
  }
  const dashIndex = text.indexOf("-");
  if (dashIndex > -1) {
    return {
      label: text.slice(0, dashIndex).trim(),
      value: text.slice(dashIndex + 1).trim(),
    };
  }
  return null;
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1).trim()}…`;
}

function createDashboardSummary(table) {
  const headers = Array.isArray(table?.headers) ? table.headers.slice(1) : [];
  const rows = Array.isArray(table?.rows) ? table.rows : [];
  if (!headers.length || !rows.length) {
    return null;
  }
  const summaryRows = rows
    .filter((row) => Array.isArray(row) && row.length === headers.length + 1)
    .slice(0, 4);
  if (!summaryRows.length) {
    return null;
  }
  const section = document.createElement("section");
  section.className = "financial-dashboard__summary";
  headers.forEach((ticker, index) => {
    const card = document.createElement("article");
    card.className = "financial-dashboard__stat-card";
    const heading = document.createElement("h4");
    heading.className = "financial-dashboard__stat-title";
    heading.textContent = normalizeDashboardText(ticker) || "—";
    card.append(heading);
    const list = document.createElement("dl");
    list.className = "financial-dashboard__stat-list";
    summaryRows.forEach((row) => {
      const dt = document.createElement("dt");
      dt.textContent = normalizeDashboardText(row[0]) || "—";
      const dd = document.createElement("dd");
      const text = normalizeDashboardText(row[index + 1]);
      dd.textContent = text || "—";
      list.append(dt, dd);
    });
    card.append(list);
    section.append(card);
  });
  return section;
}

function createDashboardHighlights(highlights) {
  if (!Array.isArray(highlights) || !highlights.length) {
    return null;
  }
  const section = document.createElement("section");
  section.className = "financial-dashboard__highlights";
  const heading = document.createElement("h4");
  heading.className = "financial-dashboard__section-title";
  heading.textContent = "Key takeaways";
  section.append(heading);
  const list = document.createElement("ul");
  list.className = "financial-dashboard__highlight-list";
  highlights.slice(0, 6).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.append(li);
  });
  section.append(list);
  return section;
}

function normalizeDashboardText(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    const absolute = Math.abs(value);
    const formatter =
      Number.isInteger(value) && absolute >= 100
        ? { maximumFractionDigits: 0 }
        : { minimumFractionDigits: absolute < 10 ? 2 : 1, maximumFractionDigits: 2 };
    return value.toLocaleString("en-US", formatter);
  }
  let text = String(value);
  try {
    text = decodeURIComponent(escape(text));
  } catch (error) {
    // ignore decoding failures
  }
  text = text
    .normalize("NFKC")
    .replace(/\u00a0/g, " ")
    .replace(/Ã—|Ã|Ã\x97/g, "×")
    .replace(/Â/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) {
    return "";
  }
  if (/^(?:n\/?a|na|not\s+available|--|-|—)$/i.test(text)) {
    return "—";
  }
  text = text.replace(/(\d)\s*%/g, "$1%");
  text = text.replace(/(\d)\s*(b|m|k)\b/gi, "$1\u00a0$2");
  text = text.replace(/(\d)\s*[xX]$/g, "$1×");
  text = text.replace(/(\d)\s*×$/g, "$1×");
  text = text
    .normalize("NFKC")
    .replace(/[^\w\s.,%$€£¥±×–—°()/\-&]/g, "")
    .trim();
  return text;
}

function createDashboardTable(table) {
  if (!table || !Array.isArray(table.headers) || !table.headers.length) {
    return null;
  }
  const section = document.createElement("section");
  section.className = "financial-dashboard__table";
  const head = document.createElement("div");
  head.className = "financial-dashboard__table-head";
  const heading = document.createElement("h4");
  heading.className = "financial-dashboard__section-title";
  heading.textContent = "Key financials";
  head.append(heading);
  if (table.descriptor) {
    const descriptor = document.createElement("span");
    descriptor.className = "financial-dashboard__table-descriptor";
    descriptor.textContent = normalizeDashboardText(table.descriptor) || "";
    head.append(descriptor);
  }
  section.append(head);
  const surface = document.createElement("div");
  surface.className = "financial-dashboard__table-surface";
  const tableEl = document.createElement("table");
  tableEl.className = "financial-dashboard__grid";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  table.headers.forEach((label, index) => {
    const cell = document.createElement("th");
    cell.textContent = normalizeDashboardText(label) || "—";
    if (index === 0) {
      cell.classList.add("is-metric");
    }
    headerRow.append(cell);
  });
  thead.append(headerRow);
  tableEl.append(thead);
  const tbody = document.createElement("tbody");
  (table.rows || []).forEach((row) => {
    if (!Array.isArray(row) || !row.length) {
      return;
    }
    const tr = document.createElement("tr");
    row.forEach((value, index) => {
      const cell = document.createElement(index === 0 ? "th" : "td");
      if (index === 0) {
        cell.scope = "row";
        cell.classList.add("is-metric");
      } else {
        cell.classList.add("is-value");
      }
      const text = normalizeDashboardText(value);
      cell.textContent = text || "—";
      tr.append(cell);
    });
    tbody.append(tr);
  });
  tableEl.append(tbody);
  surface.append(tableEl);
  section.append(surface);
  return section;
}

function createDashboardTrends(trends) {
  const seriesList = Array.isArray(trends)
    ? trends.filter((series) => Array.isArray(series.points) && series.points.length >= 2)
    : [];
  if (!seriesList.length) {
    return null;
  }
  const section = document.createElement("section");
  section.className = "financial-dashboard__charts";
  const heading = document.createElement("h4");
  heading.className = "financial-dashboard__section-title";
  heading.textContent = "Trend snapshots";
  section.append(heading);
  const grid = document.createElement("div");
  grid.className = "financial-dashboard__chart-grid";
  seriesList.slice(0, 3).forEach((series) => {
    const card = createTrendCard(series);
    if (card) {
      card.classList.add("financial-dashboard__chart-card");
      grid.append(card);
    }
  });
  section.append(grid);
  return section;
}

function createDashboardFooter({ conclusion, citations, exports }) {
  const hasConclusion = typeof conclusion === "string" && conclusion.trim().length > 0;
  const hasCitations = Array.isArray(citations) && citations.length > 0;
  const hasExports = Array.isArray(exports) && exports.length > 0;
  if (!hasConclusion && !hasCitations && !hasExports) {
    return null;
  }
  const section = document.createElement("section");
  section.className = "financial-dashboard__footnotes";
  if (hasConclusion) {
    const summary = document.createElement("article");
    summary.className = "financial-dashboard__conclusion";
    const heading = document.createElement("h4");
    heading.className = "financial-dashboard__section-title";
    heading.textContent = "Analyst summary";
    summary.append(heading);
    const copy = document.createElement("p");
    copy.textContent = conclusion.trim();
    summary.append(copy);
    section.append(summary);
  }
  if (hasCitations) {
    const citeBlock = document.createElement("article");
    citeBlock.className = "financial-dashboard__citations";
    const heading = document.createElement("h4");
    heading.className = "financial-dashboard__section-title";
    heading.textContent = `Sources (${citations.length})`;
    citeBlock.append(heading);
    const list = document.createElement("ul");
    list.className = "financial-dashboard__citation-list";
    citations.forEach((entry) => {
      const item = document.createElement("li");
      const parts = [];
      if (entry.ticker) {
        parts.push(entry.ticker);
      }
      if (entry.label) {
        parts.push(entry.label);
      }
      if (entry.period) {
        parts.push(entry.period);
      }
      if (entry.formatted_value) {
        parts.push(entry.formatted_value);
      } else if (typeof entry.value === "number") {
        parts.push(String(entry.value));
      }
      item.textContent = parts.join(" • ");
      if (entry.urls && (entry.urls.detail || entry.urls.interactive)) {
        const link = document.createElement("a");
        link.href = entry.urls.detail || entry.urls.interactive;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "View filing";
        item.append(link);
      }
      list.append(item);
    });
    citeBlock.append(list);
    section.append(citeBlock);
  }
  if (hasExports) {
    const exportsBlock = document.createElement("article");
    exportsBlock.className = "financial-dashboard__exports";
    const heading = document.createElement("h4");
    heading.className = "financial-dashboard__section-title";
    heading.textContent = "Exports";
    exportsBlock.append(heading);
    const buttons = document.createElement("div");
    buttons.className = "financial-dashboard__export-buttons";
    exports.forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "financial-dashboard__export-button";
      button.textContent = entry.label || entry.type.toUpperCase();
      button.addEventListener("click", () => handleExport(entry));
      buttons.append(button);
    });
    exportsBlock.append(buttons);
    section.append(exportsBlock);
  }
  return section;
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

function createConclusionSection(conclusion) {
  if (!conclusion) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-conclusion";
  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = "Summary & next steps";
  const text = document.createElement("p");
  text.className = "artifact-conclusion__text";
  text.textContent = conclusion;
  wrapper.append(title, text);
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
    const header = document.createElement("div");
    header.className = "artifact-table__header";
    if (table.title) {
      const title = document.createElement("h3");
      title.className = "artifact-table__title";
      title.textContent = table.title;
      header.append(title);
    }
    if (table.descriptor) {
      const descriptor = document.createElement("div");
      descriptor.className = "artifact-table__descriptor";
      descriptor.textContent = table.descriptor;
      header.append(descriptor);
    }
    wrapper.append(header);
  }

  const surface = document.createElement("div");
  surface.className = "artifact-table__surface";

  const tableEl = document.createElement("table");
  tableEl.className = "artifact-table__grid";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  table.headers.forEach((header, index) => {
    const cell = document.createElement("th");
    if (index === 0) {
      cell.classList.add("artifact-table__metric");
    }
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
        cell.classList.add("artifact-table__metric");
      } else {
        cell.classList.add("artifact-table__value");
      }
      cell.textContent = value;
      tr.append(cell);
    });
    tbody.append(tr);
  });
  tableEl.append(tbody);
  surface.append(tableEl);
  wrapper.append(surface);
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
  const wrapper = document.createElement("section");
  wrapper.className = "artifact-section artifact-sources";

  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = `Sources (${citations.length})`;
  wrapper.append(title);

  const list = document.createElement("div");
  list.className = "artifact-sources__list";

  citations.forEach((citation) => {
    const row = document.createElement("div");
    row.className = "artifact-sources__row";

    const descriptorParts = [
      citation.ticker,
      citation.label,
      citation.period,
      citation.formatted_value ||
        (typeof citation.value === "number" ? citation.value.toLocaleString() : null),
    ].filter(Boolean);

    const descriptor = document.createElement("span");
    descriptor.className = "artifact-sources__descriptor";
    descriptor.textContent = descriptorParts.join(" • ");
    row.append(descriptor);

    const filingUrl = citation.urls?.detail || citation.urls?.interactive || null;
    if (filingUrl) {
      const link = document.createElement("a");
      link.href = filingUrl;
      link.target = "_blank";
      link.rel = "noopener";
      link.className = "artifact-sources__link";
      link.textContent = "View filing";
      row.append(link);
    }

    list.append(row);
  });

  wrapper.append(list);
  return wrapper;
}

function closeAuditDrawer() {
  if (!auditDrawer) {
    return;
  }
  if (auditAbortController) {
    auditAbortController.abort();
    auditAbortController = null;
  }
  auditDrawer.classList.remove("visible");
  auditDrawer.setAttribute("aria-hidden", "true");
  auditDrawerStatus.textContent = "Select a metric to view lineage.";
  auditDrawerList.innerHTML = "";
  auditDrawerEvents = [];
  auditActiveEventIndex = -1;
  if (auditDrawerDetail) {
    auditDrawerDetail.innerHTML =
      '<p class="audit-drawer__placeholder">Select an audit event to inspect lineage details.</p>';
  }
  if (lastFocusedBeforeAudit && typeof lastFocusedBeforeAudit.focus === "function") {
    lastFocusedBeforeAudit.focus();
  }
  lastFocusedBeforeAudit = null;
}

function openAuditDrawer({ ticker, metric, label, period } = {}) {
  if (!auditDrawer || !auditDrawerList || !auditDrawerStatus) {
    return;
  }
  const cleanTicker = ticker || "";
  if (!cleanTicker) {
    showToast("Unable to load audit trail without a ticker.", "error");
    return;
  }
  if (auditAbortController) {
    auditAbortController.abort();
  }
  auditAbortController = new AbortController();
  lastFocusedBeforeAudit = document.activeElement;
  auditDrawer.classList.add("visible");
  auditDrawer.setAttribute("aria-hidden", "false");
  auditDrawerStatus.textContent = "Loading audit trail…";
  auditDrawerList.innerHTML = "";
  if (auditDrawerTitle) {
    const contextLabel = label ? `${cleanTicker} • ${label}` : cleanTicker;
    auditDrawerTitle.textContent = `Audit Trail — ${contextLabel}`;
  }
  const closeButton = auditDrawer.querySelector(".audit-drawer__close");
  if (closeButton) {
    closeButton.focus();
  }
  const params = new URLSearchParams({ ticker: cleanTicker });
  const fiscalYear = deriveFiscalYear(period);
  if (fiscalYear) {
    params.set("fiscal_year", String(fiscalYear));
  }
  fetch(`${API_BASE}/audit?${params.toString()}`, { signal: auditAbortController.signal })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Audit fetch failed (${response.status})`);
      }
      return response.json();
    })
    .then((data) => {
      const events = Array.isArray(data?.events) ? data.events : [];
      if (!events.length) {
        auditDrawerStatus.textContent = "No lineage events were recorded for this metric.";
        auditDrawerEvents = [];
        if (auditDrawerDetail) {
          auditDrawerDetail.innerHTML =
            '<p class="audit-drawer__placeholder">No audit events were captured for this metric.</p>';
        }
        return;
      }
      const sorted = [...events].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
      auditDrawerEvents = sorted;
      auditDrawerStatus.textContent = `${sorted.length} event${sorted.length === 1 ? "" : "s"} recorded.`;
      renderAuditTimeline(sorted);
      setActiveAuditEvent(sorted.length - 1);
    })
    .catch((error) => {
      if (error.name === "AbortError") {
        return;
      }
      console.warn("Audit load failed:", error);
      auditDrawerStatus.textContent = "Unable to load audit events. Try again later.";
      auditDrawerEvents = [];
      auditActiveEventIndex = -1;
      if (auditDrawerDetail) {
        auditDrawerDetail.innerHTML =
          '<p class="audit-drawer__placeholder">Unable to load audit events. Try again later.</p>';
      }
    })
    .finally(() => {
      auditAbortController = null;
    });
}

function deriveFiscalYear(period) {
  if (!period || typeof period !== "string") {
    return null;
  }
  const match = period.match(/\b(20\d{2}|19\d{2})\b/);
  return match ? Number(match[0]) : null;
}

function capitalizeFirst(value) {
  if (!value || typeof value !== "string") {
    return "";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderAuditTimeline(events) {
  if (!auditDrawerList) {
    return;
  }
  auditDrawerList.innerHTML = "";
  const fragment = document.createDocumentFragment();
  events.forEach((event, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "audit-drawer__node";
    button.dataset.index = String(index);
    button.setAttribute("aria-pressed", "false");

    const title = document.createElement("span");
    title.className = "audit-drawer__node-title";
    title.textContent = `${index + 1}. ${capitalizeFirst(event.event_type || "Event")}`;
    button.append(title);

    const meta = document.createElement("span");
    meta.className = "audit-drawer__node-meta";
    meta.textContent = event.created_at ? formatDateHuman(event.created_at) : "Unknown timestamp";
    button.append(meta);

    if (event.details) {
      const detail = document.createElement("span");
      detail.className = "audit-drawer__node-detail";
      detail.textContent = event.details;
      button.append(detail);
    }

    button.addEventListener("click", () => {
      setActiveAuditEvent(index);
    });

    item.append(button);
    fragment.append(item);
  });
  auditDrawerList.append(fragment);
}

function setActiveAuditEvent(position) {
  if (!Array.isArray(auditDrawerEvents) || !auditDrawerEvents.length) {
    return;
  }
  const bounded = Math.max(0, Math.min(position, auditDrawerEvents.length - 1));
  auditActiveEventIndex = bounded;
  const nodes = auditDrawerList?.querySelectorAll(".audit-drawer__node") || [];
  nodes.forEach((node) => {
    const nodeIndex = Number(node.dataset.index);
    const isActive = nodeIndex === bounded;
    node.classList.toggle("is-active", isActive);
    node.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
  renderAuditEventDetail(auditDrawerEvents[bounded]);
}

function renderAuditEventDetail(event) {
  if (!auditDrawerDetail) {
    return;
  }
  auditDrawerDetail.innerHTML = "";
  if (!event) {
    auditDrawerDetail.innerHTML =
      '<p class="audit-drawer__placeholder">Select an audit event to inspect lineage details.</p>';
    return;
  }

  const heading = document.createElement("h3");
  heading.textContent = capitalizeFirst(event.event_type || "Audit event");
  auditDrawerDetail.append(heading);

  const descriptor = document.createElement("dl");
  const appendRow = (label, value) => {
    if (!value && value !== 0) {
      return;
    }
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = `${value}`;
    descriptor.append(dt, dd);
  };

  appendRow("Timestamp", event.created_at ? formatDateHuman(event.created_at) : "Unknown");
  appendRow("Entity", event.entity_id || event.entity || "—");
  appendRow("Metric", event.metric || "—");
  if (event.label && event.label !== event.metric) {
    appendRow("Label", event.label);
  }
  appendRow("Details", event.details || "—");
  appendRow("Actor", event.created_by || "System");

  auditDrawerDetail.append(descriptor);

  const actions = document.createElement("div");
  actions.className = "audit-drawer__detail-actions";

  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "audit-drawer__detail-secondary";
  copyButton.textContent = "Copy event JSON";
  copyButton.addEventListener("click", () => copyAuditEvent(event));
  actions.append(copyButton);

  if (actions.children.length) {
    auditDrawerDetail.append(actions);
  }
}

function copyAuditEvent(event) {
  if (!event) {
    return;
  }
  const payload = JSON.stringify(event, null, 2);
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(payload).then(
      () => showToast("Audit event copied to clipboard.", "success"),
      () => {
        window.prompt("Copy audit event details:", payload);
        showToast("Copy the JSON shown to share manually.", "info");
      }
    );
  } else {
    window.prompt("Copy audit event details:", payload);
    showToast("Copy the JSON shown to share manually.", "info");
  }
}

function createExportSection(exports) {
  if (!Array.isArray(exports) || !exports.length) {
    return null;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "artifact-section artifact-exports";
  const title = document.createElement("h4");
  title.className = "artifact-title";
  title.textContent = "Exports";
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
  link.download = payload.filename || `finalyze-export-${Date.now()}.csv`;
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
  const title = payload.title || "Finalyze export";
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
  const sourcesList = Array.isArray(payload.sources)
    ? payload.sources
        .map((source) => {
          const text =
            typeof source?.text === "string" && source.text.trim().length
              ? source.text.trim()
              : "";
          const link =
            source?.url && typeof source.url === "string"
              ? `<a href="${source.url}" target="_blank" rel="noopener">View filing</a>`
              : "";
          if (!text && !link) {
            return "";
          }
          return `<li>${text}${link ? ' — ' + link : ''}</li>`;
        })
        .filter(Boolean)
    : [];
  const sourcesMarkup = sourcesList.length
    ? `<section class="sources">
        <h2>Sources</h2>
        <ul>${sourcesList.join("")}</ul>
      </section>`
    : "";
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
      .sources { margin-top: 28px; border-top: 1px solid #cbd5f5; padding-top: 16px; }
      .sources h2 { font-size: 16px; margin: 0 0 10px; }
      .sources ul { list-style: none; padding-left: 0; margin: 0; }
      .sources li { font-size: 13px; line-height: 1.6; margin-bottom: 6px; }
      .sources a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
      .sources a:hover { text-decoration: underline; }
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
    ${sourcesMarkup}
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

function ensureMessageProgress(wrapper) {
  if (!wrapper) {
    return null;
  }
  const body = wrapper.querySelector(".message-body");
  if (!body) {
    return null;
  }
  let container = body.querySelector(".message-progress");
  if (!container) {
    container = document.createElement("div");
    container.className = "message-progress";
    const title = document.createElement("div");
    title.className = "message-progress-title";
    title.textContent = "Preparing analysis...";
    container.append(title);
    const list = document.createElement("ul");
    list.className = "message-progress-list";
    container.append(list);
    body.append(container);
  }
  return {
    container,
    list: container.querySelector(".message-progress-list"),
    title: container.querySelector(".message-progress-title"),
  };
}

function pushProgressEventsInternal(tracker, events) {
  if (!tracker || !Array.isArray(events) || !events.length) {
    return;
  }
  const container = tracker.container;
  container.classList.add("active");
  container.classList.remove("pending");
  const typingIndicator = tracker.wrapper?.querySelector(".typing-indicator");
  if (typingIndicator && !tracker.progressStarted) {
    typingIndicator.classList.add("with-progress");
    tracker.progressStarted = true;
  }
  const freshEvents = events
    .filter(
      (event) =>
        event &&
        typeof event.sequence === "number" &&
        !tracker.seen.has(event.sequence)
    )
    .sort((a, b) => a.sequence - b.sequence);
  if (!freshEvents.length) {
    return;
  }
  freshEvents.forEach((event) => {
    tracker.seen.add(event.sequence);
    tracker.lastSequence = Math.max(tracker.lastSequence, event.sequence);
    tracker.events.push(event);
    updateProgressTrackerWithEvent(tracker, event);
  });
  tracker.render();
}
function startProgressTracking(requestId, wrapper) {
  if (!requestId || !wrapper) {
    return null;
  }
  const progressElements = ensureMessageProgress(wrapper);
  if (!progressElements || !progressElements.list) {
    return null;
  }
  const { container, list, title } = progressElements;
  container.classList.add("active", "pending");
  wrapper.dataset.requestId = requestId;
  const tracker = {
    requestId,
    wrapper,
    list,
    container,
    title,
    steps: createProgressSteps(),
    seen: new Set(),
    lastSequence: 0,
    timer: null,
    pending: false,
    complete: false,
    progressStarted: false,
    events: [],
    startedAt: Number.NaN,
    render() {
      renderProgressTracker(this);
    },
  };

  if (tracker.steps.length) {
    tracker.steps[0].status = "active";
  }

  const poll = async () => {
    if (tracker.pending) {
      return;
    }
    tracker.pending = true;
    try {
      const sinceParam = tracker.lastSequence > 0 ? `?since=${tracker.lastSequence}` : "";
      const res = await fetch(`${API_BASE}/progress/${requestId}${sinceParam}`, {
        cache: "no-store",
      });
      if (!res.ok) {
        throw new Error(`Progress status ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data?.events)) {
        pushProgressEventsInternal(tracker, data.events);
      }
      if (data?.complete) {
        tracker.complete = true;
      }
      if (data?.error && tracker.title) {
        tracker.title.textContent = data.error;
        list.parentElement?.classList.add("error");
      }
    } catch (error) {
      tracker.lastError = error;
    } finally {
      tracker.pending = false;
      if (tracker.complete && tracker.timer) {
        window.clearInterval(tracker.timer);
        tracker.timer = null;
      }
    }
  };

  tracker.poll = poll;
  progressTrackers.set(requestId, tracker);
  tracker.render();
  tracker.poll().catch(() => {});
  tracker.timer = window.setInterval(() => {
    tracker.poll().catch(() => {});
  }, PROGRESS_POLL_INTERVAL_MS);
  return tracker;
}

async function stopProgressTracking(requestId, { flush = false } = {}) {
  const tracker = progressTrackers.get(requestId);
  if (!tracker) {
    return;
  }
  if (tracker.timer) {
    window.clearInterval(tracker.timer);
    tracker.timer = null;
  }
  if (flush) {
    try {
      await tracker.poll();
    } catch (error) {
      // ignore polling failure when winding down
    }
  }
  tracker.container?.classList.remove("pending");
  tracker.render();
  renderProgressSummary(tracker);
  progressTrackers.delete(requestId);
}

function pushProgressEvents(requestId, events) {
  const tracker = progressTrackers.get(requestId);
  if (!tracker) {
    return;
  }
  pushProgressEventsInternal(tracker, events);
}

function showAssistantTyping() {
  return appendMessage("assistant", "", { isPlaceholder: true, animate: false });
}

function derivePromptSuggestionsFromPrompt(prompt) {
  if (!prompt || typeof prompt !== "string") {
    return [];
  }
  const matches = new Set();
  METRIC_KEYWORD_MAP.forEach(({ regex, label }) => {
    if (regex.test(prompt)) {
      matches.add(label);
    }
  });
  const suggestions = [];
  matches.forEach((label) => {
    const candidate = FOLLOW_UP_SUGGESTION_LIBRARY[label];
    if (candidate) {
      suggestions.push(candidate);
    }
  });
  return suggestions;
}

function mergePromptSuggestionPool(dynamicSuggestions) {
  const combined = [...(dynamicSuggestions || []), ...DEFAULT_PROMPT_SUGGESTIONS];
  const unique = [];
  const seen = new Set();
  combined.forEach((suggestion) => {
    const value = `${suggestion}`.trim();
    if (!value) {
      return;
    }
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    unique.push(value);
  });
  if (!unique.length) {
    return [...DEFAULT_PROMPT_SUGGESTIONS];
  }
  return unique.slice(0, MAX_PROMPT_SUGGESTIONS);
}

function updatePromptSuggestionsFromPrompt(prompt) {
  const dynamic = derivePromptSuggestionsFromPrompt(prompt);
  activePromptSuggestions = mergePromptSuggestionPool(dynamic);
  renderPromptChips();
}

function shouldStreamText(text) {
  if (!text || typeof text !== "string") {
    return false;
  }
  if (text.length < 80) {
    return false;
  }
  if (/\n\s*\|/.test(text)) {
    return false;
  }
  return true;
}

function streamMessageBody(wrapper, text, artifacts, { forceScroll = false } = {}) {
  const body = wrapper?.querySelector(".message-body");
  if (!body) {
    return;
  }
  if (PREFERS_REDUCED_MOTION) {
    setMessageBody(wrapper, text);
    renderMessageArtifacts(wrapper, artifacts);
    if (forceScroll || isNearBottom(120)) {
      scrollChatToBottom({ smooth: true });
      hasNewSinceScroll = false;
    } else {
      hasNewSinceScroll = true;
    }
    return;
  }
  body.innerHTML = "";
  const streamBlock = document.createElement("div");
  streamBlock.className = "message-stream";
  streamBlock.setAttribute("aria-live", "polite");
  streamBlock.setAttribute("aria-atomic", "false");
  body.append(streamBlock);
  const total = text.length;
  const stepSize = Math.min(
    STREAM_MAX_SLICE,
    Math.max(STREAM_MIN_SLICE, Math.ceil(total / 120))
  );
  let index = 0;
  const pump = () => {
    if (index >= total) {
      setMessageBody(wrapper, text);
      renderMessageArtifacts(wrapper, artifacts);
      if (forceScroll || isNearBottom(120)) {
        scrollChatToBottom({ smooth: true });
        hasNewSinceScroll = false;
      } else {
        hasNewSinceScroll = true;
      }
      return;
    }
    index = Math.min(total, index + stepSize);
    streamBlock.textContent = text.slice(0, index);
    if (forceScroll || isNearBottom(160)) {
      scrollChatToBottom({ smooth: false });
      hasNewSinceScroll = false;
    }
    window.setTimeout(pump, STREAM_STEP_MS);
  };
  pump();
}

function resolvePendingMessage(
  wrapper,
  role,
  text,
  { forceScroll = false, artifacts = null, stream = false } = {}
) {
  if (!wrapper) {
    appendMessage(role, text, { forceScroll, smooth: true, artifacts });
    return null;
  }
  updateMessageRole(wrapper, role);
  wrapper.classList.remove("typing");
  if (role === "assistant" && stream && shouldStreamText(text)) {
    streamMessageBody(wrapper, text, artifacts, { forceScroll });
    return wrapper;
  }
  setMessageBody(wrapper, text);
  renderMessageArtifacts(wrapper, artifacts);
  if (forceScroll || isNearBottom(120)) {
    scrollChatToBottom({ smooth: true });
    hasNewSinceScroll = false;
  } else {
    hasNewSinceScroll = true;
  }
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
      div.innerHTML = renderMarkdown(block.text);
      fragments.push(div);
    }
  });

  if (!blocks.length) {
    const div = document.createElement("div");
    div.className = "message-content";
    div.innerHTML = renderMarkdown(text);
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

function isNearBottom(thresholdPx = 120) {
  if (!chatLog) {
    return true;
  }
  const distanceFromBottom = chatLog.scrollHeight - chatLog.clientHeight - chatLog.scrollTop;
  return distanceFromBottom <= thresholdPx;
}

function updateScrollBtnOffset() {
  if (!scrollBtn || !chatLog) {
    return;
  }
  const offset = 20; // 16–20px as spec above composer
  const btnSize = 40;
  const extra = 8;
  // Because the button is positioned inside .chat-log, which ends at the top of the composer,
  // we only need the offset from the bottom of .chat-log (not composer height).
  scrollBtn.style.bottom = `${offset}px`;
  // Add enough padding only when the button is visible; otherwise keep a small baseline.
  const pad = scrollBtn.classList.contains("show") ? (btnSize + offset + extra) : 16;
  chatLog.style.paddingBottom = `${pad}px`;
}

function refreshScrollButton() {
  if (!scrollBtn || !chatLog) {
    return;
  }
  if (!isNearBottom(120)) {
    scrollBtn.classList.add("show");
    scrollBtn.setAttribute("aria-hidden", "false");
  } else {
    scrollBtn.classList.remove("show");
    scrollBtn.setAttribute("aria-hidden", "true");
  }
  updateScrollBtnOffset();
}
function hideIntroPanel() {
  if (!introPanel) {
    return;
  }
  introPanel.classList.add("hidden");
  if (chatPanel) {
    chatPanel.classList.remove("is-hero");
  }
  if (chatLog) {
    chatLog.classList.remove("hidden");
  }
  if (chatFormContainer) {
    chatFormContainer.classList.remove("chat-form--hero");
  }
  stopPlaceholderRotation();
}

function showIntroPanel() {
  if (!introPanel) {
    return;
  }
  introPanel.classList.remove("hidden");
  if (chatPanel) {
    chatPanel.classList.add("is-hero");
  }
  if (chatLog) {
    chatLog.classList.add("hidden");
  }
  if (chatFormContainer) {
    chatFormContainer.classList.add("chat-form--hero");
  }
  startPlaceholderRotation();
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
    if (auditDrawer?.classList.contains("visible")) {
      closeAuditDrawer();
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
  sendButton.disabled = state; // block double-submit
  chatInput.disabled = false;  // still allow typing while processing
  // keep icon-only; don't swap label
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
    
    // Clean up conversations before saving to prevent quota issues
    const cleanedConversations = cleanupConversationsForStorage();
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cleanedConversations));
  } catch (error) {
    if (error.name === 'QuotaExceededError') {
      console.warn("Storage quota exceeded. Clearing old conversations...");
      // Clear old conversations and try again
      const recentConversations = keepOnlyRecentConversations(5);
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(recentConversations));
      } catch (retryError) {
        console.error("Unable to persist even after cleanup", retryError);
        // Last resort: clear all history
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } else {
      console.warn("Unable to persist conversations", error);
    }
  }
}

function cleanupConversationsForStorage() {
  const MAX_CONVERSATIONS = 20;
  const MAX_MESSAGES_PER_CONVERSATION = 50;
  
  // Sort conversations by timestamp (most recent first)
  const sortedConvs = Object.entries(conversations)
    .sort((a, b) => {
      const aTime = a[1].messages[a[1].messages.length - 1]?.timestamp || 0;
      const bTime = b[1].messages[b[1].messages.length - 1]?.timestamp || 0;
      return bTime - aTime;
    });
  
  // Keep only recent conversations
  const recentConvs = sortedConvs.slice(0, MAX_CONVERSATIONS);
  
  // Limit messages per conversation
  const cleaned = {};
  recentConvs.forEach(([id, conv]) => {
    cleaned[id] = {
      ...conv,
      messages: conv.messages.slice(-MAX_MESSAGES_PER_CONVERSATION)
    };
  });
  
  return cleaned;
}

function keepOnlyRecentConversations(count) {
  const sortedConvs = Object.entries(conversations)
    .sort((a, b) => {
      const aTime = a[1].messages[a[1].messages.length - 1]?.timestamp || 0;
      const bTime = b[1].messages[b[1].messages.length - 1]?.timestamp || 0;
      return bTime - aTime;
    })
    .slice(0, count);
  
  const recent = {};
  sortedConvs.forEach(([id, conv]) => {
    recent[id] = {
      ...conv,
      messages: conv.messages.slice(-20) // Keep only last 20 messages
    };
  });
  
  // Update global conversations object
  conversations = recent;
  return recent;
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
  saveActiveConversationId(activeConversation.id);
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
  
  // Remove sidebar footer text if accidentally included
  const footerText = "Grounded by Finalyze analytics — audit-ready by design.";
  if (typeof text === "string" && text.includes(footerText)) {
    text = text.replace(new RegExp(footerText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '').trim();
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

function exportConversation(format) {
  const conversation = activeConversation || conversations[0] || null;
  if (!conversation || !Array.isArray(conversation.messages) || !conversation.messages.length) {
    showToast("Start a conversation to export it.", "info");
    return;
  }
  if (format === "csv") {
    exportConversationCsv(conversation);
    return;
  }
  if (format === "pdf") {
    exportConversationPdf(conversation);
    return;
  }
  showToast("Unsupported export format.", "error");
}

function exportConversationCsv(conversation) {
  const headers = ["Timestamp", "Role", "Message"];
  const lines = [headers.map(formatCsvValue).join(",")];
  conversation.messages.forEach((message) => {
    const row = [
      formatExportTimestamp(message.timestamp),
      message.role || "assistant",
      (message.text || "").replace(/\s+/g, " ").trim(),
    ];
    lines.push(row.map(formatCsvValue).join(","));
  });
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${buildConversationSlug(conversation)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast("Conversation exported as CSV", "success");
}

function exportConversationPdf(conversation) {
  const win = window.open("", "_blank", "noopener");
  if (!win) {
    showToast("Allow pop-ups to export the conversation.", "error");
    return;
  }
  const title = conversation.title || "Finalyze Conversation";
  const entries = conversation.messages
    .map((message) => {
      const roleLabel =
        message.role === "assistant" ? "Finalyze" : message.role === "user" ? "You" : "System";
      const timestamp = formatExportTimestamp(message.timestamp);
      const safeText = (message.text || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return `<article class="export-entry"><header><h3>${roleLabel}</h3><span>${timestamp}</span></header><p>${safeText.replace(
        /\n/g,
        "<br />"
      )}</p></article>`;
    })
    .join("");
  const html = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${title}</title>
    <style>
      body { font-family: "Segoe UI", Arial, sans-serif; margin: 32px; color: #0f172a; background: #fff; }
      h1 { font-size: 22px; margin-bottom: 12px; }
      .export-entry { border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 18px; margin-bottom: 16px; background: #f8fafc; }
      .export-entry header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
      .export-entry p { margin: 0; font-size: 14px; line-height: 1.6; }
    </style>
  </head>
  <body>
    <h1>${title}</h1>
    ${entries}
  </body>
</html>`;
  win.document.write(html);
  win.document.close();
  win.focus();
  window.setTimeout(() => {
    try {
      win.print();
    } catch (error) {
      // ignore print errors
    }
  }, 300);
  showToast("Conversation ready for printing", "success");
}

function buildConversationSlug(conversation) {
  const base = conversation.title || "finalyze-conversation";
  return (
    base
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "finalyze-conversation"
  );
}

function formatExportTimestamp(isoString) {
  if (!isoString) {
    return new Date().toLocaleString();
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return date.toLocaleString();
}

function saveActiveConversationId(conversationId) {
  try {
    if (window.localStorage) {
      if (conversationId) {
        window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, conversationId);
      } else {
        window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
      }
    }
  } catch (error) {
    console.warn("Failed to save active conversation ID", error);
  }
}

function getActiveConversationId() {
  try {
    if (window.localStorage) {
      return window.localStorage.getItem(ACTIVE_CONVERSATION_KEY);
    }
  } catch (error) {
    console.warn("Failed to get active conversation ID", error);
  }
  return null;
}

function loadConversation(conversationId) {
  const conversation = conversations.find((entry) => entry.id === conversationId);
  if (!conversation) {
    return;
  }
  activeConversation = conversation;
  saveActiveConversationId(conversationId);

  closeReportMenu();

  if (currentUtilityKey) {
    closeUtilityPanel();
    resetNavActive();
  }

  if (chatLog) {
    chatLog.innerHTML = "";
  }

  // Clean up footer text from existing messages
  const footerText = "Grounded by Finalyze analytics — audit-ready by design.";
  if (conversation.messages && Array.isArray(conversation.messages)) {
    let needsSave = false;
    conversation.messages.forEach((message) => {
      if (typeof message.text === "string" && message.text.includes(footerText)) {
        message.text = message.text.replace(new RegExp(footerText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '').trim();
        needsSave = true;
      }
    });
    // Save cleaned conversations if any changes were made
    if (needsSave) {
      saveConversations();
    }
  }

  if (conversation.messages.length) {
    hideIntroPanel();
  } else {
    showIntroPanel();
  }

  conversation.messages.forEach((message) => {
    // CRITICAL FIX: Don't render dashboards from old conversation history
    // Only render the text, skip artifacts/dashboards from history
    // This prevents showing stale/wrong company dashboards
    let artifactsToRender = message.metadata || null;
    if (artifactsToRender && artifactsToRender.dashboard) {
      // Clear dashboard from historical messages
      artifactsToRender = { ...artifactsToRender, dashboard: null };
    }
    
    appendMessage(message.role, message.text, {
      smooth: false,
      animate: false,
      artifacts: artifactsToRender,  // Use cleaned artifacts (no dashboard)
    });
  });

  const lastUserMessage = [...conversation.messages]
    .reverse()
    .find((message) => message.role === "user" && message.text);
  if (lastUserMessage) {
    updatePromptSuggestionsFromPrompt(lastUserMessage.text);
  } else {
    activePromptSuggestions = [...DEFAULT_PROMPT_SUGGESTIONS];
    renderPromptChips();
  }

  scrollChatToBottom({ smooth: false, force: true });
  renderConversationList();
  chatInput.focus();
}

function startNewConversation({ focusInput = true } = {}) {
  activeConversation = null;
  saveActiveConversationId(null);
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
  activePromptSuggestions = [...DEFAULT_PROMPT_SUGGESTIONS];
  renderPromptChips();
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
  if (utilityPanel.classList) {
    const expandKeys = new Set(["kpi-library", "company-universe"]);
    utilityPanel.classList.toggle("utility-panel--expanded", expandKeys.has(key));
  }
  if (topBar) {
    topBar.classList.remove("top-bar--center");
    topBar.classList.add("top-bar--left");
  }
  utilityTitle.textContent = section.title;
  utilityContent.innerHTML = section.html;
  if (utilityContent.classList) {
    const stretchKeys = new Set(["kpi-library", "company-universe"]);
    utilityContent.classList.toggle("utility-content--stretch", stretchKeys.has(key));
  }
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
  utilityPanel.classList.remove("utility-panel--expanded");
  utilityTitle.textContent = "";
  utilityContent.innerHTML = "";
  utilityContent.classList.remove("utility-content--stretch");
  currentUtilityKey = null;
  if (topBar) {
    topBar.classList.remove("top-bar--left");
    topBar.classList.add("top-bar--center");
  }
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
  // Update legacy elements (if they exist)
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

  // Update status cards in hero box (using querySelector to find elements in hero box)
  const heroBox = document.querySelector(".company-universe__hero");
  if (heroBox) {
    const universeEl = heroBox.querySelector("[data-role='company-universe-meta-universe']");
    if (universeEl) {
      universeEl.textContent = `${totalCount.toLocaleString()} companies tracked`;
    }

    const sectorsEl = heroBox.querySelector("[data-role='company-universe-meta-sectors']");
    if (sectorsEl) {
      sectorsEl.textContent = `${sectorsCount.toLocaleString()} sectors in view`;
    }

    const latestEl = heroBox.querySelector("[data-role='company-universe-meta-latest']");
    if (latestEl) {
      if (latestRecord && latestRecord.latest_filing) {
        const dateStr = formatDateHuman(latestRecord.latest_filing);
        const ticker = latestRecord.ticker || "";
        latestEl.textContent = ticker ? `${dateStr} | ${ticker}` : dateStr;
      } else {
        latestEl.textContent = "—";
      }
    }

    const coverageEl = heroBox.querySelector("[data-role='company-universe-meta-coverage']");
    if (coverageEl && coverage) {
      const { complete = 0, partial = 0, missing = 0 } = coverage;
      const total = complete + partial + missing;
      if (total > 0) {
        const completePercent = Math.round((complete / total) * 100);
        const partialCount = partial > 0 ? `, ${partial} partial` : "";
        const missingCount = missing > 0 ? `, ${missing} missing` : "";
        coverageEl.textContent = `${completePercent}% complete (${complete}${partialCount}${missingCount})`;
      } else {
        coverageEl.textContent = "—";
      }
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
    if (companyUniverseSkeleton) {
      companyUniverseSkeleton.classList.add("hidden");
    }
    if (companyUniverseEmpty) {
      companyUniverseEmpty.classList.remove("hidden");
    }
    return;
  }
  companyUniverseTable.classList.remove("hidden");
  if (companyUniverseSkeleton) {
    companyUniverseSkeleton.classList.add("hidden");
  }
  if (companyUniverseEmpty) {
    companyUniverseEmpty.classList.add("hidden");
  }

  const sorted = [...data].sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0));
  sorted.forEach((company) => {
    const row = document.createElement("tr");
    row.className = "company-universe__row";

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
    marketCapCell.className = "market-cap-cell";
    marketCapCell.textContent = formatMarketCap(company.market_cap, company.market_cap_display);
    if (Number.isFinite(company.market_cap)) {
      try {
        marketCapCell.title = `$${Number(company.market_cap).toLocaleString("en-US")}`;
      } catch (error) {
        marketCapCell.title = String(company.market_cap);
      }
      marketCapCell.setAttribute("aria-label", `${marketCapCell.textContent} (mega cap benchmark: $1T)`);
      if (Number(company.market_cap) >= 1e12) {
        marketCapCell.classList.add("market-cap--mega");
      }
    } else if (company.market_cap_display) {
      marketCapCell.title = company.market_cap_display;
      marketCapCell.setAttribute("aria-label", `${marketCapCell.textContent}`);
    }

    const filingCell = document.createElement("td");
    filingCell.className = "filing-date-cell";
    const filingLabel = formatDateHuman(company.latest_filing);
    filingCell.textContent = filingLabel;
    if (company.latest_filing) {
      const parsed = new Date(company.latest_filing);
      if (!Number.isNaN(parsed.getTime())) {
        filingCell.title = parsed.toLocaleString();
        filingCell.setAttribute("aria-label", `${filingLabel} (parsed ${filingCell.title})`);
        const daysSince = (Date.now() - parsed.getTime()) / (1000 * 60 * 60 * 24);
        if (daysSince > 180) {
          filingCell.classList.add("filing-date--stale");
          filingCell.setAttribute("aria-label", `${filingLabel} – filing older than 180 days`);
        }
      }
    } else {
      filingCell.title = "No filing on record";
      filingCell.setAttribute("aria-label", "No filing on record");
    }

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
    if (companyUniverseSkeleton) {
      companyUniverseSkeleton.classList.remove("hidden");
    }
    if (companyUniverseTable) {
      companyUniverseTable.classList.add("hidden");
    }
    if (companyUniverseEmpty) {
      companyUniverseEmpty.classList.add("hidden");
    }
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

function cloneForCache(value) {
  if (value === null || value === undefined) {
    return null;
  }
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (error) {
    return value;
  }
}

function cleanupPromptCache() {
  const now = Date.now();
  for (const [key, entry] of promptCache.entries()) {
    if (!entry || typeof entry.timestamp !== "number") {
      promptCache.delete(key);
      continue;
    }
    if (now - entry.timestamp > PROMPT_CACHE_TTL_MS) {
      promptCache.delete(key);
    }
  }
}

function canonicalisePrompt(input) {
  if (!input) {
    return "";
  }
  return input.trim().replace(/\s+/g, " ").toLowerCase();
}

function getCachedPrompt(key) {
  if (!key) {
    return null;
  }
  cleanupPromptCache();
  const entry = promptCache.get(key);
  if (!entry) {
    return null;
  }
  return {
    reply: entry.reply,
    artifacts: cloneForCache(entry.artifacts),
  };
}

function setCachedPrompt(key, reply, artifacts) {
  if (!key || !reply) {
    return;
  }
  cleanupPromptCache();
  promptCache.set(key, {
    reply,
    artifacts: cloneForCache(artifacts),
    timestamp: Date.now(),
  });
  while (promptCache.size > PROMPT_CACHE_LIMIT) {
    const oldest = promptCache.keys().next().value;
    if (oldest === undefined) {
      break;
    }
    promptCache.delete(oldest);
  }
}

async function sendPrompt(prompt, requestId) {
  const payload = { prompt };
  if (requestId) {
    payload.request_id = requestId;
  }
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

// File upload handling - initialize after DOM is ready
function initializeFileUpload() {
  console.log("[Upload] Initializing file upload handler...");

  const { input: chatFileUpload, button: chatFileUploadBtn } = getChatUploadElements();

  if (!chatFileUpload) {
    console.error("[Upload] File upload input not found in DOM");
    return;
  }

  if (!chatFileUploadBtn) {
    console.error("[Upload] File upload button not found in DOM");
    return;
  }

  bindChatUploadHandlers("initialize");

  console.log("[Upload] File upload elements ready", {
    inputPresent: true,
    buttonPresent: true,
    inputVisible: chatFileUpload.offsetParent !== null,
    buttonVisible: chatFileUploadBtn.offsetParent !== null,
  });

  if (!chatFileUpload.dataset.chatUploadChangeBound) {
    chatFileUpload.addEventListener("change", onChatFileSelected);
    chatFileUpload.dataset.chatUploadChangeBound = "true";
    chatFileUpload.addEventListener("click", (event) => {
      console.log("[Upload] File input clicked directly", {
        target: event.target,
        files: event.target.files?.length || 0,
      });
    });
  }
}

async function onChatFileSelected(event) {
  console.log("[Upload] File selection changed", {
    fileCount: event.target.files?.length || 0,
    fileName: event.target.files?.[0]?.name || "none",
  });

  const file = event.target.files[0];
  if (!file) {
    console.warn("[Upload] No file selected");
    return;
  }

  console.log("[Upload] Starting file upload", {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type || "unknown",
  });

  const conversation = ensureActiveConversation();
  let remoteConversationId = conversation?.remoteId;
  if (!remoteConversationId) {
    const generatedId =
      (typeof crypto !== "undefined" && crypto.randomUUID && crypto.randomUUID()) ||
      `conv-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    conversation.remoteId = generatedId;
    remoteConversationId = generatedId;
    promoteConversation(conversation);
    saveConversations();
  }

  const uploadingMsgWrapper = appendMessage("user", `📎 Uploading ${file.name}...`, { forceScroll: true });
  setSending(true);

  try {
    console.log("[Upload] Creating FormData and preparing upload...");
    const formData = new FormData();
    formData.append("file", file);

    if (remoteConversationId) {
      formData.append("conversation_id", remoteConversationId);
    }

    const response = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: "Upload failed" }));
      throw new Error(error.message || "Upload failed");
    }

    const result = await response.json();
    console.log("[Upload] Upload response received", { success: result.success, result });

    if (result.success) {
      console.log("[Upload] Upload successful!");
      if (result.conversation_id && result.conversation_id !== remoteConversationId) {
        remoteConversationId = result.conversation_id;
        conversation.remoteId = result.conversation_id;
        promoteConversation(conversation);
        saveConversations();
      }
      if (uploadingMsgWrapper) {
        const bodyEl = uploadingMsgWrapper.querySelector(".message-body");
        if (bodyEl) {
          bodyEl.textContent = `📎 Uploaded ${file.name} successfully`;
          uploadingMsgWrapper.classList.add("upload-success");
        }
      }

      const assistantMsg = result.message
        ? result.message
        : `✅ File "${file.name}" uploaded successfully. The document has been processed and is now available for analysis. You can ask questions about it or use it as a framework/template.`;
      recordMessage("assistant", assistantMsg, {
        upload: { documentId: result.document_id, filename: file.name },
      });
      appendMessage("assistant", assistantMsg, { forceScroll: true });

      if (Array.isArray(result.warnings) && result.warnings.length) {
        const warningText = `⚠️ Upload warnings for "${file.name}": ${result.warnings.join(" ")}`;
        recordMessage("system", warningText);
        appendMessage("system", warningText, { forceScroll: true });
      }
    } else {
      console.error("[Upload] Upload failed:", result.errors);
      throw new Error(result.errors?.[0] || "Upload failed");
    }
  } catch (error) {
    console.error("[Upload] File upload error:", error);
    if (uploadingMsgWrapper) {
      const bodyEl = uploadingMsgWrapper.querySelector(".message-body");
      if (bodyEl) {
        bodyEl.textContent = `❌ Upload failed: ${error.message}`;
        uploadingMsgWrapper.classList.add("upload-error");
      }
    }

    const errorMsg = `❌ Failed to upload ${file.name}: ${error.message}`;
    recordMessage("system", errorMsg);
    appendMessage("system", errorMsg, { forceScroll: true });
  } finally {
    setSending(false);
    event.target.value = "";
  }
}

// Initialize file upload - try multiple times with aggressive retry
let uploadInitAttempts = 0;
const MAX_UPLOAD_INIT_ATTEMPTS = 50;

function tryInitializeFileUpload() {
  uploadInitAttempts++;
  console.log(`[Upload] Attempt ${uploadInitAttempts} to initialize file upload...`);
  
  const chatFileUpload = document.getElementById("chat-file-upload");
  const chatFileUploadBtn = document.getElementById("chat-file-upload-btn");
  
  console.log(`[Upload] Element check:`, {
    input: !!chatFileUpload,
    button: !!chatFileUploadBtn,
    inputElement: chatFileUpload,
    buttonElement: chatFileUploadBtn
  });
  
  if (chatFileUpload && chatFileUploadBtn) {
    console.log("[Upload] ✅ Elements found, initializing...");
    initializeFileUpload();
    return true;
  } else {
    if (uploadInitAttempts < MAX_UPLOAD_INIT_ATTEMPTS) {
      console.log(`[Upload] ⏳ Elements not found yet, retrying in 100ms... (attempt ${uploadInitAttempts}/${MAX_UPLOAD_INIT_ATTEMPTS})`);
      setTimeout(tryInitializeFileUpload, 100);
    } else {
      console.error("[Upload] ❌ Failed to find elements after", MAX_UPLOAD_INIT_ATTEMPTS, "attempts");
      console.error("[Upload] Input element:", chatFileUpload);
      console.error("[Upload] Button element:", chatFileUploadBtn);
    }
    return false;
  }
}

// Try immediately
console.log("[Upload] Starting file upload initialization...");
console.log("[Upload] Document ready state:", document.readyState);

if (document.readyState === 'loading') {
  console.log("[Upload] Document is loading, waiting for DOMContentLoaded...");
  document.addEventListener('DOMContentLoaded', () => {
    console.log("[Upload] DOMContentLoaded fired, initializing...");
    tryInitializeFileUpload();
  });
} else {
  console.log("[Upload] Document already ready, initializing immediately...");
  tryInitializeFileUpload();
}

// Also try on window load as fallback
window.addEventListener('load', () => {
  console.log("[Upload] Window load event fired, checking elements...");
  const chatFileUpload = document.getElementById("chat-file-upload");
  const chatFileUploadBtn = document.getElementById("chat-file-upload-btn");
  console.log("[Upload] Window load check:", {
    input: !!chatFileUpload,
    button: !!chatFileUploadBtn
  });
  if (chatFileUpload && chatFileUploadBtn) {
    console.log("[Upload] ✅ Re-initializing on window load...");
    initializeFileUpload();
  } else {
    console.error("[Upload] ❌ Elements still not found on window load");
  }
});

// Final fallback - try after a longer delay
setTimeout(() => {
  console.log("[Upload] Final fallback check after 2 seconds...");
  const chatFileUpload = document.getElementById("chat-file-upload");
  const chatFileUploadBtn = document.getElementById("chat-file-upload-btn");
  if (chatFileUpload && chatFileUploadBtn) {
    console.log("[Upload] ✅ Final fallback: initializing...");
    initializeFileUpload();
  } else {
    console.error("[Upload] ❌ Final fallback: elements still not found");
  }
}, 2000);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSending) {
    return;
  }

  const prompt = chatInput.value.trim();
  if (!prompt) {
    return;
  }
  const canonicalPrompt = canonicalisePrompt(prompt);

  recordMessage("user", prompt);
  updatePromptSuggestionsFromPrompt(prompt);
  appendMessage("user", prompt, { forceScroll: true });
  chatInput.value = "";

  if (prompt.toLowerCase() === "help") {
    recordMessage("assistant", HELP_TEXT);
    appendMessage("assistant", HELP_TEXT, { forceScroll: true, animate: false });
    chatInput.focus();
    return;
  }

  setSending(true);
  const requestId = generateRequestId();
  let pendingMessage = showAssistantTyping();
  const cachedEntry = getCachedPrompt(canonicalPrompt);
  if (cachedEntry && cachedEntry.reply) {
    const resolved = resolvePendingMessage(pendingMessage, "assistant", cachedEntry.reply, {
      forceScroll: true,
      artifacts: cachedEntry.artifacts,
      stream: false,
    });
    if (resolved) {
      pendingMessage = resolved;
      pendingMessage.dataset.cached = "true";
    }
  }

  if (pendingMessage && pendingMessage.classList.contains("typing")) {
    startProgressTracking(requestId, pendingMessage);
  }

  try {
    const response = await sendPrompt(prompt, requestId);
    const cleanReply = typeof response?.reply === "string" ? response.reply.trim() : "";
    const messageText = cleanReply || "(no content)";
    const artifacts = normaliseArtifacts(response);
    pushProgressEvents(requestId, response?.progress_events || []);
    recordMessage("assistant", messageText, artifacts);
    const shouldStream = !pendingMessage?.dataset?.cached && shouldStreamText(messageText);
    const resolved = resolvePendingMessage(pendingMessage, "assistant", messageText, {
      forceScroll: true,
      artifacts,
      stream: shouldStream,
    });
    if (resolved) {
      pendingMessage = resolved;
      if (pendingMessage.dataset?.cached) {
        delete pendingMessage.dataset.cached;
      }
    }
    setCachedPrompt(canonicalPrompt, messageText, artifacts);
  } catch (error) {
    const fallback = error && error.message ? error.message : "Something went wrong. Please try again.";
    recordMessage("system", fallback);
    resolvePendingMessage(pendingMessage, "system", fallback, { forceScroll: true });
  } finally {
    await stopProgressTracking(requestId, { flush: true });
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

// Disable Send when empty
if (chatInput && sendButton) {
  const updateSendDisabled = () => {
    const hasText = !!chatInput.value && chatInput.value.trim().length > 0;
    sendButton.disabled = !hasText;
  };
  chatInput.addEventListener("input", updateSendDisabled);
  chatInput.addEventListener("input", autoResizeTextarea);
  window.addEventListener("load", autoResizeTextarea);
  updateSendDisabled();
}

// Near-bottom detection and Jump-to-latest button
if (chatLog) {
  chatLog.addEventListener("scroll", () => {
    if (!scrollBtn) {
      return;
    }
    if (!isNearBottom(120)) {
      scrollBtn.classList.add("show");
      scrollBtn.setAttribute("aria-hidden", "false");
      updateScrollBtnOffset();
    } else {
      hasNewSinceScroll = false;
      scrollBtn.classList.remove("show");
      scrollBtn.setAttribute("aria-hidden", "true");
      updateScrollBtnOffset();
    }
  });
}

if (scrollBtn) {
  scrollBtn.addEventListener("click", () => {
    scrollChatToBottom({ smooth: true });
    hasNewSinceScroll = false;
    scrollBtn.classList.remove("show");
    scrollBtn.setAttribute("aria-hidden", "true");
    updateScrollBtnOffset();
  });
}

// Keep Jump button offset in sync with composer height
function observeComposerResize() {
  if (!chatFormContainer) {
    return;
  }
  updateScrollBtnOffset();
  const ro = new (window.ResizeObserver || window.MutationObserver)(() => updateScrollBtnOffset());
  if (ro.observe) {
    ro.observe(chatFormContainer);
  } else if (ro) {
    // Fallback for MutationObserver: listen to textarea input
    const ta = document.getElementById("chat-input");
    if (ta) {
      ta.addEventListener("input", updateScrollBtnOffset);
    }
  }
  window.addEventListener("resize", updateScrollBtnOffset);
}

observeComposerResize();

// Ensure button lives inside messages container for correct z-index/positioning
if (scrollBtn && chatLog && scrollBtn.parentElement !== chatLog) {
  chatLog.appendChild(scrollBtn);
}

// Initial visibility on load
refreshScrollButton();
function renderPromptChips() {
  const suggestions =
    Array.isArray(activePromptSuggestions) && activePromptSuggestions.length
      ? activePromptSuggestions
      : DEFAULT_PROMPT_SUGGESTIONS;
  if (promptSuggestionsContainer) {
    promptSuggestionsContainer.innerHTML = "";
    promptSuggestionsContainer.setAttribute("role", "list");
    suggestions.forEach((suggestion, index) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "prompt-chip";
      chip.dataset.prompt = suggestion;
      chip.setAttribute("role", "listitem");
      chip.setAttribute("aria-label", `Suggested prompt ${index + 1}: ${suggestion}`);
      chip.textContent = suggestion;
      chip.addEventListener("click", () => {
        if (!chatInput) {
          return;
        }
        chatInput.value = suggestion;
        chatInput.focus();
      });
      promptSuggestionsContainer.append(chip);
    });
    return;
  }
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (!prompt || !chatInput) {
        return;
      }
      chatInput.value = prompt;
      chatInput.focus();
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

if (conversationExportButtons && conversationExportButtons.length) {
  conversationExportButtons.forEach((button) => {
    button.addEventListener("click", () => exportConversation(button.dataset.export));
  });
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

renderPromptChips();

if (auditDrawer) {
  auditDrawer.addEventListener("click", (event) => {
    if (!(event.target instanceof HTMLElement)) {
      return;
    }
    if (event.target.dataset.action === "close-audit") {
      event.preventDefault();
      closeAuditDrawer();
    }
  });
}
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

// Restore active conversation from localStorage, or load the first conversation
const savedActiveConversationId = getActiveConversationId();
if (savedActiveConversationId) {
  const savedConversation = conversations.find((entry) => entry.id === savedActiveConversationId);
  if (savedConversation) {
    loadConversation(savedActiveConversationId);
  } else if (conversations.length) {
    // If saved conversation not found, load the first conversation
    loadConversation(conversations[0].id);
  } else {
    startNewConversation({ focusInput: false });
  }
} else if (conversations.length) {
  loadConversation(conversations[0].id);
} else {
  startNewConversation({ focusInput: false });
}

// Global variables for status elements (will be set when DOM is ready)
// Note: These may already be declared elsewhere in the file, so we use window object
if (typeof window.statusMessage === 'undefined') {
  window.statusMessage = null;
}
if (typeof window.statusDot === 'undefined') {
  window.statusDot = null;
}

async function checkHealth() {
  try {
    // Get elements - try multiple times if needed
    // Use window object to avoid conflicts with existing declarations
    const statusMsgEl = window.statusMessage || document.getElementById("status-message");
    const statusDotEl = window.statusDot || document.getElementById("api-status");
    
    // Store references for later use
    if (statusMsgEl && !window.statusMessage) window.statusMessage = statusMsgEl;
    if (statusDotEl && !window.statusDot) window.statusDot = statusDotEl;
    
    // Build URL - use empty string if API_BASE is not set (relative URL)
    const baseUrl = API_BASE || "";
    const url = `${baseUrl}/health?ts=${Date.now()}`;
    
    console.log("Checking API health at:", url);
    
    // Try fetch with timeout - use no-cors mode if CORS fails
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
    let res;
    try {
      res = await fetch(url, { 
        cache: "no-store",
        method: "GET",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json"
        },
        mode: "cors",
        credentials: "omit",
        signal: controller.signal
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      if (fetchError.name === 'AbortError') {
        throw new Error("API health check timed out after 5 seconds");
      }
      // Re-throw the original error - CORS should work with our server
      throw fetchError;
    }
    
    if (!res || !res.ok) {
      throw new Error(`HTTP ${res ? res.status : 'unknown'}: ${res ? res.statusText : 'No response'}`);
    }
    
    let data;
    try {
      data = await res.json();
    } catch (jsonError) {
      // If JSON parsing fails, check if response is ok
      const text = await res.text();
      console.warn("Failed to parse JSON, got:", text);
      throw new Error(`Invalid JSON response from API: ${text.substring(0, 100)}`);
    }
    console.log("API health check successful:", data);
    
    // Update UI elements if they exist
    if (statusDotEl) {
      statusDotEl.classList.remove("offline");
      statusDotEl.classList.add("online");
    }
    if (statusMsgEl) {
      statusMsgEl.textContent = "API online";
    }
    
    return true;
  } catch (error) {
    console.error("Health check failed:", error);
    console.error("Error details:", {
      name: error.name,
      message: error.message,
      stack: error.stack,
      url: `${API_BASE || ""}/health`
    });
    
    const statusMsgEl = window.statusMessage || document.getElementById("status-message");
    const statusDotEl = window.statusDot || document.getElementById("api-status");
    
    // Update UI elements if they exist
    if (statusDotEl) {
      statusDotEl.classList.remove("online");
      statusDotEl.classList.add("offline");
    }
    if (statusMsgEl) {
      const errorMsg = error.message || "Cannot reach API";
      statusMsgEl.textContent = errorMsg.length > 30 ? "Cannot reach API" : errorMsg;
    }
    
    return false;
  }
}

// Wait for DOM to be ready before checking health
function startHealthCheck() {
  console.log("Starting health check...");
  // Check immediately
  checkHealth().catch(err => {
    console.error("Initial health check error:", err);
  });
  // Then check every 30 seconds
  setInterval(() => {
    checkHealth().catch(err => {
      console.error("Periodic health check error:", err);
    });
  }, 30000);
}
// Start health check - simplified approach
(function initializeHealthCheck() {
  console.log("App.js health check initializing...");
  
  // Simple function to run health check
  function runCheck() {
    console.log("Running health check from app.js...");
    checkHealth().catch(err => {
      console.error("App.js health check error:", err);
    });
  }
  
  // Run immediately if DOM is ready, otherwise wait
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runCheck);
    window.addEventListener('load', runCheck);
  } else {
    runCheck();
  }
  
  // Also set up periodic checks
  setTimeout(function() {
    setInterval(runCheck, 30000); // Every 30 seconds
  }, 2000);
})();

// Also expose checkHealth globally for manual testing
window.checkHealth = checkHealth;

loadHelpContentOverrides();

if (chatInput) {
  chatInput.focus();
}

function updateProgressTrackerWithEvent(tracker, event) {
  if (!tracker || !event) {
    return;
  }
  const stage = event.stage || "";
  const statusHint = stepStatusFromStage(stage);
  const timestamp = event.timestamp ? Date.parse(event.timestamp) : Number.NaN;
  if (Number.isFinite(timestamp) && !Number.isFinite(tracker.startedAt)) {
    tracker.startedAt = timestamp;
  }
  const elapsedMs =
    Number.isFinite(timestamp) && Number.isFinite(tracker.startedAt)
      ? Math.max(0, timestamp - tracker.startedAt)
      : null;

  const ensureMessages = (step) => {
    if (!step) {
      return [];
    }
    if (!Array.isArray(step.messages)) {
      step.messages = [];
    }
    return step.messages;
  };

  const pushMessage = (step, text) => {
    if (!step) {
      return;
    }
    const messages = ensureMessages(step);
    const messageText = text || event.detail || event.label || stage.replace(/_/g, " ").trim();
    messages.push({
      text: messageText,
      stage,
      elapsedMs,
      timestamp: event.timestamp || null,
    });
    if (messages.length > 6) {
      messages.splice(0, messages.length - 6);
    }
    if (text) {
      step.detail = text;
    }
  };

  if (stage === "error") {
    tracker.container.classList.remove("pending");
    tracker.container.classList.remove("complete");
    tracker.container.classList.add("error");
    const activeStep = tracker.steps.find((step) => step.status === "active") || tracker.steps[tracker.steps.length - 1];
    pushMessage(activeStep, event.detail || "An unexpected error occurred");
    if (tracker.title) {
      tracker.title.textContent = "Something went wrong";
    }
    return;
  }

  if (stage === "complete") {
    tracker.steps.forEach((step) => {
      step.status = "complete";
      if (!step.detail && event.detail) {
        step.detail = event.detail;
      }
    });
    tracker.container.classList.remove("pending");
    tracker.container.classList.remove("error");
    tracker.container.classList.add("complete");
    const finalStep = tracker.steps[tracker.steps.length - 1];
    pushMessage(finalStep, event.detail || "Analysis ready");
    if (tracker.title) {
      tracker.title.textContent = "Analysis ready";
    }
    return;
  }

  const matchedKey = findStepKeyForStage(stage);
  if (!matchedKey) {
    return;
  }
  const index = tracker.steps.findIndex((step) => step.key === matchedKey);
  if (index === -1) {
    return;
  }

  tracker.steps.forEach((step, idx) => {
    if (idx < index && step.status !== "complete") {
      step.status = "complete";
    }
  });

  const currentStep = tracker.steps[index];
  currentStep.status = statusHint;
  if (event.detail) {
    currentStep.detail = event.detail;
  }
  pushMessage(currentStep, event.detail);

  tracker.steps.forEach((step, idx) => {
    if (idx > index && step.status !== "complete") {
      step.status = "pending";
    }
  });

  tracker.container.classList.remove("error");
  if (statusHint === "complete" && index === tracker.steps.length - 1) {
    tracker.container.classList.add("complete");
  } else {
    tracker.container.classList.remove("complete");
  }

  if (!tracker.steps.some((step) => step.status === "active")) {
    const nextPending = tracker.steps.find((step) => step.status === "pending");
    if (nextPending) {
      nextPending.status = "active";
    }
  }

  const activeStep = tracker.steps.find((step) => step.status === "active");
  if (tracker.title) {
    tracker.title.textContent = activeStep?.label || "Analysis ready";
  }
}

function renderProgressTracker(tracker) {
  if (!tracker?.list) {
    return;
  }
  tracker.list.textContent = "";
  tracker.steps.forEach((step) => {
    const item = document.createElement("li");
    item.className = `progress-step ${step.status}`;
    item.dataset.key = step.key;

    const indicator = document.createElement("span");
    indicator.className = "progress-indicator";
    item.append(indicator);

    const copy = document.createElement("div");
    copy.className = "progress-copy";
    const label = document.createElement("div");
    label.className = "progress-label";
    label.textContent = step.label;
    copy.append(label);

    const messages = Array.isArray(step.messages) ? step.messages : [];
    if (messages.length) {
      const logList = document.createElement("ul");
      logList.className = "progress-log";
      messages.slice(-3).forEach((log) => {
        const logItem = document.createElement("li");
        const textSpan = document.createElement("span");
        textSpan.textContent = log.text;
        logItem.append(textSpan);
        if (log.elapsedMs != null) {
          const timeSpan = document.createElement("span");
          timeSpan.className = "progress-timestamp";
          const formatted = formatElapsed(log.elapsedMs);
          if (formatted) {
            timeSpan.textContent = formatted;
            logItem.append(timeSpan);
          }
        }
        logList.append(logItem);
      });
      copy.append(logList);
    } else if (step.detail) {
      const detail = document.createElement("div");
      detail.className = "progress-detail";
      detail.textContent = step.detail;
      copy.append(detail);
    }
    item.append(copy);
    tracker.list.append(item);
  });
}

function renderProgressSummary(tracker) {
  if (!Array.isArray(tracker?.steps) || !tracker.steps.length) {
    return;
  }
  if (!tracker?.wrapper) {
    return;
  }
  const body = tracker.wrapper.querySelector(".message-body");
  if (!body) {
    return;
  }
  let summary = body.querySelector(".processing-timeline");
  if (summary) {
    summary.remove();
  }
  summary = document.createElement("div");
  summary.className = "processing-timeline";
  const heading = document.createElement("h4");
  heading.textContent = "Processing timeline";
  summary.append(heading);
  const list = document.createElement("ol");
  list.className = "processing-timeline-list";
  tracker.steps.forEach((step) => {
    const item = document.createElement("li");
    item.className = `timeline-step ${step.status}`;
    const status = document.createElement("span");
    status.className = "timeline-indicator";
    item.append(status);
    const content = document.createElement("div");
    content.className = "timeline-copy";
    const label = document.createElement("div");
    label.className = "timeline-label";
    const lastLog = Array.isArray(step.messages) && step.messages.length ? step.messages[step.messages.length - 1] : null;
    const duration = lastLog?.elapsedMs != null ? formatElapsed(lastLog.elapsedMs) : null;
    label.textContent = duration ? `${step.label} (${duration})` : step.label;
    content.append(label);
    const messages = Array.isArray(step.messages) ? step.messages : [];
    if (messages.length) {
      const timelineList = document.createElement("ul");
      timelineList.className = "timeline-log";
      messages.forEach((log) => {
        const logItem = document.createElement("li");
        const textSpan = document.createElement("span");
        textSpan.textContent = log.text;
        logItem.append(textSpan);
        if (log.elapsedMs != null) {
          const timeSpan = document.createElement("span");
          timeSpan.className = "timeline-timestamp";
          const formatted = formatElapsed(log.elapsedMs);
          if (formatted) {
            timeSpan.textContent = formatted;
            logItem.append(timeSpan);
          }
        }
        timelineList.append(logItem);
      });
      content.append(timelineList);
    } else if (step.detail) {
      const detail = document.createElement("div");
      detail.className = "timeline-detail";
      detail.textContent = step.detail;
      content.append(detail);
    }
    item.append(content);
    list.append(item);
  });
  summary.append(list);
  body.prepend(summary);
}

function resolveStaticAsset(path) {
  if (!path) {
    return path;
  }
  if (path.startsWith("data:") || path.startsWith("blob:")) {
    return path;
  }
  if (/^(?:https?:)?\/\//i.test(path)) {
    return path;
  }
  if (path.startsWith("/")) {
    return path;
  }
  // Add cache-busting for critical scripts
  const cacheBust = path.includes("cfi_dashboard.js") ? "?v=20241027k" : "";
  return `/static/${path}${cacheBust}`;
}

function extractBodyMarkup(html) {
  if (!html) return "";
  const match = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  return match ? match[1] : html;
}

function stripInlineAssetTags(html, stem) {
  if (!stem) return html;
  const escapedStem = stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const cssPattern = new RegExp(`<link[^>]+${escapedStem}[^>]*>`, "gi");
  const jsPattern = new RegExp(`<script[^>]+${escapedStem}[^<]*<\/script>`, "gi");
  return html.replace(cssPattern, "").replace(jsPattern, "");
}

function prepareEmbeddedLayout(html, stem) {
  const bodyMarkup = extractBodyMarkup(html);
  return stripInlineAssetTags(bodyMarkup, stem);
}

async function ensureStylesheetOnce(id, href) {
  if (document.getElementById(id)) {
    return;
  }
  return new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = resolveStaticAsset(href);
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load stylesheet ${href}`));
    document.head.appendChild(link);
  });
}

const scriptLoadPromises = new Map();

async function ensureScriptOnce(id, src) {
  if (scriptLoadPromises.has(id)) {
    return scriptLoadPromises.get(id);
  }
  const existing = document.getElementById(id);
  if (existing) {
    if (existing.dataset.loaded === "true" || !existing.dataset.loading) {
      return Promise.resolve();
    }
    const existingPromise = new Promise((resolve, reject) => {
      const handleLoad = () => {
        existing.dataset.loaded = "true";
        resolve();
      };
      const handleError = () => {
        scriptLoadPromises.delete(id);
        reject(new Error(`Failed to load script ${src}`));
      };
      existing.addEventListener("load", handleLoad, { once: true });
      existing.addEventListener("error", handleError, { once: true });
    });
    scriptLoadPromises.set(id, existingPromise);
    return existingPromise;
  }
  const loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = id;
    script.src = resolveStaticAsset(src);
    script.async = true;
    script.dataset.loading = "true";
    script.onload = () => {
      script.dataset.loading = "false";
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => {
      scriptLoadPromises.delete(id);
      script.remove();
      reject(new Error(`Failed to load script ${src}`));
    };
    document.head.appendChild(script);
  });
  scriptLoadPromises.set(id, loadPromise);
  return loadPromise;
}

async function ensurePlotlyLoaded() {
  if (window.Plotly) {
    return;
  }
  await ensureScriptOnce("plotly-core", "https://cdn.plot.ly/plotly-2.32.0.min.js");
}

async function ensureCfiCompareRenderer() {
  if (window.CFIX && typeof window.CFIX.render === "function") {
    return;
  }
  const maxAttempts = 10;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    if (window.CFIX && typeof window.CFIX.render === "function") {
      return;
    }
  }
  throw new Error("CFI Compare renderer unavailable.");
}

function resolveDashboardHost() {
  return (
    document.getElementById("utility-content") ||
    document.querySelector(".standalone-content") ||
    document.querySelector(".chat-panel")
  );
}

async function fetchCfiDensePayload(options = {}) {
  if (options.payload) {
    return options.payload;
  }
  const params = new URLSearchParams();
  if (options.ticker) {
    params.set("ticker", options.ticker);
  }
  const url = `/api/dashboard/cfi-dense${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed (${response.status})`);
  }
  return response.json();
}

async function loadCfiDenseMarkup(host) {
  const response = await fetch(resolveStaticAsset("cfi_dense.html"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load CFI Dense layout.");
  }
  const html = await response.text();
  host.innerHTML = prepareEmbeddedLayout(html, "cfi_dense");
}

async function showCfiDenseDashboard(options = {}) {
  const { container, payload: suppliedPayload, ...fetchOptions } = options || {};
  let host = null;
  if (container instanceof HTMLElement) {
    host = container;
  } else if (typeof container === "string") {
    host = document.getElementById(container);
  }
  if (!host) {
    host = resolveDashboardHost();
  }
  if (!host) {
    throw new Error("Unable to resolve dashboard host container.");
  }
  host.innerHTML = '<div class="cfi-loading">Loading CFI dashboard...</div>';
  try {
    await loadCfiDenseMarkup(host);
    await ensureStylesheetOnce("cfi-dense-styles", "cfi_dense.css");
    await ensurePlotlyLoaded();
    await ensureScriptOnce("cfi-dense-script", "cfi_dense.js");
    const payload = suppliedPayload || (await fetchCfiDensePayload(fetchOptions));
    if (window.CFI_DENSE && typeof window.CFI_DENSE.render === "function") {
      window.CFI_DENSE.render(payload);
      window.__cfiDenseLastPayload = payload;
    } else {
      throw new Error("CFI Dense renderer unavailable.");
    }
  } catch (error) {
    console.error(error);
    host.innerHTML =
      '<div class="cfi-error">Unable to load CFI Dense dashboard. Check console for details.</div>';
    if (typeof showToast === "function") {
      showToast("Unable to load CFI Dense dashboard.", "error");
    }
  }
}

async function fetchCfiDashboardPayload(options = {}) {
  if (options.payload) {
    return options.payload;
  }
  const params = new URLSearchParams();
  if (options.ticker) {
    params.set("ticker", options.ticker);
  }
  const url = `/api/dashboard/cfi${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed (${response.status})`);
  }
  return response.json();
}

async function loadCfiDashboardMarkup(host) {
  const response = await fetch(resolveStaticAsset("cfi_dashboard.html"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load CFI dashboard layout.");
  }
  const html = await response.text();
  host.innerHTML = prepareEmbeddedLayout(html, "cfi_dashboard");
}

const DEMO_CFI_PAYLOAD = {
  meta: { company: "Amazon.com, Inc.", ticker: "AMZN", recommendation: "Buy", target_price: 2600, date: "2024-10-01" },
  overview: { Exchange: "NASDAQ", Sector: "Internet & Direct Marketing Retail", HQ: "Seattle, WA", "Upside %": 18.3 },
  key_stats: { Employees: 850000, Founded: 1994, CEO: "Andy Jassy", "Primary Industry": "E-commerce" },
  market_data: { "Shares O/S (M)": 5100, "Market Cap ($B)": 1750, "Net Debt ($B)": 17.4, "Enterprise Value ($B)": 808.7 },
  valuation_table: [
    { Label: "Share Price", Market: 1755, DCF: 2024, Comps: 2100 },
    { Label: "Enterprise Value ($B)", Market: 808.7, DCF: 891.7, Comps: 834.2 },
  ],
  key_financials: {
    columns: [2019, 2020, 2021, 2022, 2023],
    rows: [
      { label: "Revenue", values: [280522, 386064, 469822, 513983, 574800] },
      { label: "EBITDA (ex SBC)", values: [36931, 48020, 56523, 60820, 71500] },
      { label: "Net income", values: [11588, 21331, 33364, -270, 30500] },
      { label: "Net profit margin", values: [4.1, 5.5, 7.1, -0.1, 5.3], type: "percent" },
      { label: "Free cash flow", values: [25329, 29620, 36284, 42262, 65489] },
      { label: "EV/Revenue (×)", values: [3.2, 2.8, 2.3, 2.1, 1.9], type: "multiple" },
      { label: "EV/EBITDA (×)", values: [18.0, 15.2, 13.5, 12.3, 11.0], type: "multiple" },
    ],
  },
  kpi_summary: [
    { label: "Revenue CAGR", value: 0.17, type: "percent", period: "3Y CAGR", source: "SEC filings" },
    { label: "EPS CAGR", value: 0.21, type: "percent", period: "3Y CAGR", source: "SEC filings" },
    { label: "EBITDA Growth", value: 0.12, type: "percent", period: "YoY", source: "Finalyze model" },
    { label: "EBITDA margin", value: 0.178, type: "percent", period: "TTM", source: "Finalyze model" },
    { label: "Operating margin", value: 0.073, type: "percent", period: "TTM", source: "Finalyze model" },
    { label: "Net margin", value: 0.053, type: "percent", period: "FY2023", source: "SEC filings" },
    { label: "Profit margin", value: 0.058, type: "percent", period: "FY2023", source: "SEC filings" },
    { label: "Return on assets", value: 0.087, type: "percent", period: "FY2023", source: "Finalyze model" },
    { label: "Return on equity", value: 0.116, type: "percent", period: "FY2023", source: "Finalyze model" },
    { label: "Return on invested capital", value: 0.142, type: "percent", period: "FY2023", source: "Finalyze model" },
    { label: "Free cash flow margin", value: 0.114, type: "percent", period: "TTM", source: "Company filings" },
    { label: "Cash conversion", value: 1.18, type: "percent", period: "FY2023", source: "Finalyze model" },
    { label: "Debt to equity", value: 1.3, type: "multiple", period: "FY2023", source: "SEC filings" },
    { label: "P/E (ttm)", value: 112.0, type: "multiple", period: "TTM", source: "Market data" },
    { label: "EV/EBITDA (ttm)", value: 31.0, type: "multiple", period: "TTM", source: "Market data" },
    { label: "P/B ratio", value: 8.5, type: "multiple", period: "FY2023", source: "Market data" },
    { label: "PEG ratio", value: 1.6, type: "multiple", period: "FY2023", source: "Market data" },
    { label: "Dividend yield", value: 0.004, type: "percent", period: "TTM", source: "Market data" },
    { label: "Total shareholder return", value: 0.245, type: "percent", period: "1Y", source: "Market data" },
    { label: "Share buyback intensity", value: 0.018, type: "percent", period: "FY2023", source: "Company filings" },
  ],
  kpi_series: {
    revenue_cagr: { type: "percent", years: [2021, 2022, 2023], values: [0.15, 0.16, 0.17] },
    eps_cagr: { type: "percent", years: [2021, 2022, 2023], values: [0.19, 0.2, 0.21] },
    ebitda_growth: { type: "percent", years: [2021, 2022, 2023], values: [0.09, 0.11, 0.12] },
    ebitda_margin: { type: "percent", years: [2021, 2022, 2023], values: [0.172, 0.175, 0.178] },
    operating_margin: { type: "percent", years: [2021, 2022, 2023], values: [0.069, 0.071, 0.073] },
    net_margin: { type: "percent", years: [2021, 2022, 2023], values: [0.044, 0.048, 0.053] },
    profit_margin: { type: "percent", years: [2021, 2022, 2023], values: [0.048, 0.054, 0.058] },
    return_on_assets: { type: "percent", years: [2021, 2022, 2023], values: [0.072, 0.079, 0.087] },
    return_on_equity: { type: "percent", years: [2021, 2022, 2023], values: [0.102, 0.109, 0.116] },
    return_on_invested_capital: { type: "percent", years: [2021, 2022, 2023], values: [0.128, 0.135, 0.142] },
    free_cash_flow_margin: { type: "percent", years: [2021, 2022, 2023], values: [0.098, 0.106, 0.114] },
    cash_conversion: { type: "percent", years: [2021, 2022, 2023], values: [1.05, 1.12, 1.18] },
    debt_to_equity: { type: "multiple", years: [2021, 2022, 2023], values: [1.5, 1.4, 1.3] },
    pe_ratio: { type: "multiple", years: [2021, 2022, 2023], values: [78.0, 92.0, 112.0] },
    ev_ebitda: { type: "multiple", years: [2021, 2022, 2023], values: [36.0, 34.0, 31.0] },
    pb_ratio: { type: "multiple", years: [2021, 2022, 2023], values: [9.8, 9.1, 8.5] },
    peg_ratio: { type: "multiple", years: [2021, 2022, 2023], values: [1.9, 1.8, 1.6] },
    dividend_yield: { type: "percent", years: [2021, 2022, 2023], values: [0.003, 0.0035, 0.004] },
    tsr: { type: "percent", years: [2021, 2022, 2023], values: [0.18, 0.21, 0.245] },
    share_buyback_intensity: { type: "percent", years: [2021, 2022, 2023], values: [0.012, 0.015, 0.018] },
  },
  interactions: {
    kpis: {
      default_mode: "trend",
      drilldowns: [
        { id: "revenue_cagr", label: "Revenue CAGR", default_view: "trend", data_refs: { series: "kpi_series.revenue_cagr", summary_id: "revenue_cagr" } },
        { id: "eps_cagr", label: "EPS CAGR", default_view: "trend", data_refs: { series: "kpi_series.eps_cagr", summary_id: "eps_cagr" } },
        { id: "ebitda_growth", label: "EBITDA Growth", default_view: "trend", data_refs: { series: "kpi_series.ebitda_growth", summary_id: "ebitda_growth" } },
      ],
    },
    charts: { controls: { modes: ["absolute", "growth"], default: "absolute" } },
    sources: { enabled: true, types: ["filing", "market_data", "derived"] },
  },
  peer_config: {
    focus_ticker: "AMZN",
    default_peer_group: "benchmark",
    max_peers: 5,
    supports_custom: true,
    available_peer_groups: [
      { id: "benchmark", label: "S&P 500 Avg", tickers: [] },
      { id: "custom", label: "Custom selection", tickers: [] },
    ],
  },
  sources: [
    { label: "Revenue", period: "FY2023", source: "SEC 10-K 2023", value: 574800 },
    { label: "Net income", period: "FY2023", source: "SEC 10-K 2023", value: 30500 },
    { label: "Free cash flow", period: "FY2023", source: "Company filings", value: 65489 },
    { label: "Shares O/S (M)", period: "FY2023", source: "Market data snapshot", value: 5100 },
    { label: "Net margin", period: "FY2023", source: "Finalyze derived", value: 0.053 },
  ],
  charts: {
    revenue_ev: { Year: [2019, 2020, 2021, 2022, 2023], Revenue: [280522, 386064, 469822, 513983, 574800], EV_Rev: [3.2, 2.8, 2.3, 2.1, 1.9] },
    ebitda_ev: { Year: [2019, 2020, 2021, 2022, 2023], EBITDA: [36931, 48020, 56523, 60820, 71500], EV_EBITDA: [18.0, 15.2, 13.5, 12.3, 11.0] },
    forecast: { Year: [2013, 2015, 2017, 2019, 2021, 2023, 2025, 2027, 2029], Bull: [400, 600, 900, 1200, 1500, 2100, 2400, 2700, 3000], Base: [380, 520, 800, 1100, 1400, 1850, 2050, 2250, 2450], Bear: [360, 480, 700, 950, 1200, 1600, 1700, 1850, 2000] },
    valuation_bar: { Case: ["DCF - Consensus", "DCF - Bull", "DCF - Bear", "Comps", "52-Week Hi/Lo"], Value: [2921, 4136, 918, 2216, 1755] },
  },
  valuation_data: {
    current: 1755,
    notes: [
      "Football Field Chart",
      "DCF - Consensus Case",
      "DCF - Bull Case",
      "DCF - Bear Case",
      "Comps",
      "52-Week Hi/Lo",
    ],
  },
};

const DEMO_CFIX_PAYLOAD = {
  meta: {
    date: "2025-10-19",
    peerset: "Apple Inc. (AAPL) vs Microsoft Corp. (MSFT) vs Amazon.com, Inc. (AMZN) vs S&P 500 Avg",
    tickers: ["AAPL", "MSFT", "AMZN"],
    companies: { AAPL: "Apple Inc.", MSFT: "Microsoft Corp.", AMZN: "Amazon.com, Inc." },
    benchmark: "S&P 500 Avg",
  },
  cards: {
    AAPL: {
      Price: "$226.10",
      "Revenue (FY23 $B)": "383.3",
      "Net margin": "28.6%",
      ROE: "126.6%",
      "P/E (ttm)": "45.3×",
    },
    MSFT: {
      Price: "$420.50",
      "Revenue (FY23 $B)": "211.9",
      "Net margin": "35.3%",
      ROE: "47.2%",
      "P/E (ttm)": "43.7×",
    },
    AMZN: {
      Price: "$175.50",
      "Revenue (FY23 $B)": "574.8",
      "Net margin": "5.3%",
      ROE: "11.6%",
      "P/E (ttm)": "112.0×",
    },
    SP500: {
      "Revenue (Avg $B)": "18.3",
      "Net margin": "12.3%",
      ROE: "17.6%",
      "P/E (ttm)": "22.0×",
    },
  },
  table: {
    columns: ["Metric", "AAPL", "MSFT", "AMZN", "S&P 500 Avg"],
    rows: [
      { label: "Revenue (FY23 $B)", AAPL: 383.3, MSFT: 211.9, AMZN: 574.8, SPX: 18.3, type: "moneyB" },
      { label: "EBITDA margin", AAPL: 31.6, MSFT: 41.8, AMZN: 17.6, SPX: 22.0, type: "pct" },
      { label: "Net margin", AAPL: 28.6, MSFT: 41.6, AMZN: 12.3, SPX: 12.3, type: "pct" },
      { label: "ROE", AAPL: 126.6, MSFT: 42.7, AMZN: 4.8, SPX: 17.6, type: "pct" },
      { label: "P/E (ttm)", AAPL: 45.3, MSFT: 43.7, AMZN: 112.0, SPX: 22.0, type: "x" },
      { label: "EV/EBITDA (ttm)", AAPL: 37.0, MSFT: 43.0, AMZN: 56.0, SPX: 11.5, type: "x" },
      { label: "Debt/Equity", AAPL: 5.0, MSFT: 1.0, AMZN: 3.0, SPX: 1.3, type: "x" },
    ],
  },
  football: [
    { ticker: "AAPL", ranges: [{ name: "DCF", lo: 135, hi: 210 }, { name: "Comps", lo: 160, hi: 220 }, { name: "Market", lo: 226, hi: 226 }] },
    { ticker: "MSFT", ranges: [{ name: "DCF", lo: 350, hi: 480 }, { name: "Comps", lo: 380, hi: 460 }, { name: "Market", lo: 420, hi: 420 }] },
    { ticker: "AMZN", ranges: [{ name: "DCF", lo: 160, hi: 240 }, { name: "Comps", lo: 170, hi: 230 }, { name: "Market", lo: 176, hi: 176 }] },
  ],
  series: {
    years: [2019, 2020, 2021, 2022, 2023],
    revenue: { AAPL: [260, 274, 366, 394, 383], MSFT: [126, 143, 168, 211, 212], AMZN: [281, 386, 470, 514, 575] },
    ebitda: { AAPL: [31, 35, 43, 47, 46], MSFT: [57, 73, 95, 112, 118], AMZN: [37, 48, 56, 61, 72] },
  },
  scatter: [
    { ticker: "AAPL", x: 28.6, y: 126.6, size: 383.3 },
    { ticker: "MSFT", x: 41.6, y: 47.2, size: 211.9 },
    { ticker: "AMZN", x: 12.3, y: 11.6, size: 574.8 },
    { ticker: "S&P Avg", x: 12.3, y: 17.6, size: 18.3 },
  ],
  valSummary: {
    case: ["DCF-Bull", "DCF-Base", "DCF-Bear", "Comps", "Market"],
    AAPL: [250, 210, 180, 225, 226],
    MSFT: [520, 460, 400, 480, 420],
    AMZN: [240, 200, 160, 210, 176],
  },
};



async function showCfiDashboard(options = {}) {
  const { container, payload: suppliedPayload, isMultiTicker, ...fetchOptions } = options || {};
  let host = null;
  if (container instanceof HTMLElement) {
    host = container;
  } else if (typeof container === "string") {
    host = document.getElementById(container);
  }
  if (!host) {
    host = resolveDashboardHost();
  }
  if (!host) {
    throw new Error("Unable to resolve dashboard host container.");
  }
  
  // Mark host as multi-ticker if applicable
  if (isMultiTicker) {
    host.dataset.multiTicker = "true";
  }
  // Only show loading message if we don't already have a payload (i.e., need to fetch)
  if (!suppliedPayload) {
    host.innerHTML = '<div class="cfi-loading">Loading CFI dashboard...</div>';
  }
  try {
    await loadCfiDashboardMarkup(host);
    await ensureStylesheetOnce("cfi-dashboard-styles", "cfi_dashboard.css");
    await ensurePlotlyLoaded();
    await ensureScriptOnce("cfi-dashboard-script", "cfi_dashboard.js");
  } catch (error) {
    console.error(error);
    host.innerHTML =
      '<div class="cfi-error">Unable to load CFI dashboard layout. Check console for details.</div>';
    if (typeof showToast === "function") {
      showToast("Unable to load CFI dashboard.", "error");
    }
    return;
  }

  let payload = suppliedPayload || null;
  
  // Debug logging
  if (payload) {
    console.log('Dashboard payload received:', {
      hasMeta: !!payload.meta,
      hasOverview: !!payload.overview,
      ticker: payload.meta?.ticker,
      company: payload.meta?.company
    });
  }
  
  if (!payload) {
    try {
      payload = await fetchCfiDashboardPayload(fetchOptions);
    } catch (error) {
      console.warn('CFI dashboard fetch failed, falling back to demo payload.', error);
    }
  }

  if (!payload || typeof payload !== 'object') {
    console.warn('Invalid payload, using demo data');
    payload = DEMO_CFI_PAYLOAD;
  }

  try {
    if (window.CFI && typeof window.CFI.render === 'function') {
      console.log('Rendering CFI dashboard with payload');
      window.CFI.render(payload);
      window.__cfiDashboardLastPayload = payload;
    } else {
      throw new Error('CFI renderer unavailable.');
    }
  } catch (error) {
    console.error('CFI render error:', error);
    host.innerHTML =
      '<div class="cfi-error">Unable to render CFI dashboard. Check console for details.</div>';
    if (typeof showToast === 'function') {
      showToast('Unable to render CFI dashboard.', 'error');
    }
  }
}

async function fetchCfiComparePayload(options = {}) {
  if (options.payload) {
    return options.payload;
  }
  const params = new URLSearchParams();
  if (options.tickers) {
    const tickers = Array.isArray(options.tickers) ? options.tickers : [options.tickers];
    if (tickers.length) {
      params.set("tickers", tickers.join(","));
    }
  }
  if (options.benchmark) {
    params.set("benchmark", options.benchmark);
  }
  if (options.date) {
    params.set("date", options.date);
  }
  const url = `/api/dashboard/cfi-compare${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`CFI Compare fetch failed (${response.status})`);
  }
  return response.json();
}

async function loadCfiCompareMarkup(host) {
  const response = await fetch(resolveStaticAsset("cfi_compare.html"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load CFI Compare layout.");
  }
  const html = await response.text();
  host.innerHTML = prepareEmbeddedLayout(html, "cfi_compare");
}
async function showCfiCompareDashboard(options = {}) {
  const { container, payload: suppliedPayload, ...fetchOptions } = options || {};
  let host = null;
  if (container instanceof HTMLElement) {
    host = container;
  } else if (typeof container === "string") {
    host = document.getElementById(container);
  }
  if (!host) {
    host = resolveDashboardHost();
  }
  if (!host) {
    throw new Error("Unable to resolve dashboard host container.");
  }
  host.innerHTML = '<div class="cfi-loading">Loading CFI Compare dashboard...</div>';
  try {
    await loadCfiCompareMarkup(host);
    await ensureStylesheetOnce("cfi-compare-styles", "cfi_compare.css");
    await ensurePlotlyLoaded();
    await ensureScriptOnce("cfi-compare-script", "cfi_compare.js");
  } catch (error) {
    console.error(error);
    host.innerHTML =
      '<div class="cfi-error">Unable to load CFI Compare dashboard layout. Check console for details.</div>';
    if (typeof showToast === "function") {
      showToast("Unable to load CFI Compare dashboard.", "error");
    }
    return;
  }

  let payload = suppliedPayload || null;
  if (!payload) {
    try {
      payload = await fetchCfiComparePayload(fetchOptions);
    } catch (error) {
      console.warn("CFI Compare dashboard fetch failed, falling back to demo payload.", error);
    }
  }

  if (!payload || typeof payload !== "object") {
    payload = DEMO_CFIX_PAYLOAD;
  }

  try {
    await ensureCfiCompareRenderer();
  } catch (error) {
    console.warn(error?.message || "CFI Compare renderer unavailable. Check cfi_compare.js delivery.");
    host.innerHTML =
      '<div class="cfi-error">Unable to render CFI Compare dashboard. Renderer unavailable.</div>';
    if (typeof showToast === "function") {
      showToast("CFI Compare renderer unavailable.", "error");
    }
    return;
  }

  try {
    window.CFIX.render(payload);
    window.__cfiCompareLastPayload = payload;
  } catch (error) {
    console.error(error);
    host.innerHTML =
      '<div class="cfi-error">Unable to render CFI Compare dashboard. Check console for details.</div>';
    if (typeof showToast === "function") {
      showToast("Unable to render CFI Compare dashboard.", "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  showCfiCompareDashboard().catch(() => {});
});

window.showCfiDenseDashboard = showCfiDenseDashboard;
window.showCfiDashboard = showCfiDashboard;
window.showCfiCompareDashboard = showCfiCompareDashboard;
}