const API_BASE = window.API_BASE || "";

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const statusDot = document.getElementById("api-status");
const statusMessage = document.getElementById("status-message");

let conversationId = null;
let isSending = false;

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const label = document.createElement("span");
  label.className = "message-role";
  label.textContent = role === "user" ? "You" : role === "assistant" ? "Assistant" : "System";
  wrapper.append(label);

  const fragments = buildMessageBlocks(text);
  fragments.forEach((node) => wrapper.append(node));

  chatLog.append(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
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
    const rowCells = parseRow(compact[i]);
    if (!rowCells.length) continue;
    const tr = document.createElement("tr");
    const totalColumns = Math.max(headerCells.length, rowCells.length);
    for (let c = 0; c < totalColumns; c += 1) {
      const raw = (rowCells[c] || "").trim();
      const td = document.createElement("td");
      const { isNumeric, value, suffix } = formatTableCell(raw);
      if (isNumeric) {
        td.classList.add("numeric");
      }

      const valueSpan = document.createElement("span");
      valueSpan.className = "cell-value";
      valueSpan.textContent = value;
      td.append(valueSpan);

      if (suffix) {
        const suffixSpan = document.createElement("span");
        suffixSpan.className = "cell-suffix";
        suffixSpan.textContent = suffix;
        td.append(suffixSpan);
      }

      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(tbody);
  wrapper.append(table);

  return wrapper;
}

function parseRow(line) {
  const trimmed = line.trim();
  if (!trimmed) {
    return [];
  }
  const withoutOuter = trimmed.replace(/^\|/, "").replace(/\|$/, "");
  return withoutOuter.split("|").map((cell) => cell.trim());
}

function formatTableCell(raw) {
  const trimmed = raw.trim();
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

function isNumericCell(value) {
  return /^[-+]?[$]?\d[\d,]*(\.\d+)?(%|x)?$/.test(value) || /^[-+]?\d+(\.\d+)?%?$/.test(value);
}

function setSending(state) {
  isSending = state;
  sendButton.disabled = state;
  chatInput.disabled = state;
  sendButton.textContent = state ? "Sending..." : "Send";
}

async function sendPrompt(prompt) {
  const payload = { prompt };
  if (conversationId) {
    payload.conversation_id = conversationId;
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
  conversationId = data.conversation_id;
  return data.reply;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSending) return;

  const prompt = chatInput.value.trim();
  if (!prompt) return;

  appendMessage("user", prompt);
  chatInput.value = "";
  setSending(true);

  try {
    const reply = await sendPrompt(prompt);
    appendMessage("assistant", reply.trim() || "(no content)");
  } catch (error) {
    appendMessage("system", error.message);
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

async function checkHealth() {
  try {
    const url = `${API_BASE}/health?ts=${Date.now()}`;
    const res = await fetch(url, { cache: 'no-store' });
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
