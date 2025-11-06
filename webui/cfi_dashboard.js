(function(){
  function resolveScope() {
    const container = window.__cfiActiveContainer;
    return container instanceof HTMLElement ? container : document;
  }
  function scopedQuery(id) {
    const scope = resolveScope();
    if (scope === document) return document.getElementById(id);
    return scope.querySelector(`#${id}`);
  }
  function scopedSelect(selector) {
    const scope = resolveScope();
    if (scope === document) return document.querySelector(selector);
    return scope.querySelector(selector);
  }
  function scopedSelectAll(selector) {
    const scope = resolveScope();
    if (scope === document) return document.querySelectorAll(selector);
    return scope.querySelectorAll(selector);
  }

  const COLORS = {
    navy: "#0B2E59",
    navyDark: "#082249",
    accent: "#1C7ED6",
    accentLight: "#4DABF7",
    accentDark: "#1864AB",
    orange: "#FF7F0E",
    orangeLight: "#FFA94D",
    green: "#10B981",
    greenLight: "#51CF66",
    red: "#EF4444",
    slate: "#5B6B82",
    slateLight: "#8C9BB0"
  };
  const BASE_LAYOUT = {
    paper_bgcolor: "rgba(250, 252, 254, 0.5)",
    plot_bgcolor: "#ffffff",
    font: { family: "Inter, Open Sans, Roboto", color: COLORS.navy, size: 12, weight: 500 },
    xaxis: { 
      gridcolor: "rgba(220, 228, 244, 0.4)", 
      zeroline: false, 
      tickfont: { size: 11 },
      showline: true,
      linecolor: "rgba(220, 228, 244, 0.6)",
      linewidth: 1
    },
    yaxis: { 
      gridcolor: "rgba(220, 228, 244, 0.4)", 
      zeroline: false, 
      tickfont: { size: 11 },
      showline: true,
      linecolor: "rgba(220, 228, 244, 0.6)",
      linewidth: 1
    },
    legend: { 
      orientation: "h", 
      y: 1.14, 
      x: 1.0, 
      xanchor: "right", 
      font: { size: 10 },
      bgcolor: "rgba(255, 255, 255, 0.9)",
      bordercolor: "rgba(220, 228, 244, 0.5)",
      borderwidth: 1
    },
    margin: { l: 48, r: 36, t: 32, b: 40 },
    hoverlabel: { 
      bgcolor: "#ffffff", 
      bordercolor: COLORS.accentLight, 
      font: { family: "Inter, Open Sans, Roboto", size: 11 },
      align: "left"
    },
    hovermode: "x unified"
  };
  const CONFIG = { 
    displayModeBar: false, 
    responsive: true,
    doubleClick: false
  };

  const isNumber = (value) => value !== null && value !== undefined && Number.isFinite(Number(value));

  /**
   * Aggressively sanitize data before passing to Plotly to prevent NaN errors.
   * Replaces NaN, Infinity, null, undefined with 0 for numeric arrays.
   */
  function sanitizePlotlyData(data) {
    if (!data || typeof data !== 'object') return data;
    
    const sanitized = Array.isArray(data) ? [] : {};
    
    for (const key in data) {
      const value = data[key];
      
      if (Array.isArray(value)) {
        // For arrays, filter out or replace invalid numbers
        sanitized[key] = value.map(v => {
          if (v === null || v === undefined) return 0;
          if (typeof v === 'number') {
            if (!Number.isFinite(v)) return 0; // Catches NaN and Infinity
            return v;
          }
          return v; // Keep non-numeric values (like strings for labels)
        });
      } else if (typeof value === 'number') {
        // For single numbers, replace invalid with 0
        sanitized[key] = Number.isFinite(value) ? value : 0;
      } else if (value && typeof value === 'object') {
        // Recursively sanitize nested objects
        sanitized[key] = sanitizePlotlyData(value);
      } else {
        sanitized[key] = value;
      }
    }
    
    return sanitized;
  }

  function formatMoney(value) {
    if (!isNumber(value)) return "—";
    const sign = value < 0 ? "-" : "";
    const abs = Math.abs(value);
    const unit = abs >= 1e9 ? "B" : abs >= 1e6 ? "M" : abs >= 1e3 ? "K" : "";
    const divisor = unit === "B" ? 1e9 : unit === "M" ? 1e6 : unit === "K" ? 1e3 : 1;
    const scaled = abs / divisor;
    const decimals = scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2;
    const text = scaled.toFixed(decimals).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
    return `${sign}$${text}${unit}`;
  }

  function formatCurrency(value) {
    if (!isNumber(value)) return "—";
    const number = Number(value);
    const abs = Math.abs(number);
    const decimals = abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
    return `$${number.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    })}`;
  }

  const formatPercent = (value) => {
    if (!isNumber(value)) return "—";
    const percent = Number(value) * 100;
    const decimals = Math.abs(percent) >= 10 ? 1 : 2;
    return `${percent.toFixed(decimals)}%`;
  };
  const formatMultiple = (value) => (isNumber(value) ? `${Number(value).toFixed(1)}×` : "—");
  const formatInteger = (value) => (isNumber(value) ? Number(value).toLocaleString() : "—");

  function formatKpiValue(value, type) {
    if (!isNumber(value)) return "—";
    const kind = type || "number";
    if (kind === "percent") return formatPercent(value);
    if (kind === "multiple") return formatMultiple(value);
    if (kind === "currency") return formatMoney(value);
    if (kind === "integer") return formatInteger(value);
    return formatMoney(value);
  }

  function normalizePairs(source) {
    if (!source) return [];
    if (Array.isArray(source)) {
      return source.map((row) => ({
        label: row.label ?? row.Label ?? row.key ?? row.k ?? "",
        value: row.value ?? row.Value ?? row.v ?? row.val ?? row
      }));
    }
    return Object.entries(source).map(([label, value]) => ({ label, value }));
  }

  function sanitizeText(value) {
    if (value === null || value === undefined) return "";
    let text = String(value);
    try {
      text = decodeURIComponent(escape(text));
    } catch (error) {
      // ignore; fallback to original text
    }
    return text
      .normalize("NFKC")
      .replace(/\u00a0/g, " ")
      .replace(/Â/g, "")
      .replace(/Ã[\u0097\u0098×]/g, "×")
      .replace(/\u00A6/g, "×")
      .replace(/\s+/g, " ")
      .trim();
  }

  function coerceFromText(label, raw) {
    const cleaned = sanitizeText(raw);
    if (!cleaned) return { text: "", numeric: null };
    if (/^(?:n\/?a|na|not available|--|-|—)$/i.test(cleaned)) {
      return { text: "—", numeric: null };
    }
    const lowerLabel = String(label || "").toLowerCase();
    const moneyMatch = cleaned.match(/^(-?\d+(?:\.\d+)?)(?:\s*)([bmk])$/i);
    if (moneyMatch) {
      const rawNumber = Number(moneyMatch[1]);
      const unit = moneyMatch[2].toUpperCase();
      const multiplier = unit === "B" ? 1e9 : unit === "M" ? 1e6 : 1e3;
      return { text: cleaned, numeric: rawNumber * multiplier, meta: { unit } };
    }
    const multipleMatch = cleaned.match(/^(-?\d+(?:\.\d+)?)[x×]$/i);
    if (multipleMatch) {
      return { text: cleaned, numeric: Number(multipleMatch[1]), meta: { kind: "multiple" } };
    }
    const percentMatch = cleaned.match(/^(-?\d+(?:\.\d+)?)%$/);
    if (percentMatch) {
      return { text: cleaned, numeric: Number(percentMatch[1]) / 100, meta: { kind: "percent" } };
    }
    const plainNumber = cleaned.replace(/[,]/g, "");
    if (/^-?\d+(?:\.\d+)?$/.test(plainNumber)) {
      return { text: cleaned, numeric: Number(plainNumber), meta: {} };
    }
    return { text: cleaned, numeric: null };
  }

  function toNumericValue(value, label) {
    if (isNumber(value)) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : null;
    }
    if (typeof value === "string") {
      const coerced = coerceFromText(label, value);
      if (coerced && isNumber(coerced.numeric)) {
        return Number(coerced.numeric);
      }
      const normalized = value.replace(/[^0-9.\-]/g, "");
      if (normalized) {
        const parsed = Number(normalized);
        if (Number.isFinite(parsed)) return parsed;
      }
    }
    return null;
  }

  function buildNumericSeries(categories = [], values = [], labelPrefix = "") {
    if (!Array.isArray(categories) || !Array.isArray(values)) return [];
    const safe = [];
    const count = Math.min(categories.length, values.length);
    for (let idx = 0; idx < count; idx += 1) {
      const label = labelPrefix ? `${labelPrefix} ${categories[idx] ?? ""}` : categories[idx];
      const numeric = toNumericValue(values[idx], label);
      // Strict validation: must be a finite number (not NaN, not Infinity)
      if (numeric === null || !Number.isFinite(numeric)) continue;
      safe.push({ x: categories[idx], y: numeric });
    }
    return safe;
  }
  
  // Helper function to sanitize array of numeric values
  function sanitizeNumericArray(arr) {
    if (!Array.isArray(arr)) return [];
    return arr.map(val => {
      if (val === null || val === undefined) return null;
      const num = Number(val);
      return Number.isFinite(num) ? num : null;
    });
  }

  function formatValue(label, value) {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "string") {
      const coerced = coerceFromText(label, value);
      if (coerced.numeric !== null) {
        const numeric = coerced.numeric;
        const lower = String(label || "").toLowerCase();
        if (coerced.meta?.kind === "percent" || lower.includes("percent") || lower.includes("%")) {
          return formatPercent(numeric);
        }
        if (coerced.meta?.kind === "multiple" || lower.includes("multiple") || lower.includes("ev/")) {
          return formatMultiple(numeric);
        }
        if (coerced.meta?.unit) {
          return formatMoney(numeric);
        }
        return formatMoney(numeric);
      }
      return coerced.text || "—";
    }
    const lower = String(label || "").toLowerCase();
    if (lower.includes("margin") || lower.includes("growth") || lower.includes("pct") || lower.includes("%")) return formatPercent(value);
    if (
      lower.includes("share price") ||
      lower.includes("target price") ||
      lower.includes("current price") ||
      lower.includes("52-week") ||
      lower.includes("hi/lo")
    ) {
      return formatCurrency(value);
    }
    if (lower.includes("multiple") || lower.includes("ev/") || lower.includes("turnover")) return formatMultiple(value);
    if (lower.includes("employee") || lower.includes("shares") || lower.includes("count")) return formatInteger(value);
    if (
      lower.includes("price") ||
      lower.includes("value") ||
      lower.includes("cap") ||
      lower.includes("debt") ||
      lower.includes("cash") ||
      lower.includes("revenue") ||
      lower.includes("income") ||
      lower.includes("flow")
    ) {
      return formatMoney(value);
    }
  return formatMoney(value);
}

  function ensureTBody(table) {
    if (!table) return null;
    let tbody = table.querySelector("tbody");
    if (!tbody) {
      tbody = document.createElement("tbody");
      table.appendChild(tbody);
    }
    return tbody;
  }

  function renderPairsTable(target, source) {
    const table = typeof target === "string" ? scopedQuery(target) : target;
    if (!table) return;
    const tbody = ensureTBody(table);
    if (!tbody) return;
    tbody.innerHTML = "";
    const rows = normalizePairs(source);
    if (!rows.length) {
      const emptyRow = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 2;
      cell.textContent = "—";
      emptyRow.appendChild(cell);
      tbody.appendChild(emptyRow);
      return;
    }
    rows.forEach(({ label, value }) => {
      if (!label) return;
      const tr = document.createElement("tr");
      const left = document.createElement("td");
      left.className = "kv-label";
      left.textContent = sanitizeText(String(label).replace(/_/g, " "));
      const right = document.createElement("td");
      right.className = "kv-value";
      right.textContent = formatValue(label, value);
      tr.append(left, right);
      tbody.appendChild(tr);
    });
  }

  function renderValuationTable(target, rows) {
    const table = typeof target === "string" ? scopedQuery(target) : target;
    if (!table) return;
    table.innerHTML = "";
    if (!rows || !rows.length) {
      const empty = document.createElement("caption");
      empty.textContent = "No valuation detail available.";
      table.appendChild(empty);
      return;
    }
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    const columns = Object.keys(rows[0]).filter((key) => key !== "Label" && key !== "label");
    const headings = ["Metric", ...columns];
    headings.forEach((heading, index) => {
      const th = document.createElement("th");
      th.textContent = sanitizeText(heading);
      if (index === 0) th.className = "col-label";
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const labelCell = document.createElement("td");
      labelCell.className = "kv-label";
      labelCell.textContent = sanitizeText(row.Label || row.label || "");
      tr.appendChild(labelCell);
      columns.forEach((field) => {
        const td = document.createElement("td");
        td.className = "kv-value";
        td.textContent = formatValue(field, row[field]);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  function renderValuationNotes(target, notes) {
    const list = typeof target === "string" ? scopedQuery(target) : target;
    if (!list) return;
    list.innerHTML = "";
    if (!Array.isArray(notes) || !notes.length) return;
    notes.forEach((entry) => {
      if (!entry) return;
      const li = document.createElement("li");
      li.textContent = entry;
      list.appendChild(li);
    });
  }

  function renderKeyFinancials(targetId, table) {
    const container = scopedQuery(targetId);
    if (!container) return;
    container.innerHTML = "";
    if (!table || !Array.isArray(table.columns) || !table.columns.length) {
      container.textContent = "—";
      return;
    }
    const columns = table.columns;
    const tbl = document.createElement("table");
    tbl.className = "cfi-table";

    const colgroup = document.createElement("colgroup");
    colgroup.appendChild(document.createElement("col"));
    columns.forEach(() => colgroup.appendChild(document.createElement("col")));
    tbl.appendChild(colgroup);

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    const metricHeader = document.createElement("th");
    metricHeader.textContent = "Metric";
    headerRow.appendChild(metricHeader);
    columns.forEach((year) => {
      const th = document.createElement("th");
      th.textContent = sanitizeText(year);
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    tbl.appendChild(thead);

    const tbody = document.createElement("tbody");
    (table.rows || []).forEach((row) => {
      const tr = document.createElement("tr");
      const metricCell = document.createElement("td");
      metricCell.className = "metric";
      metricCell.textContent = sanitizeText(row.label || "");
      tr.appendChild(metricCell);
      columns.forEach((_, index) => {
        const td = document.createElement("td");
        td.className = "num";
        const rawValue = row.values ? row.values[index] : null;
        let numericValue = null;
        let fallback = "";
        if (isNumber(rawValue)) {
          numericValue = Number(rawValue);
        } else if (typeof rawValue === "string") {
          const coerced = coerceFromText(row.label, rawValue);
          if (coerced.numeric !== null) {
            numericValue = Number(coerced.numeric);
          } else {
            fallback = coerced.text || "—";
          }
        }
        let formatted = "—";
        if (fallback) {
          formatted = fallback;
        } else if (numericValue !== null) {
          if (row.type === "percent") formatted = formatPercent(numericValue);
          else if (row.type === "multiple") formatted = formatMultiple(numericValue);
          else if (row.type === "currency") formatted = formatCurrency(numericValue);
          else if (row.type === "integer") formatted = formatInteger(numericValue);
          else formatted = formatMoney(numericValue);
        }
        td.textContent = formatted;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    container.appendChild(tbl);
  }

  function renderKpiSummary(targetId, items) {
    const container = scopedQuery(targetId);
    if (!container) return;
    container.innerHTML = "";
    if (!Array.isArray(items) || !items.length) {
      const empty = document.createElement("div");
      empty.className = "cfi-kpi-empty";
      empty.textContent = "No KPI metrics available.";
      container.appendChild(empty);
      return;
    }
    const grid = document.createElement("div");
    grid.className = "cfi-kpi-grid";
    items.forEach((item) => {
      if (!item) return;
      const metricId = item.id || item.kpi_id || item.label || "";
      const card = document.createElement("div");
      card.className = "cfi-kpi-item";
      card.dataset.metricId = metricId;
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      const label = document.createElement("div");
      label.className = "cfi-kpi-label";
      label.textContent = item.label || item.id || "";
      const value = document.createElement("div");
      value.className = "cfi-kpi-value";
      value.textContent = formatKpiValue(item.value, item.type);
      if (isNumber(item.value)) {
        if (item.type === "percent") {
          value.classList.add(item.value >= 0 ? "positive" : "negative");
        } else if (item.type === "multiple" && item.value < 0) {
          value.classList.add("negative");
        }
      }
      card.appendChild(label);
      card.appendChild(value);
      if (item.period) {
        const meta = document.createElement("div");
        meta.className = "cfi-kpi-meta";
        meta.textContent = item.period;
        card.appendChild(meta);
      }
      card.addEventListener("click", () => openKpiDrilldown(metricId));
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openKpiDrilldown(metricId);
        }
      });
      grid.appendChild(card);
    });
    container.appendChild(grid);
  }

  function deepSanitize(value) {
    if (typeof value === "string") {
      return sanitizeText(value);
    }
    if (Array.isArray(value)) {
      return value.map((item) => deepSanitize(item));
    }
    if (value && typeof value === "object") {
      const result = Array.isArray(value) ? [] : {};
      Object.entries(value).forEach(([key, entry]) => {
        result[key] = deepSanitize(entry);
      });
      return result;
    }
    return value;
  }

  function parseFilenameFromDisposition(disposition) {
    if (!disposition) return "";
    const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utfMatch && utfMatch[1]) {
      try {
        return decodeURIComponent(utfMatch[1]);
      } catch (error) {
        console.warn("Unable to decode filename from disposition:", error);
      }
    }
    const simpleMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
    if (simpleMatch && simpleMatch[1]) {
      return simpleMatch[1];
    }
    return "";
  }

  async function triggerExport(button, format, payload) {
    const exporter = button;
    const exportFormat = (format || "").toLowerCase();
    const ticker =
      payload?.meta?.ticker_label ||
      payload?.meta?.ticker ||
      payload?.meta?.ticker_display ||
      payload?.meta?.company ||
      "";
    if (!exportFormat) {
      return;
    }
    if (!ticker) {
      if (typeof window.showToast === "function") {
        window.showToast("Unable to determine ticker for export.", "error");
      }
      return;
    }
    try {
      exporter.disabled = true;
      exporter.classList.add("loading");
      const params = new URLSearchParams();
      params.set("format", exportFormat);
      params.set("ticker", ticker);
      const response = await fetch(`/api/export/cfi?${params.toString()}`);
      if (!response.ok) {
        // Try to get error details from the response
        let errorMessage = `Export failed (${response.status})`;
        try {
          // Clone the response to read it without consuming the original
          const responseClone = response.clone();
          const errorData = await responseClone.json();
          console.error("Export error details:", errorData);
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          }
        } catch (jsonError) {
          // If response is not JSON, try text
          try {
            const responseClone = response.clone();
            const errorText = await responseClone.text();
            console.error("Export error text:", errorText);
            if (errorText && errorText.trim()) {
              errorMessage = errorText;
            }
          } catch (textError) {
            console.error("Could not read error response:", textError);
            // Keep default message
          }
        }
        console.error("Final error message:", errorMessage);
        throw new Error(errorMessage);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition");
      const filename =
        parseFilenameFromDisposition(disposition) ||
        `benchmarkos-export-${Date.now()}.${exportFormat === "ppt" ? "pptx" : exportFormat}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      if (typeof window.showToast === "function") {
        window.showToast(`Export ready (${filename})`, "success");
      }
    } catch (error) {
      console.error("Export failed:", error);
      const errorMsg = error.message || "Unable to generate export.";
      if (typeof window.showToast === "function") {
        window.showToast(errorMsg, "error");
      } else {
        alert(`Export failed: ${errorMsg}`);
      }
    } finally {
      exporter.disabled = false;
      exporter.classList.remove("loading");
    }
  }

  function attachExportHandlers(payload) {
    const buttons = scopedSelectAll("[data-export-format]");
    if (!buttons || !buttons.length) return;
    buttons.forEach((button) => {
      const format = button.getAttribute("data-export-format");
      button.onclick = () => triggerExport(button, format, payload);
    });
  }

  function closeKpiDrilldown() {
    const wrapper = scopedQuery("cfi-drilldown");
    if (!wrapper) return;
    wrapper.classList.remove("visible");
    wrapper.classList.add("hidden");
  }

  function openKpiDrilldown(metricId) {
    if (!metricId) return;
    const payload = window.__cfiDashboardLastPayload;
    if (!payload) return;
    const wrapper = scopedQuery("cfi-drilldown");
    const content = scopedQuery("cfi-drilldown-content");
    if (!wrapper || !content) return;

    const summary =
      (payload.kpi_summary || []).find(
        (item) =>
          item?.id === metricId ||
          item?.kpi_id === metricId ||
          (item?.label && item.label.toLowerCase() === metricId.toLowerCase())
      ) || null;
    const drilldown =
      (payload.interactions?.kpis?.drilldowns || []).find((entry) => entry?.id === metricId) || null;
    const series = payload.kpi_series?.[metricId] || null;

    content.innerHTML = "";

    const title = document.createElement("h2");
    title.textContent = drilldown?.label || summary?.label || metricId;
    content.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "drilldown-meta";
    const period = summary?.period || "";
    meta.textContent = period ? `Latest period: ${period}` : "Latest period unavailable";
    content.appendChild(meta);

    const cards = document.createElement("div");
    cards.className = "drilldown-grid";

    const latestCard = document.createElement("div");
    latestCard.className = "drilldown-card";
    const latestLabel = document.createElement("label");
    latestLabel.textContent = "Latest Value";
    const latestValue = document.createElement("strong");
    latestValue.textContent = formatKpiValue(summary?.value, summary?.type);
    latestCard.append(latestLabel, latestValue);
    cards.appendChild(latestCard);

    if (series && Array.isArray(series.values) && series.values.length >= 2) {
      const last = series.values[series.values.length - 1];
      const prev = series.values[series.values.length - 2];
      if (isNumber(last) && isNumber(prev)) {
        const diff = last - prev;
        const diffCard = document.createElement("div");
        diffCard.className = "drilldown-card";
        const diffLabel = document.createElement("label");
        diffLabel.textContent = "Change vs Prior Period";
        const diffValue = document.createElement("strong");
        diffValue.textContent = formatKpiValue(diff, series.type || summary?.type);
        diffCard.append(diffLabel, diffValue);
        cards.appendChild(diffCard);

        if (prev !== 0) {
          const growth = last / prev - 1;
          const growthCard = document.createElement("div");
          growthCard.className = "drilldown-card";
          const growthLabel = document.createElement("label");
          growthLabel.textContent = "Growth Rate";
          const growthValue = document.createElement("strong");
          growthValue.textContent = formatKpiValue(growth, "percent");
          growthCard.append(growthLabel, growthValue);
          cards.appendChild(growthCard);
        }
      }
    }

    content.appendChild(cards);

    const chartNode = document.createElement("div");
    chartNode.className = "drilldown-series";
    content.appendChild(chartNode);

    if (window.Plotly && series && Array.isArray(series.years) && series.years.length) {
      const cleanPoints = series.years
        .map((year, idx) => {
          const value = series.values?.[idx];
          return (isNumber(value) && Number.isFinite(value)) ? { year, value } : null;
        })
        .filter(Boolean);
      if (cleanPoints.length) {
        const traces = [
          {
            type: "scatter",
            mode: "lines+markers",
            x: cleanPoints.map((pt) => pt.year),
            y: cleanPoints.map((pt) => pt.value),
            name: drilldown?.label || summary?.label || metricId,
            line: { color: "#1C7ED6", width: 3 },
            marker: { color: "#1C7ED6", size: 6 },
            connectgaps: false,
          },
        ];
        const layout = {
          ...BASE_LAYOUT,
          title: { text: "Historical Trend", x: 0.02, font: { size: 14 } },
          yaxis:
            series.type === "percent"
              ? { ...BASE_LAYOUT.yaxis, tickformat: ",.1%", rangemode: "tozero" }
              : series.type === "multiple"
              ? { ...BASE_LAYOUT.yaxis, tickformat: ",.1" }
              : { ...BASE_LAYOUT.yaxis, separatethousands: true },
        };
        Plotly.newPlot(chartNode, sanitizePlotlyData(traces), sanitizePlotlyData(layout), CONFIG);
      } else {
        chartNode.innerHTML = '<div class="cfi-error">Insufficient data for trend.</div>';
      }
    } else {
      chartNode.innerHTML = '<div class="cfi-error">Trend chart unavailable.</div>';
    }

    if (series && Array.isArray(series.years)) {
      const table = document.createElement("table");
      table.className = "drilldown-table";
      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      const thYear = document.createElement("th");
      thYear.textContent = "Period";
      headerRow.appendChild(thYear);
      const thValue = document.createElement("th");
      thValue.textContent = "Value";
      headerRow.appendChild(thValue);
      thead.appendChild(headerRow);
      table.appendChild(thead);
      const tbody = document.createElement("tbody");
      series.years.forEach((year, idx) => {
        const tr = document.createElement("tr");
        const tdYear = document.createElement("td");
        tdYear.textContent = year;
        const tdValue = document.createElement("td");
        tdValue.textContent = formatKpiValue(series.values?.[idx], series.type || summary?.type);
        tr.append(tdYear, tdValue);
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      content.appendChild(table);
    }

    wrapper.classList.remove("hidden");
    wrapper.classList.add("visible");
  }

  function setupDrilldownListeners() {
    const wrapper = scopedQuery("cfi-drilldown");
    if (!wrapper || wrapper.dataset.bound === "true") return;
    wrapper.dataset.bound = "true";
    wrapper.addEventListener("click", (event) => {
      if (event.target instanceof HTMLElement && event.target.dataset.action === "close-drilldown") {
        closeKpiDrilldown();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeKpiDrilldown();
      }
    });
  }

  function renderTrendChart(metricId, mode = "absolute") {
    const chartNode = scopedQuery("cfi-trend-chart");
    if (!chartNode) return;
    const payload = window.__cfiDashboardLastPayload;
    if (!payload) return;
    const series = payload.kpi_series?.[metricId];
    if (!series || !Array.isArray(series.years) || !series.years.length) {
      chartNode.innerHTML = '<div class="cfi-error">Trend unavailable.</div>';
      return;
    }
    if (!window.Plotly) {
      chartNode.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
      return;
    }
    const baseType = series.type || "number";
    let years = series.years.slice();
    let values = sanitizeNumericArray(series.values.slice());
    let type = baseType;
    if (mode === "growth") {
      const growth = [];
      for (let i = 1; i < values.length; i += 1) {
        const prev = values[i - 1];
        const curr = values[i];
        if (!isNumber(prev) || !isNumber(curr) || !Number.isFinite(prev) || !Number.isFinite(curr) || prev === 0) {
          growth.push(null);
        } else {
          const growthVal = curr / prev - 1;
          growth.push(Number.isFinite(growthVal) ? growthVal : null);
        }
      }
      years = years.slice(1);
      values = growth;
      type = "percent";
    }
    const cleanPoints = years
      .map((year, idx) => {
        const value = values[idx];
        return (isNumber(value) && Number.isFinite(value)) ? { year, value } : null;
      })
      .filter(Boolean);
    if (!cleanPoints.length) {
      chartNode.innerHTML = '<div class="cfi-error">Trend unavailable.</div>';
      return;
    }
    const traces = [
      {
        type: "scatter",
        mode: "lines+markers",
        x: cleanPoints.map((pt) => pt.year),
        y: cleanPoints.map((pt) => pt.value),
        line: { color: "#FF7F0E", width: 3 },
        marker: { color: "#FF7F0E", size: 6 },
        connectgaps: false,
      },
    ];
    const layout = {
      ...BASE_LAYOUT,
      title: { text: mode === "growth" ? "Growth Trend" : "Absolute Trend", x: 0.02, font: { size: 14 } },
      yaxis:
        type === "percent"
          ? { ...BASE_LAYOUT.yaxis, tickformat: ",.1%", rangemode: "tozero" }
          : type === "multiple"
          ? { ...BASE_LAYOUT.yaxis, tickformat: ",.1" }
          : { ...BASE_LAYOUT.yaxis, separatethousands: true },
    };
    Plotly.newPlot(chartNode, sanitizePlotlyData(traces), sanitizePlotlyData(layout), CONFIG);
  }

  function setupTrendExplorer(payload) {
    const form = scopedQuery("cfi-trend-form");
    const metricSelect = scopedQuery("cfi-trend-metric");
    const viewSelect = scopedQuery("cfi-trend-view");
    const chartNode = scopedQuery("cfi-trend-chart");
    if (!form || !metricSelect || !viewSelect || !chartNode) return;
    const metrics = (payload.kpi_summary || []).filter((item) => item?.id && payload.kpi_series?.[item.id]);
    metricSelect.innerHTML = "";
    if (!metrics.length) {
      metricSelect.innerHTML = '<option value="">No metrics available</option>';
      chartNode.innerHTML = '<div class="cfi-error">Trend data unavailable.</div>';
      form.querySelector("button")?.setAttribute("disabled", "disabled");
      return;
    }
    metrics.forEach((item, index) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.label || item.id;
      if (index === 0) option.selected = true;
      metricSelect.appendChild(option);
    });
    form.querySelector("button")?.removeAttribute("disabled");
    form.onsubmit = (event) => {
      event.preventDefault();
      if (!metricSelect.value) return;
      renderTrendChart(metricSelect.value, viewSelect.value || "absolute");
    };
    renderTrendChart(metricSelect.value, viewSelect.value || "absolute");
  }

  function setupPeerControls(payload) {
    const panel = scopedSelect('[data-area="peers"]');
    const form = scopedQuery("cfi-peer-form");
    const select = scopedQuery("cfi-peer-group");
    const customInput = scopedQuery("cfi-peer-custom");
    const status = scopedQuery("cfi-peer-status");
    const host = scopedQuery("cfi-peer-compare");
    if (!panel || !form || !select || !customInput || !status || !host) return;

    const peerConfig = payload.peer_config;
    if (!peerConfig) {
      panel.style.display = "none";
      return;
    }
    panel.style.display = "";

    const groups = Array.isArray(peerConfig.available_peer_groups) ? peerConfig.available_peer_groups : [];
    select.innerHTML = "";
    groups.forEach((group) => {
      const option = document.createElement("option");
      option.value = group.id || group.label || "";
      option.textContent = group.label || group.id || "Group";
      select.appendChild(option);
    });
    if (!select.value && groups.length) {
      select.value = peerConfig.default_peer_group || groups[0].id || groups[0].label || "";
    } else if (peerConfig.default_peer_group) {
      select.value = peerConfig.default_peer_group;
    }

    status.textContent = "Select a peer group or enter tickers to compare.";
    host.innerHTML = "";

    form.onsubmit = (event) => {
      event.preventDefault();
      const selectedGroup = select.value;
      const groupDefinition = groups.find((group) => group.id === selectedGroup || group.label === selectedGroup);
      const focus = peerConfig.focus_ticker ? [peerConfig.focus_ticker] : [];
      const groupTickers = Array.isArray(groupDefinition?.tickers) ? groupDefinition.tickers.slice() : [];
      const customTickers = customInput.value
        .split(",")
        .map((ticker) => ticker.trim().toUpperCase())
        .filter((ticker) => ticker && /^[A-Z0-9\.-]+$/.test(ticker));
      const tickers = Array.from(new Set([...focus, ...groupTickers, ...customTickers]));
      if (tickers.length < 2) {
        status.textContent = "Add at least one peer ticker to compare.";
        return;
      }
      status.textContent = "Loading peer comparison…";
      host.innerHTML = '<div class="cfi-loading">Loading peer comparison…</div>';
      window
        .showCfiCompareDashboard({
          container: host,
          tickers,
          benchmark: peerConfig.default_peer_group === selectedGroup ? peerConfig.benchmark_label : selectedGroup,
        })
        .then(() => {
          status.textContent = `Comparing ${tickers.join(", ")}`;
        })
        .catch((error) => {
          console.error("Peer comparison failed:", error);
          status.textContent = "Unable to load peer comparison.";
          host.innerHTML = '<div class="cfi-error">Unable to load peer comparison.</div>';
        });
    };
  }

  function plotRevenueChart(data) {
    const node = scopedQuery("cfi-rev");
    if (!node) {
      console.warn('[plotRevenueChart] Chart node not found');
      return;
    }
    if (!window.Plotly) {
      node.textContent = "Chart library loading...";
      return;
    }
    if (!data || !Array.isArray(data.Year) || !Array.isArray(data.Revenue)) {
      console.warn('[plotRevenueChart] Invalid data:', { hasData: !!data, hasYear: Array.isArray(data?.Year), hasRevenue: Array.isArray(data?.Revenue) });
      node.textContent = "No revenue data.";
      return;
    }
    
    console.log('[plotRevenueChart] Data received:', {
      yearCount: data.Year.length,
      revenueCount: data.Revenue.length,
      sampleYear: data.Year.slice(0, 3),
      sampleRevenue: data.Revenue.slice(0, 3)
    });

    const revenueSeries = buildNumericSeries(data.Year, data.Revenue, "Revenue");
    console.log('[plotRevenueChart] Built series:', {
      seriesLength: revenueSeries.length,
      samplePoints: revenueSeries.slice(0, 3)
    });
    
    if (!revenueSeries.length) {
      console.warn('[plotRevenueChart] No valid series data after buildNumericSeries');
      node.textContent = "No revenue data.";
      return;
    }
    const xValues = revenueSeries.map((point) => point.x);
    const yValues = revenueSeries.map((point) => point.y).filter(v => Number.isFinite(v));
    
    console.log('[plotRevenueChart] Filtered values:', {
      xValuesLength: xValues.length,
      yValuesLength: yValues.length,
      sampleYValues: yValues.slice(0, 3)
    });
    
    if (yValues.length === 0) {
      console.warn('[plotRevenueChart] All values filtered out - no finite numbers');
      node.textContent = "No valid revenue data.";
      return;
    }
    
    const denominator = Math.max(yValues.length - 1, 1);
    const barColors = yValues.map((_, idx) => {
      const ratio = denominator === 0 ? 0 : idx / denominator;
      return `rgba(11, 46, 89, ${0.7 + ratio * 0.3})`;
    });
    
    const traces = [
      {
        type: "bar",
        x: xValues,
        y: yValues,
        name: "Revenue ($M)",
        marker: { 
          color: barColors,
          line: { color: COLORS.navyDark, width: 1.5 },
          pattern: { shape: "" }
        },
        hovertemplate: "<b>FY %{x}</b><br>Revenue: $%{y:,.0f}M<extra></extra>"
      }
    ];
    const multiplesSource = data.EV_Rev || data["EV/Revenue"] || [];
    const multiplesSeries = buildNumericSeries(data.Year, multiplesSource, "EV/Revenue");
    if (multiplesSeries.length) {
      const multipleYValues = multiplesSeries.map((point) => point.y).filter(v => Number.isFinite(v));
      if (multipleYValues.length > 0) {
        traces.push({
          type: "scatter",
          mode: "lines+markers",
          x: multiplesSeries.map((point) => point.x),
          y: multipleYValues,
          name: "EV/Revenue (×)",
          yaxis: "y2",
          line: { color: COLORS.accent, width: 3, shape: "spline" },
          marker: { 
            size: 8, 
            color: COLORS.accentLight,
            line: { color: COLORS.accent, width: 2 }
          },
          connectgaps: false,
          hovertemplate: "<b>FY %{x}</b><br>EV/Revenue: %{y:.2f}×<extra></extra>"
        });
      }
    }
    const layout = {
      ...BASE_LAYOUT,
      yaxis: { ...BASE_LAYOUT.yaxis, title: "Revenue ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { 
        title: "EV/Revenue (×)", 
        overlaying: "y", 
        side: "right", 
        showgrid: false, 
        ticksuffix: "×",
        linecolor: "rgba(220, 228, 244, 0.6)"
      },
      bargap: 0.25,
      bargroupgap: 0.1
    };
    
    // Debug logging
    console.log('[plotRevenueChart] Rendering chart:', {
      tracesCount: traces.length,
      xValuesLength: xValues.length,
      yValuesLength: yValues.length,
      hasData: xValues.length > 0 && yValues.length > 0,
      xValues: xValues.slice(0, 5),
      yValues: yValues.slice(0, 5),
      traces: traces.map(t => ({ 
        type: t.type, 
        name: t.name,
        xLength: t.x?.length, 
        yLength: t.y?.length,
        xSample: t.x?.slice(0, 3),
        ySample: t.y?.slice(0, 3),
        yMin: t.y ? Math.min(...t.y.filter(v => Number.isFinite(v))) : null,
        yMax: t.y ? Math.max(...t.y.filter(v => Number.isFinite(v))) : null
      }))
    });
    
    // Ensure we have valid traces with data
    const validTraces = traces.filter(trace => {
      const hasX = Array.isArray(trace.x) && trace.x.length > 0;
      const hasY = Array.isArray(trace.y) && trace.y.length > 0;
      return hasX && hasY;
    });
    
    if (validTraces.length === 0) {
      console.warn('[plotRevenueChart] No valid traces to render');
      node.textContent = "No valid revenue data to display.";
      return;
    }
    
    try {
      // Ensure node is visible and has dimensions
      node.style.display = 'block';
      node.style.visibility = 'visible';
      node.style.opacity = '1';
      if (node.offsetHeight === 0) {
        node.style.minHeight = '240px';
        node.style.height = '240px';
      }
      Plotly.newPlot(node, sanitizePlotlyData(validTraces), sanitizePlotlyData(layout), CONFIG);
      // Resize chart to ensure it's visible
      setTimeout(() => {
        Plotly.Plots.resize(node);
      }, 100);
      console.log('[plotRevenueChart] Chart rendered successfully with', validTraces.length, 'traces');
    } catch (error) {
      console.error('[plotRevenueChart] Error rendering chart:', error);
      node.textContent = `Chart error: ${error.message}`;
    }
  }

  function plotEbitdaChart(data) {
    const node = scopedQuery("cfi-ebitda");
    if (!node) return;
    if (!window.Plotly) {
      node.textContent = "Chart library loading...";
      return;
    }
    if (!data || !Array.isArray(data.Year) || !Array.isArray(data.EBITDA)) {
      node.textContent = "No EBITDA data.";
      return;
    }
    
    const ebitdaSeries = buildNumericSeries(data.Year, data.EBITDA, "EBITDA");
    if (!ebitdaSeries.length) {
      node.textContent = "No EBITDA data.";
      return;
    }
    const xValues = ebitdaSeries.map((point) => point.x);
    const yValues = ebitdaSeries.map((point) => point.y).filter(v => Number.isFinite(v));
    
    if (yValues.length === 0) {
      node.textContent = "No valid EBITDA data.";
      return;
    }
    
    const denominator = Math.max(yValues.length - 1, 1);
    const barColors = yValues.map((_, idx) => {
      const ratio = denominator === 0 ? 0 : idx / denominator;
      return `rgba(16, 185, 129, ${0.6 + ratio * 0.4})`;
    });
    
    const traces = [
      {
        type: "bar",
        x: xValues,
        y: yValues,
        name: "EBITDA ($M)",
        marker: { 
          color: barColors,
          line: { color: COLORS.green, width: 1.5 }
        },
        hovertemplate: "<b>FY %{x}</b><br>EBITDA: $%{y:,.0f}M<extra></extra>"
      }
    ];
    const multiplesSource = data.EV_EBITDA || data["EV/EBITDA"] || [];
    const multiplesSeries = buildNumericSeries(data.Year, multiplesSource, "EV/EBITDA");
    if (multiplesSeries.length) {
      const multipleYValues = multiplesSeries.map((point) => point.y).filter(v => Number.isFinite(v));
      if (multipleYValues.length > 0) {
        traces.push({
          type: "scatter",
          mode: "lines+markers",
          x: multiplesSeries.map((point) => point.x),
          y: multipleYValues,
          name: "EV/EBITDA (×)",
          yaxis: "y2",
          line: { color: COLORS.orange, width: 3, shape: "spline" },
          marker: { 
            size: 8, 
            color: COLORS.orangeLight,
            line: { color: COLORS.orange, width: 2 }
          },
          connectgaps: false,
          hovertemplate: "<b>FY %{x}</b><br>EV/EBITDA: %{y:.2f}×<extra></extra>"
        });
      }
    }
    const layout = {
      ...BASE_LAYOUT,
      yaxis: { ...BASE_LAYOUT.yaxis, title: "EBITDA ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { 
        title: "EV/EBITDA (×)", 
        overlaying: "y", 
        side: "right", 
        showgrid: false, 
        ticksuffix: "×",
        linecolor: "rgba(220, 228, 244, 0.6)"
      },
      bargap: 0.25,
      bargroupgap: 0.1
    };
    
    // Debug logging
    console.log('[plotEbitdaChart] Rendering chart:', {
      tracesCount: traces.length,
      xValuesLength: xValues.length,
      yValuesLength: yValues.length,
      hasData: xValues.length > 0 && yValues.length > 0,
      xValues: xValues.slice(0, 5),
      yValues: yValues.slice(0, 5),
      traces: traces.map(t => ({ 
        type: t.type, 
        name: t.name,
        xLength: t.x?.length, 
        yLength: t.y?.length,
        xSample: t.x?.slice(0, 3),
        ySample: t.y?.slice(0, 3),
        yMin: t.y ? Math.min(...t.y.filter(v => Number.isFinite(v))) : null,
        yMax: t.y ? Math.max(...t.y.filter(v => Number.isFinite(v))) : null
      }))
    });
    
    // Ensure we have valid traces with data
    const validTraces = traces.filter(trace => {
      const hasX = Array.isArray(trace.x) && trace.x.length > 0;
      const hasY = Array.isArray(trace.y) && trace.y.length > 0;
      return hasX && hasY;
    });
    
    if (validTraces.length === 0) {
      console.warn('[plotEbitdaChart] No valid traces to render');
      node.textContent = "No valid EBITDA data to display.";
      return;
    }
    
    try {
      // Ensure node is visible and has dimensions
      node.style.display = 'block';
      node.style.visibility = 'visible';
      node.style.opacity = '1';
      if (node.offsetHeight === 0) {
        node.style.minHeight = '240px';
        node.style.height = '240px';
      }
      Plotly.newPlot(node, sanitizePlotlyData(validTraces), sanitizePlotlyData(layout), CONFIG);
      // Resize chart to ensure it's visible
      setTimeout(() => {
        Plotly.Plots.resize(node);
      }, 100);
      console.log('[plotEbitdaChart] Chart rendered successfully with', validTraces.length, 'traces');
    } catch (error) {
      console.error('[plotEbitdaChart] Error rendering chart:', error);
      node.textContent = `Chart error: ${error.message}`;
    }
  }

  function plotForecastChart(data) {
    const node = scopedQuery("cfi-forecast");
    if (!node) return;
    if (!window.Plotly) {
      node.textContent = "Chart library loading...";
      return;
    }
    if (!data || !Array.isArray(data.Year)) {
      node.textContent = "No forecast data.";
      return;
    }
    const years = data.Year.slice();
    const traces = [];
    const scenarios = [
      ["Bull", COLORS.green, "solid", "rgba(16, 185, 129, 0.15)"],
      ["Base", COLORS.accent, "solid", "rgba(28, 126, 214, 0.15)"],
      ["Bear", COLORS.red, "solid", "rgba(239, 68, 68, 0.15)"]
    ];
    
    scenarios.forEach(([key, color, dash, fillColor]) => {
      if (Array.isArray(data[key])) {
        // Sanitize values and filter out invalid entries
        const yValues = sanitizeNumericArray(years.map((year, idx) => {
          const raw = data[key][idx];
          const numeric = toNumericValue(raw, `${key} ${year ?? idx}`);
          return numeric;
        }));
        
        // Check if we have at least some valid data
        const validCount = yValues.filter(v => v !== null && Number.isFinite(v)).length;
        if (validCount === 0) {
          return;
        }
        
        traces.push({
          type: "scatter",
          mode: "lines",
          x: years,
          y: yValues,
          name: key,
          line: { color, dash, width: 3, shape: "spline", smoothing: 0.8 },
          fill: 'tonexty',
          fillcolor: fillColor,
          connectgaps: false, // Don't connect across null values
          hovertemplate: "<b>%{fullData.name} Case</b><br>FY %{x}: $%{y:,.0f}<extra></extra>"
        });
      }
    });
    
    if (!traces.length) {
      node.textContent = "No forecast data.";
      return;
    }
    
    // Remove fill from first trace
    if (traces.length > 0) traces[0].fill = 'none';
    
    const layout = {
      ...BASE_LAYOUT,
      yaxis: { 
        ...BASE_LAYOUT.yaxis, 
        title: "Share Price ($)", 
        tickprefix: "$", 
        separatethousands: true,
        rangemode: "tozero"
      },
      showlegend: true
    };
    
    // Debug logging
    console.log('[plotForecastChart] Rendering chart:', {
      tracesCount: traces.length,
      hasData: traces.length > 0,
      traces: traces.map(t => ({ 
        name: t.name, 
        type: t.type, 
        xLength: t.x?.length, 
        yLength: t.y?.length,
        xSample: t.x?.slice(0, 3),
        ySample: t.y?.slice(0, 3),
        yMin: t.y ? Math.min(...t.y.filter(v => v !== null && Number.isFinite(v))) : null,
        yMax: t.y ? Math.max(...t.y.filter(v => v !== null && Number.isFinite(v))) : null
      }))
    });
    
    // Ensure we have valid traces with data
    const validTraces = traces.filter(trace => {
      const hasX = Array.isArray(trace.x) && trace.x.length > 0;
      const hasY = Array.isArray(trace.y) && trace.y.length > 0;
      // Check if y array has at least one finite number
      const hasValidY = hasY && trace.y.some(v => v !== null && Number.isFinite(v));
      return hasX && hasValidY;
    });
    
    if (validTraces.length === 0) {
      console.warn('[plotForecastChart] No valid traces to render');
      node.textContent = "No valid forecast data to display.";
      return;
    }
    
    try {
      // Ensure node is visible and has dimensions
      node.style.display = 'block';
      node.style.visibility = 'visible';
      node.style.opacity = '1';
      if (node.offsetHeight === 0) {
        node.style.minHeight = '240px';
        node.style.height = '240px';
      }
      Plotly.newPlot(node, sanitizePlotlyData(validTraces), sanitizePlotlyData(layout), CONFIG);
      // Resize chart to ensure it's visible
      setTimeout(() => {
        Plotly.Plots.resize(node);
      }, 100);
      console.log('[plotForecastChart] Chart rendered successfully with', validTraces.length, 'traces');
    } catch (error) {
      console.error('[plotForecastChart] Error rendering chart:', error);
      node.textContent = `Chart error: ${error.message}`;
    }
  }

  function plotValuationBar(data, meta = {}) {
    const node = scopedQuery("cfi-valbar");
    if (!node) return;
    if (!window.Plotly) {
      node.textContent = "Chart library loading...";
      return;
    }
    if (!data || !Array.isArray(data.Case) || !Array.isArray(data.Value)) {
      node.textContent = "No valuation data.";
      return;
    }
    
    // Sanitize data to remove NaN/Inf values before processing
    const sanitizedData = {
      Case: [],
      Value: []
    };
    
    for (let i = 0; i < Math.min(data.Case.length, data.Value.length); i++) {
      const val = data.Value[i];
      const numVal = Number(val);
      // Only include valid finite numbers
      if (Number.isFinite(numVal) && numVal !== null && numVal !== undefined) {
        sanitizedData.Case.push(data.Case[i]);
        sanitizedData.Value.push(numVal);
      }
    }
    
    if (sanitizedData.Case.length === 0) {
      node.textContent = "No valid valuation data.";
      return;
    }
    
    const entries = buildNumericSeries(sanitizedData.Case, sanitizedData.Value, "Valuation");
    if (!entries.length) {
      node.textContent = "No valuation data.";
      return;
    }
    
    // Filter entries to only include those with valid finite y values
    // Keep x and y paired together
    const validEntries = entries.filter(entry => Number.isFinite(entry.y));
    
    if (validEntries.length === 0) {
      node.textContent = "No valid valuation values.";
      return;
    }
    
    const xValues = validEntries.map((entry) => entry.x);
    const yValues = validEntries.map((entry) => entry.y);
    
    // Create color scheme for different valuation methods
    const colorMap = {
      "DCF": COLORS.accent,
      "Comps": COLORS.green,
      "52-Week": COLORS.orange,
      "Bull": COLORS.greenLight,
      "Bear": COLORS.red
    };
    
    const barColors = xValues.map((caseName) => {
      for (const [key, color] of Object.entries(colorMap)) {
        if (caseName && caseName.includes(key)) return color;
      }
      return COLORS.navy;
    });
    
    const traces = [
      {
        type: "bar",
        x: xValues,
        y: yValues,
        name: "Valuation",
        marker: { 
          color: barColors,
          line: { color: COLORS.navyDark, width: 1.5 },
          opacity: 0.85
        },
        text: yValues.map((value) => formatMoney(value)),
        textposition: "outside",
        textfont: { size: 11, weight: 600 },
        cliponaxis: false,
        hovertemplate: "<b>%{x}</b><br>Value: $%{y:,.0f}<extra></extra>"
      }
    ];
    
    // Add reference lines only if they're valid
    const currentValue = toNumericValue(meta?.current, "Current Price");
    const averageValue = toNumericValue(meta?.average, "Average");
    const referenceLines = [
      ["Current Price", currentValue, COLORS.slate, "dot"],
      ["Average", averageValue, COLORS.orange, "dash"]
    ].filter(([, value]) => value !== null && Number.isFinite(value));
    
    referenceLines.forEach(([label, value, color, dash]) => {
      traces.push({
        type: "scatter",
        mode: "lines",
        x: xValues,
        y: xValues.map(() => value),
        name: label,
        line: { color, dash, width: 2.5 },
        hovertemplate: `<b>${label}</b><br>${formatMoney(value)}<extra></extra>`
      });
    });
    
    const layout = {
      ...BASE_LAYOUT,
      margin: { l: 52, r: 32, t: 32, b: 80 },
      yaxis: { 
        ...BASE_LAYOUT.yaxis, 
        title: "$/Share", 
        tickprefix: "$", 
        separatethousands: true 
      },
      xaxis: {
        ...BASE_LAYOUT.xaxis,
        tickangle: -35
      },
      bargap: 0.28,
      showlegend: true
    };
    
    // Final sanitization pass to catch any remaining NaN values
    const sanitizedTraces = sanitizePlotlyData(traces);
    const sanitizedLayout = sanitizePlotlyData(layout);
    
    // Debug logging
    console.log('[plotValuationBar] Rendering chart:', {
      tracesCount: sanitizedTraces.length,
      xValuesLength: xValues.length,
      yValuesLength: yValues.length,
      hasData: xValues.length > 0 && yValues.length > 0,
      xValues: xValues.slice(0, 5),
      yValues: yValues.slice(0, 5),
      traces: sanitizedTraces.map(t => ({ 
        name: t.name, 
        type: t.type, 
        xLength: t.x?.length, 
        yLength: t.y?.length,
        xSample: t.x?.slice(0, 3),
        ySample: t.y?.slice(0, 3),
        yMin: t.y ? Math.min(...t.y.filter(v => Number.isFinite(v))) : null,
        yMax: t.y ? Math.max(...t.y.filter(v => Number.isFinite(v))) : null
      }))
    });
    
    // Ensure we have valid traces with data
    const validTraces = sanitizedTraces.filter(trace => {
      const hasX = Array.isArray(trace.x) && trace.x.length > 0;
      const hasY = Array.isArray(trace.y) && trace.y.length > 0;
      return hasX && hasY;
    });
    
    if (validTraces.length === 0) {
      console.warn('[plotValuationBar] No valid traces to render');
      node.textContent = "No valid valuation data to display.";
      return;
    }
    
    try {
      // Ensure node is visible and has dimensions
      node.style.display = 'block';
      node.style.visibility = 'visible';
      node.style.opacity = '1';
      if (node.offsetHeight === 0) {
        node.style.minHeight = '240px';
        node.style.height = '240px';
      }
      Plotly.newPlot(node, validTraces, sanitizedLayout, CONFIG);
      // Resize chart to ensure it's visible
      setTimeout(() => {
        Plotly.Plots.resize(node);
      }, 100);
      console.log('[plotValuationBar] Chart rendered successfully with', validTraces.length, 'traces');
    } catch (error) {
      console.error('[plotValuationBar] Error rendering chart:', error);
      node.textContent = `Chart error: ${error.message}`;
    }
  }

  function renderMeta(meta = {}) {
    const company = meta.company || "";
    const ticker = meta.ticker ? String(meta.ticker).toUpperCase() : "";
    const brand = meta.brand || company.split(" ")[0] || ticker || "";

    const brandNode = scopedQuery("cfi-brand");
    if (brandNode) brandNode.textContent = brand ? brand.toLowerCase() : "";

    const companyNode = scopedQuery("cfi-company");
    if (companyNode) companyNode.textContent = company;

    const tickerNode = scopedQuery("cfi-ticker");
    if (tickerNode) {
      const explicit = meta.ticker_label || meta.ticker_display;
      if (explicit) tickerNode.textContent = explicit;
      else {
        const exchange = meta.exchange ? String(meta.exchange).toUpperCase() : "";
        const label = [exchange, ticker].filter(Boolean).join(": ");
        tickerNode.textContent = label || ticker;
      }
    }

    const recNode = scopedQuery("cfi-rec");
    if (recNode) recNode.textContent = meta.recommendation || "—";

    const targetNode = scopedQuery("cfi-target");
    if (targetNode) targetNode.textContent = isNumber(meta.target_price) ? formatCurrency(meta.target_price) : meta.target_price || "—";

    const scenarioNode = scopedQuery("cfi-scenario");
    if (scenarioNode) scenarioNode.textContent = meta.scenario || meta.live_scenario || meta.case || "Consensus";

    const dateNode = scopedQuery("cfi-date");
    if (dateNode) dateNode.textContent = meta.date || "";

    const websiteNode = scopedQuery("cfi-website");
    if (websiteNode) {
      const value = meta.website || meta.url || "";
      websiteNode.textContent = value;
      websiteNode.style.display = value ? "" : "none";
    }

    const tagNode = scopedQuery("cfi-report-tag");
    if (tagNode) {
      const value = meta.report_tag || meta.report || "";
      tagNode.textContent = value;
      tagNode.style.display = value ? "" : "none";
    }
  }

  // ============================================================
  // DASHBOARD ENHANCEMENTS - JavaScript Functionality
  // ============================================================
  
  // KPI Categories for grouping (Improvement #8)
  const KPI_CATEGORIES = {
    growth: {
      title: "Growth & Performance",
      icon: "📈",
      metrics: ["revenue_cagr", "revenue_cagr_3y", "eps_cagr", "eps_cagr_3y", "ebitda_growth"]
    },
    profitability: {
      title: "Profitability Margins",
      icon: "💰",
      metrics: ["ebitda_margin", "gross_margin", "operating_margin", "net_margin", "profit_margin", "free_cash_flow_margin"]
    },
    liquidity: {
      title: "Liquidity & Solvency",
      icon: "🏦",
      metrics: ["current_ratio", "quick_ratio", "debt_to_equity", "interest_coverage", "cash_conversion"]
    },
    efficiency: {
      title: "Returns & Efficiency",
      icon: "🎯",
      metrics: ["return_on_assets", "return_on_equity", "return_on_invested_capital", "asset_turnover"]
    },
    valuation: {
      title: "Valuation Multiples",
      icon: "💎",
      metrics: ["pe_ratio", "ev_ebitda", "pb_ratio", "peg_ratio"]
    },
    shareholder: {
      title: "Shareholder Returns",
      icon: "💸",
      metrics: ["tsr", "dividend_yield", "share_buyback_intensity"]
    }
  };

  // Improvement #8: Enhanced KPI rendering with categories
  function renderKpiSummaryGrouped(containerId, items) {
    const container = scopedQuery(containerId);
    if (!container) return;
    
    // Clear skeleton
    container.innerHTML = "";
    
    if (!Array.isArray(items) || items.length === 0) {
      container.innerHTML = '<p class="cfi-kpi-empty">No KPIs available</p>';
      return;
    }
    
    console.log("📊 Rendering KPIs:", items.length, "items");
    
    // Group KPIs by category
    const grouped = {};
    const uncategorized = [];
    
    items.forEach(item => {
      // Extract metric ID - try multiple field names
      let metricId = item.id || item.metric || item.name || "";
      
      // If still no ID, try to derive from label
      if (!metricId && item.label) {
        metricId = item.label.toLowerCase()
          .replace(/ cagr/g, "_cagr")
          .replace(/ /g, "_")
          .replace(/[()]/g, "");
      }
      
      // Add ID back to item for later use
      if (!item.id && !item.metric) {
        item.id = metricId;
      }
      
      let found = false;
      
      for (const [catKey, catDef] of Object.entries(KPI_CATEGORIES)) {
        if (catDef.metrics.includes(metricId)) {
          if (!grouped[catKey]) grouped[catKey] = [];
          grouped[catKey].push(item);
          found = true;
          break;
        }
      }
      
      if (!found) {
        uncategorized.push(item);
      }
    });
    
    console.log("📂 Grouped:", Object.keys(grouped).length, "categories, Uncategorized:", uncategorized.length);
    
    // Render each category
    Object.entries(grouped).forEach(([catKey, catItems]) => {
      const catDef = KPI_CATEGORIES[catKey];
      const catDiv = document.createElement("div");
      catDiv.className = "kpi-category collapsed"; // Start collapsed
      catDiv.dataset.category = catKey;
      
      const header = document.createElement("div");
      header.className = "kpi-category-header";
      header.innerHTML = `
        <div class="kpi-category-title">
          <span class="kpi-category-icon">${catDef.icon}</span>
          <span>${catDef.title}</span>
          <span style="color: var(--muted); font-size: 11px; font-weight: 500;">(${catItems.length})</span>
        </div>
        <div class="kpi-category-toggle">▼</div>
      `;
      
      header.addEventListener("click", () => {
        catDiv.classList.toggle("collapsed");
      });
      
      const content = document.createElement("div");
      content.className = "kpi-category-content";
      
      catItems.forEach(item => {
        const kpiEl = createKpiItem(item);
        content.appendChild(kpiEl);
      });
      
      catDiv.appendChild(header);
      catDiv.appendChild(content);
      container.appendChild(catDiv);
    });
    
    // ALWAYS show uncategorized section - it will contain all metrics if categorization fails
    if (uncategorized.length > 0 || Object.keys(grouped).length === 0) {
      console.log("📊 Uncategorized metrics:", uncategorized.length);
      uncategorized.forEach(item => {
        console.log("  -", item.label || item.id, "ID:", item.id || item.metric);
      });
      
      const catDiv = document.createElement("div");
      catDiv.className = "kpi-category collapsed"; // Start collapsed
      catDiv.innerHTML = `
        <div class="kpi-category-header">
          <div class="kpi-category-title">
            <span class="kpi-category-icon">📊</span>
            <span>Other Metrics</span>
            <span style="color: var(--muted); font-size: 11px; font-weight: 500;">(${uncategorized.length})</span>
          </div>
          <div class="kpi-category-toggle">▼</div>
        </div>
        <div class="kpi-category-content"></div>
      `;
      
      const content = catDiv.querySelector(".kpi-category-content");
      uncategorized.forEach(item => {
        const kpiEl = createKpiItem(item);
        content.appendChild(kpiEl);
      });
      
      container.appendChild(catDiv);
    }
    
    // If no data at all, show empty state
    if (Object.keys(grouped).length === 0 && uncategorized.length === 0) {
      container.innerHTML = '<p class="cfi-kpi-empty">No KPIs available. Data may still be loading.</p>';
    }
  }
  
  function createKpiItem(item) {
    const div = document.createElement("div");
    div.className = "cfi-kpi-item";
    div.dataset.kpiId = item.id || item.metric || "";
    div.dataset.kpiLabel = (item.label || "").toLowerCase();
    
    const label = document.createElement("div");
    label.className = "cfi-kpi-label";
    label.textContent = item.label || "";
    
    const value = document.createElement("div");
    value.className = "cfi-kpi-value";
    const formatted = formatKpiValue(item.value, item.type);
    value.textContent = formatted;
    
    // Add positive/negative class
    if (isNumber(item.value)) {
      const numVal = Number(item.value);
      if (numVal > 0 && (item.type === "percent" || item.label.toLowerCase().includes("growth"))) {
        value.classList.add("positive");
      } else if (numVal < 0) {
        value.classList.add("negative");
      }
    }
    
    // Add metadata with trend
    const meta = document.createElement("div");
    meta.className = "cfi-kpi-meta";
    if (item.period) {
      meta.textContent = item.period;
    }
    
    div.appendChild(label);
    div.appendChild(value);
    div.appendChild(meta);
    
    return div;
  }
  
  // Improvement #2: Search functionality
  function setupSearch() {
    const searchInput = scopedQuery("dashboard-search");
    if (!searchInput) return;
    
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      const kpiItems = scopedSelectAll(".cfi-kpi-item");
      const categories = scopedSelectAll(".kpi-category");
      
      kpiItems.forEach(item => {
        const label = item.dataset.kpiLabel || "";
        const matches = !query || label.includes(query);
        item.style.display = matches ? "" : "none";
      });
      
      // Show/hide categories based on visible items
      categories.forEach(cat => {
        const visibleItems = cat.querySelectorAll(".cfi-kpi-item:not([style*='display: none'])");
        cat.style.display = visibleItems.length > 0 ? "" : "none";
      });
    });
  }
  
  // Improvement #1: Data freshness tracking
  function updateDataFreshness(timestamp) {
    const freshnessEl = scopedQuery("data-freshness");
    if (!freshnessEl) return;
    
    const dot = freshnessEl.querySelector(".freshness-dot");
    const text = freshnessEl.querySelector(".freshness-text");
    if (!dot || !text) return;
    
    const now = Date.now();
    const dataTime = timestamp ? new Date(timestamp).getTime() : now;
    const ageMs = now - dataTime;
    const ageMin = Math.floor(ageMs / 60000);
    
    if (ageMin < 5) {
      dot.className = "freshness-dot fresh";
      text.textContent = "Updated just now";
    } else if (ageMin < 60) {
      dot.className = "freshness-dot recent";
      text.textContent = `Updated ${ageMin} min ago`;
    } else if (ageMin < 1440) {
      const ageHr = Math.floor(ageMin / 60);
      dot.className = "freshness-dot recent";
      text.textContent = `Updated ${ageHr}h ago`;
    } else {
      const ageDays = Math.floor(ageMin / 1440);
      dot.className = "freshness-dot stale";
      text.textContent = `Updated ${ageDays}d ago`;
    }
  }
  
  // Improvement #1: Refresh handler
  function setupRefreshButton() {
    const refreshBtn = scopedQuery("refresh-dashboard");
    if (!refreshBtn) return;
    
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.style.opacity = "0.6";
      
      try {
        const payload = window.__cfiDashboardLastPayload;
        if (payload && payload.meta && payload.meta.ticker) {
          // Trigger re-fetch
          if (window.CFI && typeof window.CFI.render === "function") {
            window.CFI.render(payload);
          }
        }
        updateDataFreshness(new Date());
      } catch (error) {
        console.error("Refresh failed:", error);
      } finally {
        setTimeout(() => {
          refreshBtn.disabled = false;
          refreshBtn.style.opacity = "1";
        }, 1000);
      }
    });
  }
  
  // Improvement #10: Export preview modal
  function setupExportPreview() {
    const exportButtons = scopedSelectAll(".export-button");
    const modal = document.getElementById("export-preview-modal");
    const confirmBtn = document.getElementById("confirm-export-btn");
    
    if (!modal || !confirmBtn) return;
    
    let pendingExport = null;
    
    exportButtons.forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const format = btn.dataset.exportFormat || "pdf";
        const payload = window.__cfiDashboardLastPayload;
        
        if (!payload) return;
        
        // Show modal with preview
        const previewFormat = scopedQuery("preview-format");
        const previewCompany = scopedQuery("preview-company");
        if (previewFormat) previewFormat.textContent = format.toUpperCase();
        if (previewCompany) previewCompany.textContent = 
          payload.meta?.company || payload.meta?.ticker || "Unknown";
        
        modal.style.display = "flex";
        
        pendingExport = { format, btn, payload };
      });
    });
    
    confirmBtn.addEventListener("click", () => {
      if (!pendingExport) {
        alert("Nothing to export yet.");
        return;
      }
      
      modal.style.display = "none";
      
      // Trigger actual export using triggerExport function
      const { format, btn, payload } = pendingExport;
      triggerExport(btn, format, payload).catch(error => {
        console.error("Export error:", error);
      });
      
      pendingExport = null;
    });
  }
  
  // Improvement #9: Dashboard switcher
  function setupDashboardSwitcher() {
    const switcher = scopedQuery("dashboard-switcher");
    if (!switcher) return;
    
    switcher.addEventListener("change", (e) => {
      const viewType = e.target.value;
      const payload = window.__cfiDashboardLastPayload;
      
      if (!payload) return;
      
      // Trigger view change
      if (window.showCfiDashboard && viewType === "cfi-classic") {
        window.showCfiDashboard({ payload });
      } else if (window.showCfiCompareDashboard && viewType === "cfi-compare") {
        window.showCfiCompareDashboard({ payload });
      } else if (window.showCfiDenseDashboard && viewType === "cfi-dense") {
        window.showCfiDenseDashboard({ payload });
      }
    });
  }

  window.CFI = {
    render(payload) {
      if (!payload) return;
      payload = deepSanitize(payload);
      
      // Check if this is a multi-ticker dashboard and hide toolbar if so
      const scope = resolveScope();
      const isMultiTicker = scope.dataset && scope.dataset.multiTicker === "true";
      if (isMultiTicker) {
        const toolbar = scopedSelect(".dashboard-toolbar");
        if (toolbar) {
          toolbar.style.display = "none";
        }
      }
      
      const meta = { ...(payload.meta || {}) };
      const priceTicker = payload.price?.Ticker || payload.price?.ticker || payload.price?.symbol;
      if (!meta.ticker_label && priceTicker) meta.ticker_label = String(priceTicker);
      if (!meta.ticker && typeof priceTicker === "string" && priceTicker.includes(":")) {
        const [exchangePart, tickerPart] = priceTicker.split(":").map((part) => part.trim());
        meta.exchange = meta.exchange || exchangePart;
        meta.ticker = meta.ticker || tickerPart;
      }
      renderMeta(meta);
      const priceSource = payload.price || payload.overview?.price || payload.overview || null;
      renderPairsTable("cfi-price-table", priceSource);
      const keyStatsSource = payload.key_stats || payload.overview?.key_stats || null;
      renderPairsTable("cfi-stat-table", keyStatsSource);
      const marketSource = payload.market_data || payload.overview?.market_data || null;
      renderPairsTable("cfi-market-table", marketSource);
      renderValuationTable("cfi-valuation-table", payload.valuation_table || []);
      renderValuationNotes("cfi-valuation-notes", payload.valuation_data?.notes || payload.valuation_notes || []);
      renderKeyFinancials("cfi-keyfin", payload.key_financials || {});
      
      // Use grouped KPI rendering (Improvement #8)
      const kpiItems = payload.kpi_summary || payload.kpis || [];
      renderKpiSummaryGrouped("cfi-kpi", kpiItems);
      
      window.__cfiDashboardLastPayload = payload;
      setupDrilldownListeners();
      setupTrendExplorer(payload);
      setupPeerControls(payload);
      window.__cfiDashboardInteractions = payload.interactions || null;
      window.__cfiDashboardPeerConfig = payload.peer_config || null;
      window.__cfiDashboardSeries = window.__cfiDashboardSeries || {};
      window.__cfiDashboardSeries.kpi = payload.kpi_series || {};
      
      // Render data sources section
      console.log('[CFI] Checking sources...', {
        sourcesCount: payload.sources?.length || 0,
        hasEnhancements: !!window.DashboardEnhancements
      });
      
      if (payload.sources && payload.sources.length > 0) {
        if (window.DashboardEnhancements && window.DashboardEnhancements.renderDataSources) {
          window.DashboardEnhancements.renderDataSources(payload.sources);
          setupSourcesToggle();
          console.log('[CFI] ✅ Sources rendered successfully');
        } else {
          console.error('[CFI] ❌ DashboardEnhancements.renderDataSources not available');
        }
      } else {
        console.warn('[CFI] ⚠️ No sources in payload');
      }
      
      attachExportHandlers(payload);
      const charts = payload.charts || {};
      
      // Debug logging
      console.log('[CFI Dashboard] Charts data:', {
        hasRevenueEv: !!charts.revenue_ev,
        hasEbitdaEv: !!charts.ebitda_ev,
        hasValuationBar: !!charts.valuation_bar,
        hasForecast: !!charts.forecast,
        plotlyLoaded: !!window.Plotly,
        revenueEvData: charts.revenue_ev ? {
          hasYear: Array.isArray(charts.revenue_ev.Year),
          yearCount: charts.revenue_ev.Year?.length || 0,
          hasRevenue: Array.isArray(charts.revenue_ev.Revenue),
          revenueCount: charts.revenue_ev.Revenue?.length || 0,
          sampleRevenue: charts.revenue_ev.Revenue?.slice(0, 3),
          hasValidRevenue: charts.revenue_ev.Revenue?.some(v => v !== null && v !== undefined && Number.isFinite(v))
        } : null,
        ebitdaEvData: charts.ebitda_ev ? {
          hasYear: Array.isArray(charts.ebitda_ev.Year),
          yearCount: charts.ebitda_ev.Year?.length || 0,
          hasEbitda: Array.isArray(charts.ebitda_ev.EBITDA),
          ebitdaCount: charts.ebitda_ev.EBITDA?.length || 0,
          sampleEbitda: charts.ebitda_ev.EBITDA?.slice(0, 3),
          hasValidEbitda: charts.ebitda_ev.EBITDA?.some(v => v !== null && v !== undefined && Number.isFinite(v))
        } : null,
        forecastData: charts.forecast ? {
          hasYear: Array.isArray(charts.forecast.Year),
          yearCount: charts.forecast.Year?.length || 0,
          hasBull: Array.isArray(charts.forecast.Bull),
          hasBase: Array.isArray(charts.forecast.Base),
          hasBear: Array.isArray(charts.forecast.Bear)
        } : null,
        valuationBarData: charts.valuation_bar ? {
          hasCase: Array.isArray(charts.valuation_bar.Case),
          caseCount: charts.valuation_bar.Case?.length || 0,
          hasValue: Array.isArray(charts.valuation_bar.Value),
          valueCount: charts.valuation_bar.Value?.length || 0,
          hasValidValue: charts.valuation_bar.Value?.some(v => v !== null && v !== undefined && Number.isFinite(v))
        } : null
      });
      
      // Function to render charts with proper checks
      const renderCharts = () => {
        // Check if chart containers exist
        const revNode = scopedQuery("cfi-rev");
        const ebitdaNode = scopedQuery("cfi-ebitda");
        const forecastNode = scopedQuery("cfi-forecast");
        const valbarNode = scopedQuery("cfi-valbar");
        
        console.log('[CFI Dashboard] Chart containers:', {
          revNode: !!revNode,
          ebitdaNode: !!ebitdaNode,
          forecastNode: !!forecastNode,
          valbarNode: !!valbarNode
        });
        
        if (!revNode || !ebitdaNode || !forecastNode || !valbarNode) {
          console.warn('[CFI Dashboard] Chart containers not found, waiting for DOM...');
          return false;
        }
        
        if (!window.Plotly) {
          console.warn('[CFI Dashboard] Plotly not loaded yet');
          return false;
        }
        
        // Ensure chart panels are visible
        const revPanel = scopedSelect('[data-area="rev"]');
        const ebitdaPanel = scopedSelect('[data-area="ebitda"]');
        const forecastPanel = scopedSelect('[data-area="pricechart"]');
        const valbarPanel = scopedSelect('[data-area="valbar"]');
        
        if (revPanel) revPanel.style.display = 'flex';
        if (ebitdaPanel) ebitdaPanel.style.display = 'flex';
        if (forecastPanel) forecastPanel.style.display = 'flex';
        if (valbarPanel) valbarPanel.style.display = 'flex';
        
        // All checks passed, render charts
        console.log('[CFI Dashboard] Rendering charts...');
        plotRevenueChart(charts.revenue_ev || null);
        plotEbitdaChart(charts.ebitda_ev || null);
        plotValuationBar(charts.valuation_bar || null, payload.valuation_data || {});
        plotForecastChart(charts.forecast || null);
        return true;
      };
      
      // Try to render immediately
      if (!renderCharts()) {
        // If containers don't exist or Plotly isn't loaded, wait and retry
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max
        const checkInterval = setInterval(() => {
          attempts++;
          if (renderCharts() || attempts >= maxAttempts) {
            clearInterval(checkInterval);
            if (attempts >= maxAttempts) {
              console.error('[CFI Dashboard] Failed to render charts after', maxAttempts, 'attempts');
            }
          }
        }, 100);
      }
      
      // Initialize enhancements
      setupSearch();
      setupRefreshButton();
      setupExportPreview();
      setupDashboardSwitcher();
      setupKeyboardShortcuts();
      updateDataFreshness(meta.date || meta.updated_at || new Date());
      
      // Setup collapsible panels after a short delay to ensure DOM is ready
      setTimeout(() => {
        const kpiPanelHeader = scopedQuery("kpi-panel-header");
        const kpiPanelContent = scopedQuery("cfi-kpi");
        const kpiPanel = scopedQuery("kpi-panel");
        const toggleButton = scopedQuery("toggle-kpi-panel");

        if (kpiPanelHeader && kpiPanelContent && toggleButton && kpiPanel) {
          // Load saved state from localStorage
          const savedState = localStorage.getItem('kpiPanelCollapsed');
          if (savedState === 'true') {
            kpiPanelHeader.classList.add('collapsed');
            kpiPanelContent.classList.add('collapsed');
            kpiPanel.classList.add('collapsed');
          }

          // Toggle function
          function toggleKpiPanel() {
            const isCollapsed = kpiPanelHeader.classList.toggle('collapsed');
            kpiPanelContent.classList.toggle('collapsed');
            kpiPanel.classList.toggle('collapsed');
            
            // Save state to localStorage
            localStorage.setItem('kpiPanelCollapsed', isCollapsed);
          }

          // Add click listeners
          kpiPanelHeader.addEventListener('click', toggleKpiPanel);
          toggleButton.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleKpiPanel();
          });

          // Keyboard accessibility
          kpiPanelHeader.setAttribute('tabindex', '0');
          kpiPanelHeader.setAttribute('role', 'button');
          kpiPanelHeader.setAttribute('aria-expanded', !kpiPanelHeader.classList.contains('collapsed'));
          kpiPanelHeader.setAttribute('aria-controls', 'cfi-kpi');
          
          kpiPanelHeader.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleKpiPanel();
              kpiPanelHeader.setAttribute('aria-expanded', !kpiPanelHeader.classList.contains('collapsed'));
            }
          });
        }
      }, 100);
    }
  };
  
  // Keyboard shortcuts for power users
  function setupKeyboardShortcuts() {
    if (window.__cfiKeyboardHandlerAttached) return;
    window.__cfiKeyboardHandlerAttached = true;
    
    // Wire up help button
    const helpBtn = scopedQuery("show-shortcuts");
    if (helpBtn) {
      helpBtn.addEventListener("click", () => {
        const modal = document.getElementById("keyboard-shortcuts-modal");
        if (modal) modal.style.display = "flex";
      });
    }
    
    document.addEventListener("keydown", (e) => {
      // Don't trigger if typing in an input
      if (e.target.matches("input, textarea, select")) return;
      
      // '/' - Focus search
      if (e.key === "/") {
        e.preventDefault();
        const searchInput = scopedQuery("dashboard-search");
        if (searchInput) searchInput.focus();
      }
      
      // 'r' or 'R' - Refresh dashboard
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        const refreshBtn = scopedQuery("refresh-dashboard");
        if (refreshBtn) refreshBtn.click();
      }
      
      // 'e' or 'E' - Open export modal
      if (e.key === "e" || e.key === "E") {
        e.preventDefault();
        const exportBtn = scopedSelectAll(".export-button")[0];
        if (exportBtn) exportBtn.click();
      }
      
      // 'Escape' - Close any open modals
      if (e.key === "Escape") {
        const modal = document.getElementById("export-preview-modal");
        if (modal && modal.style.display === "flex") {
          modal.style.display = "none";
        }
      }
      
      // Numbers 1-6 - Toggle KPI categories
      if (e.key >= "1" && e.key <= "6") {
        const categories = scopedSelectAll(".kpi-category");
        const index = parseInt(e.key) - 1;
        if (categories[index]) {
          categories[index].classList.toggle("collapsed");
        }
      }
      
      // '?' - Show keyboard shortcuts help
      if (e.key === "?") {
        e.preventDefault();
        const modal = document.getElementById("keyboard-shortcuts-modal");      
        if (modal) {
          modal.style.display = "flex";
        }
      }

      // 'd' or 'D' - Toggle dark mode
      if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        const themeToggle = document.getElementById("theme-toggle");
        if (themeToggle) themeToggle.click();
      }
    });
  }

  // ========================================
  //  COMPREHENSIVE NEW FEATURES
  // ========================================

  // State Management & Local Storage
  const DashboardState = {
    theme: localStorage.getItem('cfi-theme') || 'light',
    density: localStorage.getItem('cfi-density') || 'compact',
    currency: localStorage.getItem('cfi-currency') || 'USD',
    searchHistory: JSON.parse(localStorage.getItem('cfi-search-history') || '[]'),
    
    save(key, value) {
      this[key] = value;
      localStorage.setItem(`cfi-${key}`, typeof value === 'object' ? JSON.stringify(value) : value);
    },
    
    get(key) {
      return this[key];
    }
  };

  // Theme Toggle Functionality
  function initThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    // Apply saved theme
    const savedTheme = DashboardState.get('theme');
    document.documentElement.setAttribute('data-theme', savedTheme);

    toggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      DashboardState.save('theme', newTheme);
      
      showNotification('Theme Changed', `Switched to ${newTheme} mode`, 'info');
    });
  }

  // Density Controls
  function initDensityControls() {
    const densityBtns = document.querySelectorAll('.density-btn');
    const root = document.getElementById('cfi-root');
    if (!root) return;

    // Apply saved density
    const savedDensity = DashboardState.get('density');
    root.setAttribute('data-density', savedDensity);

    densityBtns.forEach(btn => {
      const density = btn.getAttribute('data-density');
      if (density === savedDensity) {
        btn.classList.add('active');
      }

      btn.addEventListener('click', () => {
        densityBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        root.setAttribute('data-density', density);
        DashboardState.save('density', density);
        
        showNotification('View Changed', `Switched to ${density} view`, 'info');
      });
    });
  }

  // Currency Selector
  function initCurrencySelector() {
    const currencyBtns = document.querySelectorAll('.currency-btn');
    
    // Apply saved currency
    const savedCurrency = DashboardState.get('currency');
    
    currencyBtns.forEach(btn => {
      const currency = btn.getAttribute('data-currency');
      if (currency === savedCurrency) {
        btn.classList.add('active');
      }

      btn.addEventListener('click', () => {
        currencyBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        DashboardState.save('currency', currency);
        
        showNotification('Currency Changed', `Switched to ${currency}`, 'info');
        
        // In a real implementation, you'd reload data with new currency
        // For now, just show the notification
      });
    });
  }

  // Back to Top Button
  function initBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;

    window.addEventListener('scroll', () => {
      if (window.scrollY > 300) {
        btn.classList.add('visible');
      } else {
        btn.classList.remove('visible');
      }
    });

    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Notification System
  function showNotification(title, message, type = 'info') {
    const toast = document.getElementById('notification-toast');
    const titleEl = document.getElementById('notification-title');
    const messageEl = document.getElementById('notification-message');
    const iconEl = document.getElementById('notification-icon');
    
    if (!toast) return;

    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    // Set icon
    const icons = {
      success: '✓',
      error: '⚠',
      info: 'ℹ',
    };
    iconEl.textContent = icons[type] || 'ℹ';
    
    // Set type class
    toast.className = 'notification-toast visible ' + type;
    
    // Auto-hide after 4 seconds
    setTimeout(() => {
      toast.classList.remove('visible');
    }, 4000);
  }

  // Notification Close Button
  function initNotificationClose() {
    const closeBtn = document.getElementById('notification-close');
    const toast = document.getElementById('notification-toast');
    
    if (closeBtn && toast) {
      closeBtn.addEventListener('click', () => {
        toast.classList.remove('visible');
      });
    }
  }

  // Loading Progress Bar
  function showLoadingProgress() {
    const progress = document.getElementById('loading-progress');
    const bar = document.getElementById('loading-progress-bar');
    
    if (!progress || !bar) return;
    
    progress.classList.add('active');
    bar.classList.add('indeterminate');
  }

  function hideLoadingProgress() {
    const progress = document.getElementById('loading-progress');
    const bar = document.getElementById('loading-progress-bar');
    
    if (!progress || !bar) return;
    
    setTimeout(() => {
      progress.classList.remove('active');
      bar.classList.remove('indeterminate');
    }, 300);
  }

  // Enhanced Search with Fuzzy Matching
  function initEnhancedSearch() {
    const searchInput = document.getElementById('dashboard-search');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        const query = e.target.value.toLowerCase();
        performSearch(query);
      }, 300);
    });
  }

  function performSearch(query) {
    if (!query) {
      clearSearchHighlights();
      return;
    }

    // Save to history
    const history = DashboardState.get('searchHistory');
    if (!history.includes(query)) {
      history.unshift(query);
      if (history.length > 10) history.pop();
      DashboardState.save('searchHistory', history);
    }

    // Fuzzy search through all metric labels
    const allLabels = document.querySelectorAll('.cfi-kpi-label, .cfi-table td:first-child, .overview-table .kv-label');
    let matchCount = 0;

    allLabels.forEach(label => {
      const text = label.textContent.toLowerCase();
      const matches = fuzzyMatch(query, text);
      
      const panel = label.closest('.cfi-panel');
      if (matches) {
        matchCount++;
        if (panel) panel.classList.add('highlight-related');
        label.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
      } else {
        if (panel) panel.classList.remove('highlight-related');
        label.style.backgroundColor = '';
      }
    });

    if (matchCount > 0) {
      showNotification('Search', `Found ${matchCount} matches`, 'info');
    }
  }

  function fuzzyMatch(needle, haystack) {
    const nLen = needle.length;
    const hLen = haystack.length;
    
    if (nLen > hLen) return false;
    if (nLen === hLen) return needle === haystack;
    
    let nIndex = 0;
    let hIndex = 0;
    
    while (nIndex < nLen && hIndex < hLen) {
      if (needle[nIndex] === haystack[hIndex]) {
        nIndex++;
      }
      hIndex++;
    }
    
    return nIndex === nLen;
  }

  function clearSearchHighlights() {
    document.querySelectorAll('.cfi-panel').forEach(panel => {
      panel.classList.remove('highlight-related');
    });
    document.querySelectorAll('.cfi-kpi-label, .cfi-table td:first-child, .overview-table .kv-label').forEach(label => {
      label.style.backgroundColor = '';
    });
  }

  // Sparkline Generation
  function createSparkline(data, container, isPositive = true) {
    if (!data || data.length < 2) return;

    const width = container.offsetWidth;
    const height = 24;
    const padding = 2;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('kpi-sparkline-svg');
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttribute('preserveAspectRatio', 'none');

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((val, i) => {
      const x = (i / (data.length - 1)) * (width - 2 * padding) + padding;
      const y = height - padding - ((val - min) / range) * (height - 2 * padding);
      return { x, y };
    });

    // Area
    const areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const areaD = `M ${points[0].x},${height} ${points.map(p => `L ${p.x},${p.y}`).join(' ')} L ${points[points.length-1].x},${height} Z`;
    areaPath.setAttribute('d', areaD);
    areaPath.classList.add('sparkline-area');
    if (isPositive) areaPath.classList.add('positive');
    else areaPath.classList.add('negative');
    svg.appendChild(areaPath);

    // Line
    const linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const lineD = `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`;
    linePath.setAttribute('d', lineD);
    linePath.classList.add('sparkline-path');
    if (isPositive) linePath.classList.add('positive');
    else linePath.classList.add('negative');
    svg.appendChild(linePath);

    // Last point dot
    const lastPoint = points[points.length - 1];
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.classList.add('sparkline-dot');
    dot.setAttribute('cx', lastPoint.x);
    dot.setAttribute('cy', lastPoint.y);
    dot.setAttribute('r', '3');
    svg.appendChild(dot);

    container.appendChild(svg);
  }

  // Add sparklines to KPI cards
  function addSparklinestoKPIs(kpiSeries) {
    if (!kpiSeries) return;

    Object.keys(kpiSeries).forEach(key => {
      const seriesData = kpiSeries[key];
      if (!seriesData || !seriesData.values) return;

      const kpiItems = document.querySelectorAll('.cfi-kpi-item');
      kpiItems.forEach(item => {
        const label = item.querySelector('.cfi-kpi-label');
        if (!label) return;
        
        const labelText = label.textContent.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const keyText = key.toLowerCase().replace(/[^a-z0-9]/g, '_');
        
        if (labelText.includes(keyText) || keyText.includes(labelText)) {
          const existingSparkline = item.querySelector('.kpi-sparkline');
          if (existingSparkline) return;

          const sparklineContainer = document.createElement('div');
          sparklineContainer.classList.add('kpi-sparkline');
          item.appendChild(sparklineContainer);

          const lastValue = seriesData.values[seriesData.values.length - 1];
          const firstValue = seriesData.values[0];
          const isPositive = lastValue >= firstValue;

          createSparkline(seriesData.values, sparklineContainer, isPositive);
        }
      });
    });
  }

  // URL Deep Linking
  function initDeepLinking() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check for section parameter
    const section = urlParams.get('section');
    if (section) {
      setTimeout(() => {
        const panel = document.querySelector(`[data-area="${section}"]`);
        if (panel) {
          panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
          panel.classList.add('deep-link-active');
          setTimeout(() => panel.classList.remove('deep-link-active'), 6000);
        }
      }, 500);
    }

    // Check for metric parameter
    const metric = urlParams.get('metric');
    if (metric) {
      setTimeout(() => {
        performSearch(metric);
      }, 500);
    }
  }

  // Screenshot functionality
  function initScreenshotMode() {
    // Add keyboard shortcut Ctrl+Shift+S for screenshot
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        captureScreenshot();
      }
    });
  }

  function captureScreenshot() {
    showNotification('Screenshot', 'Screenshot feature requires html2canvas library', 'info');
    // In a real implementation, you would use html2canvas or similar
    // to capture the dashboard and download it as an image
  }

  // Number animation
  function animateNumber(element, start, end, duration = 1000) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    element.classList.add('number-changing');

    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
        current = end;
        clearInterval(timer);
        element.classList.remove('number-changing');
      }
      element.textContent = Math.round(current).toLocaleString();
    }, 16);
  }

  // Cross-panel highlighting
  function initCrossPanelHighlighting() {
    const kpiItems = document.querySelectorAll('.cfi-kpi-item');
    
    kpiItems.forEach(item => {
      item.addEventListener('mouseenter', () => {
        const label = item.querySelector('.cfi-kpi-label');
        if (!label) return;
        
        const metric = label.textContent.toLowerCase();
        
        // Highlight related panels
        document.querySelectorAll('.cfi-table td:first-child').forEach(cell => {
          if (cell.textContent.toLowerCase().includes(metric.split(' ')[0])) {
            const row = cell.closest('tr');
            if (row) row.classList.add('highlight-related');
          }
        });
      });
      
      item.addEventListener('mouseleave', () => {
        document.querySelectorAll('.highlight-related').forEach(el => {
          el.classList.remove('highlight-related');
        });
      });
    });
  }

  // Initialize all new features
  function initAllEnhancements() {
    initThemeToggle();
    initDensityControls();
    initCurrencySelector();
    initBackToTop();
    initNotificationClose();
    initEnhancedSearch();
    initDeepLinking();
    initScreenshotMode();
    initCrossPanelHighlighting();

    // Show welcome notification
    setTimeout(() => {
      showNotification('Dashboard Ready', 'All features loaded successfully', 'success');
    }, 1000);
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllEnhancements);
  } else {
    initAllEnhancements();
  }

  // Render Data Sources Section - Using same citation format as audit drawer
  function renderDataSources(sources) {
    console.log('[renderDataSources] START - Received sources:', sources?.length || 0);
    
    const container = document.getElementById('cfi-sources-grid');
    if (!container) {
      console.error('[renderDataSources] ❌ Container #cfi-sources-grid NOT FOUND in DOM!');
      alert('ERROR: Sources container not found! Check browser console.');
      return;
    }

    console.log('[renderDataSources] ✅ Container found, rendering', sources?.length || 0, 'sources');
    
    // Debug: Check first source structure
    if (sources && sources.length > 0) {
      const first = sources[0];
      console.log('[renderDataSources] First source structure:', {
        hasUrls: !!first.urls,
        hasUrl: !!first.url,
        urlValue: first.urls?.detail || first.urls?.interactive || first.url || 'NONE'
      });
    }

    if (!sources || sources.length === 0) {
      container.innerHTML = `
        <div class="sources-empty">
          <div class="sources-empty-icon">📊</div>
          <p>No data sources available</p>
        </div>
      `;
      return;
    }

    const sourcesHTML = sources.map(source => {
      // Use same structure as citations in app.js (lines 3246-3273, 3521-3550)
      const ticker = source.ticker || '';
      const label = source.label || source.metric || 'Unknown';
      const period = source.period || source.date || 'N/A';
      
      // Format value using same logic as citations
      let displayValue = '';
      if (source.formatted_value) {
        displayValue = source.formatted_value;
      } else if (source.value !== undefined) {
        displayValue = formatSourceValue(source.value, label);
      }
      
      // Use actual SEC filing URLs - support both formats:
      // 1. Nested: source.urls.detail / source.urls.interactive (audit drawer format)
      // 2. Flat: source.url (dashboard_utils.py format)
      const filingUrl = source.urls?.detail || source.urls?.interactive || source.url || null;
      const sourceType = source.source || 'N/A';
      const sourceText = filingUrl ? '📄 View SEC Filing' : sourceType;
      
      // Check if metric has a calculation formula
      const hasCalculation = source.calculation && source.calculation.display;
      
      return `
        <div class="source-item">
          <div class="source-header">
            <span class="source-metric">${ticker ? `${ticker} • ${label}` : label}</span>
            <span class="source-period">${period}</span>
          </div>
          ${displayValue ? `<div class="source-value">${displayValue}</div>` : ''}
          <div class="source-metadata">
            <span class="source-type-badge source-type-${sourceType.toLowerCase()}">${sourceType}</span>
            ${filingUrl ? `
              <a href="${filingUrl}" target="_blank" rel="noopener noreferrer" class="source-link">
                ${sourceText}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
              </a>
            ` : ''}
          </div>
          ${hasCalculation ? `
            <div class="source-calculation">
              <strong>Formula:</strong> ${source.calculation.display}
              ${source.note ? `<div style="font-size: 11px; color: var(--muted); margin-top: 4px;">${source.note}</div>` : ''}
            </div>
          ` : ''}
          ${source.description ? `<div class="source-description">${source.description}</div>` : ''}
        </div>
      `;
    }).join('');

    container.innerHTML = sourcesHTML;
    console.log('[renderDataSources] ✅ HTML inserted into container, innerHTML length:', sourcesHTML.length);
    
    // Make absolutely sure the container is visible
    container.style.display = 'grid';
    container.style.visibility = 'visible';
    container.style.opacity = '1';
    
    // Show count in header
    const sourcesPanel = document.querySelector('.cfi-panel[data-area="sources"]');
    if (sourcesPanel) {
      const headerText = sourcesPanel.querySelector('.cfi-strip');
      if (headerText && !headerText.querySelector('.sources-count')) {
        const countBadge = document.createElement('span');
        countBadge.className = 'sources-count';
        countBadge.textContent = `${sources.length} items`;
        headerText.insertBefore(countBadge, headerText.querySelector('.toggle-sources-btn'));
      }
    }
    
    // Debug: Check if links are properly created
    setTimeout(() => {
      const links = container.querySelectorAll('.source-link');
      const items = container.querySelectorAll('.source-item');
      console.log(`[renderDataSources] Created ${items.length} source items and ${links.length} links`);
      
      if (items.length === 0) {
        console.error('[renderDataSources] ❌ NO SOURCE ITEMS RENDERED! Check sourcesHTML');
        console.log('[renderDataSources] sourcesHTML sample:', sourcesHTML.substring(0, 500));
      }
      
      links.forEach((link, i) => {
        if (link.href) {
          console.log(`  Link ${i+1}:`, link.href, 'clickable:', link.style.pointerEvents !== 'none');
          
          // Add click listener for debugging
          link.addEventListener('click', (e) => {
            console.log(`✅ Click on link ${i+1}:`, link.href);
          });
        }
      });
    }, 100);
  }

  function formatSourceValue(value, label) {
    const lowerLabel = String(label || '').toLowerCase();
    
    if (lowerLabel.includes('shares') || lowerLabel.includes('employees')) {
      return formatInteger(value);
    }
    
    if (lowerLabel.includes('margin') || lowerLabel.includes('return') || 
        lowerLabel.includes('yield') || lowerLabel.includes('%')) {
      return formatPercent(value);
    }
    
    if (lowerLabel.includes('ratio') || lowerLabel.includes('multiple') ||
        lowerLabel.includes('ev/') || lowerLabel.includes('p/')) {
      return formatMultiple(value);
    }
    
    return formatMoney(value);
  }

  // Expose functions for external use
  window.DashboardEnhancements = {
    showNotification,
    showLoadingProgress,
    hideLoadingProgress,
    createSparkline,
    addSparklinestoKPIs,
    animateNumber,
    renderDataSources
  };
})();

// Setup toggle button for sources section
function setupSourcesToggle() {
  console.log('[setupSourcesToggle] Initializing toggle button...');
  
  const toggleBtn = document.getElementById('toggle-sources-btn');
  const sourcesBody = document.getElementById('sources-body');
  const sourcesPanel = document.querySelector('.cfi-panel[data-area="sources"]');
  const sourcesGrid = document.getElementById('cfi-sources-grid');
  const toggleText = toggleBtn?.querySelector('.toggle-text');
  
  console.log('[setupSourcesToggle] Elements found:', {
    toggleBtn: !!toggleBtn,
    sourcesBody: !!sourcesBody,
    sourcesPanel: !!sourcesPanel,
    sourcesGrid: !!sourcesGrid,
    toggleText: !!toggleText
  });
  
  // Check if sources were rendered
  if (sourcesGrid) {
    const sourceItems = sourcesGrid.querySelectorAll('.source-item');
    console.log('[setupSourcesToggle] Source items in grid:', sourceItems.length);
    if (sourceItems.length === 0) {
      console.warn('[setupSourcesToggle] ⚠️ No source items found! Sources may not have been rendered.');
      console.log('[setupSourcesToggle] Grid HTML:', sourcesGrid.innerHTML.substring(0, 200));
    }
  }
  
  if (!toggleBtn || !sourcesBody) {
    console.error('[setupSourcesToggle] ❌ Required elements not found!');
    return;
  }
  
  // Make absolutely sure sources panel is visible
  if (sourcesPanel) {
    sourcesPanel.style.display = 'flex';
    sourcesPanel.style.visibility = 'visible';
    console.log('[setupSourcesToggle] ✅ Forced sources panel visibility');
  }
  
  // Start with sources expanded by default (as it was originally)
  let isCollapsed = false;
  sourcesBody.classList.remove('collapsed');
  toggleBtn.classList.remove('collapsed');
  if (toggleText) toggleText.textContent = 'Hide';
  
  toggleBtn.addEventListener('click', (e) => {
    console.log('[setupSourcesToggle] 🖱️ BUTTON CLICKED!', { isCollapsed });
    e.preventDefault();
    e.stopPropagation();
    
    isCollapsed = !isCollapsed;
    
    if (isCollapsed) {
      sourcesBody.classList.add('collapsed');
      toggleBtn.classList.add('collapsed');
      if (toggleText) toggleText.textContent = 'Show';
      console.log('[setupSourcesToggle] ➖ Sources collapsed');
    } else {
      sourcesBody.classList.remove('collapsed');
      toggleBtn.classList.remove('collapsed');
      if (toggleText) toggleText.textContent = 'Hide';
      console.log('[setupSourcesToggle] ➕ Sources expanded');
      
      // Log what's in the sources body
      setTimeout(() => {
        const items = sourcesBody.querySelectorAll('.source-item');
        console.log('[setupSourcesToggle] Sources expanded, items visible:', items.length);
      }, 100);
    }
    
    console.log('[setupSourcesToggle] After toggle:', {
      isCollapsed,
      bodyHasCollapsed: sourcesBody.classList.contains('collapsed'),
      btnHasCollapsed: toggleBtn.classList.contains('collapsed'),
      buttonText: toggleText?.textContent
    });
  });
  
  console.log('[setupSourcesToggle] ✅ Toggle button initialized and sources COLLAPSED (click to show)');
  console.log('[setupSourcesToggle] Button element:', toggleBtn);
  console.log('[setupSourcesToggle] Try clicking the button now!');
}
