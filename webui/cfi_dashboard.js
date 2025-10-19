(function(){
  const COLORS = {
    navy: "#0B2E59",
    accent: "#1C7ED6",
    orange: "#FF7F0E",
    slate: "#5B6B82"
  };
  const BASE_LAYOUT = {
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: { family: "Inter, Open Sans, Roboto", color: COLORS.navy, size: 12 },
    xaxis: { gridcolor: "#E1E8F5", zeroline: false, tickfont: { size: 11 } },
    yaxis: { gridcolor: "#E1E8F5", zeroline: false, tickfont: { size: 11 } },
    legend: { orientation: "h", y: 1.12, x: 1.0, xanchor: "right", font: { size: 10 } },
    margin: { l: 40, r: 32, t: 26, b: 34 },
    hoverlabel: { bgcolor: "#fff", bordercolor: "#d5def0", font: { family: "Inter, Open Sans, Roboto", size: 11 } }
  };
  const CONFIG = { displayModeBar: false, responsive: true };

  const isNumber = (value) => value !== null && value !== undefined && Number.isFinite(Number(value));

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

  function formatValue(label, value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "string") return value;
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
    const table = typeof target === "string" ? document.getElementById(target) : target;
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
      left.textContent = String(label).replace(/_/g, " ");
      const right = document.createElement("td");
      right.className = "kv-value";
      right.textContent = formatValue(label, value);
      tr.append(left, right);
      tbody.appendChild(tr);
    });
  }

  function renderValuationTable(target, rows) {
    const table = typeof target === "string" ? document.getElementById(target) : target;
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
      th.textContent = heading;
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
      labelCell.textContent = row.Label || row.label || "";
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
    const list = typeof target === "string" ? document.getElementById(target) : target;
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
    const container = document.getElementById(targetId);
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
      th.textContent = year;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    tbl.appendChild(thead);

    const tbody = document.createElement("tbody");
    (table.rows || []).forEach((row) => {
      const tr = document.createElement("tr");
      const metricCell = document.createElement("td");
      metricCell.className = "metric";
      metricCell.textContent = row.label || "";
      tr.appendChild(metricCell);
      columns.forEach((_, index) => {
        const td = document.createElement("td");
        td.className = "num";
        const value = row.values ? row.values[index] : null;
        let formatted = formatMoney(value);
        if (row.type === "percent") formatted = formatPercent(value);
        else if (row.type === "multiple") formatted = formatMultiple(value);
        td.textContent = formatted;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    container.appendChild(tbl);
  }

  function plotRevenueChart(data) {
    const node = document.getElementById("cfi-rev");
    if (!node) return;
    if (!data || !Array.isArray(data.Year) || !Array.isArray(data.Revenue)) {
      node.textContent = "No revenue data.";
      return;
    }
    const traces = [
      {
        type: "bar",
        x: data.Year,
        y: data.Revenue,
        name: "Revenue ($M)",
        marker: { color: COLORS.navy, line: { color: "#052142", width: 1 } },
        hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>"
      }
    ];
    const multiples = data.EV_Rev || data["EV/Revenue"];
    if (Array.isArray(multiples) && multiples.length) {
      traces.push({
        type: "scatter",
        mode: "lines+markers",
        x: data.Year,
        y: multiples,
        name: "EV/Revenue (×)",
        yaxis: "y2",
        line: { color: COLORS.accent, width: 2 },
        marker: { size: 5, color: COLORS.accent },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>"
      });
    }
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "Revenue vs EV/Revenue", x: 0.01, y: 0.99, font: { size: 14 } },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "Revenue ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/Revenue (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" },
      bargap: 0.3
    };
    Plotly.newPlot(node, traces, layout, CONFIG);
  }

  function plotEbitdaChart(data) {
    const node = document.getElementById("cfi-ebitda");
    if (!node) return;
    if (!data || !Array.isArray(data.Year) || !Array.isArray(data.EBITDA)) {
      node.textContent = "No EBITDA data.";
      return;
    }
    const traces = [
      {
        type: "bar",
        x: data.Year,
        y: data.EBITDA,
        name: "EBITDA ($M)",
        marker: { color: COLORS.navy, line: { color: "#052142", width: 1 } },
        hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>"
      }
    ];
    const multiples = data.EV_EBITDA || data["EV/EBITDA"];
    if (Array.isArray(multiples) && multiples.length) {
      traces.push({
        type: "scatter",
        mode: "lines+markers",
        x: data.Year,
        y: multiples,
        name: "EV/EBITDA (×)",
        yaxis: "y2",
        line: { color: COLORS.accent, width: 2 },
        marker: { size: 5, color: COLORS.accent },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>"
      });
    }
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "EBITDA vs EV/EBITDA", x: 0.01, y: 0.99, font: { size: 14 } },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "EBITDA ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/EBITDA (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" },
      bargap: 0.3
    };
    Plotly.newPlot(node, traces, layout, CONFIG);
  }

  function plotForecastChart(data) {
    const node = document.getElementById("cfi-forecast");
    if (!node) return;
    if (!data || !Array.isArray(data.Year)) {
      node.textContent = "No forecast data.";
      return;
    }
    const traces = [];
    [
      ["Bull", COLORS.navy, "solid"],
      ["Base", COLORS.accent, "dash"],
      ["Bear", COLORS.slate, "dot"]
    ].forEach(([key, color, dash]) => {
      if (Array.isArray(data[key])) {
        traces.push({
          type: "scatter",
          mode: "lines",
          x: data.Year,
          y: data[key],
          name: key,
          line: { color, dash, width: 2.4 },
          hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>"
        });
      }
    });
    if (!traces.length) {
      node.textContent = "No forecast data.";
      return;
    }
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "Share Price — Historical & Forecast", x: 0.01, y: 0.99, font: { size: 14 } },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "Share Price ($)", tickprefix: "$", separatethousands: true }
    };
    Plotly.newPlot(node, traces, layout, CONFIG);
  }

  function plotValuationBar(data, meta = {}) {
    const node = document.getElementById("cfi-valbar");
    if (!node) return;
    if (!data || !Array.isArray(data.Case) || !Array.isArray(data.Value)) {
      node.textContent = "No valuation data.";
      return;
    }
    const traces = [
      {
        type: "bar",
        x: data.Case,
        y: data.Value,
        name: "Value",
        marker: { color: COLORS.navy, line: { color: "#052142", width: 1 } },
        text: data.Value.map((v) => formatMoney(v)),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{x}: %{y:$,.0f}<extra></extra>"
      }
    ];
    const { current, average } = meta || {};
    const referenceLines = [
      ["Current", current, COLORS.slate, "dot"],
      ["Average", average, COLORS.orange, "dash"]
    ].filter(([, value]) => isNumber(value));
    referenceLines.forEach(([label, value, color, dash]) => {
      traces.push({
        type: "scatter",
        mode: "lines",
        x: data.Case,
        y: data.Case.map(() => value),
        name: label,
        line: { color, dash, width: 2 },
        hovertemplate: `${label}: ${formatMoney(value)}<extra></extra>`
      });
    });
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "Valuation Summary — Equity Value per Share ($)", x: 0.01, y: 0.99, font: { size: 14 } },
      margin: { l: 40, r: 24, t: 24, b: 40 },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "$/Share", tickprefix: "$", separatethousands: true },
      bargap: 0.32
    };
    Plotly.newPlot(node, traces, layout, CONFIG);
  }

  function renderMeta(meta = {}) {
    const company = meta.company || "";
    const ticker = meta.ticker ? String(meta.ticker).toUpperCase() : "";
    const brand = meta.brand || company.split(" ")[0] || ticker || "";

    const brandNode = document.getElementById("cfi-brand");
    if (brandNode) brandNode.textContent = brand ? brand.toLowerCase() : "";

    const companyNode = document.getElementById("cfi-company");
    if (companyNode) companyNode.textContent = company;

    const tickerNode = document.getElementById("cfi-ticker");
    if (tickerNode) {
      const explicit = meta.ticker_label || meta.ticker_display;
      if (explicit) tickerNode.textContent = explicit;
      else {
        const exchange = meta.exchange ? String(meta.exchange).toUpperCase() : "";
        const label = [exchange, ticker].filter(Boolean).join(": ");
        tickerNode.textContent = label || ticker;
      }
    }

    const recNode = document.getElementById("cfi-rec");
    if (recNode) recNode.textContent = meta.recommendation || "—";

    const targetNode = document.getElementById("cfi-target");
    if (targetNode) targetNode.textContent = isNumber(meta.target_price) ? formatCurrency(meta.target_price) : meta.target_price || "—";

    const scenarioNode = document.getElementById("cfi-scenario");
    if (scenarioNode) scenarioNode.textContent = meta.scenario || meta.live_scenario || meta.case || "Consensus";

    const dateNode = document.getElementById("cfi-date");
    if (dateNode) dateNode.textContent = meta.date || "";

    const websiteNode = document.getElementById("cfi-website");
    if (websiteNode) {
      const value = meta.website || meta.url || "";
      websiteNode.textContent = value;
      websiteNode.style.display = value ? "" : "none";
    }

    const tagNode = document.getElementById("cfi-report-tag");
    if (tagNode) {
      const value = meta.report_tag || meta.report || "";
      tagNode.textContent = value;
      tagNode.style.display = value ? "" : "none";
    }
  }

  window.CFI = {
    render(payload) {
      if (!payload) return;
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
      const charts = payload.charts || {};
      plotRevenueChart(charts.revenue_ev || null);
      plotEbitdaChart(charts.ebitda_ev || null);
      plotValuationBar(charts.valuation_bar || null, payload.valuation_data || {});
      plotForecastChart(charts.forecast || null);
    }
  };
})();
