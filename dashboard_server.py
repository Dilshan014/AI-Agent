"""
STEP: Live Dashboard for your Trading Bot
=============================================
Runs a small local web server that reads status.json and trade_log.csv
(written by live_bot.py) and shows them on a live-updating dashboard
in your browser.

SETUP:
    pip install flask

RUN (in a SEPARATE terminal window, while live_bot.py is also running):
    python dashboard_server.py

Then open in your browser:
    http://localhost:5000
"""

import os
import json
import csv
from flask import Flask, jsonify, Response

app = Flask(__name__, static_folder="static", static_url_path="/static")

STATUS_FILE = "status.json"
TRADE_LOG_FILE = "trade_log.csv"
WEBHOOK_SIGNAL_FILE = "webhook_signal.json"

# Set this to something only you know, and use the SAME value in your
# TradingView alert message. This stops random internet traffic from
# triggering trades on your bot once the webhook URL is public.
WEBHOOK_PASSPHRASE = "change-this-to-your-own-secret"


@app.route("/webhook", methods=["POST"])
def webhook():
    from flask import request

    data = request.get_json(silent=True) or {}

    if data.get("passphrase") != WEBHOOK_PASSPHRASE:
        return jsonify({"error": "invalid passphrase"}), 403

    action = data.get("action", "").lower()
    if action not in ("buy", "sell"):
        return jsonify({"error": "action must be 'buy' or 'sell'"}), 400

    signal = {
        "action": action,
        "received_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "processed": False,
    }
    with open(WEBHOOK_SIGNAL_FILE, "w") as f:
        json.dump(signal, f, indent=2)

    print(f"[WEBHOOK] Received signal: {action}")
    return jsonify({"status": "ok", "action": action})


@app.route("/api/status")
def api_status():
    if not os.path.exists(STATUS_FILE):
        return jsonify({"error": "Bot hasn't written status yet. Is live_bot.py running?"}), 404
    with open(STATUS_FILE, "r") as f:
        return jsonify(json.load(f))


@app.route("/api/trades")
def api_trades():
    if not os.path.exists(TRADE_LOG_FILE):
        return jsonify([])
    with open(TRADE_LOG_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        trades = list(reader)
    trades.reverse()  # most recent first
    return jsonify(trades)


@app.route("/")
def dashboard():
    return Response(DASHBOARD_HTML, mimetype="text/html")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Trading Bot Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

  :root {
    --bg: #0b0f0e;
    --panel: #121715;
    --panel-border: #1f2b27;
    --text-primary: #e8f0ed;
    --text-dim: #6e8079;
    --green: #3ddc97;
    --red: #ff5c6c;
    --amber: #e8b04b;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--bg);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
    padding: 28px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 20px;
  }

  .title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 22px;
    letter-spacing: -0.02em;
  }

  .title span {
    color: var(--green);
  }

  .subtitle {
    color: var(--text-dim);
    font-size: 12px;
    margin-top: 4px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .price-block {
    text-align: right;
  }

  .price-label {
    color: var(--text-dim);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .price-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 40px;
    line-height: 1;
    transition: color 0.3s ease;
  }

  .price-value.flash-up { color: var(--green); }
  .price-value.flash-down { color: var(--red); }

  .status-row {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-dim);
  }

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    display: inline-block;
    margin-right: 6px;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.35; }
    100% { opacity: 1; }
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 28px;
  }

  .card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 16px 18px;
  }

  .card-label {
    color: var(--text-dim);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .card-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 22px;
  }

  .card-value.green { color: var(--green); }
  .card-value.red { color: var(--red); }
  .card-value.amber { color: var(--amber); }

  .mini-breakdown {
    color: var(--text-dim);
    font-size: 11px;
    margin-top: 6px;
  }

  .panel-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.02em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    overflow: hidden;
  }

  th {
    text-align: left;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-dim);
    padding: 12px 14px;
    border-bottom: 1px solid var(--panel-border);
    font-weight: 500;
  }

  td {
    padding: 12px 14px;
    font-size: 13px;
    border-bottom: 1px solid var(--panel-border);
  }

  tr:last-child td { border-bottom: none; }

  .pnl-positive { color: var(--green); }
  .pnl-negative { color: var(--red); }

  .reason-tag {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 11px;
    background: rgba(255,255,255,0.06);
    color: var(--text-dim);
  }

  .reason-tag.open-tag {
    background: rgba(232, 176, 75, 0.15);
    color: var(--amber);
  }

  .row-open {
    background: rgba(232, 176, 75, 0.05);
  }

  .row-open td:first-child {
    border-left: 2px solid var(--amber);
  }

  .empty-state {
    color: var(--text-dim);
    text-align: center;
    padding: 40px;
    font-size: 13px;
  }

  .chart-container {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 8px;
    margin-bottom: 28px;
    height: 450px;
  }

  #tradingview_chart {
    height: 100%;
  }

  #chart {
    position: relative;
  }

  .zone-box {
    position: absolute;
    left: 0;
    right: 60px;
    pointer-events: none;
    z-index: 2;
    display: none;
  }

  .zone-tp {
    background: rgba(61, 220, 151, 0.12);
    border-top: 1px dashed rgba(61, 220, 151, 0.55);
    border-bottom: 1px dashed rgba(61, 220, 151, 0.55);
  }

  .zone-sl {
    background: rgba(255, 92, 108, 0.12);
    border-top: 1px dashed rgba(255, 92, 108, 0.55);
    border-bottom: 1px dashed rgba(255, 92, 108, 0.55);
  }
</style>
</head>
<body>

  <div class="header">
    <div>
      <div class="title">BTC<span>USDT</span> // Live Bot</div>
      <div class="subtitle">Binance Testnet · Fake Money · SMA Crossover Strategy</div>
    </div>
    <div class="price-block">
      <div class="price-label">Current Price</div>
      <div class="price-value" id="price">--</div>
      <div class="status-row">
        <span><span class="pulse-dot"></span>Updated <span id="updated-at">--</span></span>
      </div>
    </div>
  </div>

  <div class="panel-title" style="margin-top:0;">Live Chart — Red: Stop-Loss · Green: Take-Profit · Amber: Entry</div>
  <div class="chart-container">
    <div id="chart" style="width:100%; height:100%;"></div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-label">Position</div>
      <div class="card-value" id="position-status">--</div>
    </div>
    <div class="card">
      <div class="card-label">Entry Price</div>
      <div class="card-value" id="entry-price">--</div>
    </div>
    <div class="card">
      <div class="card-label">SMA20 / SMA60</div>
      <div class="card-value" id="sma-values" style="font-size:16px;">--</div>
    </div>
    <div class="card">
      <div class="card-label">Total Realized P&amp;L</div>
      <div class="card-value" id="total-pnl">--</div>
    </div>
    <div class="card">
      <div class="card-label">Account Value</div>
      <div class="card-value" id="portfolio-value">--</div>
      <div class="mini-breakdown" id="balance-breakdown">--</div>
    </div>
  </div>

  <div class="panel-title">Trade History</div>
  <table id="trades-table">
    <thead>
      <tr>
        <th>Entry Time</th>
        <th>Exit Time</th>
        <th>Entry Price</th>
        <th>Exit Price</th>
        <th>P&amp;L</th>
        <th>Reason</th>
      </tr>
    </thead>
    <tbody id="trades-body">
      <tr><td colspan="6" class="empty-state">Waiting for trade data...</td></tr>
    </tbody>
  </table>

<script>
let lastPrice = null;
let latestStatus = null;

async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();
    latestStatus = data;

    const priceEl = document.getElementById('price');
    const newPrice = parseFloat(data.price).toFixed(2);
    priceEl.textContent = newPrice;

    if (lastPrice !== null) {
      priceEl.classList.remove('flash-up', 'flash-down');
      if (data.price > lastPrice) priceEl.classList.add('flash-up');
      else if (data.price < lastPrice) priceEl.classList.add('flash-down');
    }
    lastPrice = data.price;

    document.getElementById('updated-at').textContent = data.updated_at;
    document.getElementById('sma-values').textContent =
      parseFloat(data.short_ma).toFixed(2) + ' / ' + parseFloat(data.long_ma).toFixed(2);

    if (data.portfolio_value !== undefined) {
      document.getElementById('portfolio-value').textContent =
        parseFloat(data.portfolio_value).toFixed(2) + ' USDT';
      document.getElementById('balance-breakdown').textContent =
        parseFloat(data.usdt_balance).toFixed(2) + ' USDT + ' +
        parseFloat(data.btc_balance).toFixed(6) + ' BTC';
    }

    if (typeof updatePriceLines === 'function') updatePriceLines(data);

    const posEl = document.getElementById('position-status');
    if (data.in_position) {
      posEl.textContent = 'OPEN';
      posEl.className = 'card-value amber';
      document.getElementById('entry-price').textContent = parseFloat(data.entry_price).toFixed(2);
    } else {
      posEl.textContent = 'FLAT';
      posEl.className = 'card-value';
      document.getElementById('entry-price').textContent = '--';
    }
  } catch (e) {
    console.error(e);
  }
}

async function refreshTrades() {
  try {
    const res = await fetch('/api/trades');
    const trades = await res.json();
    const tbody = document.getElementById('trades-body');

    let rowsHtml = '';

    // Live open position row (unrealized P&L), shown at the top
    if (latestStatus && latestStatus.in_position) {
      const entryPrice = parseFloat(latestStatus.entry_price);
      const currentPrice = parseFloat(latestStatus.price);
      const quantity = parseFloat(latestStatus.quantity);
      const unrealizedPnl = (currentPrice - entryPrice) * quantity;
      const unrealizedPct = (currentPrice - entryPrice) / entryPrice * 100;
      const pnlClass = unrealizedPnl >= 0 ? 'pnl-positive' : 'pnl-negative';
      const pnlSign = unrealizedPnl >= 0 ? '+' : '';

      rowsHtml += `<tr class="row-open">
        <td>${latestStatus.entry_time || '--'}</td>
        <td>--</td>
        <td>${entryPrice.toFixed(2)}</td>
        <td>${currentPrice.toFixed(2)}</td>
        <td class="${pnlClass}">${pnlSign}${unrealizedPnl.toFixed(2)} (${pnlSign}${unrealizedPct.toFixed(2)}%)</td>
        <td><span class="reason-tag open-tag">open (unrealized)</span></td>
      </tr>`;
    }

    let totalPnl = 0;
    if (trades.length === 0 && rowsHtml === '') {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No trades yet.</td></tr>';
      document.getElementById('total-pnl').textContent = '0.00';
      return;
    }

    rowsHtml += trades.map(t => {
      const pnl = parseFloat(t.pnl);
      totalPnl += pnl;
      const pnlClass = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
      const pnlSign = pnl >= 0 ? '+' : '';
      return `<tr>
        <td>${t.entry_time}</td>
        <td>${t.exit_time}</td>
        <td>${parseFloat(t.entry_price).toFixed(2)}</td>
        <td>${parseFloat(t.exit_price).toFixed(2)}</td>
        <td class="${pnlClass}">${pnlSign}${pnl.toFixed(2)} (${pnlSign}${parseFloat(t.pnl_pct).toFixed(2)}%)</td>
        <td><span class="reason-tag">${t.exit_reason}</span></td>
      </tr>`;
    }).join('');

    tbody.innerHTML = rowsHtml;

    const totalEl = document.getElementById('total-pnl');
    totalEl.textContent = (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2);
    totalEl.className = 'card-value ' + (totalPnl >= 0 ? 'green' : 'red');
  } catch (e) {
    console.error(e);
  }
}

async function refreshAll() {
  await refreshStatus();
  await refreshTrades();
}
</script>

<script src="/static/lightweight-charts.standalone.production.js"></script>
<script>
  var candleSeries = null;
  var chartPriceLines = [];
  var zoneTpEl = null;
  var zoneSlEl = null;
  var allCandles = [];

  function initChart() {
    if (typeof LightweightCharts === 'undefined') {
      document.getElementById('chart').innerHTML =
        '<div style="color:#ff5c6c; padding:20px; font-size:13px;">Chart library failed to load (check internet connection, then refresh this page).</div>';
      return;
    }

    var chartEl = document.getElementById('chart');
    var chart = LightweightCharts.createChart(chartEl, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#6e8079',
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: '#1f2b27' },
        horzLines: { color: '#1f2b27' },
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#1f2b27' },
      rightPriceScale: { borderColor: '#1f2b27' },
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: '#3ddc97', downColor: '#ff5c6c',
      borderUpColor: '#3ddc97', borderDownColor: '#ff5c6c',
      wickUpColor: '#3ddc97', wickDownColor: '#ff5c6c',
      autoscaleInfoProvider: function() {
        if (!allCandles || allCandles.length === 0) return null;
        var min = Infinity, max = -Infinity;
        for (var i = 0; i < allCandles.length; i++) {
          if (allCandles[i].low < min) min = allCandles[i].low;
          if (allCandles[i].high > max) max = allCandles[i].high;
        }
        var padding = (max - min) * 0.08;
        return { priceRange: { minValue: min - padding, maxValue: max + padding } };
      },
    });

    zoneTpEl = document.createElement('div');
    zoneTpEl.className = 'zone-box zone-tp';
    zoneSlEl = document.createElement('div');
    zoneSlEl.className = 'zone-box zone-sl';
    chartEl.appendChild(zoneTpEl);
    chartEl.appendChild(zoneSlEl);

    chart.timeScale().subscribeVisibleLogicalRangeChange(function() {
      updateZones(latestStatus);
    });

    new ResizeObserver(function(entries) {
      var rect = entries[0].contentRect;
      chart.applyOptions({ width: rect.width, height: rect.height });
      updateZones(latestStatus);
    }).observe(chartEl);

    loadKlines();
    setInterval(loadKlines, 15000);
  }

  async function loadKlines() {
    if (!candleSeries) return;
    try {
      const res = await fetch('https://testnet.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=150');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const klines = await res.json();
      const candles = klines.map(k => ({
        time: Math.floor(k[0] / 1000),
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
      }));
      candleSeries.setData(candles);
      allCandles = candles;
      updateZones(latestStatus);
    } catch (e) {
      console.error('Failed to load klines:', e);
      document.getElementById('chart').insertAdjacentHTML('beforeend',
        '<div style="color:#e8b04b; padding:12px; font-size:12px; position:absolute; top:0; left:0;">Could not load price data from Binance (network/firewall may be blocking it). Chart grid still shown below.</div>');
    }
  }

  function updatePriceLines(status) {
    if (!candleSeries) return;

    chartPriceLines.forEach(line => candleSeries.removePriceLine(line));
    chartPriceLines = [];

    if (!status || !status.in_position) return;

    const entryPrice = parseFloat(status.entry_price);
    const stopLossPrice = entryPrice * (1 - 0.025);   // matches STOP_LOSS_PCT in live_bot.py
    const takeProfitPrice = entryPrice * (1 + 0.075); // matches TAKE_PROFIT_PCT in live_bot.py

    chartPriceLines.push(candleSeries.createPriceLine({
      price: entryPrice, color: '#e8b04b', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true, title: 'Entry',
    }));
    chartPriceLines.push(candleSeries.createPriceLine({
      price: stopLossPrice, color: '#ff5c6c', lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid,
      axisLabelVisible: true, title: 'Stop-Loss',
    }));
    chartPriceLines.push(candleSeries.createPriceLine({
      price: takeProfitPrice, color: '#3ddc97', lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid,
      axisLabelVisible: true, title: 'Take-Profit',
    }));

    updateZones(status);
  }

  function updateZones(status) {
    if (!candleSeries || !zoneTpEl || !zoneSlEl) return;

    if (!status || !status.in_position) {
      zoneTpEl.style.display = 'none';
      zoneSlEl.style.display = 'none';
      return;
    }

    const entryPrice = parseFloat(status.entry_price);
    const stopLossPrice = entryPrice * (1 - 0.025);
    const takeProfitPrice = entryPrice * (1 + 0.075);

    const yEntry = candleSeries.priceToCoordinate(entryPrice);
    const yTp = candleSeries.priceToCoordinate(takeProfitPrice);
    const ySl = candleSeries.priceToCoordinate(stopLossPrice);

    if (yEntry === null || yTp === null || ySl === null) {
      zoneTpEl.style.display = 'none';
      zoneSlEl.style.display = 'none';
      return;
    }

    zoneTpEl.style.display = 'block';
    zoneTpEl.style.top = Math.min(yTp, yEntry) + 'px';
    zoneTpEl.style.height = Math.abs(yEntry - yTp) + 'px';

    zoneSlEl.style.display = 'block';
    zoneSlEl.style.top = Math.min(ySl, yEntry) + 'px';
    zoneSlEl.style.height = Math.abs(ySl - yEntry) + 'px';
  }

  initChart();
</script>

<script>
refreshAll();
setInterval(refreshAll, 5000); // refresh every 5 seconds
</script>

</body>
</html>
"""


if __name__ == "__main__":
    print("Dashboard running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
