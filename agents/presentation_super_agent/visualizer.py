from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.azure_models import azure_llm
from LLMs.ollama_llm import ollama_llm



class VisualizerOutput(BaseModel):
    visualization: str = Field(..., description="The visualization code in HTML/CSS format.")
    
system_prompt = """
    You are the Graph Maker Agent.
    Convert this insights into visualization code (HTML, CSS, JavaScript):
    Try to include interactive elements where appropriate.
    Leave space for dynamic data loading and user interactions.
    You are not allowed to write any emojis.
"""
user_prompt = """
    insights: {insights}
    message from the orchestrator: {message}
"""

template = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Shuffle Palette Dashboard</title>
  <style>
    /* ---------- Core palette (tweak these three values to change the theme) ---------- */
    :root {{
      --left: #0b2740;   /* dark navy (matches left block) */
      --mid:  #114a7b;   /* deep blue (matches middle block) */
      --right:#7ED321;   /* lime green (matches right block) */

      --accent: var(--mid);
      --page-bg: #f6f8fb;
      --card-bg: #ffffff;
      --ink: #0f172a;
      --muted: #64748b;
      --shadow: 0 10px 24px rgba(15, 23, 42, .08);
      --ring: rgba(17, 74, 123, .25);
      --radius: 16px;
    }}

    /* ---------- Reset / base ---------- */
    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font: 14px/1.45 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
      color: var(--ink);
      background: var(--page-bg);
    }}
    a {{ color: inherit; text-decoration: none; }}
    .visually-hidden {{ position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; clip: rect(0 0 0 0); overflow: hidden; }}

    /* ---------- Layout ---------- */
    .app {{
      display: grid;
      grid-template-rows: 56px 1fr;
      grid-template-areas:
        "header"
        "main";
      min-height: 100dvh;
    }}

    .sidebar {{
      grid-area: sidebar;
      background: linear-gradient(180deg, var(--left), var(--mid));
      color: #fff;
      padding: 20px 16px;
    }}
    .brand {{
      display: flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: .2px;
    }}
    .brand-badge {{
      width: 28px; height: 28px; display: grid; place-items: center;
      border-radius: 8px; background: var(--right); color: var(--left); font-weight: 900;
      box-shadow: 0 6px 16px rgba(0,0,0,.15);
    }}
    .nav {{ margin-top: 24px; display: grid; gap: 6px; }}
    .nav a {{ padding: 10px 12px; border-radius: 10px; color: #e8f0f7; opacity: .9; display: flex; align-items: center; gap: 10px; }}
    .nav a:hover {{ background: rgba(255,255,255,.08); opacity: 1; }}
    .nav a.active {{ background: rgba(255,255,255,.16); color: #fff; }}

    .header {{
      grid-area: header; display: flex; align-items: center; justify-content: space-between;
      padding: 12px 20px; background: #fff; box-shadow: var(--shadow); z-index: 1;
    }}
    .search {{
      position: relative; width: min(560px, 55vw);
    }}
    .search input {{
      width: 100%; height: 40px; border-radius: 999px; border: 1px solid #e5e7eb; background: #fff;
      padding: 0 42px 0 14px; outline: none; box-shadow: 0 1px 0 rgba(0,0,0,.02);
    }}
    .search input:focus {{ border-color: var(--mid); box-shadow: 0 0 0 4px var(--ring); }}
    .search .kbd {{ position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 12px; color: var(--muted); background: #f1f5f9; padding: 2px 6px; border-radius: 6px; border: 1px solid #e2e8f0; }}

    .header-actions {{ display: flex; align-items: center; gap: 12px; }}

    /* ---------- The 3-segment Shuffle button (replicates your image) ---------- */
    .shuffle-btn {{
      display: flex; border: 0; padding: 0; border-radius: 999px; overflow: hidden; cursor: pointer;
      box-shadow: var(--shadow); transition: transform .15s ease, box-shadow .2s ease;
    }}
    .shuffle-btn:focus-visible {{ outline: 3px solid var(--right); outline-offset: 3px; }}
    .shuffle-btn:hover {{ transform: translateY(-1px); box-shadow: 0 14px 30px rgba(15,23,42,.14); }}
    .shuffle-btn .seg {{ height: 42px; display: inline-flex; align-items: center; justify-content: center; color: #fff; }}
    .shuffle-btn .seg.left  {{ width: 74px; background: var(--left); }}
    .shuffle-btn .seg.mid   {{ min-width: 150px; gap: 10px; padding: 0 16px; font-weight: 700; background: var(--mid); }}
    .shuffle-btn .seg.right {{ width: 74px; background: var(--right); color: #0b3a00; font-weight: 700; }}
    .shuffle-btn svg {{ width: 18px; height: 18px; stroke: currentColor; stroke-width: 2; fill: none; }}

    .avatar {{ width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, var(--right), var(--mid)); box-shadow: 0 6px 16px rgba(0,0,0,.08); }}

    .main {{ grid-area: main; padding: 24px; }}

    .kpis {{ display: grid; gap: 12px; grid-template-columns: repeat(2, 1fr); }}
    .card {{ background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px; }}
    .card h3 {{ margin: 0 0 8px; font-size: 13px; letter-spacing: .3px; text-transform: uppercase; color: var(--muted); }}
    .kpi {{ display: flex; align-items: baseline; gap: 8px; }}
    .kpi .num {{ font-size: 28px; font-weight: 800; color: var(--accent); letter-spacing: .5px; }}
    .kpi .delta {{ font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: rgba(126, 211, 33, .12); color: #11640a; }}

    .content-grid {{ margin-top: 14px; display: grid; grid-template-columns: 1fr; gap: 14px; align-items: start; }}

    .chart-wrap {{ padding: 0; overflow: hidden; }}
    .chart-head {{ display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid #eef2f7; }}
    .chart-title {{ font-weight: 800; }}
    canvas {{ display: block; width: 100%; height: 304px; }}

    .table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    .table th, .table td {{ text-align: left; padding: 12px; border-bottom: 1px solid #eef2f7; }}
    .pill {{ font-size: 12px; padding: 4px 8px; border-radius: 999px; background: #f1f5f9; }}

    .progress {{ height: 8px; width: 100%; background: #f1f5f9; border-radius: 999px; overflow: hidden; }}
    .progress .bar {{ height: 100%; width: 0%; background: var(--accent); transition: width .8s ease; }}

    /* ---------- Responsive ---------- */
    @media (max-width: 380px) {{
      .kpis {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header class="header">
      <div class="brand">
        <div class="brand-badge">S</div>
        <div>ShuffleDash</div>
      </div>
      <button id="shuffle" class="shuffle-btn" title="Shuffle palette">
        <span class="seg left" aria-hidden="true"></span>
        <span class="seg mid"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 4h3v3"/><path d="M21 7c-3 0-5 2-7 5s-4 5-7 5H3"/><path d="M3 7h4c3 0 5 2 7 5 .6.8 1.2 1.6 1.8 2.3"/><path d="M18 20h3v-3"/></svg>Shuffle</span>
        <span class="seg right" aria-hidden="true"></span>
      </button>
    </header>

    <main class="main">
      <section class="kpis">
        <div class="card">
          <h3>Revenue</h3>
          <div class="kpi"><div class="num" id="rev">$0</div><span class="delta" id="revDelta">+0.0%</span></div>
        </div>
        <div class="card">
          <h3>New Users</h3>
          <div class="kpi"><div class="num" id="users">0</div><span class="pill">30d</span></div>
        </div>
        <div class="card">
          <h3>Conversion</h3>
          <div class="kpi"><div class="num" id="conv">0%</div><span class="pill">A/B</span></div>
        </div>
        <div class="card">
          <h3>NPS</h3>
          <div class="kpi"><div class="num" id="nps">0</div><span class="pill">QTD</span></div>
        </div>
      </section>

      <section class="content-grid">
        <div class="card chart-wrap">
          <div class="chart-head"><div class="chart-title">Monthly Sales</div><div class="pill" id="legend">Accent: #114a7b</div></div>
          <canvas id="chart" width="900" height="340" role="img" aria-label="Bar chart of monthly sales"></canvas>
        </div>

        <div class="card">
          <h3>Projects</h3>
          <table class="table" aria-label="Project progress">
            <thead>
              <tr><th>Project</th><th>Status</th><th style="width:40%">Progress</th></tr>
            </thead>
            <tbody id="projects">
              <!-- rows injected by JS -->
            </tbody>
          </table>
        </div>
              <div class="card chart-wrap">
          <div class="chart-head"><div class="chart-title">Traffic (Line)</div></div>
          <canvas id="lineChart" width="900" height="340" role="img" aria-label="Line graph of monthly traffic"></canvas>
        </div>

        <div class="card chart-wrap">
          <div class="chart-head"><div class="chart-title">Channel Mix (Pie)</div></div>
          <canvas id="pieChart" width="900" height="340" role="img" aria-label="Pie chart of channels"></canvas>
        </div>
      </section>
    </main>
  </div>

  <script>
    // ---------- Helpers ----------
    const $ = (sel) => document.querySelector(sel);
    const setCSSVar = (name, value) => document.documentElement.style.setProperty(name, value);

    // Base palette as hex values (left, mid, right). Matches the button blocks.
    let palette = [getComputedStyle(document.documentElement).getPropertyValue('--left').trim(),
                   getComputedStyle(document.documentElement).getPropertyValue('--mid').trim(),
                   getComputedStyle(document.documentElement).getPropertyValue('--right').trim()];

    // ---------- Data (demo) ----------
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    let data = months.map(() => Math.floor(Math.random()*40)+10);
    // Smooth line series derived from bar data
    let lineData = data.map((v,i,arr)=> Math.round((v + (arr[i-1]||v) + (arr[i+1]||v))/3));
    // Pie chart demo data (3 slices to match palette)
    const pieData = [
      {{label:'Direct',  value: 42}},
      {{label:'Referral',value: 26}},
      {{label:'Ads',     value: 32}},
    ];

    const projects = [
      {{ name: 'Mercury', status: 'On track',    pct: 76 }},
      {{ name: 'Aurora',  status: 'At risk',     pct: 42 }},
      {{ name: 'Nebula',  status: 'Blocked',     pct: 18 }},
      {{ name: 'Zephyr',  status: 'On track',    pct: 64 }},
      {{ name: 'Ion',     status: 'Monitoring',  pct: 53 }},
    ];

    // ---------- Simple bar chart (no external libs) ----------
    function drawChart() {{
      const canvas = $('#chart');
      const ctx = canvas.getContext('2d');
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0,0,W,H);

      // Padding and axes
      const pad = 36, base = H - pad; // bottom baseline
      ctx.lineWidth = 1;
      ctx.strokeStyle = '#e5e7eb';
      for (let y = 0; y <= 4; y++) {{ // grid lines
        const gy = pad + (base - pad) * (y/4);
        ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke();
      }}

      // Bars
      const max = Math.max(...data) * 1.2;
      const n = data.length;
      const gap = 8;
      const barW = ((W - pad*2) - gap*(n-1)) / n;

      for (let i = 0; i < n; i++) {{
        const x = pad + i*(barW + gap);
        const h = Math.round((data[i] / max) * (base - pad));
        const y = base - h;
        // Alternate through the 3 palette colors
        const color = [palette[0], palette[1], palette[2]][i % 3];
        ctx.fillStyle = color;
        ctx.fillRect(x, y, barW, h);
      }}

      // Axis labels
      ctx.fillStyle = '#475569';
      ctx.font = '12px system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica Neue,Arial,Noto Sans,sans-serif';
      ctx.textAlign = 'center';
      months.forEach((m, i) => {{
        const x = pad + i*(barW + gap) + barW/2;
        ctx.fillText(m, x, H - 10);
      }});

      // Update legend
      $('#legend').textContent = `Accent: ${{getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()}}`;
    }}

    // ---------- Line & Pie charts ----------
    function drawLineChart(){{
      const canvas = document.getElementById('lineChart');
      const ctx = canvas.getContext('2d');
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0,0,W,H);

      const pad = 28, base = H - pad;
      ctx.lineWidth = 1; ctx.strokeStyle = '#e5e7eb';
      for (let y = 0; y <= 4; y++) {{
        const gy = pad + (base - pad) * (y/4);
        ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke();
      }}

      const max = Math.max(...lineData) * 1.2;
      const n = lineData.length;
      const xGap = (W - pad*2) / (n - 1);

      // Line
      ctx.beginPath();
      for (let i=0;i<n;i++){{
        const x = pad + i*xGap;
        const y = base - Math.round((lineData[i] / max) * (base - pad));
        if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }}
      ctx.lineWidth = 3; ctx.strokeStyle = palette[2];
      ctx.stroke();

      // Points
      ctx.fillStyle = palette[1];
      for (let i=0;i<n;i++){{
        const x = pad + i*xGap;
        const y = base - Math.round((lineData[i] / max) * (base - pad));
        ctx.beginPath(); ctx.arc(x,y,3.5,0,Math.PI*2); ctx.fill();
      }}

      // Labels
      ctx.fillStyle = '#475569';
      ctx.font = '12px system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica Neue,Arial,Noto Sans,sans-serif';
      ctx.textAlign = 'center';
      months.forEach((m, i) => {{
        const x = pad + i*xGap; ctx.fillText(m, x, H - 8);
      }});
    }}

    function drawPieChart(){{
      const canvas = document.getElementById('pieChart');
      const ctx = canvas.getContext('2d');
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0,0,W,H);

      const cx = W/2, cy = H/2 + 4; const r = Math.min(W,H)/2 - 36; const inner = r*0.6;
      const colors = [palette[0], palette[1], palette[2]];
      const total = pieData.reduce((s,p)=>s+p.value,0);
      let a0 = -Math.PI/2;

      // Slices
      pieData.forEach((p,i)=>{{
        const a1 = a0 + (p.value/total) * Math.PI*2;
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.arc(cx,cy,r,a0,a1); ctx.closePath();
        ctx.fillStyle = colors[i % colors.length]; ctx.fill();

        // Label
        const mid = (a0 + a1)/2; const lx = cx + Math.cos(mid)*(r+12); const ly = cy + Math.sin(mid)*(r+12);
        ctx.fillStyle = '#334155'; ctx.font = '12px system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica Neue,Arial,Noto Sans,sans-serif';
        ctx.textAlign = mid > Math.PI/2 || mid < -Math.PI/2 ? 'right' : 'left';
        ctx.fillText(`${{p.label}} ${{(p.value*100/total).toFixed(0)}}%`, lx, ly);
        a0 = a1;
      }});

      // Donut hole
      ctx.beginPath(); ctx.arc(cx,cy,inner,0,Math.PI*2); ctx.fillStyle = '#fff'; ctx.fill();
      ctx.fillStyle = '#334155'; ctx.font = '600 13px system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica Neue,Arial,Noto Sans,sans-serif';
      ctx.textAlign = 'center'; ctx.fillText('Channel Mix', cx, cy+3);
    }}

    // Mobile-friendly canvas sizing (crisp on DPR screens)
    function resizeCharts(){{
      const dpr = window.devicePixelRatio || 1;
      const sizes = {{ chart: 220, lineChart: 220, pieChart: 260 }};
      Object.keys(sizes).forEach(id=>{{
        const c = document.getElementById(id);
        if(!c) return;
        const cssH = sizes[id];
        c.style.height = cssH + 'px';
        const cssW = c.clientWidth;
        c.width  = Math.max(300, Math.floor(cssW * dpr));
        c.height = Math.floor(cssH * dpr);
      }});
      drawChart();
      drawLineChart();
      drawPieChart();
    }}

    window.addEventListener('resize', resizeCharts);

    // ---------- KPI animation ----------
    function animateNumber(el, to, prefix = '', suffix = '') {{
      const start = 0; const dur = 800; const t0 = performance.now();
      function tick(t){{
        const p = Math.min(1, (t - t0) / dur);
        const val = Math.round(start + (to-start)*p);
        el.textContent = prefix + val.toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }}
      requestAnimationFrame(tick);
    }}

    function hydrateKpis(){{
      const rev = Math.floor(25000 + Math.random()*50000);
      const delta = (Math.random()*8+1).toFixed(1);
      animateNumber($('#rev'), rev, '$');
      $('#revDelta').textContent = `+${{delta}}%`;
      animateNumber($('#users'), Math.floor(800 + Math.random()*2200));
      animateNumber($('#conv'), (Math.random()*7+2).toFixed(1), '', '%');
      animateNumber($('#nps'), Math.floor(30 + Math.random()*40));
    }}

    // ---------- Projects table ----------
    function renderProjects(){{
      const tbody = $('#projects');
      tbody.innerHTML = '';
      projects.forEach(p => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${{p.name}}</td>
          <td><span class="pill">${{p.status}}</span></td>
          <td>
            <div class="progress" aria-hidden="true"><div class="bar" style="width:${{p.pct}}%"></div></div>
          </td>`;
        tbody.appendChild(tr);
      }});
    }}

    // ---------- Shuffle palette / theme ----------
    function rotate(arr){{ arr.push(arr.shift()); return arr; }}
    function applyPalette(){{
      setCSSVar('--left',  palette[0]);
      setCSSVar('--mid',   palette[1]);
      setCSSVar('--right', palette[2]);
      setCSSVar('--accent', palette[1]); // mid drives accents
      drawChart();
      drawLineChart();
      drawPieChart();
      // recolor progress bars instantly
      document.querySelectorAll('.progress .bar').forEach(el => el.style.background = palette[1]);
      // update avatar gradient
      const av = document.querySelector('.avatar'); if (av) {{ av.style.background = `linear-gradient(135deg, ${{palette[2]}}, ${{palette[1]}})`; }}
    }}

    $('#shuffle').addEventListener('click', () => {{
      // Rotate palette order: left -> mid -> right -> left
      rotate(palette);
      applyPalette();
    }});

    // First paint
    renderProjects();
    hydrateKpis();
    resizeCharts();
    applyPalette();
  </script>
</body>
</html>
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user","Here is a template you can follow: " + template),
    ("human", user_prompt)
])

Visualizer = prompt | gemini_llm.with_structured_output(VisualizerOutput)
