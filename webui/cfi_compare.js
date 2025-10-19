(function(){
  const L = {
    paper_bgcolor:"#fff", plot_bgcolor:"#fff",
    font:{family:"Inter, Open Sans, Roboto", color:"#003366", size:12},
    xaxis:{gridcolor:"#E6E9EF", zeroline:false},
    yaxis:{gridcolor:"#E6E9EF", zeroline:false},
    legend:{orientation:"h", y:1.16, x:1.0, xanchor:"right", font:{size:10}},
    margin:{l:48,r:36,t:24,b:36}
  };
  const money = n => (n==null||isNaN(n)) ? "—" : ((s=>`${s[0]}$${s[1]}${s[2]}`)((() => {
    const sign = n<0?"-":""; const a=Math.abs(n);
    const unit = a>=1e9?"B":a>=1e6?"M":a>=1e3?"K":""; const v = a>=1e9?a/1e9:a>=1e6?a/1e6:a>=1e3?a/1e3:a;
    return [sign, v.toFixed(v>=100?0:v>=10?1:2), unit];
  })()));
  const pct   = n => (n==null||isNaN(n)) ? "—" : `${(+n).toFixed(1)}%`;
  const xfmt  = n => (n==null||isNaN(n)) ? "—" : `${(+n).toFixed(2)}×`;

  function kv(container, obj){
    const el=document.getElementById(container); el.innerHTML="";
    const pairs=Object.entries(obj);
    for(const [k,v] of pairs){
      const L=document.createElement("div"); L.textContent=k;
      const R=document.createElement("div");
      if (typeof v === "number") {
        R.textContent = money(v);
      } else {
        R.textContent = v ?? "—";
      }
      el.append(L,R);
    }
  }

  function renderCompareTable(id, table){
    const root=document.getElementById(id); root.innerHTML="";
    const t=document.createElement("table"); t.className="cfix-table";
    const thead=document.createElement("thead"); const trh=document.createElement("tr");
    const columns = Array.isArray(table?.columns) ? table.columns : [];
    for(const col of columns){ const th=document.createElement("th"); th.textContent=col; trh.append(th); }
    thead.append(trh); t.append(thead);
    const tb=document.createElement("tbody");
    const metricColumns = columns.slice(1);
    const benchLabel = metricColumns[metricColumns.length-1];
    const formatValue = (value, type) => {
      if (value == null || Number.isNaN(value)) return "—";
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
    const node = document.getElementById(div);
    const entries = Object.entries(seriesMap || {}).filter(([,vals])=>Array.isArray(vals) && vals.length);
    if (!node) return;
    if (!entries.length || !(years || []).length) {
      node.innerHTML = "<div class=\"cfi-error\">No data available</div>";
      return;
    }
    const traces = entries.map(([ticker,vals])=>({
      type:"scatter", x:years, y:vals, mode:"lines", name:ticker
    }));
    Plotly.newPlot(node, traces, {...L, yaxis:{...L.yaxis,title:label}}, {displayModeBar:false,responsive:true});
  }

  function plotFootball(div, football){
    // Horizontal ranged bars per company and method
    const node = document.getElementById(div);
    if (!node) return;
    const filtered = (football || []).filter(entry => Array.isArray(entry?.ranges) && entry.ranges.length);
    if (!filtered.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valuation ranges</div>";
      return;
    }
    const traces=[];
    let y=0, yticks=[];
    for(const comp of filtered){
      for(const rng of comp.ranges){
        traces.push({type:"scatter", mode:"lines", x:[rng.lo,rng.hi], y:[y,y],
          name:`${comp.ticker} — ${rng.name}`, line:{width:6,color:"#003366"}});
        y+=1; yticks.push(`${comp.ticker} • ${rng.name}`);
      }
      y+=0.5; // small gap between companies
    }
    const layout={...L, xaxis:{...L.xaxis,title:"$/Share"}, yaxis:{showgrid:false, tickmode:"array", tickvals:[...Array(y).keys()], ticktext:yticks}};
    Plotly.newPlot(node, traces, layout, {displayModeBar:false,responsive:true});
  }

  function plotPeerScatter(div, data){
    const node = document.getElementById(div);
    if (!node) return;
    const filtered = (data || []).filter(d => d && typeof d.x === "number" && typeof d.y === "number");
    if (!filtered.length) {
      node.innerHTML = "<div class=\"cfi-error\">No peer data</div>";
      return;
    }
    const trace={type:"scatter", mode:"markers+text",
      x=filtered.map(d=>d.x), y=filtered.map(d=>d.y), text=filtered.map(d=>d.ticker), textposition:"top center",
      marker:{size=filtered.map(d=>Math.sqrt(Math.max(d.size || 1,1))*2.2), color:"#003366", opacity:0.8}};
    Plotly.newPlot(node, [trace], {...L, xaxis:{...L.xaxis,title:"Net margin (%)"},
      yaxis:{...L.yaxis,title:"ROE (%)"}}, {displayModeBar:false,responsive:true});
  }

  function plotValSummary(div, cases, perCompany, order){
    const node = document.getElementById(div);
    if (!node) return;
    const tickers = (order || Object.keys(perCompany || {}))
      .filter(t => Array.isArray(perCompany?.[t]));
    if (!tickers.length || !cases.length) {
      node.innerHTML = "<div class=\"cfi-error\">No valuation summary</div>";
      return;
    }
    const traces = tickers.map(t=>({
      type:"bar", x:cases, y:perCompany[t], name:t, marker:{line:{width:0}}
    }));
    Plotly.newPlot(node, traces, {...L, yaxis:{...L.yaxis,title:"$/Share"}}, {displayModeBar:false,responsive:true});
  }

  function renderCards(payload){
    const tickers = (payload.meta?.tickers && payload.meta.tickers.length
      ? payload.meta.tickers.slice(0,3)
      : Object.keys(payload.cards || {}).filter(k => k !== "SP500" && k !== "SPX").slice(0,3));
    const companies = payload.meta?.companies || {};
    const strips = ["kpiA","kpiB","kpiC"].map(area => document.querySelector(`.panel[data-area="${area}"] .strip`));
    ["kpiA","kpiB","kpiC"].forEach(id => { const el=document.getElementById(id); if (el) el.innerHTML=""; });
    tickers.forEach((ticker, index) => {
      const area = ["kpiA","kpiB","kpiC"][index];
      if (!area) return;
      const labelNode = strips[index];
      const company = companies[ticker];
      const text = company && company !== ticker ? `${company} (${ticker})` : ticker;
      if (labelNode) labelNode.textContent = text;
      kv(area, payload.cards?.[ticker] || {});
    });
    ["kpiA","kpiB","kpiC"].forEach((area, index) => {
      if (index >= tickers.length) {
        const strip = strips[index];
        if (strip) strip.textContent = "—";
        kv(area, {});
      }
    });
    const benchStrip = document.querySelector('.panel[data-area="benchmark"] .strip');
    const benchLabel = payload.meta?.benchmark ? `Benchmark (${payload.meta.benchmark})` : "Benchmark";
    if (benchStrip) benchStrip.textContent = benchLabel;
    kv("kpiBench", payload.cards?.SP500 || payload.cards?.SPX || {});
  }

  window.CFIX = {
    render(payload){
      // header + kpi cards
      document.getElementById("cfix-peerset").textContent = payload.meta?.peerset || "";
      document.getElementById("cfix-date").textContent    = payload.meta?.date || "";
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
