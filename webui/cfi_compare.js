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

  const L = {
    paper_bgcolor:"#fff", plot_bgcolor:"#fff",
    font:{family:"Inter, Open Sans, Roboto", color:"#003366", size:12},
    xaxis:{gridcolor:"#E6E9EF", zeroline:false},
    yaxis:{gridcolor:"#E6E9EF", zeroline:false},
    legend:{orientation:"h", y:1.16, x:1.0, xanchor:"right", font:{size:10}},
    margin:{l:48,r:36,t:24,b:36}
  };
  const money = n => (n==null||isNaN(n)) ? "â" : ((s=>`${s[0]}$${s[1]}${s[2]}`)((() => {
    const val = Number(n);
    const sign = val<0?"-":""; const a=Math.abs(val);
    const unit = a>=1e9?"B":a>=1e6?"M":a>=1e3?"K":""; const v = a>=1e9?a/1e9:a>=1e6?a/1e6:a>=1e3?a/1e3:a;
    return [sign, v.toFixed(v>=100?0:v>=10?1:2), unit];
  })()));
  const pct   = n => (n==null||isNaN(n)) ? "â" : `${(+n).toFixed(1)}%`;
  const xfmt  = n => (n==null||isNaN(n)) ? "â" : `${(+n).toFixed(2)}Ã`;

  const PANEL_CONFIG = {
    kpiA: { label: "Company A", bodyId: "kpiA", bodyClass: "body tight kv" },
    kpiB: { label: "Company B", bodyId: "kpiB", bodyClass: "body tight kv" },
    kpiC: { label: "Company C", bodyId: "kpiC", bodyClass: "body tight kv" },
    benchmark: { label: "Benchmark (S&P 500 Avg)", bodyId: "kpiBench", bodyClass: "body tight kv" },
    compareTable: { label: "Key Financials â Side by Side", bodyId: "compareTable", bodyClass: "body tight" },
    compareFootball: { label: "Valuation Ranges â Football Field", bodyId: "compareFootball", bodyClass: "body tight plot" },
    revTrend: { label: "Revenue â Multi-Company Trend", bodyId: "revTrend", bodyClass: "body tight plot" },
    ebitdaTrend: { label: "EBITDA â Multi-Company Trend", bodyId: "ebitdaTrend", bodyClass: "body tight plot" },
    marginVsPeers: { label: "Net Margin vs ROE â Peer Map", bodyId: "marginVsPeers", bodyClass: "body tight plot" },
    valuationSummary: { label: "Valuation Summary â Equity Value per Share ($)", bodyId: "valuationSummary", bodyClass: "body tight plot" },
  };

  function ensureRoot(scope) {
    let root = scopedQuery("cfix-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "cfix-root";
      root.className = "cfix-grid";
      // If scope is document, append to document.body instead
      const container = (scope instanceof HTMLElement) ? scope : document.body;
      container.appendChild(root);
    }
    return root;
  }

  function ensureHeader(root) {
    let header = scopedSelect('.panel.header[data-area="header"]');
    if (!header) {
      header = document.createElement("div");
      header.className = "panel header";
      header.dataset.area = "header";
      const title = document.createElement("h1");
      title.textContent = "Financial Model Dashboard â Compare";
      const meta = document.createElement("div");
      meta.className = "meta";
      const peerset = document.createElement("span");
      peerset.id = "cfix-peerset";
      const date = document.createElement("span");
      date.id = "cfix-date";
      meta.append(peerset, date);
      header.append(title, meta);
      root.insertBefore(header, root.firstChild);
    } else {
      let peerset = scopedQuery("cfix-peerset");
      if (!peerset) {
        peerset = document.createElement("span");
        peerset.id = "cfix-peerset";
        const meta = header.querySelector(".meta") || (() => {
          const m = document.createElement("div");
          m.className = "meta";
          header.appendChild(m);
          return m;
        })();
        meta.appendChild(peerset);
      }
      let date = scopedQuery("cfix-date");
      if (!date) {
        date = document.createElement("span");
        date.id = "cfix-date";
        const meta = header.querySelector(".meta") || (() => {
          const m = document.createElement("div");
          m.className = "meta";
          header.appendChild(m);
          return m;
        })();
        meta.appendChild(date);
      }
    }
  }

  function ensurePanel(root, area, config) {
    let panel = scopedSelect(`.panel[data-area="${area}"]`);
    if (!panel) {
      panel = document.createElement("div");
      panel.className = "panel";
      panel.dataset.area = area;
      root.appendChild(panel);
    }
    if (config.label !== null) {
      let strip = panel.querySelector(".strip");
      if (!strip) {
        strip = document.createElement("div");
        strip.className = "strip";
        if (config.label) strip.textContent = config.label;
        panel.prepend(strip);
      } else if (!strip.textContent && config.label) {
        strip.textContent = config.label;
      }
    }
    if (config.bodyId) {
      let body = panel.querySelector(`#${config.bodyId}`);
      if (!body) {
        body = document.createElement("div");
        body.id = config.bodyId;
        body.className = config.bodyClass || "body";
        panel.appendChild(body);
      }
    }
  }

  function ensureCompareLayout() {
    const scope = resolveScope();
    const root = ensureRoot(scope);
    ensureHeader(root);
    Object.entries(PANEL_CONFIG).forEach(([area, config]) => ensurePanel(root, area, config));
  }


  function formatCardValue(label, raw){
    if (raw === null || raw === undefined || raw === "") return "â";
    const text = typeof raw === "string" ? raw : null;
    const numeric = Number(raw);
    if (!Number.isFinite(numeric)) {
      return text ?? "â";
    }
    const lowerLabel = (label || "").toLowerCase();
    if (lowerLabel.includes("margin") || lowerLabel.includes("roe") || lowerLabel.includes("%") || lowerLabel.includes("return")) {
      return pct(numeric);
    }
    if (lowerLabel.includes("p/e") || lowerLabel.includes("ev/") || lowerLabel.includes("multiple") || lowerLabel.includes("ratio")) {
      return xfmt(numeric);
    }
    if (lowerLabel.includes("price") || lowerLabel.includes("share")) {
      return money(numeric);
    }
    const hasBillionsHint = lowerLabel.includes("$b") || lowerLabel.includes(" (b") || lowerLabel.includes("billions");
    const formatted = money(numeric);
    if (hasBillionsHint && !formatted.endsWith("B")) {
      return `${formatted}B`;
    }
    return formatted;
  }

  function kv(container, obj){
    const el=scopedQuery(container);
    if (!el) return;
    el.innerHTML="";
    const pairs=Object.entries(obj || {});
    if (!pairs.length){
      const placeholderLabel=document.createElement("div");
      placeholderLabel.textContent="â";
      const placeholderValue=document.createElement("div");
      placeholderValue.textContent="â";
      el.append(placeholderLabel, placeholderValue);
      return;
    }
    for(const [k,v] of pairs){
      const L=document.createElement("div"); L.textContent=k ?? "";
      const R=document.createElement("div");
      R.textContent = formatCardValue(k, v);
      el.append(L,R);
    }
  }

  function renderCompareTable(id, table){
    const root = scopedQuery(id);
    if (!root) {
      if (console && typeof console.warn === "function") console.warn(`CFI Compare: table container "${id}" missing`);
      return;
    }
    root.innerHTML="";
    const t=document.createElement("table"); t.className="cfix-table";
    const thead=document.createElement("thead"); const trh=document.createElement("tr");
    const columns = Array.isArray(table?.columns) ? table.columns : [];
    for(const col of columns){ const th=document.createElement("th"); th.textContent=col; trh.append(th); }
    thead.append(trh); t.append(thead);
    const tb=document.createElement("tbody");
    const metricColumns = columns.slice(1);
    const benchLabel = metricColumns[metricColumns.length-1];
    const formatValue = (value, type) => {
      if (value == null || Number.isNaN(value)) return "â";
      if (type === "pct") return pct(value);
      if (type === "x") return xfmt(value);
      if (type === "moneyB") return `${money(value)}B`;
      return money(value);
    };
    for(const r of (table.rows || [])){
      const tr=document.createElement("tr");
      const td0=document.createElement("td"); td0.className="metric"; td0.textContent=r.label; tr.append(td0);
      for(const col of metricColumns){
        const td=document.createElement("td"); td.className="num";
        let value = r[col];
        if (value == null && (col === benchLabel || col === "S&P 500 Avg")) {
          value = r.SPX ?? r["S&P 500 Avg"];
        }
        td.textContent = formatValue(value, r.type);
        tr.append(td);
      }
      tb.append(tr);
    }
    t.append(tb); root.append(t);
  }

  function plotMultiLine(div, years, seriesMap, label){
    const node = scopedQuery(div);
    if (!node) {
      if (console && typeof console.warn === "function") console.warn(`CFI Compare: chart container "${div}" missing`);
      return;
    }
    if (!window.Plotly || typeof window.Plotly.newPlot !== "function") {
      node.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
      return;
    }
    const entries = Object.entries(seriesMap || {}).filter(([,vals])=>Array.isArray(vals) && vals.length);
    if (!entries.length || !(years || []).length) {
      node.innerHTML = "<div class=\"cfi-error\">No data available</div>";
      return;
    }
    // Filter out NaN/null values for each trace
    const traces = entries.map(([ticker,vals])=>{
      const cleanedPairs = (years || [])
        .map((year, idx) => {
          const val = vals[idx];
          return (val !== null && val !== undefined && Number.isFinite(Number(val))) ? {year, val: Number(val)} : null;
        })
        .filter(Boolean);
      return {
        type:"scatter", 
        x: cleanedPairs.map(p => p.year), 
        y: cleanedPairs.map(p => p.val), 
        mode:"lines", 
        name:ticker
      };
    }).filter(trace => trace.x.length > 0);
    if (!traces.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valid data available</div>";
      return;
    }
    Plotly.newPlot(node, traces, {...L, yaxis:{...L.yaxis,title:label}}, {displayModeBar:false,responsive:true});
  }

  function plotFootball(div, football){
    // Horizontal ranged bars per company and method
    const node = scopedQuery(div);
    if (!node) return;
    if (!window.Plotly || typeof window.Plotly.newPlot !== "function") {
      if (node) node.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
      return;
    }
    const filtered = (football || []).filter(entry => Array.isArray(entry?.ranges) && entry.ranges.length);
    if (!filtered.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valuation ranges</div>";
      return;
    }
    const traces=[];
    const tickvals=[];
    const ticktext=[];
    let y=0;
    for(const comp of filtered){
      const ranges = Array.isArray(comp.ranges) ? comp.ranges : [];
      let addedForCompany = false;
      for(const rng of ranges){
        const lo = Number.isFinite(rng?.lo) ? Number(rng.lo) : null;
        const hi = Number.isFinite(rng?.hi) ? Number(rng.hi) : null;
        if (lo == null || hi == null) continue;
        const label = `${comp.ticker}${rng?.name ? ` • ${rng.name}` : ""}`;
        const position = y;
        traces.push({
          type:"scatter",
          mode:"lines",
          x:[lo,hi],
          y:[position,position],
          name:label,
          line:{width:6,color:"#003366"}
        });
        tickvals.push(position);
        ticktext.push(label);
        y += 1;
        addedForCompany = true;
      }
      if (addedForCompany) {
        y += 0.6; // gap between companies
      }
    }
    if (!traces.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valuation ranges</div>";
            return;
        }
    const layout={
      ...L,
      xaxis:{...L.xaxis,title:"$/Share"},
      yaxis:{showgrid:false, tickmode:"array", tickvals, ticktext}
    };
    Plotly.newPlot(node, traces, layout, {displayModeBar:false,responsive:true});
  }

  function plotPeerScatter(div, data){
    const node = scopedQuery(div);
    if (!node) return;
    if (!window.Plotly || typeof window.Plotly.newPlot !== "function") {
      node.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
      return;
    }
    const filtered = (data || []).filter(d => d && typeof d.x === "number" && typeof d.y === "number");
    if (!filtered.length) {
      node.innerHTML = "<div class=\"cfi-error\">No peer data</div>";
      return;
    }
    const trace={
      type:"scatter",
      mode:"markers+text",
      x:filtered.map(d=>d.x),
      y:filtered.map(d=>d.y),
      text:filtered.map(d=>d.ticker),
      textposition:"top center",
      marker:{
        size:filtered.map(d=>Math.sqrt(Math.max(d.size || 1,1))*2.2),
        color:"#003366",
        opacity:0.8
      }
    };
    Plotly.newPlot(node, [trace], {
      ...L,
      xaxis:{...L.xaxis,title:"Net margin (%)"},
      yaxis:{...L.yaxis,title:"ROE (%)"}
    }, {displayModeBar:false,responsive:true});
  }

  function plotValSummary(div, cases, perCompany, order){
    const node = scopedQuery(div);
    if (!node) return;
    if (!window.Plotly || typeof window.Plotly.newPlot !== "function") {
      node.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
      return;
    }
    const tickers = (order || Object.keys(perCompany || {}))
      .filter(t => Array.isArray(perCompany?.[t]));
    if (!tickers.length || !cases.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valuation summary</div>";
      return;
    }
    // Clean data to remove NaN/null values
    const traces = tickers.map(t=>{
      const yValues = (perCompany[t] || []).map(v => 
        (v !== null && v !== undefined && Number.isFinite(Number(v))) ? Number(v) : null
      );
      return {
        type:"bar", 
        x:cases, 
        y:yValues, 
        name:t, 
        marker:{line:{width:0}}
      };
    });
    Plotly.newPlot(node, traces, {...L, yaxis:{...L.yaxis,title:"$/Share"}}, {displayModeBar:false,responsive:true});
  }

  function resolveStrip(area) {
    const panel = scopedSelect(`.panel[data-area="${area}"]`);
    if (panel) {
      let strip = panel.querySelector(".strip");
      if (!strip) {
        strip = document.createElement("div");
        strip.className = "strip";
        panel.prepend(strip);
      }
      return strip;
    }
    return null;
  }

  function renderCards(payload){
    const tickers = (payload.meta?.tickers && payload.meta.tickers.length
      ? payload.meta.tickers.slice(0,3)
      : Object.keys(payload.cards || {}).filter(k => k !== "SP500" && k !== "SPX").slice(0,3));
    const companies = payload.meta?.companies || {};
    ["kpiA","kpiB","kpiC"].forEach((id) => {
      const el = scopedQuery(id);
      if (el) el.innerHTML = "";
    });
    tickers.forEach((ticker, index) => {
      const area = ["kpiA","kpiB","kpiC"][index];
      if (!area) return;
      const labelNode = resolveStrip(area);
      const company = companies[ticker];
      const text = company && company !== ticker ? `${company} (${ticker})` : ticker;
      if (labelNode) {
        labelNode.textContent = text;
      } else if (console && typeof console.warn === "function") {
        console.warn(`CFI Compare: missing strip node for area ${area}`);
      }
      kv(area, payload.cards?.[ticker] || {});
    });
    ["kpiA","kpiB","kpiC"].forEach((area, index) => {
      if (index >= tickers.length) {
        const strip = resolveStrip(area);
        if (strip) strip.textContent = "â";
        kv(area, {});
      }
    });
    const benchStrip = resolveStrip("benchmark");
    const benchLabel = payload.meta?.benchmark ? `Benchmark (${payload.meta.benchmark})` : "Benchmark";
    if (benchStrip) benchStrip.textContent = benchLabel;
    kv("kpiBench", payload.cards?.SP500 || payload.cards?.SPX || {});
  }

  window.CFIX = {
    render(payload){
      ensureCompareLayout();
      if (!window.Plotly || typeof window.Plotly.newPlot !== "function") {
        const retries = Number(payload?.__plotlyRetry || 0);
        if (retries < 5) {
          setTimeout(() => {
            const next = { ...(payload || {}), __plotlyRetry: retries + 1 };
            window.CFIX.render(next);
          }, 120);
        } else {
          scopedSelectAll(".plot").forEach((node) => {
            if (node) node.innerHTML = '<div class="cfi-error">Chart library unavailable.</div>';
          });
        }
        return;
      }
      // header + kpi cards
      const peerNode = scopedQuery("cfix-peerset");
      if (peerNode) peerNode.textContent = payload.meta?.peerset || "";
      else if (console && typeof console.warn === "function") console.warn("CFI Compare: peerset node missing");
      const dateNode = scopedQuery("cfix-date");
      if (dateNode) dateNode.textContent = payload.meta?.date || "";
      else if (console && typeof console.warn === "function") console.warn("CFI Compare: date node missing");
      renderCards(payload);

      // dense table
      renderCompareTable("compareTable", payload.table);

      // charts
      plotFootball("compareFootball", payload.football || []);
      plotMultiLine("revTrend", payload.series?.years || [], payload.series?.revenue || {}, "Revenue ($B)");
      plotMultiLine("ebitdaTrend", payload.series?.years || [], payload.series?.ebitda || {}, "EBITDA ($B)");
      plotPeerScatter("marginVsPeers", payload.scatter || []);
      const valuationMap = {...payload.valSummary};
      delete valuationMap.case;
      plotValSummary(
        "valuationSummary",
        payload.valSummary?.case || [],
        valuationMap,
        payload.meta?.tickers || []
      );
    }
  };
})();
