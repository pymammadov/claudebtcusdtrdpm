"""
Advanced Models Report Generator - Shows all models with trade details
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class ModelsReportGenerator:
    """Generate comprehensive report of all models with trade details."""

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, output_file: str = "models_analysis.html"):
        """Generate comprehensive models analysis report."""

        winner_file = self.results_dir / "winner.json"

        if not winner_file.exists():
            print("No winner.json found!")
            return

        with open(winner_file) as f:
            winner = json.load(f)

        # For now, create report from winner
        # In full implementation, would load all models from optimization run
        html = self._create_html(winner)

        output_path = self.results_dir / output_file
        with open(output_path, "w") as f:
            f.write(html)

        print(f"Report saved to: {output_path}")
        return output_path

    def _create_html(self, winner: dict) -> str:
        """Create comprehensive HTML report."""

        trades = winner.get("trades", [])
        metrics = winner["in_sample_metrics"]

        # Build trades table
        trades_html = self._build_trades_table(trades)

        # Build trade statistics
        trade_stats = self._calculate_trade_stats(trades, metrics)

        # Build metrics cards
        metrics_cards = self._build_metrics_cards(metrics, trade_stats)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Models Trade Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
        }}

        header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px 30px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 40px;
        }}

        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            text-align: center;
        }}

        .metric-card h3 {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .metric-card .value {{
            color: #667eea;
            font-size: 28px;
            font-weight: bold;
        }}

        .metric-card .unit {{
            color: #999;
            font-size: 12px;
        }}

        section {{
            margin-bottom: 40px;
        }}

        h2 {{
            color: #333;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .controls {{
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .search-box {{
            flex: 1;
            min-width: 200px;
        }}

        .search-box input {{
            width: 100%;
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }}

        .filter-btn {{
            padding: 10px 15px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }}

        .filter-btn:hover {{
            background: #764ba2;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 13px;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}

        td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .positive {{
            color: #27ae60;
            font-weight: bold;
        }}

        .negative {{
            color: #e74c3c;
            font-weight: bold;
        }}

        .trade-number {{
            color: #667eea;
            font-weight: bold;
        }}

        .summary-box {{
            background: #f0f8ff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin-bottom: 20px;
        }}

        .summary-box h3 {{
            color: #333;
            margin-bottom: 15px;
        }}

        .summary-box ul {{
            list-style: none;
            padding: 0;
        }}

        .summary-box li {{
            margin-bottom: 10px;
            color: #666;
            line-height: 1.6;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 5px;
        }}

        .badge.winning {{
            background: #d4edda;
            color: #155724;
        }}

        .badge.losing {{
            background: #f8d7da;
            color: #721c24;
        }}

        .chart-container {{
            position: relative;
            height: 300px;
            margin-bottom: 30px;
        }}

        footer {{
            background: #f5f7fa;
            color: #999;
            text-align: center;
            padding: 20px;
            font-size: 12px;
            border-top: 1px solid #eee;
        }}

        .pnl-distribution {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}

        .pnl-box {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}

        .pnl-box label {{
            color: #666;
            font-size: 12px;
            display: block;
            margin-bottom: 10px;
        }}

        .pnl-box .value {{
            font-size: 20px;
            font-weight: bold;
        }}

        .pnl-box.wins {{
            border-left: 4px solid #27ae60;
        }}

        .pnl-box.losses {{
            border-left: 4px solid #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Trading Models - Trade Analysis Report</h1>
            <p>Detailed Trade-by-Trade Performance Analysis</p>
        </header>

        <div class="content">
            <!-- Metrics Overview -->
            <div class="metrics-grid">
                {metrics_cards}
            </div>

            <!-- Trade Statistics Summary -->
            <section>
                <h2>Trade Statistics Summary</h2>
                <div class="summary-box">
                    <h3>Key Insights</h3>
                    <ul>
                        <li>✓ <strong>Total Trades:</strong> {metrics['trade_count']} trades executed</li>
                        <li>✓ <strong>Win Rate:</strong> {metrics['win_rate']:.1%} of trades were profitable</li>
                        <li>✓ <strong>Profit Factor:</strong> {metrics['profit_factor']:.2f}x (winning trades vs losing trades ratio)</li>
                        <li>✓ <strong>Consecutive Losses:</strong> Maximum {int(metrics['consecutive_losses'])} consecutive losing trades</li>
                        <li>✓ <strong>Max Drawdown:</strong> {metrics['max_drawdown_pct']:.2f}% peak-to-trough decline</li>
                    </ul>
                </div>

                <h3 style="margin-top: 25px; margin-bottom: 15px;">P&L Distribution</h3>
                <div class="pnl-distribution">
                    {trade_stats['pnl_boxes']}
                </div>
            </section>

            <!-- Detailed Trades Table -->
            <section>
                <h2>Detailed Trade List</h2>
                <div class="controls">
                    <div class="search-box">
                        <input type="text" id="tradeFilter" placeholder="Search trades by direction, time...">
                    </div>
                    <button class="filter-btn" onclick="filterTable()">Filter</button>
                    <button class="filter-btn" onclick="resetTable()">Reset</button>
                </div>

                {trades_html}
            </section>

            <!-- Trade Quality Analysis -->
            <section>
                <h2>Trade Quality Metrics</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Assessment</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Average Win Size</strong></td>
                            <td>{trade_stats['avg_win']:.4f}</td>
                            <td>Average profit per winning trade</td>
                        </tr>
                        <tr>
                            <td><strong>Average Loss Size</strong></td>
                            <td>{trade_stats['avg_loss']:.4f}</td>
                            <td>Average loss per losing trade</td>
                        </tr>
                        <tr>
                            <td><strong>Win/Loss Ratio</strong></td>
                            <td>{trade_stats['win_loss_ratio']:.2f}</td>
                            <td>How much you win vs lose on average</td>
                        </tr>
                        <tr>
                            <td><strong>Expectancy</strong></td>
                            <td>{trade_stats['expectancy']:.4f}</td>
                            <td>Average profit per trade</td>
                        </tr>
                        <tr>
                            <td><strong>Recovery Factor</strong></td>
                            <td>{trade_stats['recovery_factor']:.2f}</td>
                            <td>Total profit / Max drawdown (higher is better)</td>
                        </tr>
                    </tbody>
                </table>
            </section>

            <!-- Recommendations -->
            <section>
                <h2>📈 Model Strength Assessment</h2>
                <div class="summary-box">
                    {trade_stats['recommendations']}
                </div>
            </section>
        </div>

        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Trading Strategy Analysis v1.0</p>
        </footer>
    </div>

    <script>
        function filterTable() {{
            const input = document.getElementById('tradeFilter');
            const filter = input.value.toUpperCase();
            const table = document.getElementById('tradesTable');
            const tr = table.getElementsByTagName('tr');

            for (let i = 1; i < tr.length; i++) {{
                let found = false;
                const td = tr[i].getElementsByTagName('td');
                for (let j = 0; j < td.length; j++) {{
                    if (td[j].textContent.toUpperCase().indexOf(filter) > -1) {{
                        found = true;
                        break;
                    }}
                }}
                tr[i].style.display = found ? '' : 'none';
            }}
        }}

        function resetTable() {{
            document.getElementById('tradeFilter').value = '';
            const table = document.getElementById('tradesTable');
            const tr = table.getElementsByTagName('tr');
            for (let i = 1; i < tr.length; i++) {{
                tr[i].style.display = '';
            }}
        }}
    </script>
</body>
</html>
"""
        return html

    def _build_trades_table(self, trades: List[Dict]) -> str:
        """Build HTML table for trades."""
        if not trades:
            return "<p>No trades recorded.</p>"

        rows = ""
        for i, trade in enumerate(trades, 1):
            direction = trade['direction'].upper()
            pnl = float(trade['pnl'])
            pnl_pct = float(trade['pnl_pct'])

            pnl_class = "positive" if pnl > 0 else "negative"
            direction_badge = '<span class="badge winning">LONG ↑</span>' if direction == "LONG" else '<span class="badge losing">SHORT ↓</span>'

            rows += f"""
            <tr>
                <td class="trade-number">#{i}</td>
                <td>{direction_badge}</td>
                <td>{trade['entry_time']}</td>
                <td>{float(trade['entry_price']):.2f}</td>
                <td>{trade['exit_time']}</td>
                <td>{float(trade['exit_price']):.2f}</td>
                <td class="{pnl_class}">${pnl:.2f}</td>
                <td class="{pnl_class}">{pnl_pct*100:+.2f}%</td>
                <td>{float(trade['size']):.6f}</td>
            </tr>
            """

        return f"""
        <table id="tradesTable">
            <thead>
                <tr>
                    <th>Trade #</th>
                    <th>Type</th>
                    <th>Entry Time</th>
                    <th>Entry Price</th>
                    <th>Exit Time</th>
                    <th>Exit Price</th>
                    <th>P&L ($)</th>
                    <th>P&L (%)</th>
                    <th>Size (BTC)</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """

    def _calculate_trade_stats(self, trades: List[Dict], metrics: Dict) -> Dict:
        """Calculate trade statistics."""
        if not trades:
            return {
                "avg_win": 0,
                "avg_loss": 0,
                "win_loss_ratio": 0,
                "expectancy": 0,
                "recovery_factor": 0,
                "pnl_boxes": "",
                "recommendations": "<p>No trades to analyze.</p>"
            }

        pnls = [float(t['pnl']) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        win_count = len(wins)
        loss_count = len(losses)

        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        total_pnl = sum(pnls)
        expectancy = total_pnl / len(trades) if trades else 0

        max_drawdown = abs(metrics['max_drawdown_pct']) / 100
        recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else 0

        # Build P&L boxes
        pnl_boxes = f"""
        <div class="pnl-box wins">
            <label>Total Wins</label>
            <div class="value positive">${sum(wins):.2f}</div>
            <div style="font-size: 12px; color: #666;">({win_count} trades)</div>
        </div>
        <div class="pnl-box losses">
            <label>Total Losses</label>
            <div class="value negative">${sum(losses):.2f}</div>
            <div style="font-size: 12px; color: #666;">({loss_count} trades)</div>
        </div>
        <div class="pnl-box">
            <label>Net P&L</label>
            <div class="value" style="color: {'#27ae60' if total_pnl > 0 else '#e74c3c'};">${total_pnl:.2f}</div>
            <div style="font-size: 12px; color: #666;">All trades</div>
        </div>
        """

        # Build recommendations
        strength = self._assess_model_strength(metrics, win_loss_ratio, recovery_factor)
        recommendations = f"""
        <h3>Model Strength: {strength['rating']}</h3>
        <ul>
            {strength['text']}
        </ul>
        """

        return {
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "win_loss_ratio": win_loss_ratio,
            "expectancy": expectancy,
            "recovery_factor": recovery_factor,
            "pnl_boxes": pnl_boxes,
            "recommendations": recommendations
        }

    def _assess_model_strength(self, metrics: Dict, win_loss_ratio: float, recovery_factor: float) -> Dict:
        """Assess overall model strength."""
        sharpe = metrics['sharpe_ratio']
        profit_factor = metrics['profit_factor']
        win_rate = metrics['win_rate']
        max_dd = metrics['max_drawdown_pct']

        score = 0
        feedback = []

        # Sharpe ratio assessment
        if sharpe > 1.5:
            score += 3
            feedback.append("<li>✅ <strong>Excellent Sharpe ratio:</strong> Strong risk-adjusted returns</li>")
        elif sharpe > 1.0:
            score += 2
            feedback.append("<li>✅ <strong>Good Sharpe ratio:</strong> Acceptable risk-adjusted returns</li>")
        else:
            feedback.append("<li>⚠️ <strong>Low Sharpe ratio:</strong> Consider improving risk management</li>")

        # Profit factor assessment
        if profit_factor > 2.0:
            score += 3
            feedback.append("<li>✅ <strong>Excellent Profit Factor:</strong> 2x+ more wins than losses</li>")
        elif profit_factor > 1.5:
            score += 2
            feedback.append("<li>✅ <strong>Good Profit Factor:</strong> Solid win/loss ratio</li>")
        else:
            feedback.append("<li>⚠️ <strong>Low Profit Factor:</strong> Losing trades outweigh wins</li>")

        # Win rate assessment
        if win_rate > 0.60:
            score += 3
            feedback.append("<li>✅ <strong>High Win Rate:</strong> 60%+ of trades profitable</li>")
        elif win_rate > 0.50:
            score += 2
            feedback.append("<li>✅ <strong>Acceptable Win Rate:</strong> >50% profitable trades</li>")
        else:
            feedback.append("<li>⚠️ <strong>Low Win Rate:</strong> <50% trades are profitable</li>")

        # Drawdown assessment
        if max_dd < 20:
            score += 3
            feedback.append("<li>✅ <strong>Controlled Drawdown:</strong> <20% max peak-to-trough</li>")
        elif max_dd < 40:
            score += 2
            feedback.append("<li>⚠️ <strong>Moderate Drawdown:</strong> 20-40% peak-to-trough</li>")
        else:
            feedback.append("<li>❌ <strong>High Drawdown:</strong> >40% peak-to-trough decline</li>")

        # Determine rating
        if score >= 10:
            rating = "🟢 STRONG - Ready for deployment"
        elif score >= 7:
            rating = "🟡 MODERATE - Consider with caution"
        else:
            rating = "🔴 WEAK - Needs improvement"

        return {
            "rating": rating,
            "text": "".join(feedback),
            "score": score
        }

    def _build_metrics_cards(self, metrics: Dict, trade_stats: Dict) -> str:
        """Build metrics card grid HTML."""
        return f"""
        <div class="metric-card">
            <h3>Sharpe Ratio</h3>
            <div class="value" style="color: {'#27ae60' if metrics['sharpe_ratio'] > 1 else '#e74c3c'};">{metrics['sharpe_ratio']:.2f}</div>
            <div class="unit">Risk-Adjusted Returns</div>
        </div>
        <div class="metric-card">
            <h3>Profit Factor</h3>
            <div class="value" style="color: {'#27ae60' if metrics['profit_factor'] > 1.5 else '#e74c3c'};">{metrics['profit_factor']:.2f}x</div>
            <div class="unit">Win/Loss Ratio</div>
        </div>
        <div class="metric-card">
            <h3>Win Rate</h3>
            <div class="value" style="color: {'#27ae60' if metrics['win_rate'] > 0.50 else '#e74c3c'};">{metrics['win_rate']:.1%}</div>
            <div class="unit">Profitable Trades</div>
        </div>
        <div class="metric-card">
            <h3>Max Drawdown</h3>
            <div class="value" style="color: {'#27ae60' if metrics['max_drawdown_pct'] < 20 else '#e74c3c'};">{metrics['max_drawdown_pct']:.2f}%</div>
            <div class="unit">Peak-to-Trough</div>
        </div>
        <div class="metric-card">
            <h3>Total Trades</h3>
            <div class="value">{int(metrics['trade_count'])}</div>
            <div class="unit">Executed</div>
        </div>
        <div class="metric-card">
            <h3>Expectancy</h3>
            <div class="value" style="color: {'#27ae60' if trade_stats['expectancy'] > 0 else '#e74c3c'};">${trade_stats['expectancy']:.4f}</div>
            <div class="unit">Avg Per Trade</div>
        </div>
        """


if __name__ == "__main__":
    generator = ModelsReportGenerator()
    generator.generate_report()
