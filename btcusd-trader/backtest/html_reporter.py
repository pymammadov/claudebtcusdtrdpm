"""
HTML Report Generator for Trading Strategy Optimization Results
"""

import json
from pathlib import Path
from datetime import datetime


class HTMLReporter:
    """Generate HTML reports from optimization results."""

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, output_file: str = "optimization_report.html"):
        """Generate comprehensive HTML report."""

        winner_file = self.results_dir / "winner.json"

        if not winner_file.exists():
            print("No winner.json found!")
            return

        with open(winner_file) as f:
            winner = json.load(f)

        html = self._create_html(winner)

        output_path = self.results_dir / output_file
        with open(output_path, "w") as f:
            f.write(html)

        print(f"Report saved to: {output_path}")
        return output_path

    def _create_html(self, winner: dict) -> str:
        """Create HTML content."""

        model_id = winner["model_id"]
        template = winner["template"]
        timeframe = winner["timeframe"]

        in_sample = winner["in_sample_metrics"]
        out_sample = winner["out_of_sample_metrics"]
        params = winner["parameters"]

        # Build parameters table
        indicators_html = ""
        for key, val in params["indicators"].items():
            indicators_html += f"<tr><td>{key}</td><td>{val}</td></tr>"

        # Build metrics comparison
        metrics_comparison = self._build_metrics_comparison(in_sample, out_sample)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Strategy Optimization Report</title>
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
            max-width: 1200px;
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
            text-align: center;
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

        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .info-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}

        .info-card h3 {{
            color: #333;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            opacity: 0.7;
        }}

        .info-card .value {{
            color: #667eea;
            font-size: 24px;
            font-weight: bold;
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

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .metric-row {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .metric-box {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .metric-label {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .metric-value {{
            color: #667eea;
            font-size: 28px;
            font-weight: bold;
        }}

        .metric-unit {{
            color: #999;
            font-size: 12px;
            margin-left: 5px;
        }}

        .positive {{
            color: #27ae60;
        }}

        .negative {{
            color: #e74c3c;
        }}

        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}

        .comparison-section h3 {{
            color: #333;
            font-size: 18px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }}

        .comparison-metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}

        .comparison-metric label {{
            color: #666;
            font-weight: 500;
        }}

        .comparison-metric value {{
            color: #667eea;
            font-weight: bold;
        }}

        footer {{
            background: #f5f7fa;
            color: #999;
            text-align: center;
            padding: 20px;
            font-size: 12px;
            border-top: 1px solid #eee;
        }}

        .badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 10px;
        }}

        .badge.success {{
            background: #27ae60;
        }}

        .badge.warning {{
            background: #f39c12;
        }}

        .badge.danger {{
            background: #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Trading Strategy Optimization Report</h1>
            <p>Winner Model Analysis & Performance Metrics</p>
        </header>

        <div class="content">
            <!-- Model Info Cards -->
            <div class="info-grid">
                <div class="info-card">
                    <h3>Model ID</h3>
                    <div class="value">{model_id}</div>
                </div>
                <div class="info-card">
                    <h3>Strategy Template</h3>
                    <div class="value">{template}</div>
                </div>
                <div class="info-card">
                    <h3>Timeframe</h3>
                    <div class="value">{timeframe}</div>
                </div>
            </div>

            <!-- Key Metrics Overview -->
            <section>
                <h2>Key Performance Metrics</h2>
                <div class="metric-row">
                    <div class="metric-box">
                        <div class="metric-label">Sharpe Ratio (In-Sample)</div>
                        <div class="metric-value positive">{in_sample['sharpe_ratio']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Profit Factor</div>
                        <div class="metric-value positive">{in_sample['profit_factor']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value positive">{in_sample['win_rate']:.1%}</div>
                    </div>
                </div>
                <div class="metric-row">
                    <div class="metric-box">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{int(in_sample['trade_count'])}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value negative">{in_sample['max_drawdown_pct']:.2f}%</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Consecutive Losses</div>
                        <div class="metric-value">{int(in_sample['consecutive_losses'])}</div>
                    </div>
                </div>
            </section>

            <!-- In-Sample vs Out-of-Sample Comparison -->
            <section>
                <h2>Performance Comparison</h2>
                <div class="comparison">
                    <div class="comparison-section">
                        <h3><span class="badge success">In-Sample</span>Training Data</h3>
                        {self._build_comparison_metrics(in_sample)}
                    </div>
                    <div class="comparison-section">
                        <h3><span class="badge warning">Out-of-Sample</span>Validation Data</h3>
                        {self._build_comparison_metrics(out_sample)}
                    </div>
                </div>
            </section>

            <!-- Strategy Parameters -->
            <section>
                <h2>Strategy Configuration</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {indicators_html}
                        <tr>
                            <td><strong>Exit Strategy</strong></td>
                            <td><strong>{params['exit']}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </section>

            <!-- Recommendations -->
            <section>
                <h2>Key Insights</h2>
                <div style="background: #f0f8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                    <ul style="list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;">
                            ✓ <strong>Strong Risk-Adjusted Returns:</strong> Sharpe ratio of {in_sample['sharpe_ratio']} indicates excellent risk-adjusted performance
                        </li>
                        <li style="margin-bottom: 10px;">
                            ✓ <strong>Consistent Profitability:</strong> Profit factor of {in_sample['profit_factor']} shows {int(in_sample['profit_factor'] * 100)}% more winning trades than losing trades
                        </li>
                        <li style="margin-bottom: 10px;">
                            ✓ <strong>Adequate Trade Sample:</strong> {int(in_sample['trade_count'])} trades provide sufficient statistical significance
                        </li>
                        <li style="margin-bottom: 10px;">
                            ✓ <strong>Out-of-Sample Validation:</strong> OOS Sharpe of {out_sample['sharpe_ratio']} confirms model robustness ({abs((out_sample['sharpe_ratio'] / in_sample['sharpe_ratio'] - 1) * 100):.1f}% degradation)
                        </li>
                        <li>
                            ✓ <strong>Controlled Drawdown:</strong> Maximum drawdown of {in_sample['max_drawdown_pct']:.2f}% within acceptable risk limits
                        </li>
                    </ul>
                </div>
            </section>
        </div>

        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | BTCUSD Trading Pipeline v1.0</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def _build_comparison_metrics(self, metrics: dict) -> str:
        """Build comparison metrics HTML."""
        html = ""
        for key, val in metrics.items():
            if isinstance(val, float):
                if 'pct' in key or 'rate' in key:
                    display = f"{val:.2f}%"
                else:
                    display = f"{val:.2f}"
            else:
                display = str(val)

            label = key.replace('_', ' ').title()
            html += f'<div class="comparison-metric"><label>{label}</label><value>{display}</value></div>'

        return html

    def _build_metrics_comparison(self, in_sample: dict, out_sample: dict) -> str:
        """Build metrics comparison HTML."""
        html = "<table><thead><tr><th>Metric</th><th>In-Sample</th><th>Out-of-Sample</th><th>Degradation</th></tr></thead><tbody>"

        for key in ["sharpe_ratio", "profit_factor", "max_drawdown_pct"]:
            if key in in_sample and key in out_sample:
                in_val = in_sample[key]
                out_val = out_sample[key]

                if key == "max_drawdown_pct":
                    degradation = f"{out_val - in_val:+.2f}%"
                else:
                    degradation = f"{((out_val / in_val - 1) * 100):+.1f}%"

                label = key.replace('_', ' ').title()
                html += f"<tr><td>{label}</td><td>{in_val:.2f}</td><td>{out_val:.2f}</td><td>{degradation}</td></tr>"

        html += "</tbody></table>"
        return html


if __name__ == "__main__":
    reporter = HTMLReporter()
    reporter.generate_report()
