/* global Plotly */
window.CFI_DENSE = (function () {
  const THEME = {
    layout: {
      paper_bgcolor: "#fff",
      plot_bgcolor: "#fff",
      font: { family: "Inter, Open Sans, Roboto", color: "#003366", size: 12 },
      xaxis: { gridcolor: "#E6E9EF", zeroline: false },
      yaxis: { gridcolor: "#E6E9EF", zeroline: false },
      legend: { orientation: "h", y: 1.12, x: 1.0, xanchor: "right", font: { size: 11 } },
    },
    config: { displayModeBar: false, responsive: true },
    colorway: ["#003366", "#FF7F0E", "#2CA02C", "#9467BD", "#6B7A90"],
  };

  const fmtMoney = (n) => {
    if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
    const value = Number(n);
    const sign = value < 0 ? "-" : "";
    const abs = Math.abs(value);
    const unit = abs >= 1e12 ? "T" : abs >= 1e9 ? "B" : abs >= 1e6 ? "M" : abs >= 1e3 ? "K" : "";
    const divisor = unit === "T" ? 1e12 : unit === "B" ? 1e9 : unit === "M" ? 1e6 : unit === "K" ? 1e3 : 1;
    const scaled = abs / divisor;
    const decimals = scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2;
    const formatted = scaled.toFixed(decimals).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
    return `${sign}$${formatted}${unit}`;
  };
  const fmtPct = (n) => (n === null || n === undefined || Number.isNaN(Number(n)) ? "—" : `${Number(n).toFixed(1)}%`);
  const fmtX = (n) => (n === null || n === undefined || Number.isNaN(Number(n)) ? "—" : `${Number(n).toFixed(1)}×`);
  const fmtNum = (n) => (n === null || n === undefined || Number.isNaN(Number(n)) ? "—" : Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 }));
  const fmtDate = (value) => {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
  };

  function normaliseEntries(obj) {
    if (!obj) return [];
    if (Array.isArray(obj)) {
      return obj.map((row) => ({
        label: row.label ?? row.Label ?? row.k ?? row.key ?? "",
        value: row.value ?? row.Value ?? row.v ?? row.val ?? row,
      }));
    }
    return Object.entries(obj).map(([label, value]) => ({ label, value }));
  }

  function formatKVValue(label, value) {
    if (value === null || value === undefined || value === "") return "—";
    const lower = String(label).toLowerCase();
    if (typeof value === "number") {
      if (lower.includes("margin") || lower.includes("growth") || lower.includes("pct") || lower.includes("%")) return fmtPct(value);
      if (lower.includes("multiple") || lower.includes("ev/") || lower.includes("turnover")) return fmtX(value);
      if (lower.includes("employees") || lower.includes("shares") || lower.includes("count")) return fmtNum(value);
      if (
        lower.includes("price") ||
        lower.includes("value") ||
        lower.includes("cap") ||
        lower.includes("debt") ||
        lower.includes("cash") ||
        lower.includes("revenue") ||
        lower.includes("income") ||
        lower.includes("flow")
      )
        return fmtMoney(value);
      return fmtMoney(value);
    }
    return value;
  }

  function renderKV(id, source) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "kv";
    normaliseEntries(source).forEach(({ label, value }) => {
      if (!label) return;
      const labelText = String(label).replace(/_/g, " ");
      const rowLabel = document.createElement("div");
      rowLabel.className = "k";
      rowLabel.textContent = labelText;
      const rowValue = document.createElement("div");
      rowValue.className = "v";
      rowValue.textContent = formatKVValue(label, value);
      wrap.appendChild(rowLabel);
      wrap.appendChild(rowValue);
    });
    el.appendChild(wrap);
  }

  function computeWidths(yearCount) {
    const year = Math.max(68, Math.min(100, 92 - Math.max(0, yearCount - 6) * 4));
    const metric = Math.max(180, 300 - Math.max(0, yearCount - 6) * 8);
    return { year, metric };
  }

  function renderKeyFinancials(containerId, data) {
    const el = document.getElementById(containerId);
    if (!el || !data || !Array.isArray(data.columns) || !Array.isArray(data.rows)) return;
    const years = data.columns;
    const { year: yearWidth, metric: metricWidth } = computeWidths(years.length);

    const table = document.createElement("table");
    table.className = "table";

    const thead = document.createElement("thead");
    const groupRow = document.createElement("tr");
    groupRow.className = "group-row";
    const metricGroup = document.createElement("th");
    metricGroup.colSpan = 1;
    metricGroup.textContent = "";
    groupRow.appendChild(metricGroup);
    const yearsGroup = document.createElement("th");
    yearsGroup.colSpan = years.length;
    yearsGroup.textContent = "Fiscal Year";
    groupRow.appendChild(yearsGroup);
    thead.appendChild(groupRow);

    const headerRow = document.createElement("tr");
    headerRow.className = "header-row";
    const metricTh = document.createElement("th");
    metricTh.className = "col-metric";
    metricTh.style.width = `${metricWidth}px`;
    metricTh.textContent = "Metric";
    headerRow.appendChild(metricTh);
    years.forEach((year) => {
      const th = document.createElement("th");
      th.className = "col-year";
      th.style.width = `${yearWidth}px`;
      th.textContent = year;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    data.rows.forEach((row) => {
      const tr = document.createElement("tr");
      const metricCell = document.createElement("th");
      metricCell.className = "metric";
      metricCell.textContent = row.label;
      tr.appendChild(metricCell);
      years.forEach((_, index) => {
        const td = document.createElement("td");
        td.className = "num";
        const value = row.values?.[index];
        if (row.type === "percent") td.textContent = fmtPct(value);
        else if (row.type === "multiple") td.textContent = fmtX(value);
        else td.textContent = fmtMoney(value);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    el.innerHTML = "";
    const scroller = document.createElement("div");
    scroller.className = "dense-table";
    scroller.appendChild(table);
    el.appendChild(scroller);
  }

  function renderValuationMatrix(containerId, rows) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = "";
    if (!Array.isArray(rows) || !rows.length) {
      el.textContent = "—";
      return;
    }
    const cols = ["Market", "DCF", "Comps"];
    const table = document.createElement("table");
    table.className = "kv-table";
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    const blank = document.createElement("th");
    blank.textContent = "";
    headerRow.appendChild(blank);
    cols.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const labelCell = document.createElement("td");
      labelCell.className = "label";
      labelCell.textContent = row.Label || row.label || "";
      tr.appendChild(labelCell);
      cols.forEach((col) => {
        const td = document.createElement("td");
        td.className = "value";
        td.textContent = fmtMoney(row[col]);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    el.appendChild(table);
  }

  function plotRevenue(divId, data) {
    const host = document.getElementById(divId);
    if (!host) return;
    if (!data || !data.Year) {
      host.textContent = "No revenue data.";
      return;
    }
    if (!Array.isArray(data.Revenue) || !data.Revenue.length) {
      host.textContent = "No revenue data.";
      return;
    }
    const lineValues = data.EV_Rev || data["EV/Revenue"];
    const traces = [
      {
        type: "bar",
        x: data.Year,
        y: data.Revenue,
        name: "Revenue ($M)",
        marker: { color: "#003366" },
        hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>",
      },
    ];
    if (Array.isArray(lineValues) && lineValues.length) {
      traces.push({
        type: "scatter",
        mode: "lines+markers",
        name: "EV/Revenue (×)",
        x: data.Year,
        y: lineValues,
        yaxis: "y2",
        line: { color: "#FF7F0E", width: 2 },
        marker: { size: 5, color: "#FF7F0E" },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>",
      });
    }
    const layout = {
      ...THEME.layout,
      title: "Revenue vs EV/Revenue",
      yaxis: { ...THEME.layout.yaxis, title: "Revenue ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/Revenue (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" },
    };
    Plotly.newPlot(divId, traces, layout, THEME.config);
  }

  function plotEbitda(divId, data) {
    const host = document.getElementById(divId);
    if (!host) return;
    if (!data || !data.Year) {
      host.textContent = "No EBITDA data.";
      return;
    }
    if (!Array.isArray(data.EBITDA) || !data.EBITDA.length) {
      host.textContent = "No EBITDA data.";
      return;
    }
    const lineValues = data.EV_EBITDA || data["EV/EBITDA"];
    const traces = [
      {
        type: "bar",
        x: data.Year,
        y: data.EBITDA,
        name: "EBITDA ($M)",
        marker: { color: "#003366" },
        hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>",
      },
    ];
    if (Array.isArray(lineValues) && lineValues.length) {
      traces.push({
        type: "scatter",
        mode: "lines+markers",
        name: "EV/EBITDA (×)",
        x: data.Year,
        y: lineValues,
        yaxis: "y2",
        line: { color: "#FF7F0E", width: 2 },
        marker: { size: 5, color: "#FF7F0E" },
        hovertemplate: "FY %{x}: %{y:.2f}×<extra></extra>",
      });
    }
    const layout = {
      ...THEME.layout,
      title: "EBITDA vs EV/EBITDA",
      yaxis: { ...THEME.layout.yaxis, title: "EBITDA ($M)", tickprefix: "$", separatethousands: true },
      yaxis2: { title: "EV/EBITDA (×)", overlaying: "y", side: "right", showgrid: false, ticksuffix: "×" },
    };
    Plotly.newPlot(divId, traces, layout, THEME.config);
  }

  function plotValuationBar(divId, data, current) {
    const host = document.getElementById(divId);
    if (!host) return;
    if (!data || !data.Case) {
      host.textContent = "No valuation details.";
      return;
    }
    const bar = {
      type: "bar",
      x: data.Case,
      y: data.Value,
      marker: { color: "#003366" },
      text: data.Value.map((v) => fmtMoney(v)),
      textposition: "outside",
      hovertemplate: "%{x}: %{y:$,.0f}<extra></extra>",
    };
    const shapes = [];
    if (current !== null && current !== undefined && !Number.isNaN(Number(current))) {
      shapes.push({
        type: "line",
        xref: "x",
        x0: -0.5,
        x1: data.Case.length - 0.5,
        y0: current,
        y1: current,
        line: { color: "#FF7F0E", dash: "dot", width: 2 },
      });
    }
    const layout = {
      ...THEME.layout,
      title: "Valuation Summary — Equity Value per Share ($)",
      shapes,
      yaxis: { ...THEME.layout.yaxis, title: "Value ($/Share)", tickprefix: "$", separatethousands: true },
    };
    Plotly.newPlot(divId, [bar], layout, THEME.config);
  }

  function plotForecast(divId, data) {
    const host = document.getElementById(divId);
    if (!host) return;
    if (!data || !data.Year) {
      host.textContent = "No forecast data.";
      return;
    }
    const traces = [];
    if (Array.isArray(data.Bull))
      traces.push({ type: "scatter", mode: "lines+markers", x: data.Year, y: data.Bull, name: "Bull", line: { color: "#003366", width: 2 }, marker: { size: 5, color: "#003366" }, hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>" });
    if (Array.isArray(data.Base))
      traces.push({ type: "scatter", mode: "lines+markers", x: data.Year, y: data.Base, name: "Base", line: { color: "#FF7F0E", dash: "dash", width: 2 }, marker: { size: 5, color: "#FF7F0E" }, hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>" });
    if (Array.isArray(data.Bear))
      traces.push({ type: "scatter", mode: "lines+markers", x: data.Year, y: data.Bear, name: "Bear", line: { color: "#6B7A90", dash: "dot", width: 2 }, marker: { size: 5, color: "#6B7A90" }, hovertemplate: "FY %{x}: %{y:$,.0f}<extra></extra>" });
    if (!traces.length) {
      host.textContent = "No forecast data.";
      return;
    }
    const layout = {
      ...THEME.layout,
      title: "Share Price — Historical & Forecast",
      yaxis: { ...THEME.layout.yaxis, title: "Price ($)", tickprefix: "$", separatethousands: true },
    };
    Plotly.newPlot(divId, traces, layout, THEME.config);
  }

  function render(payload) {
    if (!payload) return;
    const meta = payload.meta || {};
    const ticker = meta.ticker ? String(meta.ticker).toUpperCase() : "";
    const company = meta.company ? String(meta.company) : "";
    const companyLabel = ticker ? `${company} (${ticker})`.trim() : company || ticker;
    const companyNode = document.getElementById("company");
    if (companyNode) companyNode.textContent = companyLabel;
    const recNode = document.getElementById("rec");
    if (recNode) recNode.textContent = meta.recommendation || "";
    const targetNode = document.getElementById("target");
    if (targetNode) targetNode.textContent = meta.target_price ? `Target ${fmtMoney(meta.target_price)}` : "";
    const dateNode = document.getElementById("date");
    if (dateNode) dateNode.textContent = fmtDate(meta.date);

    renderKV("ov", payload.overview || {});
    renderKV("ks", payload.key_stats || {});
    renderKV("md", payload.market_data || {});
    renderValuationMatrix("val", payload.valuation_table || []);

    if (payload.key_financials) {
      renderKeyFinancials("keyfin-table", payload.key_financials);
    }

    const charts = payload.charts || {};
    plotForecast("forecast", charts.forecast);
    plotRevenue("rev", charts.revenue_ev || {});
    plotEbitda("ebitda", charts.ebitda_ev || {});
    const baseline = payload.overview?.price ?? null;
    plotValuationBar("valbar", charts.valuation_bar || {}, baseline);
  }

  return { render };
})();
