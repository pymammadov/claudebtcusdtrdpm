"""
MT4-Style Report Generator
Generates professional MetaTrader 4 format HTML reports from backtest results.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class MT4ReportGenerator:
    """Generate professional MT4-style HTML reports."""

    TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTCUSD Trading Report - MetaTrader Style</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: "Courier New", monospace;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: linear-gradient(135deg, #2c2c3e 0%, #1a1a2e 100%);
            border: 1px solid #3a3a4e;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}

        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
            color: #00d4ff;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            font-size: 12px;
            margin-top: 15px;
        }}

        .info-item {{
            border-left: 3px solid #00d4ff;
            padding-left: 10px;
        }}

        .info-item label {{
            color: #888;
            display: block;
            font-size: 10px;
            text-transform: uppercase;
            margin-bottom: 3px;
        }}

        .info-item value {{
            color: #00d4ff;
            font-weight: bold;
            font-size: 14px;
        }}

        .section {{
            background: #252535;
            border: 1px solid #3a3a4e;
            margin-bottom: 20px;
            border-radius: 4px;
            overflow: hidden;
        }}

        .section-title {{
            background: #1a1a2e;
            padding: 12px 15px;
            border-bottom: 2px solid #3a3a4e;
            font-weight: bold;
            color: #00d4ff;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0;
        }}

        .summary-item {{
            padding: 15px;
            border-right: 1px solid #3a3a4e;
            border-bottom: 1px solid #3a3a4e;
        }}

        .summary-label {{
            color: #888;
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}

        .summary-value {{
            font-size: 16px;
            font-weight: bold;
        }}

        .profit {{
            color: #00ff00;
        }}

        .loss {{
            color: #ff3333;
        }}

        .neutral {{
            color: #00d4ff;
        }}

        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}

        .trades-table thead {{
            background: #1a1a2e;
            border-bottom: 2px solid #00d4ff;
        }}

        .trades-table th {{
            padding: 10px;
            text-align: left;
            color: #00d4ff;
            font-weight: bold;
            text-transform: uppercase;
            border-right: 1px solid #3a3a4e;
            white-space: nowrap;
        }}

        .trades-table td {{
            padding: 10px;
            border-right: 1px solid #3a3a4e;
            border-bottom: 1px solid #2a2a3a;
        }}

        .trades-table tr:hover {{
            background: #2a2a3a;
        }}

        .trade-win {{
            background: rgba(0, 255, 0, 0.05);
        }}

        .trade-loss {{
            background: rgba(255, 51, 51, 0.05);
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .chart-container {{
            background: #252535;
            border: 1px solid #3a3a4e;
            padding: 15px;
            border-radius: 4px;
            position: relative;
            height: 350px;
        }}

        .chart-title {{
            font-size: 12px;
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}

        .tabs {{
            display: flex;
            background: #1a1a2e;
            border-bottom: 2px solid #3a3a4e;
            margin-bottom: 20px;
            border-radius: 4px 4px 0 0;
        }}

        .tab {{
            flex: 1;
            padding: 12px;
            text-align: center;
            cursor: pointer;
            border-right: 1px solid #3a3a4e;
            color: #888;
            font-weight: bold;
            transition: all 0.3s;
        }}

        .tab:hover {{
            background: #2a2a3a;
        }}

        .tab.active {{
            background: #2a2a3a;
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
            margin-bottom: -2px;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 10px;
            border-top: 1px solid #3a3a4e;
            margin-top: 40px;
        }}

        .stats-2col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }}

        .stat-box {{
            background: #1a1a2e;
            padding: 15px;
            border-left: 3px solid #00d4ff;
        }}

        .stat-label {{
            color: #888;
            font-size: 10px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}

        .stat-value {{
            font-size: 18px;
            font-weight: bold;
            color: #00d4ff;
        }}

        .positive {{
            color: #00ff00 !important;
            border-left-color: #00ff00 !important;
        }}

        .negative {{
            color: #ff3333 !important;
            border-left-color: #ff3333 !important;
        }}

        .filter-input {{
            background: #1a1a2e;
            border: 1px solid #3a3a4e;
            color: #e0e0e0;
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-family: "Courier New", monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 BTCUSD Trading Strategy Report</h1>
            <div class="header-info">
                <div class="info-item">
                    <label>Model</label>
                    <value>{model_id}</value>
                </div>
                <div class="info-item">
                    <label>Strategy</label>
                    <value>{template_name}</value>
                </div>
                <div class="info-item">
                    <label>Timeframe</label>
                    <value>{timeframe}</value>
                </div>
                <div class="info-item">
                    <label>Period</label>
                    <value>2023-01-01 to 2023-02-18 (~50 days)</value>
                </div>
            </div>
        </div>

        <div style="margin-bottom: 20px;">
            <div class="tabs">
                <div class="tab active" onclick="showTab(event, 'summary')">Summary</div>
                <div class="tab" onclick="showTab(event, 'trades')">Trades ({total_trades})</div>
                <div class="tab" onclick="showTab(event, 'charts')">Charts</div>
                <div class="tab" onclick="showTab(event, 'statistics')">Statistics</div>
            </div>

            <div id="summary" class="tab-content active">
                <div class="section">
                    <div class="section-title">💰 Account Summary</div>
                    <div class="summary-grid">
                        <div class="summary-item">
                            <div class="summary-label">Initial Deposit</div>
                            <div class="summary-value neutral">${initial_balance:,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Final Balance</div>
                            <div class="summary-value neutral">${final_balance:,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Net Profit</div>
                            <div class="summary-value {profit_color}">${net_profit:+,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Total Return</div>
                            <div class="summary-value {profit_color}">{total_return_pct:+.2f}%</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Gross Profit</div>
                            <div class="summary-value profit">${winning_profit:,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Gross Loss</div>
                            <div class="summary-value loss">${losing_loss:,.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Profit Factor</div>
                            <div class="summary-value profit">{profit_factor:.2f}x</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Sharpe Ratio</div>
                            <div class="summary-value positive">{sharpe_ratio:.2f}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Max Drawdown</div>
                            <div class="summary-value negative">{max_drawdown:-.2f}%</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Recovery Factor</div>
                            <div class="summary-value positive">{recovery_factor:.2f}x</div>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">📈 Trade Statistics</div>
                    <div class="stats-2col">
                        <div class="stat-box">
                            <div class="stat-label">Total Trades</div>
                            <div class="stat-value">{total_trades}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Winning Trades</div>
                            <div class="stat-value positive">{winning_trades} ({win_rate_pct:.1f}%)</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Losing Trades</div>
                            <div class="stat-value negative">{losing_trades} ({lose_rate_pct:.1f}%)</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Win/Loss Ratio</div>
                            <div class="stat-value positive">{win_loss_ratio:.2f}x</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Average Win</div>
                            <div class="stat-value positive">${avg_win:,.2f}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Average Loss</div>
                            <div class="stat-value negative">${avg_loss:,.2f}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Best Trade</div>
                            <div class="stat-value positive">${max_win:,.2f}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Worst Trade</div>
                            <div class="stat-value negative">${max_loss:,.2f}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Expectancy per Trade</div>
                            <div class="stat-value positive">${expectancy:,.2f}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Max Consecutive Losses</div>
                            <div class="stat-value negative">{consecutive_losses}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="trades" class="tab-content">
                <div class="section">
                    <div class="section-title">📋 Closed Trades ({total_trades} Total)</div>
                    <input type="text" class="filter-input" id="tradeFilter" placeholder="Filter trades...">
                    <div style="overflow-x: auto;">
                        <table class="trades-table" id="tradesTable">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Open Time</th>
                                    <th>Type</th>
                                    <th>Size</th>
                                    <th>Open Price</th>
                                    <th>Close Time</th>
                                    <th>Close Price</th>
                                    <th>Commission</th>
                                    <th>Profit</th>
                                    <th>Profit %</th>
                                </tr>
                            </thead>
                            <tbody id="tradesBody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div id="charts" class="tab-content">
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">Daily Profit Distribution</div>
                        <canvas id="profitChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">Win Rate vs Trade Count</div>
                        <canvas id="winRateChart"></canvas>
                    </div>
                </div>
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">Cumulative P&L</div>
                        <canvas id="cumulativeChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">Trade Size Over Time</div>
                        <canvas id="sizeChart"></canvas>
                    </div>
                </div>
            </div>

            <div id="statistics" class="tab-content">
                <div class="section">
                    <div class="section-title">📊 Position Analysis</div>
                    <div class="stats-2col">
                        <div class="stat-box">
                            <div class="stat-label">Long Positions</div>
                            <div class="stat-value">{long_count} trades</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Long Win Rate</div>
                            <div class="stat-value positive">{long_win_rate:.1f}%</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Short Positions</div>
                            <div class="stat-value">{short_count} trades</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Short Win Rate</div>
                            <div class="stat-value neutral">{short_win_rate:.1f}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Generated: {generated_at} | BTCUSD Trading Strategy Report | Model: {model_id} | Backtest Period: ~50 days</p>
        <p>⚠️ This report is for backtesting purposes only. Past performance does not guarantee future results. Use at your own risk.</p>
    </div>

    <script>
        const trades = {trades_json};

        function populateTrades() {{
            const tbody = document.getElementById('tradesBody');
            trades.forEach(t => {{
                const tr = document.createElement('tr');
                tr.className = t.profit >= 0 ? 'trade-win' : 'trade-loss';
                const profitColor = t.profit >= 0 ? '#00ff00' : '#ff3333';
                tr.innerHTML = `
                    <td>${{t.idx}}</td>
                    <td>${{t.open}}</td>
                    <td><strong>${{t.type}}</strong></td>
                    <td>${{t.lots.toFixed(4)}}</td>
                    <td>${{t.open_price.toFixed(2)}}</td>
                    <td>${{t.close}}</td>
                    <td>${{t.close_price.toFixed(2)}}</td>
                    <td>$0.60</td>
                    <td style="font-weight:bold; color: ${{profitColor}};">${{(t.profit >= 0 ? '+' : '')}}${{Math.abs(t.profit).toFixed(2)}}</td>
                    <td style="color: ${{profitColor}};">${{(t.profit >= 0 ? '+' : '')}}${{t.profit_pct.toFixed(2)}}%</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        document.getElementById('tradeFilter').addEventListener('keyup', function(e) {{
            const filter = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#tradesBody tr');
            rows.forEach(row => {{
                row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none';
            }});
        }});

        function showTab(evt, tabName) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            evt.currentTarget.classList.add('active');
            if (tabName === 'charts') setTimeout(initCharts, 100);
        }}

        function initCharts() {{
            const profitCtx = document.getElementById('profitChart');
            if (profitCtx && !profitCtx.chart) {{
                profitCtx.chart = new Chart(profitCtx, {{
                    type: 'bar',
                    data: {{
                        labels: trades.map(t => `T${{t.idx}}`),
                        datasets: [{{
                            label: 'Profit/Loss ($)',
                            data: trades.map(t => t.profit),
                            backgroundColor: trades.map(t => t.profit >= 0 ? '#00ff00' : '#ff3333'),
                            borderColor: trades.map(t => t.profit >= 0 ? '#00dd00' : '#dd0000'),
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{legend: {{display: false}}}},
                        scales: {{
                            y: {{grid: {{color: '#2a2a3a'}}, ticks: {{color: '#888'}}, beginAtZero: true}},
                            x: {{grid: {{display: false}}, ticks: {{color: '#888'}}}}
                        }}
                    }}
                }});
            }}

            const winRateCtx = document.getElementById('winRateChart');
            if (winRateCtx && !winRateCtx.chart) {{
                const wins = {winning_trades};
                const losses = {losing_trades};
                const winPct = {win_rate_pct:.1f};
                winRateCtx.chart = new Chart(winRateCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: [`Wins (${{wins}})`, `Losses (${{losses}})`],
                        datasets: [{{
                            data: [winPct, {lose_rate_pct:.1f}],
                            backgroundColor: ['#00ff00', '#ff3333'],
                            borderColor: '#1a1a2e',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{legend: {{labels: {{color: '#888', font: {{size: 11}}}}}}}}
                    }}
                }});
            }}

            let cumulative = 0;
            const cumulativeData = trades.map(t => cumulative += t.profit);
            const cumulativeCtx = document.getElementById('cumulativeChart');
            if (cumulativeCtx && !cumulativeCtx.chart) {{
                cumulativeCtx.chart = new Chart(cumulativeCtx, {{
                    type: 'line',
                    data: {{
                        labels: trades.map(t => `T${{t.idx}}`),
                        datasets: [{{
                            label: 'Cumulative P&L ($)',
                            data: cumulativeData,
                            borderColor: '#00d4ff',
                            backgroundColor: 'rgba(0,212,255,0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: cumulativeData.map(v => v >= 0 ? '#00ff00' : '#ff3333'),
                            pointBorderColor: '#1a1a2e'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{grid: {{color: '#2a2a3a'}}, ticks: {{color: '#888'}}}},
                            x: {{grid: {{display: false}}, ticks: {{color: '#888'}}}}
                        }}
                    }}
                }});
            }}

            const sizeCtx = document.getElementById('sizeChart');
            if (sizeCtx && !sizeCtx.chart) {{
                sizeCtx.chart = new Chart(sizeCtx, {{
                    type: 'line',
                    data: {{
                        labels: trades.map(t => `T${{t.idx}}`),
                        datasets: [{{
                            label: 'Position Size (mBTC)',
                            data: trades.map(t => t.lots * 1000),
                            borderColor: '#ffaa00',
                            backgroundColor: 'rgba(255,170,0,0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{grid: {{color: '#2a2a3a'}}, ticks: {{color: '#888'}}}},
                            x: {{grid: {{display: false}}, ticks: {{color: '#888'}}}}
                        }}
                    }}
                }});
            }}
        }}

        populateTrades();
    </script>
</body>
</html>
"""

    def __init__(self, results_dir: Path = None):
        """Initialize report generator."""
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"

    def load_winner(self) -> Dict[str, Any]:
        """Load winner.json data."""
        winner_file = self.results_dir / "winner.json"
        with open(winner_file, 'r') as f:
            return json.load(f)

    def calculate_metrics(self, winner: Dict) -> Dict[str, Any]:
        """Calculate all metrics from trades."""
        trades = winner.get("trades", [])
        if not trades:
            return {}

        profits = [t["pnl"] for t in trades]
        win_trades = [t for t in trades if t["pnl"] > 0]
        loss_trades = [t for t in trades if t["pnl"] < 0]
        long_trades = [t for t in trades if t["direction"] == "long"]
        short_trades = [t for t in trades if t["direction"] == "short"]

        total_profit = sum(profits)
        winning_profit = sum(p for p in profits if p > 0)
        losing_loss = sum(p for p in profits if p < 0)

        return {
            "total_trades": len(trades),
            "winning_trades": len(win_trades),
            "losing_trades": len(loss_trades),
            "win_rate_pct": (len(win_trades) / len(trades) * 100) if trades else 0,
            "lose_rate_pct": (len(loss_trades) / len(trades) * 100) if trades else 0,
            "total_profit": total_profit,
            "winning_profit": winning_profit,
            "losing_loss": losing_loss,
            "avg_win": sum(p for p in profits if p > 0) / len(win_trades) if win_trades else 0,
            "avg_loss": sum(p for p in profits if p < 0) / len(loss_trades) if loss_trades else 0,
            "max_win": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "expectancy": total_profit / len(trades) if trades else 0,
            "profit_factor": winning_profit / abs(losing_loss) if losing_loss != 0 else 0,
            "long_count": len(long_trades),
            "short_count": len(short_trades),
            "long_win_rate": len([t for t in long_trades if t["pnl"] > 0]) / len(long_trades) * 100 if long_trades else 0,
            "short_win_rate": len([t for t in short_trades if t["pnl"] > 0]) / len(short_trades) * 100 if short_trades else 0,
            "win_loss_ratio": (sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0))) if sum(p for p in profits if p < 0) != 0 else 0,
        }

    def format_trades_json(self, winner: Dict) -> str:
        """Format trades as JSON for JavaScript."""
        trades = winner.get("trades", [])
        js_trades = []

        for idx, trade in enumerate(trades, 1):
            js_trades.append(
                f"{{idx:{idx}, open:'{trade['entry_time']}', type:'{('SELL' if trade['direction'] == 'short' else 'BUY')}', "
                f"lots:{trade['size']:.4f}, open_price:{trade['entry_price']:.2f}, close:'{trade['exit_time']}', "
                f"close_price:{trade['exit_price']:.2f}, profit:{trade['pnl']:.2f}, profit_pct:{trade['pnl_pct']*100:.2f}}}"
            )

        return "[" + ",\n            ".join(js_trades) + "]"

    def generate_report(self, output_file: str = "mt4_report.html") -> str:
        """Generate complete MT4 report."""
        winner = self.load_winner()
        metrics = self.calculate_metrics(winner)
        in_sample = winner.get("in_sample_metrics", {})

        # Calculate values
        initial_balance = 10000.0
        net_profit = metrics.get("total_profit", 0)
        final_balance = initial_balance + net_profit
        total_return_pct = (net_profit / initial_balance) * 100
        max_drawdown = in_sample.get("max_drawdown_pct", 0)
        recovery_factor = net_profit / abs(max_drawdown) * 100 if max_drawdown != 0 else 0

        # Format values
        context = {
            "model_id": winner.get("model_id", "N/A"),
            "template_name": winner.get("template", "N/A") + " - Mean Reversion",
            "timeframe": winner.get("timeframe", "15m"),
            "total_trades": metrics.get("total_trades", 0),
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "net_profit": net_profit,
            "profit_color": "profit" if net_profit > 0 else "loss",
            "total_return_pct": total_return_pct,
            "winning_profit": metrics.get("winning_profit", 0),
            "losing_loss": metrics.get("losing_loss", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "sharpe_ratio": in_sample.get("sharpe_ratio", 0),
            "max_drawdown": max_drawdown,
            "recovery_factor": recovery_factor,
            "winning_trades": metrics.get("winning_trades", 0),
            "losing_trades": metrics.get("losing_trades", 0),
            "win_rate_pct": metrics.get("win_rate_pct", 0),
            "lose_rate_pct": metrics.get("lose_rate_pct", 0),
            "win_loss_ratio": metrics.get("win_loss_ratio", 0),
            "avg_win": metrics.get("avg_win", 0),
            "avg_loss": metrics.get("avg_loss", 0),
            "max_win": metrics.get("max_win", 0),
            "max_loss": metrics.get("max_loss", 0),
            "expectancy": metrics.get("expectancy", 0),
            "consecutive_losses": in_sample.get("consecutive_losses", 0),
            "long_count": metrics.get("long_count", 0),
            "short_count": metrics.get("short_count", 0),
            "long_win_rate": metrics.get("long_win_rate", 0),
            "short_win_rate": metrics.get("short_win_rate", 0),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "trades_json": self.format_trades_json(winner),
        }

        html = self.TEMPLATE.format(**context)
        output_path = self.results_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html)

        return str(output_path)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    gen = MT4ReportGenerator()
    output = gen.generate_report()
    print(f"✅ Report generated: {output}")
