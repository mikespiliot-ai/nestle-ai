"""
Dashboard and alert HTML report generation.
"""

import json
import os
from datetime import datetime
from typing import Dict

from config import REPORTS_DIR


def generate_dashboard(portfolio_state: Dict, metrics: Dict, memory_data: Dict) -> str:
    """Generate the live dashboard HTML. Returns the file path."""
    nav_history = portfolio_state.get("nav_history", [])
    holdings = portfolio_state.get("holdings", {})
    nav = portfolio_state.get("nav", 0)
    cash = portfolio_state.get("cash", 0)
    initial = 10000

    dates_js = json.dumps([e["date"] for e in nav_history])
    navs_js = json.dumps([e["nav"] for e in nav_history])

    holdings_rows = ""
    for sym, h in holdings.items():
        holdings_rows += f"""
        <tr>
          <td>{sym}</td>
          <td>{h.get('quantity', 0):.6f}</td>
          <td>${h.get('avg_entry_price', 0):.4f}</td>
        </tr>"""

    sharpe_ratios = memory_data.get("all_sharpe_ratios", {})
    sharpe_rows = "".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
        for k, v in sorted(sharpe_ratios.items(), key=lambda x: -x[1])
    )

    emergency_log = memory_data.get("emergency_log", [])
    alert_rows = "".join(
        f"<tr><td>{e.get('timestamp','')}</td><td>{e.get('action','')}</td>"
        f"<td>{e.get('emergency_score',0):.3f}</td><td>{e.get('source','')}</td></tr>"
        for e in reversed(emergency_log[-10:])
    )

    s1 = memory_data.get("s1_signals", {"buys": [], "sells": []})
    s2 = memory_data.get("s2_signals", {"buys": [], "sells": []})
    selected = memory_data.get("selected_universe", [])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{5 * 60}">
<title>Crypto Portfolio Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; }}
  h2 {{ color: #79c0ff; border-bottom: 1px solid #30363d; padding-bottom: 6px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .card .val {{ font-size: 1.8em; font-weight: bold; color: #58a6ff; }}
  .card .lbl {{ font-size: 0.85em; color: #8b949e; }}
  .green {{ color: #3fb950; }}
  .red {{ color: #f85149; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
  th {{ background: #21262d; padding: 8px; text-align: left; color: #8b949e; font-size: 0.85em; }}
  td {{ padding: 8px; border-bottom: 1px solid #21262d; font-size: 0.9em; }}
  tr:hover td {{ background: #161b22; }}
  .chart-wrap {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin: 2px; }}
  .badge-buy {{ background: #196c2e; color: #3fb950; }}
  .badge-sell {{ background: #5c1b1b; color: #f85149; }}
  .badge-sel {{ background: #1c3a6e; color: #58a6ff; }}
  .status-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .status-box {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; flex: 1; min-width: 160px; }}
</style>
</head>
<body>
<h1>Crypto Portfolio Dashboard <small style="font-size:0.5em;color:#8b949e">(Paper Trading)</small></h1>
<p style="color:#8b949e">Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &bull; Auto-refreshes every 5 minutes</p>

<div class="grid">
  <div class="card">
    <div class="lbl">Current NAV</div>
    <div class="val">${nav:,.2f}</div>
  </div>
  <div class="card">
    <div class="lbl">Total Return</div>
    <div class="val {'green' if nav >= initial else 'red'}">{((nav/initial-1)*100):+.2f}%</div>
  </div>
  <div class="card">
    <div class="lbl">Sharpe Ratio</div>
    <div class="val">{metrics.get('sharpe_ratio', 0):.3f}</div>
  </div>
  <div class="card">
    <div class="lbl">Max Drawdown</div>
    <div class="val red">{metrics.get('max_drawdown_pct', 0):.1f}%</div>
  </div>
  <div class="card">
    <div class="lbl">Annualized Return</div>
    <div class="val">{metrics.get('annualized_return_pct', 0):.1f}%</div>
  </div>
  <div class="card">
    <div class="lbl">Cash Available</div>
    <div class="val">${cash:,.2f}</div>
  </div>
  <div class="card">
    <div class="lbl">Active Method</div>
    <div class="val" style="font-size:1em">{memory_data.get('best_method', 'N/A')}</div>
  </div>
  <div class="card">
    <div class="lbl">Win Rate</div>
    <div class="val">{metrics.get('win_rate_pct', 0):.1f}%</div>
  </div>
</div>

<div class="chart-wrap">
  <h2>NAV Over Time</h2>
  <canvas id="navChart" height="80"></canvas>
</div>

<h2>Current Holdings</h2>
<table>
  <tr><th>Symbol</th><th>Quantity</th><th>Avg Entry</th></tr>
  {holdings_rows if holdings_rows else '<tr><td colspan="3" style="color:#8b949e">No holdings yet</td></tr>'}
</table>

<h2>Signal Panel</h2>
<div class="status-row">
  <div class="status-box">
    <strong>LLM-S (Layer 1a) Buys</strong><br>
    {''.join(f'<span class="badge badge-buy">{s}</span>' for s in s1.get('buys', [])[:15]) or '<em>None</em>'}
  </div>
  <div class="status-box">
    <strong>Sentiment (Layer 1b) Buys</strong><br>
    {''.join(f'<span class="badge badge-buy">{s}</span>' for s in s2.get('buys', [])[:15]) or '<em>None</em>'}
  </div>
  <div class="status-box">
    <strong>Consensus Selected</strong><br>
    {''.join(f'<span class="badge badge-sel">{s}</span>' for s in selected[:15]) or '<em>None</em>'}
  </div>
</div>

<h2>Precision Matrix Sharpe Rankings</h2>
<table>
  <tr><th>Method × Objective</th><th>OOS Sharpe</th></tr>
  {sharpe_rows if sharpe_rows else '<tr><td colspan="2" style="color:#8b949e">No data yet</td></tr>'}
</table>

<h2>Emergency Alert Log</h2>
<table>
  <tr><th>Timestamp</th><th>Action</th><th>Score</th><th>Source</th></tr>
  {alert_rows if alert_rows else '<tr><td colspan="4" style="color:#8b949e">No emergency events</td></tr>'}
</table>

<script>
const ctx = document.getElementById('navChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {dates_js},
    datasets: [{{
      label: 'Portfolio NAV ($)',
      data: {navs_js},
      borderColor: '#58a6ff',
      backgroundColor: 'rgba(88,166,255,0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
      y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    path = os.path.join(REPORTS_DIR, "dashboard.html")
    with open(path, "w") as f:
        f.write(html)
    return path


def generate_alert_html(event: Dict) -> str:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Emergency Alert</title>
<style>body{{font-family:sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
.alert{{border:2px solid #f85149;border-radius:8px;padding:20px;max-width:600px}}
h1{{color:#f85149}}.key{{color:#8b949e;font-size:.85em}}.val{{font-size:1.1em}}</style>
</head><body>
<div class="alert">
  <h1>⚠ EMERGENCY REBALANCING TRIGGERED</h1>
  <p class="key">Timestamp</p><p class="val">{event.get('timestamp')}</p>
  <p class="key">Action</p><p class="val">{event.get('action')}</p>
  <p class="key">Composite Score</p><p class="val">{event.get('emergency_score', 0):.4f}</p>
  <p class="key">Trigger Source</p><p class="val">{event.get('source')}</p>
  <p class="key">Macro Score</p><p class="val">{event.get('macro_score', 0):.3f}</p>
  <p class="key">Onchain Score</p><p class="val">{event.get('onchain_score', 0):.3f}</p>
  <p class="key">Social Panic Score</p><p class="val">{event.get('social_score', 0):.3f}</p>
</div>
</body></html>"""

    ts = event.get("timestamp", datetime.utcnow().isoformat())[:10]
    path = os.path.join(REPORTS_DIR, f"ALERT_{ts}.html")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(html)
    return path
