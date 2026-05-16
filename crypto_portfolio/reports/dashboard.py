"""Dashboard generator — dark-theme HTML with Chart.js and auto-refresh."""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import DASHBOARD_REFRESH_MINUTES, REPORTS_DIR


def generate_dashboard(
    portfolio_state: Dict[str, Any],
    metrics: Dict[str, Any],
    memory_data: Dict[str, Any],
) -> str:
    """Generate an HTML dashboard and return the file path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, "dashboard.html")

    nav_history: List[Dict] = memory_data.get("nav_history", [])
    nav_labels = [r.get("timestamp", "")[:10] for r in nav_history]
    nav_values = [r.get("nav", 0.0) for r in nav_history]

    holdings = portfolio_state.get("holdings", {})
    cash = portfolio_state.get("cash", 0.0)
    mode = portfolio_state.get("mode", "NORMAL")

    sharpe_rankings: Dict[str, float] = memory_data.get("all_sharpe_ratios", {})
    sharpe_sorted = sorted(sharpe_rankings.items(), key=lambda x: x[1], reverse=True)[:10]

    consensus_buys: List[str] = memory_data.get("consensus_buys", [])
    consensus_sells: List[str] = memory_data.get("consensus_sells", [])
    best_method: str = memory_data.get("best_method", "N/A")
    macro_regime: str = memory_data.get("macro_regime", "NORMAL")
    macro_score: float = memory_data.get("macro_score", 0.0)

    alert_log: List[Dict] = memory_data.get("alert_log", [])

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    holdings_rows = "".join(
        f"<tr><td>{cid}</td><td>{h.get('quantity', 0):.6f}</td>"
        f"<td>${h.get('avg_cost', 0):.4f}</td></tr>"
        for cid, h in holdings.items()
    )

    sharpe_rows = "".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
        for k, v in sharpe_sorted
    )

    alert_rows = "".join(
        f"<tr><td>{a.get('timestamp','')[:19]}</td><td>{a.get('action','')}</td>"
        f"<td>{a.get('score',0):.3f}</td></tr>"
        for a in alert_log[-10:]
    )

    mode_color = {"NORMAL": "#00ff88", "REDUCE": "#ffaa00", "DEFENSIVE": "#ff4444",
                  "REDUCED": "#ffaa00", "HEDGED": "#ff8800"}.get(mode, "#aaaaaa")
    regime_color = {"NORMAL": "#00ff88", "REDUCE": "#ffaa00", "DEFENSIVE": "#ff4444"}.get(macro_regime, "#aaaaaa")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{DASHBOARD_REFRESH_MINUTES * 60}">
<title>Crypto Portfolio Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  body {{ background:#0d0d0d; color:#e0e0e0; font-family:monospace; margin:0; padding:20px; }}
  h1 {{ color:#00ff88; }} h2 {{ color:#aaaaff; border-bottom:1px solid #333; padding-bottom:4px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .card {{ background:#1a1a1a; border:1px solid #333; border-radius:8px; padding:16px; }}
  .metric {{ display:flex; justify-content:space-between; margin:6px 0; }}
  .metric span {{ color:#aaa; }} .metric strong {{ color:#fff; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
  th {{ color:#aaaaff; border-bottom:1px solid #333; text-align:left; padding:4px; }}
  td {{ padding:4px; border-bottom:1px solid #1e1e1e; }}
  .badge {{ padding:2px 8px; border-radius:4px; font-weight:bold; }}
  canvas {{ max-height:300px; }}
</style>
</head>
<body>
<h1>Crypto Portfolio Dashboard</h1>
<p style="color:#666">Last updated: {ts} &nbsp;|&nbsp; Mode: <span class="badge" style="background:{mode_color};color:#000">{mode}</span>
&nbsp;|&nbsp; Macro: <span class="badge" style="background:{regime_color};color:#000">{macro_regime}</span>
&nbsp;|&nbsp; Best Method: <strong style="color:#00ff88">{best_method}</strong></p>

<div class="grid">
  <div class="card">
    <h2>Performance Metrics</h2>
    <div class="metric"><span>Current NAV</span><strong>${metrics.get('current_nav', 0):.2f}</strong></div>
    <div class="metric"><span>Total Return</span><strong>{metrics.get('total_return_pct', 0):.2f}%</strong></div>
    <div class="metric"><span>Ann. Return</span><strong>{metrics.get('annualized_return_pct', 0):.2f}%</strong></div>
    <div class="metric"><span>Ann. Volatility</span><strong>{metrics.get('annualized_volatility_pct', 0):.2f}%</strong></div>
    <div class="metric"><span>Sharpe Ratio</span><strong>{metrics.get('sharpe_ratio', 0):.3f}</strong></div>
    <div class="metric"><span>Max Drawdown</span><strong>{metrics.get('max_drawdown_pct', 0):.2f}%</strong></div>
    <div class="metric"><span>Calmar Ratio</span><strong>{metrics.get('calmar_ratio', 0):.3f}</strong></div>
    <div class="metric"><span>Win Rate</span><strong>{metrics.get('win_rate_pct', 0):.1f}%</strong></div>
    <div class="metric"><span>Cash</span><strong>${cash:.2f}</strong></div>
    <div class="metric"><span>Macro Score</span><strong>{macro_score:.3f}</strong></div>
  </div>
  <div class="card">
    <h2>NAV History</h2>
    <canvas id="navChart"></canvas>
  </div>
</div>

<div class="grid" style="margin-top:20px">
  <div class="card">
    <h2>Holdings</h2>
    <table><thead><tr><th>Asset</th><th>Qty</th><th>Avg Cost</th></tr></thead>
    <tbody>{holdings_rows}</tbody></table>
  </div>
  <div class="card">
    <h2>Signal Panel</h2>
    <p><strong style="color:#00ff88">BUY ({len(consensus_buys)}):</strong> {', '.join(consensus_buys[:10])}</p>
    <p><strong style="color:#ff4444">SELL ({len(consensus_sells)}):</strong> {', '.join(consensus_sells[:10])}</p>
  </div>
</div>

<div class="grid" style="margin-top:20px">
  <div class="card">
    <h2>Sharpe Rankings (Top 10)</h2>
    <table><thead><tr><th>Method</th><th>Sharpe</th></tr></thead>
    <tbody>{sharpe_rows}</tbody></table>
  </div>
  <div class="card">
    <h2>Emergency Alert Log</h2>
    <table><thead><tr><th>Time</th><th>Action</th><th>Score</th></tr></thead>
    <tbody>{alert_rows}</tbody></table>
  </div>
</div>

<script>
const ctx = document.getElementById('navChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(nav_labels)},
    datasets: [{{
      label: 'NAV (USD)',
      data: {json.dumps(nav_values)},
      borderColor: '#00ff88',
      backgroundColor: 'rgba(0,255,136,0.1)',
      borderWidth: 2,
      pointRadius: 2,
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#aaa' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#666', maxTicksLimit: 8 }}, grid: {{ color: '#222' }} }},
      y: {{ ticks: {{ color: '#666' }}, grid: {{ color: '#222' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(path, "w") as fh:
        fh.write(html)

    return path


def generate_alert_html(event: Dict[str, Any]) -> str:
    """Generate a standalone alert HTML snippet."""
    action = event.get("action", "UNKNOWN")
    score = event.get("composite_score", 0.0)
    ts = event.get("timestamp", datetime.now(timezone.utc).isoformat())[:19]
    color = {"DEFENSIVE": "#ff4444", "REDUCE": "#ffaa00", "HEDGE": "#ff8800"}.get(action, "#aaa")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"ALERT_{ts[:10]}_{action}.html")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{background:#0d0d0d;color:#e0e0e0;font-family:monospace;padding:20px;}}
.alert{{border:2px solid {color};border-radius:8px;padding:16px;max-width:600px;}}
h2{{color:{color};}}</style></head>
<body>
<div class="alert">
<h2>EMERGENCY ALERT: {action}</h2>
<p><strong>Time:</strong> {ts}</p>
<p><strong>Composite Score:</strong> {score:.3f}</p>
<pre>{json.dumps(event, indent=2, default=str)}</pre>
</div>
</body></html>"""
    with open(path, "w") as fh:
        fh.write(html)
    return path
