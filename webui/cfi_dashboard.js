(function(){
  const BASE_LAYOUT = {
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    font: { family: "Inter, Open Sans, Roboto", color: "#003366", size: 12 },
    xaxis: { gridcolor: "#E6E9EF", zeroline: false, tickfont: { size: 11 } },
    yaxis: { gridcolor: "#E6E9EF", zeroline: false, tickfont: { size: 11 } },
    legend: { orientation: "h", y: 1.16, x: 1.0, xanchor: "right", font: { size: 10 } },
    margin: { l: 40, r: 32, t: 24, b: 32 }
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

  const formatPercent = (value) => (isNumber(value) ? `${Number(value).toFixed(1)}%` : "—");
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
      left.textContent = String(label).replace(/_/g, " ");
      const right = document.createElement("td");
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
      labelCell.textContent = row.Label || row.label || "";
      tr.appendChild(labelCell);
      columns.forEach((field) => {
        const td = document.createElement("td");
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
        marker: { color: "#003366" },
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
        line: { color: "#FF7F0E", width: 2 },
        marker: { size: 5, color: "#FF7F0E" },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>"
      });
    }
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "Revenue vs EV/Revenue", x: 0.01, y: 0.99, font: { size: 14 } },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "Revenue ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/Revenue (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" }
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
        marker: { color: "#003366" },
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
        line: { color: "#FF7F0E", width: 2 },
        marker: { size: 5, color: "#FF7F0E" },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>"
      });
    }
    const layout = {
      ...BASE_LAYOUT,
      title: { text: "EBITDA vs EV/EBITDA", x: 0.01, y: 0.99, font: { size: 14 } },
      yaxis: { ...BASE_LAYOUT.yaxis, title: "EBITDA ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/EBITDA (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" }
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
      ["Bull", "#003366", "solid"],
      ["Base", "#FF7F0E", "dash"],
      ["Bear", "#6B7A90", "dot"]
    ].forEach(([key, color, dash]) => {
      if (Array.isArray(data[key])) {
        traces.push({
          type: "scatter",
          mode: "lines",
          x: data.Year,
          y: data[key],
          name: key,
          line: { color, dash, width: 2 },
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
        marker: { color: "#003366" },
        text: data.Value.map((v) => formatMoney(v)),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{x}: %{y:$,.0f}<extra></extra>"
      }
    ];
    const { current, average } = meta || {};
    const referenceLines = [
      ["Current", current, "#6B7A90", "dot"],
      ["Average", average, "#FF7F0E", "dash"]
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
      yaxis: { ...BASE_LAYOUT.yaxis, title: "$/Share", tickprefix: "$", separatethousands: true }
    };
    Plotly.newPlot(node, traces, layout, CONFIG);
  }

  function renderMeta(meta = {}) {
    const companyNode = document.getElementById("cfi-company");
    if (companyNode) {
      const ticker = meta.ticker ? String(meta.ticker).toUpperCase() : "";
      companyNode.textContent = ticker ? `${meta.company || ""} (${ticker})`.trim() : meta.company || ticker || "";
    }
    const recNode = document.getElementById("cfi-rec");
    if (recNode) recNode.textContent = meta.recommendation || "";
    const targetNode = document.getElementById("cfi-target");
    if (targetNode) targetNode.textContent = isNumber(meta.target_price) ? `Target: ${formatMoney(meta.target_price)}` : "";
    const dateNode = document.getElementById("cfi-date");
    if (dateNode) dateNode.textContent = meta.date || "";
  }

  window.CFI = {
    render(payload) {
      if (!payload) return;
      renderMeta(payload.meta);
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
