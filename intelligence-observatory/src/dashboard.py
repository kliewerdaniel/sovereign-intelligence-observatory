"""Intelligence Observatory - Chart.js Dashboard Router

Serves a self-contained HTML dashboard at ``/dashboard`` that consumes
the existing REST endpoints for timeline, obsolescent prompts, and signal
correlations.
"""

import logging
from string import Template
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from .database import ObservatoryDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_db():
    db = ObservatoryDatabase()
    yield db
    await db.close()


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sovereign Intelligence Observatory - Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; }
h1 { color: #58a6ff; margin-bottom: 24px; }
h2 { color: #8b949e; margin-bottom: 12px; font-size: 18px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 24px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.chart-container { position: relative; height: 280px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #21262d; }
th { color: #8b949e; font-weight: 600; }
tr:hover { background: #1c2128; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge-declining { background: #d73a4a33; color: #f85149; border: 1px solid #d73a4a55; }
.badge-stable { background: #58a6ff33; color: #58a6ff; border: 1px solid #58a6ff55; }
.badge-improving { background: #3fb95033; color: #3fb950; border: 1px solid #3fb95055; }
.stats-bar { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 24px; min-width: 140px; }
.stat-label { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { color: #c9d1d9; font-size: 28px; font-weight: 700; margin-top: 4px; }
.error { color: #f85149; padding: 24px; text-align: center; }
.loading { color: #8b949e; padding: 24px; text-align: center; }
</style>
</head>
<body>
<h1>Sovereign Intelligence Observatory</h1>
<div class="stats-bar" id="stats-bar">
  <div class="stat"><div class="stat-label">Timeline Entries</div><div class="stat-value" id="stat-timeline">-</div></div>
  <div class="stat"><div class="stat-label">Obsolescent Prompts</div><div class="stat-value" id="stat-prompts">-</div></div>
  <div class="stat"><div class="stat-label">Unused Memories</div><div class="stat-value" id="stat-memories">-</div></div>
  <div class="stat"><div class="stat-label">Signal Correlations</div><div class="stat-value" id="stat-correlations">-</div></div>
  <div class="stat"><div class="stat-label">Capability Changes</div><div class="stat-value" id="stat-capability">-</div></div>
</div>
<div class="grid">
  <div class="card">
    <div class="card-header"><h2>Timeline: Recipes per Day</h2></div>
    <div class="chart-container"><canvas id="timelineChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Timeline: Capability Index</h2></div>
    <div class="chart-container"><canvas id="capabilityChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Obsolescent Prompts</h2></div>
    <div class="chart-container" style="height:auto;min-height:200px;">
      <table><thead><tr><th>Prompt</th><th>Uses</th><th>Relevance</th><th>Trend</th></tr></thead>
      <tbody id="prompts-table"><tr><td colspan="4" class="loading">Loading...</td></tr></tbody></table>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Signal Correlations</h2></div>
    <div class="chart-container" style="height:auto;min-height:200px;">
      <table><thead><tr><th>Signal</th><th>Coefficient</th><th>p-value</th><th>Significance</th></tr></thead>
      <tbody id="signals-table"><tr><td colspan="4" class="loading">Loading...</td></tr></tbody></table>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Capability Changes</h2></div>
    <div class="chart-container" style="height:auto;min-height:200px;">
      <div id="capability-content"><p class="loading">Loading...</p></div>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Unused Memories</h2></div>
    <div class="chart-container" style="height:auto;min-height:200px;">
      <table><thead><tr><th>Memory</th><th>Uses</th><th>Last Retrieved</th></tr></thead>
      <tbody id="memories-table"><tr><td colspan="3" class="loading">Loading...</td></tr></tbody></table>
    </div>
  </div>
</div>
<script>
async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  return resp.json();
}

function fmt(v) {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'number') return v.toFixed(2);
  return String(v);
}

async function init() {
  try {
    const [stats, timeline, prompts, signals, capabilities, memories] = await Promise.all([
      fetchJSON('/api/observatory/stats'),
      fetchJSON('/api/timeline/2000-01-01/2099-12-31'),
      fetchJSON('/api/prompts/obsolescent'),
      fetchJSON('/api/signals/correlations'),
      fetchJSON('/api/capability/changes'),
      fetchJSON('/api/memories/unused'),
    ]);

    document.getElementById('stat-timeline').textContent = stats.timeline_entries || timeline.length;
    document.getElementById('stat-prompts').textContent = stats.obsolescent_prompts || prompts.length;
    document.getElementById('stat-memories').textContent = stats.unused_memories || memories.length;
    document.getElementById('stat-correlations').textContent = stats.signal_correlations || signals.length;
    document.getElementById('stat-capability').textContent = stats.capability_changes || 
      ((capabilities.regressions?.length || 0) + (capabilities.improvements?.length || 0));

    if (timeline.length) {
      const labels = timeline.map(e => e.date || '');
      const recipeCounts = timeline.map(e => e.recipe_count || 0);
      const capIndices = timeline.map(e => e.capability_index || 1.0);

      new Chart(document.getElementById('timelineChart'), {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Recipes', data: recipeCounts, backgroundColor: '#58a6ff88', borderColor: '#58a6ff', borderWidth: 1 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { x: { ticks: { color: '#8b949e' } }, y: { beginAtZero: true, ticks: { color: '#8b949e' } } } }
      });

      new Chart(document.getElementById('capabilityChart'), {
        type: 'line',
        data: { labels, datasets: [{ label: 'Capability Index', data: capIndices, borderColor: '#3fb950', backgroundColor: '#3fb95033', fill: true, tension: 0.3 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { x: { ticks: { color: '#8b949e' } }, y: { min: 0, ticks: { color: '#8b949e' } } } }
      });
    }

    if (prompts.length) {
      document.getElementById('prompts-table').innerHTML = prompts.map(p => 
        '<tr><td>' + fmt(p.prompt_name || p.prompt_id) + '</td><td>' + p.usage_count + '</td><td>' + fmt(p.avg_relevance) + '</td>' +
        '<td><span class="badge badge-' + (p.trend || 'stable') + '">' + (p.trend || 'stable') + '</span></td></tr>'
      ).join('');
    }

    if (signals.length) {
      document.getElementById('signals-table').innerHTML = signals.map(s =>
        '<tr><td>' + fmt(s.signal_name) + '</td><td>' + fmt(s.correlation_coefficient) + '</td><td>' + fmt(s.p_value) + '</td>' +
        '<td>' + (s.significance || 'not_significant').replace('_', ' ') + '</td></tr>'
      ).join('');
    }

    if (capabilities && (capabilities.regressions?.length || capabilities.improvements?.length)) {
      let html = '';
      if (capabilities.regressions?.length) {
        html += '<h3 style="color:#f85149;margin-bottom:8px;">Regressions (' + capabilities.regressions.length + ')</h3>';
        html += '<table><thead><tr><th>Task</th><th>Score Change</th><th>Severity</th></tr></thead><tbody>';
        html += capabilities.regressions.map(c =>
          '<tr><td>' + fmt(c.task) + '</td><td style="color:#f85149;">' + fmt(c.score_change) + '</td><td>' + (c.severity || 'low') + '</td></tr>'
        ).join('');
        html += '</tbody></table>';
      }
      if (capabilities.improvements?.length) {
        html += '<h3 style="color:#3fb950;margin-top:16px;margin-bottom:8px;">Improvements (' + capabilities.improvements.length + ')</h3>';
        html += '<table><thead><tr><th>Task</th><th>Score Change</th><th>Severity</th></tr></thead><tbody>';
        html += capabilities.improvements.map(c =>
          '<tr><td>' + fmt(c.task) + '</td><td style="color:#3fb950;">+' + fmt(Math.abs(c.score_change)) + '</td><td>' + (c.severity || 'low') + '</td></tr>'
        ).join('');
        html += '</tbody></table>';
      }
      document.getElementById('capability-content').innerHTML = html;
    }

    if (memories.length) {
      document.getElementById('memories-table').innerHTML = memories.map(m =>
        '<tr><td>' + fmt(m.title || m.memory_id) + '</td><td>' + (m.usage_count || 0) + '</td><td>' + (m.last_retrieved || '-') + '</td></tr>'
      ).join('');
    }
  } catch (err) {
    document.querySelectorAll('.loading, .stat-value').forEach(el => el.textContent = 'Error: ' + err.message);
    document.querySelectorAll('tbody').forEach(tb => tb.innerHTML = '<tr><td colspan="4" class="error">Failed to load data: ' + err.message + '</td></tr>');
  }
}

init();
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(db: ObservatoryDatabase = Depends(get_db)) -> HTMLResponse:
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)
