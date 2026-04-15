# Trading Strategy Optimization - Report Guide

## 📊 Available Reports

### 1. **models_analysis.html** - Trade-Level Analysis Report
**Yeri:** `btcusd-trader/results/models_analysis.html`

**İçərisində:**
- ✅ Hər bir trade-in detayı (entry price, exit price, P&L, timing)
- ✅ Trade istatistikası:
  - Average win/loss size
  - Win/loss ratio
  - Expectancy (hər trade-dən orta gəlir)
  - Recovery factor (profit / max drawdown)
- ✅ P&L dağılımı (total wins, losses, net)
- ✅ Modelin gücü qiymətləndirmesi:
  - 🟢 STRONG - Deployment-a hazır
  - 🟡 MODERATE - Ehtiyatla işlət
  - 🔴 WEAK - Yaxşılaşdırma lazım
- ✅ İnterktiv trade filtrləmə (axtarış)
- ✅ Model quality metrics

**Istifadə:**
```bash
# Browser-də aç
firefox btcusd-trader/results/models_analysis.html

# Və ya VS Code-da
code btcusd-trader/results/models_analysis.html
```

---

### 2. **optimization_report.html** - Winner Model Overview
**Yeri:** `btcusd-trader/results/optimization_report.html`

**İçərisində:**
- ✅ Ən yaxşı modelin xülasəsi
- ✅ Key performance metrics:
  - Sharpe ratio
  - Profit factor
  - Win rate
  - Max drawdown
- ✅ In-sample vs Out-of-sample comparison
- ✅ Strategy parameters
- ✅ Key insights

---

## 🎯 Model Seçim Kriteriləri

### Strong Model Şərtləri ✅
```
Sharpe Ratio       > 1.5  (risk-adjusted returns)
Profit Factor      > 2.0  (2x more wins than losses)
Win Rate          > 60%   (60%+ profitable trades)
Max Drawdown      < 20%   (controllable risk)
Trade Count       > 50    (statistical significance)
```

### Moderate Model Şərtləri ⚠️
```
Sharpe Ratio       1.0-1.5
Profit Factor      1.5-2.0
Win Rate          50-60%
Max Drawdown      20-40%
Trade Count       30-50
```

### Weak Model - Avoid ❌
```
Sharpe Ratio       < 1.0
Profit Factor      < 1.5
Win Rate          < 50%
Max Drawdown      > 40%
Trade Count       < 20
```

---

## 📈 Trade Analysis - Ne Axtarmaq Lazım

### 1. **Win/Loss Ratio**
- **İdeal:** 1.5x-2.5x
- **Nə deməkdir:** Hər uduşlu trade ortalama 1.5-2.5 dəfə böyük uduş əldə edir

### 2. **Expectancy (Orta Gəlir)**
- **İdeal:** > $0.50 per trade
- **Hesablama:** (Total Wins - Total Losses) / Trade Count
- **Nə deməkdir:** Hər trade-dən ortalama gəlir

### 3. **Recovery Factor**
- **İdeal:** > 2.0
- **Hesablama:** Total Profit / Max Drawdown
- **Nə deməkdir:** Nə qədər tez profit-ə qayıda bilir

### 4. **Consecutive Losses**
- **İdeal:** < 5
- **Nə deməkdir:** Maksimum ardıcıl itki əld e tutan trade sayı
- **Risk:** Yüksək consecutive losses = psikoloji stress

---

## 🚀 Workflow: Model Seçim

### Step 1: Report Açın
```bash
firefox btcusd-trader/results/models_analysis.html
```

### Step 2: Model Gücünü Qiymətləndirin
- 🟢 **STRONG** modellərə fokuslanın
- Sharpe, Profit Factor, Win Rate yoxlayın

### Step 3: Trade Detaylarını Analiz Edin
- Trade histogram-ını yoxlayın
- P&L distribution-u analiz edin
- Consecutive losses kontrol edin

### Step 4: Parametrləri Yoxlayın
- Strategy template (A, B, C, D, E)
- Indicator parametrləri
- Exit strategy (fixed_rr, atr_based, signal_reversal)

### Step 5: Out-of-Sample Validation
- OOS Sharpe ratio In-Sample-dən yüksəkdir?
- Degradation < 20%?

---

## 📊 Rapor Yaratma Komutu

### Tek Report Yaratmaq
```python
from backtest.models_report import ModelsReportGenerator

gen = ModelsReportGenerator()
gen.generate_report("models_analysis.html")
```

### Optimization-dan Sonra Avtomatik
Optimization bitdikdən sonra `winner.json` avtomatik olaraq `trades` sahəsi ilə yaranacaq.

---

## 💡 Nümunə: Winner Model Analiz

**Siz burada göstərilən:**
```json
{
  "model_id": "MODEL_042",
  "template": "TEMPLATE_A (Trend + Momentum)",
  "timeframe": "15m",
  "sharpe_ratio": 1.85,        ✅ Strong
  "profit_factor": 2.3,         ✅ Strong
  "win_rate": 0.58,            ✅ 58% - Good
  "max_drawdown_pct": 12.5,    ✅ Controllable
  "trade_count": 52,           ✅ Statistically valid
  "out_of_sample_sharpe": 1.42  ✅ Robust (23% degradation is OK)
}
```

**Qiymətləndirmə:**
- 🟢 **STRONG - Ready for deployment**
- Bütün kriteriyalar keçilmiş
- OOS performance yaxşı
- Trade count yeterli

---

## ⚙️ Optimization Fonda Çalışarkən

Optimallaşdırma davam edərkən:

```bash
# Progress yoxla
tail -f /tmp/opt_full.log | grep "Progress\|WINNER"

# Model sayı kontrol et
tail -1 /tmp/opt_full.log | grep -oE "MODEL_[0-9]+"
```

**Təxmini vaxt:** 4392 model × 2-3ms = 8-13 saniyə (+ data setup)

---

## 📁 File Structure

```
btcusd-trader/
├── backtest/
│   ├── engine.py              ← Trade export method
│   ├── run_optimization.py    ← Trades saved here
│   └── models_report.py       ← Report generator
├── results/
│   ├── winner.json            ← Winner with trades
│   ├── models_analysis.html   ← 📊 Trade analysis report
│   ├── optimization_report.html  ← Winner overview
│   └── leaderboard.csv        ← All models ranking
```

---

## 🎓 Real-World Sceario

**Siz istəyirsiniz:** Ən güçlü 3-5 modeli seçmək

1. **models_analysis.html açın** → Report göstəri
2. **Metrics yoxlayın** → 🟢 STRONG filtri
3. **Trade patterns analiz edin** → Consistent wins?
4. **Parametrləri yazın** → Config.json-da saxlayın
5. **Live trading-ə hazırla** → Position sizing, risk management

---

**Hazır? Aşağıdakı komutu çalıştırın:**

```bash
cd btcusd-trader
python backtest/run_optimization.py  # Optimization başlat
# Bitdikdən sonra:
python backtest/models_report.py     # Report yarataq
# Sonra browser-də:
firefox results/models_analysis.html # Analiz et
```

