const API_BASE = window.API_BASE || "";

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const conversationInput = document.getElementById("conversation-id");

const metricsForm = document.getElementById("metrics-form");
const metricsOutput = document.getElementById("metrics-output");

const factsForm = document.getElementById("facts-form");
const factsOutput = document.getElementById("facts-output");

const auditForm = document.getElementById("audit-form");
const auditOutput = document.getElementById("audit-output");

const statusDot = document.getElementById("api-status");
const statusMessage = document.getElementById("status-message");

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error();
    statusDot.classList.add("online");
    statusMessage.textContent = "API online";
  } catch (error) {
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
    statusMessage.textContent = "Cannot reach API";
  }
}

function appendChat(role, text) {
  const container = document.createElement("div");
  container.className = "chat-entry";
  const label = document.createElement("strong");
  label.textContent = role;
  const content = document.createElement("p");
  content.textContent = text;
  container.append(label, content);
  chatLog.append(container);
  chatLog.scrollTop = chatLog.scrollHeight;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = chatInput.value.trim();
  if (!prompt) return;
  const conversationId = conversationInput.value.trim() || undefined;
  appendChat("You", prompt);
  chatInput.value = "";

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, conversation_id: conversationId }),
    });
    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`);
    }
    const data = await response.json();
    conversationInput.value = data.conversation_id;
    appendChat("Assistant", data.reply);
  } catch (error) {
    appendChat("System", `Unable to get response: ${error.message}`);
  }
});

metricsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  metricsOutput.innerHTML = "Loading metrics…";
  const tickers = document.getElementById("metrics-tickers").value.trim();
  const startYear = document.getElementById("metrics-start").value;
  const endYear = document.getElementById("metrics-end").value;

  const params = new URLSearchParams({ tickers });
  if (startYear && endYear) {
    params.set("start_year", startYear);
    params.set("end_year", endYear);
  }

  try {
    const response = await fetch(`${API_BASE}/metrics?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`);
    }
    const payload = await response.json();
    renderMetrics(payload);
  } catch (error) {
    metricsOutput.innerHTML = `<div class="alert warn">${error.message}</div>`;
  }
});

function renderMetrics(payload) {
  if (!Array.isArray(payload) || payload.length === 0) {
    metricsOutput.innerHTML = `<div class="alert warn">No metrics returned.</div>`;
    return;
  }

  const allMetrics = new Set();
  payload.forEach((entry) => {
    Object.keys(entry.metrics).forEach((metric) => allMetrics.add(metric));
  });

  const orderedMetrics = Array.from(allMetrics);
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.appendChild(document.createElement("th")).textContent = "Metric";
  payload.forEach((entry) => {
    const th = document.createElement("th");
    th.innerHTML = `${entry.ticker}<span class="badge">${entry.period}</span>`;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  orderedMetrics.forEach((metric) => {
    const row = document.createElement("tr");
    row.appendChild(document.createElement("td")).textContent = metric;
    payload.forEach((entry) => {
      const td = document.createElement("td");
      const value = entry.metrics[metric];
      td.textContent = formatValue(value);
      row.appendChild(td);
    });
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  metricsOutput.innerHTML = "";
  metricsOutput.appendChild(table);
}

function formatValue(value) {
  if (value === null || value === undefined) return "n/a";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "n/a";
    if (Math.abs(value) >= 1000) return value.toFixed(0);
    if (Math.abs(value) >= 1) return value.toFixed(2);
    return value.toFixed(3);
  }
  return String(value);
}

factsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  factsOutput.innerHTML = "Loading facts…";
  const ticker = document.getElementById("facts-ticker").value.trim();
  const fiscalYear = document.getElementById("facts-year").value;
  const metric = document.getElementById("facts-metric").value.trim();

  const params = new URLSearchParams({ ticker, fiscal_year: fiscalYear });
  if (metric) params.set("metric", metric);

  try {
    const response = await fetch(`${API_BASE}/facts?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`);
    }
    const payload = await response.json();
    renderFacts(payload);
  } catch (error) {
    factsOutput.innerHTML = `<div class="alert warn">${error.message}</div>`;
  }
});

function renderFacts(payload) {
  factsOutput.innerHTML = "";
  const heading = document.createElement("p");
  heading.innerHTML = `<strong>${payload.ticker}</strong> – FY${payload.fiscal_year}`;
  factsOutput.appendChild(heading);

  payload.items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "alert";
    row.innerHTML = `<strong>${item.metric}</strong>: ${formatValue(item.value)}<br/><small>${item.source}${
      item.adjusted ? " · adjusted" : ""
    }${item.adjustment_note ? ` · ${item.adjustment_note}` : ""}</small>`;
    factsOutput.appendChild(row);
  });
}

auditForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  auditOutput.innerHTML = "Loading audit events…";
  const ticker = document.getElementById("audit-ticker").value.trim();
  const fiscalYear = document.getElementById("audit-year").value;
  const params = new URLSearchParams({ ticker });
  if (fiscalYear) params.set("fiscal_year", fiscalYear);

  try {
    const response = await fetch(`${API_BASE}/audit?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`);
    }
    const payload = await response.json();
    renderAudit(payload);
  } catch (error) {
    auditOutput.innerHTML = `<div class="alert warn">${error.message}</div>`;
  }
});

function renderAudit(payload) {
  auditOutput.innerHTML = "";
  payload.events.forEach((event) => {
    const row = document.createElement("div");
    row.className = "alert";
    row.innerHTML = `<strong>${event.event_type}</strong> · ${event.created_at}<br/>${
      event.details
    }${event.entity_id ? ` <span class="badge">${event.entity_id}</span>` : ""}`;
    auditOutput.appendChild(row);
  });
}

checkHealth();
setInterval(checkHealth, 30000);
