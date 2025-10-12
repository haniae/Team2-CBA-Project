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
const utilityCloseButton = document.getElementById("utility-close");
const introPanel = document.getElementById("chat-intro");
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


let isSending = false;
let conversations = loadStoredConversations();
let activeConversation = null;
let conversationSearch = "";
let currentUtilityKey = null;

const UTILITY_SECTIONS = {
  "kpi-library": {
    title: "KPI Library",
    html: `
      <p>Central knowledge base for the standardized KPIs that BenchmarkOS supports.</p>
      <ul>
        <li>Review definitions, formulas, and calculation logic for each KPI (EPS CAGR, ROE, TSR, FCF Margin, and more).</li>
        <li>Understand source data lineage and any preprocessing done before metrics are calculated.</li>
        <li>Browse KPIs by category: growth, profitability, efficiency, valuation.</li>
      </ul>
      <p class="panel-note">Tip: ask the assistant with "help metrics" to surface featured KPIs instantly.</p>
    `,
  },
  "company-universe": {
    title: "Company Universe",
    html: `
      <p>Catalog of companies and sectors currently covered in BenchmarkOS.</p>
      <ul>
        <li>Filter by industry (Tech, Consumer, Healthcare...) and market-cap tiers.</li>
        <li>Check coverage status: <strong>✅ complete</strong>, <strong>🟡 filings missing</strong>, <strong>❌ not yet ingested</strong>.</li>
        <li>Look up aliases or brand names and map them to their official tickers.</li>
      </ul>
      <p class="panel-note">Tip: run “metrics &lt;ticker&gt;” right after confirming coverage.</p>
    `,
  },
  "filing-viewer": {
    title: "Filing Source Viewer",
    html: `
      <p>Trace every data point back to its original SEC filing.</p>
      <ul>
        <li>View raw lines extracted from 10-K and 10-Q filings alongside their accession numbers.</li>
        <li>Jump straight to the SEC document to reconcile figures with the official report.</li>
        <li>Build an audit trail per KPI to guarantee transparency and compliance.</li>
      </ul>
      <p class="panel-note">Tip: try “audit TSLA 2023” to inspect the most recent pipeline run.</p>
    `,
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
    html: `
      <p>Tùy chỉnh trải nghiệm BenchmarkOS cho doanh nghiệp của bạn.</p>
      <ul>
        <li>Quản lý API key, nguồn dữ liệu, và lịch cập nhật.</li>
        <li>Chọn mô hình AI (GPT-4, nội bộ, hay custom fine-tune).</li>
        <li>Thiết lập định dạng xuất bản: PDF, Excel, Markdown.</li>
        <li>Ưu tiên về ngôn ngữ, timezone, currency, và quy tắc tuân thủ.</li>
      </ul>
      <p class="panel-note">Các thay đổi tại đây tác động trực tiếp tới cả web UI và CLI.</p>
    `,
  },
};

function appendMessage(
  role,
  text,
  { smooth = true, forceScroll = false, isPlaceholder = false, animate = true } = {}
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
  } else {
    const fragments = buildMessageBlocks(text);
    fragments.forEach((node) => body.append(node));
  }
  wrapper.append(body);

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
  const fragments = buildMessageBlocks(text);
  fragments.forEach((node) => body.append(node));
}

function showAssistantTyping() {
  return appendMessage("assistant", "", { isPlaceholder: true, animate: false });
}

function resolvePendingMessage(wrapper, role, text, { forceScroll = false } = {}) {
  if (!wrapper) {
    appendMessage(role, text, { forceScroll, smooth: true });
    return null;
  }
  updateMessageRole(wrapper, role);
  wrapper.classList.remove("typing");
  setMessageBody(wrapper, text);
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

function recordMessage(role, text) {
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
  conversation.messages.push({ role, text, timestamp });
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
    appendMessage(message.role, message.text, { smooth: false, animate: false });
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
  setActiveNav(`open-${key}`);
}

function closeUtilityPanel() {
  if (!utilityPanel || !utilityTitle || !utilityContent) {
    return;
  }
  utilityPanel.classList.add("hidden");
  utilityTitle.textContent = "";
  utilityContent.innerHTML = "";
  currentUtilityKey = null;
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
  return data.reply;
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
  setSending(true);
  const pendingMessage = showAssistantTyping();

  try {
    const reply = await sendPrompt(prompt);
    const cleanReply = typeof reply === "string" ? reply.trim() : "";
    const messageText = cleanReply || "(no content)";
    recordMessage("assistant", messageText);
    resolvePendingMessage(pendingMessage, "assistant", messageText, { forceScroll: true });
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

if (utilityCloseButton) {
  utilityCloseButton.addEventListener("click", () => {
    closeUtilityPanel();
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

chatInput.focus();
