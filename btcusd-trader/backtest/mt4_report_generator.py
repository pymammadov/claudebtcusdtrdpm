"""
Top 10 Models HTML Report Generator.
Creates comparison view and expandable trade lists from optimization outputs.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List


class MT4ReportGenerator:
    """Generate a top-10 comparison report from winner and leaderboard model files."""

    TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Top 10 BTCUSD Models Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    h1 {{ margin-bottom: 8px; color: #38bdf8; }}
    .meta {{ margin-bottom: 20px; color: #94a3b8; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #334155; padding: 10px; font-size: 13px; text-align: left; }}
    th {{ background: #1e293b; color: #38bdf8; }}
    tr:nth-child(even) td {{ background: #111827; }}
    tr:nth-child(odd) td {{ background: #0b1220; }}
    .winner {{ background: rgba(34,197,94,0.15) !important; }}
    details {{ margin-bottom: 12px; border: 1px solid #334155; border-radius: 6px; overflow: hidden; }}
    summary {{ cursor: pointer; padding: 10px 12px; background: #1e293b; color: #38bdf8; font-weight: 700; }}
    .trade-wrap {{ max-height: 420px; overflow: auto; }}
    .small {{ font-size: 12px; color: #94a3b8; margin-bottom: 8px; }}
  </style>
</head>
<body>
<div class=\"container\">
  <h1>BTCUSD Top 10 Models Comparison Report</h1>
  <div class=\"meta\">Generated at: {generated_at} | Winner: {winner_model_id}</div>

  <table>
    <thead>
      <tr>
        <th>Model ID</th>
        <th>Template</th>
        <th>Timeframe</th>
        <th>Total Trades</th>
        <th>Win Rate</th>
        <th>Profit Factor</th>
        <th>Sharpe Ratio</th>
        <th>Max Drawdown</th>
        <th>Net Profit</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <h2>Model Trade Lists</h2>
  <div class=\"small\">Click each model to expand its individual trade list.</div>
  {details_html}
</div>
</body>
</html>
"""

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"

    def load_winner(self) -> Dict[str, Any]:
        with open(self.results_dir / "winner.json", "r") as f:
            return json.load(f)

    def load_top_10_models(self) -> List[Dict[str, Any]]:
        with open(self.results_dir / "top_10_models.json", "r") as f:
            return json.load(f)

    @staticmethod
    def _metric(model: Dict[str, Any], key: str, default: float = 0.0) -> float:
        return float(model.get("in_sample_metrics", {}).get(key, default))

    @staticmethod
    def _net_profit(trades: List[Dict[str, Any]]) -> float:
        return float(sum(float(t.get("pnl", 0.0)) for t in trades))

    def _build_rows_html(self, models: List[Dict[str, Any]], winner_model_id: str) -> str:
        rows = []
        for model in models[:10]:
            trades = model.get("trades", [])
            net_profit = self._net_profit(trades)
            row_class = "winner" if model.get("model_id") == winner_model_id else ""
            rows.append(
                f"<tr class='{row_class}'><td>{model.get('model_id', 'N/A')}</td>"
                f"<td>{model.get('template', 'N/A')}</td>"
                f"<td>{model.get('timeframe', 'N/A')}</td>"
                f"<td>{int(self._metric(model, 'trade_count', len(trades)))}</td>"
                f"<td>{self._metric(model, 'win_rate') * 100:.2f}%</td>"
                f"<td>{self._metric(model, 'profit_factor'):.2f}</td>"
                f"<td>{self._metric(model, 'sharpe_ratio'):.2f}</td>"
                f"<td>{self._metric(model, 'max_drawdown_pct'):.2f}%</td>"
                f"<td>{net_profit:,.2f}</td></tr>"
            )
        return "\n".join(rows)

    def _build_trade_details_html(self, models: List[Dict[str, Any]]) -> str:
        sections = []
        for model in models[:10]:
            model_id = model.get("model_id", "N/A")
            trades = model.get("trades", [])

            trade_rows = []
            for idx, trade in enumerate(trades, start=1):
                trade_rows.append(
                    "<tr>"
                    f"<td>{idx}</td>"
                    f"<td>{trade.get('entry_time', '')}</td>"
                    f"<td>{trade.get('exit_time', '')}</td>"
                    f"<td>{trade.get('direction', '')}</td>"
                    f"<td>{float(trade.get('size', 0.0)):.6f}</td>"
                    f"<td>{float(trade.get('entry_price', 0.0)):.2f}</td>"
                    f"<td>{float(trade.get('exit_price', 0.0)):.2f}</td>"
                    f"<td>{float(trade.get('pnl', 0.0)):.2f}</td>"
                    f"<td>{float(trade.get('pnl_pct', 0.0)) * 100:.2f}%</td>"
                    "</tr>"
                )

            if trade_rows:
                table_html = (
                    "<div class='trade-wrap'><table><thead><tr>"
                    "<th>#</th><th>Entry Time</th><th>Exit Time</th><th>Direction</th>"
                    "<th>Size</th><th>Entry Price</th><th>Exit Price</th><th>PNL</th><th>PNL %</th>"
                    "</tr></thead><tbody>"
                    + "".join(trade_rows)
                    + "</tbody></table></div>"
                )
            else:
                table_html = "<div style='padding:12px;'>No trades available.</div>"

            sections.append(
                f"<details><summary>{model_id} | {model.get('template', 'N/A')} | {model.get('timeframe', 'N/A')}</summary>{table_html}</details>"
            )

        return "\n".join(sections)

    def generate_report(self, output_file: str = "top10_report.html") -> str:
        winner = self.load_winner()
        models = self.load_top_10_models()
        winner_model_id = winner.get("model_id", "N/A")

        rows_html = self._build_rows_html(models, winner_model_id)
        details_html = self._build_trade_details_html(models)

        html = self.TEMPLATE.format(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            winner_model_id=winner_model_id,
            rows_html=rows_html,
            details_html=details_html,
        )

        output_path = self.results_dir / output_file
        with open(output_path, "w") as f:
            f.write(html)

        return str(output_path)


if __name__ == "__main__":
    gen = MT4ReportGenerator()
    output = gen.generate_report()
    print(f"✅ Report generated: {output}")
