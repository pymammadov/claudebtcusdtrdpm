# BTCUSD Perpetual Futures Automated Trading Pipeline

Complete automated strategy discovery, validation, and deployment system for BTCUSDT perpetual futures trading on Binance.

## Overview

This system implements a 4-stage pipeline:

1. **Stage 1**: Data Collection — Fetch historical BTCUSDT candles from Binance API
2. **Stage 2**: Strategy Discovery — Generate 120+ strategies using 5 templates + 3 timeframes
3. **Stage 3**: Validation & Selection — Backtest, score, and select the best model
4. **Stage 4**: Live Deployment — Paper/live trading bot with risk management

---

## Directory Structure

```
btcusd-trader/
├── data/
│   ├── fetch_data.py          # Stage 1: Data collection
│   └── raw/                   # Generated: Parquet files (15m, 1h, 4h)
│
├── backtest/
│   ├── indicators.py          # Technical indicator library
│   ├── templates.py           # Strategy templates (A-E)
│   ├── engine.py              # Vectorized backtesting engine
│   ├── scorer.py              # Model validation & scoring
│   └── run_optimization.py    # Main orchestrator (Stages 2-3)
│
├── live/
│   ├── data_feed.py           # Live candle fetching
│   ├── indicators.py          # Real-time indicator computation
│   ├── strategy.py            # Signal evaluation
│   ├── risk_manager.py        # Position sizing & drawdown limits
│   ├── executor.py            # Order execution
│   ├── monitor.py             # Health checks & reconnection
│   ├── journal.py             # Trade logging (SQLite + CSV)
│   └── main.py                # Main bot orchestrator
│
├── results/                   # Generated outputs
│   ├── leaderboard.csv        # All models ranked
│   ├── winner.json            # Selected strategy config
│   ├── trade_journal.db       # SQLite trade records
│   ├── trades.csv             # CSV trade log
│   └── run_*.log              # Execution logs
│
├── tests/                     # Unit tests
│
├── config.yaml                # Live bot configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Setup

### 1. Clone & Install

```bash
git clone <repo>
cd btcusd-trader
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.yaml`:

```yaml
# Critical settings
paper_trading: true                    # MUST be true initially
risk_per_trade_pct: 1.0               # 1% risk per trade
max_daily_loss_pct: 3.0               # Kill-switch at 3% daily loss
```

Set environment variables:

```bash
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

---

## Usage

### Stage 1: Fetch Data

```bash
cd data
python fetch_data.py
```

Fetches all 3 timeframes (15m, 1h, 4h) from 2020-01-01 to present. Saves to `data/raw/BTCUSDT_*.parquet`.

**Time**: ~5-10 minutes depending on API rate limits.

### Stage 2 & 3: Strategy Discovery & Validation

```bash
cd backtest
python run_optimization.py
```

Generates 120+ models, backtests on in-sample period (2020-01-01 to 2023-06-30), validates on out-of-sample period (2023-07-01 to present).

**Outputs**:
- `results/leaderboard.csv` — All models ranked by composite score
- `results/winner.json` — Best model configuration
- `results/oos_report.md` — Out-of-sample comparison
- `results/run_*.log` — Full execution log

**Time**: 30-60 minutes (depending on machine).

### Stage 4: Live Paper Trading

```bash
cd live
python main.py
```

Starts paper trading bot using the winner strategy. Runs indefinitely until stopped.

**Outputs**:
- `trade_journal.db` — SQLite database of all trades
- `trades.csv` — CSV export of trades
- `trading_bot.log` — Real-time bot logs

---

## Strategy Templates

### Template A: Trend + Momentum
Entry: Fast EMA > Slow EMA AND RSI < threshold (long)
Exit: Fixed RR (1.5, 2.0, 2.5, 3.0) or ATR-based SL/TP

### Template B: Bollinger Bands Breakout
Entry: Close breaks above/below BB with volume confirmation
Exit: Fixed RR or ATR-based

### Template C: Mean Reversion
Entry: RSI oversold/overbought + close beyond Keltner Channel
Exit: Signal reversal or fixed RR

### Template D: MACD Cross + Trend Filter
Entry: MACD crossover + trend filter (EMA)
Exit: Signal reversal or fixed RR

### Template E: Multi-Timeframe
Entry: Higher TF trend + lower TF RSI signal
Exit: ATR-based SL/TP

---

## Backtesting Rules

- **Fees**: 0.06% taker fee (worst-case)
- **Slippage**: 0.04% per side
- **Position Sizing**: 1% risk per trade (ATR-based)
- **Max 1 Position**: No pyramiding
- **Entry**: On NEXT candle OPEN after signal (no lookahead)
- **Train/Test Split**: 
  - In-sample: 2020-01-01 → 2023-06-30
  - Out-of-sample: 2023-07-01 → present

---

## Model Selection Criteria

### Hard Filters (disqualify if ANY fails)
- Sharpe Ratio < 1.2
- Profit Factor < 1.5
- Max Drawdown > 20%
- Trade Count < 40 (in-sample)
- Consecutive Losses > 8

### Scoring (normalized)
```
Score = 0.35 × Sharpe Ratio
      + 0.25 × Profit Factor
      + 0.20 × 1/Max Drawdown
      + 0.10 × Win Rate
      + 0.10 × Trade Count
```

### Out-of-Sample Overfitting Filter (top 10 models)
- OOS Sharpe ≥ 70% of IS Sharpe
- OOS Profit Factor ≥ 65% of IS Profit Factor

---

## Live Trading

### Paper Trading Mode

Default mode (`paper_trading: true`):
- Simulates order fills at signal candle close price
- Tracks virtual portfolio separately
- All risk controls active
- **Minimum duration before live**: 30 days OR 20 trades (whichever is later)

### Transitioning to Live

**DO NOT GO LIVE UNTIL:**

- [ ] Paper trading for ≥30 days with consistent profitability
- [ ] ≥20 trades completed in paper mode
- [ ] Daily P&L matches backtest expectations
- [ ] Risk manager limits tested (confirm kill-switch works)
- [ ] API keys tested (deposit small amount, verify orders work)
- [ ] All logs reviewed for errors
- [ ] Drawdown < 10% in paper mode
- [ ] No issues with connectivity or data feed

**Going Live**:

```yaml
# config.yaml
paper_trading: false        # CAREFUL!
initial_balance: 100.0      # Start small
risk_per_trade_pct: 1.0     # Increase cautiously
```

---

## Risk Management

### Non-Negotiable Controls

1. **Daily Loss Kill-Switch**
   - Halts trading if daily P&L < -3% of initial balance
   - Triggered in `risk_manager.py`

2. **Per-Trade Stop-Loss**
   - Mandatory at order placement
   - Based on ATR (1.5×ATR or 2×ATR)

3. **API Failure Handling**
   - Cancel open orders on disconnect
   - Close positions on extended API downtime
   - Exponential backoff retry (max 5 attempts)

4. **Unexpected Price Gaps**
   - Reduce position size 50% on gap detection
   - Implemented in `risk_manager.calculate_position_size()`

5. **Reconnection Logic**
   - Exponential backoff: 2s → 4s → 8s → 16s → 32s max
   - Max 5 retries before halt

---

## Monitoring

### Console Output

```
2026-04-14 10:30:45 - main - INFO - Status: {'balance': 1050.23, 'daily_pnl': 50.23, 'drawdown_%': 0.0, 'open_positions': 1}
```

### Log Files

- `trading_bot.log` — Real-time trades and system events
- `results/run_*.log` — Backtesting execution logs

### Trade Journal

All trades recorded to:
- `trade_journal.db` — SQLite (queryable)
- `trades.csv` — Excel-friendly export

Query trades:

```python
from live.journal import TradeJournal
journal = TradeJournal()
stats = journal.get_stats()
print(stats)  # {'total_trades': 42, 'win_rate_%': 52.4, 'total_pnl': 234.56, ...}
```

### Optional: Telegram Alerts

```yaml
telegram_enabled: true
telegram_bot_token: ${TELEGRAM_BOT_TOKEN}
telegram_chat_id: ${TELEGRAM_CHAT_ID}
```

Alerts on:
- Trade open/close
- Kill-switch triggered
- API errors

---

## Monthly Retraining

Reoptimize monthly to adapt to market changes:

```bash
# 1. Fetch latest data
python data/fetch_data.py

# 2. Rerun optimization
python backtest/run_optimization.py

# 3. Review new winner
cat results/winner.json

# 4. Update live bot (paper first!)
# Edit config.yaml, restart main.py
```

---

## Troubleshooting

### No data fetched
```
ERROR: No data files found
→ Run: python data/fetch_data.py
→ Check: data/raw/BTCUSDT_*.parquet exists
```

### Backtest produces 0 trades
```
→ Check: Signal generation (debug _signal_template_* functions)
→ Check: Data has sufficient history for indicators
→ Lower hard filter thresholds temporarily
```

### Paper trading not executing signals
```
→ Check: results/winner.json is valid JSON
→ Check: config.yaml timeframe matches winner timeframe
→ Check: API connectivity (print candle updates)
```

### Kill-switch triggers immediately
```
→ Check: Max daily loss % threshold (too tight?)
→ Check: Paper mode balance (might be too small)
→ Review: risk_manager.py logic
```

---

## Testing

Unit tests for critical modules:

```bash
pytest tests/test_signals.py -v      # Signal generation
pytest tests/test_risk_manager.py -v # Position sizing
pytest tests/test_scorer.py -v       # Model scoring
```

---

## Performance Expectations

### Backtesting (Stage 2-3)
- **Target Sharpe**: 1.5-2.5 (in-sample)
- **Target Profit Factor**: 1.8-2.5
- **Target Win Rate**: 45-60%
- **Expected Drawdown**: 8-15%

### Live Trading
- Expect 10-30% degradation vs. backtest (slippage, fees, market impact)
- Require ≥3-6 months of paper trading data before live
- Daily P&L variance is normal; focus on weekly/monthly trends

---

## Language Choices & Justification

**Python** for entire stack (data, backtest, live):

| Component | Language | Rationale |
|-----------|----------|-----------|
| Data fetching | Python | Binance API library, pandas ecosystem |
| Backtesting | Python | Vectorized (NumPy), fast enough for 120 models |
| Indicator calculation | Python | TA-Lib integration, NumPy performance |
| Model scoring | Python | Statistical analysis (SciPy), consistent stack |
| Live trading | Python | AsyncIO for concurrent API/data, single codebase |

**Alternative considered**: Rust for backtesting (faster), but Python's ecosystem and development speed won out. Backtest runtime (30-60 min) is acceptable.

---

## Files & Deliverables

✅ Complete, runnable codebase
✅ Clear docstrings on all modules
✅ All magic numbers in config.yaml
✅ Unit tests for signals, risk manager, scorer
✅ No external paid APIs (Binance public only)
✅ Comprehensive README with "DO NOT GO LIVE UNTIL" checklist

---

## Support & Contributing

For issues, check:
1. Logs (results/*.log, trading_bot.log)
2. Data quality (verify parquet files have 3+ timeframes)
3. Backtest metrics (leaderboard.csv has passing models)
4. Configuration (config.yaml matches env vars)

---

## License

Proprietary trading system. Use at your own risk.

---

**Last Updated**: 2026-04-14
