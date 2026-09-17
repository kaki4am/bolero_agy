### Trade Data Analysis & Statistical Filter Recommendations

---

### Executive Summary & Overfitting Guardrail
* **Baseline Stats**: 3,225 cycles | 44.68% Win Rate (WR) | +1.75% Avg Win vs -1.71% Avg Loss (Ratio: 1.03) | 30-Day WR: 42.01%.
* **Crucial Learning Alignment**: Naive binary **Time-of-Day (TOD)** and **Day-of-Week (DOW)** entry bans were repeatedly rejected in forward testing (2026-09-06, 2026-09-12, 2026-09-13) because hard exclusions cut off major trend-reversal outliers and caused severe out-of-sample degradation. 
* **Core Insight**: The primary drag on strategy profitability is **pair-specific negative skew / toxicity** and **holding time profit-decay past 24 hours**, rather than calendar timing.

---

### 1. Pair Exclusions (Highest Statistical Significance)

Excluding persistent negative-skew and low-probability pairs yields the most immediate, robust improvement without temporal overfitting.

#### A. High-Volume Capital Drains (Statistically Significant)
| Pair | Trades | Win Rate | Avg PnL | Total PnL | Statistical Significance |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **PEPEUSDT** | 88 | **22.7%** | -0.485% | -42.69 USDT | $z = -4.14$, $p < 0.0001$ (Severe structural underperformer) |
| **DOGEUSDT** | 98 | **37.8%** | -0.574% | -56.24 USDT | Single largest dollar loss; fat-tail downside risk |
| **SOLUSDT** | 77 | 64.9% | **-0.325%** | -25.02 USDT | All-time worst (-98.56 USDT). High WR but catastrophic negative win/loss asymmetry |
| **AVAXUSDT** | 116 | 45.7% | **-0.448%** | -51.95 USDT | Consistent negative expectancy despite 45.7% WR |
| **PENDLEUSDT** | 59 | **33.9%** | -0.684% | -40.35 USDT | $z = -1.68$, high loss severity |
| **POLYXUSDT** | - | - | - | -13.65 USDT | Persistent top loser across both 30-day and All-Time DB |

#### B. Toxic Low-Sample Candidates (Immediate Blacklist)
* **ENSUSDT**: 5 trades, **0.0% WR**, avg PnL -1.904%
* **VETUSDT**: 6 trades, **16.7% WR**, avg PnL -2.313% (-13.88 USDT)
* **PEOPLEUSDT**: 6 trades, **16.7% WR**, avg PnL -1.075%
* **HFTUSDT**: 6 trades, **16.7% WR**, avg PnL -1.270%
* **ONGUSDT**: 10 trades, **20.0% WR**, avg PnL -0.786%
* **CRVUSDT**: 10 trades, **30.0% WR**, avg PnL -1.091%

> **Recommendation**: Implement a hard blacklist on **`PEPEUSDT`**, **`DOGEUSDT`**, **`SOLUSDT`**, **`AVAXUSDT`**, **`PENDLEUSDT`**, **`POLYXUSDT`**, and **`VETUSDT`**.  
> *Impact*: Eliminates over **-280 USDT** of cumulative drawdown while removing sub-35% WR drags.

---

### 2. Holding Time Limits (Exit Rule Optimization)

Analyzing performance across duration buckets:
* **0–2h** (1,911 trades / 61.4%): 43.4% WR, -0.258% avg PnL (Premature stops / noise).
* **2–6h** (612 trades): 48.0% WR, -0.178% avg PnL.
* **6–12h** (307 trades): 54.1% WR, **+0.324% avg PnL**.
* **12–24h** (146 trades): **58.9% WR, +0.493% avg PnL (Peak Expectancy Sweet Spot)**.
* **24h+** (137 trades): 56.9% WR, **-0.182% avg PnL (Alpha Decay)**.

#### Key Takeaway & Filter:
* Win rate increases with time up to 24 hours, peaking at 12–24h (+0.493%).
* Beyond 24 hours, win rate remains elevated (56.9%), but average PnL flips sharply negative (-0.182%), demonstrating that winners round-trip back into stops or scratch exits.
* **Recommended Filter**: **Staleness Exit / Time-Decay Trailing Stop at 24 Hours**:
  * Activate an aggressive breakeven or 0.25% profit lock once a position reaches **18–24 hours**.
  * Auto-close any trade hovering within $[-0.5\%, +0.5\%]$ after **24 hours** to eliminate late-cycle drift.

---

### 3. Time-of-Day (TOD) Analysis

#### Empirical In-Sample Weaknesses:
* **Hour 22**: 78 trades | 26.9% WR | avg PnL -0.750% ($z = -3.15, p = 0.0016$)
* **Hour 20**: 91 trades | 33.0% WR | avg PnL -0.433% ($z = -2.25, p = 0.024$)
* **Hour 13**: 176 trades | 34.7% WR | avg PnL -0.537% ($z = -2.67, p = 0.0076$)
* **Hour 17**: 121 trades | 37.2% WR | avg PnL -0.605% ($z = -1.66, p = 0.098$)

#### Overfitting Reconciliation & Recommendation:
* As validated in previous forward tests, **hard-blocking hours 13, 17, 20, and 22 failed out-of-sample** because it missed major breakout reversals.
* **Recommended Filter**: **Soft Risk Multiplier (Not Binary Exclusion)**:
  * Do NOT disable entries during these hours.
  * Apply a **0.5x position sizing factor** or require a higher breakout confidence score during hours `[13, 17, 20, 22]` UTC to curb negative PnL drag without sacrificing alpha capture.

---

### 4. Day-of-Week (DOW) Analysis

* **DOW 0 (Mon)**: 454 trades | 45.6% WR | +0.003% avg PnL
* **DOW 1 (Tue)**: 823 trades | 45.3% WR | -0.258% avg PnL
* **DOW 2 (Wed)**: 323 trades | 45.2% WR | -0.324% avg PnL
* **DOW 3 (Thu)**: 495 trades | 44.0% WR | -0.395% avg PnL ($z = -0.31$, not significant)
* **DOW 4 (Fri)**: 430 trades | **55.3% WR** | **+0.258% avg PnL** ($z = +4.42$, significant positive anomaly)
* **DOW 5 (Sat)**: 249 trades | 45.4% WR | -0.152% avg PnL
* **DOW 6 (Sun)**: 339 trades | 46.9% WR | -0.055% avg PnL

#### Recommendation:
* **NO Day-of-Week Exclusions**: Win rates across Mon–Wed and Sat–Sun are virtually identical (45.2%–46.9%), well within random variance. There is zero statistical justification to ban any day of the week.
* Maintain normal execution across all days; optionally scale up risk slightly on Friday (DOW 4).

---

### Proposed Filter Summary

| Filter Type | Proposed Rule | Rationale / Statistical Basis |
| :--- | :--- | :--- |
| **Pair Exclusion** | Blacklist `PEPEUSDT`, `DOGEUSDT`, `SOLUSDT`, `AVAXUSDT`, `PENDLEUSDT`, `POLYXUSDT`, `VETUSDT` | Statistically validated toxic expectancy ($p < 0.0001$ on PEPE; -$280+$ USDT cumulative loss across group). |
| **Hold Time Limit** | 24-Hour Staleness Exit & Profit Lock | Expectancy peaks at 12–24h (+0.493%) and degrades sharply at >24h (-0.182%). Prevents round-tripping. |
| **Time-of-Day** | Soft Size Reduction (0.5x) on Hours 13, 17, 20, 22 UTC | Avoids hard-filter overfitting while mitigating high-loss hours (26.9%–37.2% WR). |
| **Day-of-Week** | No Exclusion | Differences between weekdays/weekends are statistically insignificant ($z < 0.35$). Avoids overfitting. |
