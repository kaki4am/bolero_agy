# Historical Trade Data Statistical Analysis & Filter Recommendations

## 1. Executive Summary & Core Diagnosis
* **Long-Term Baseline (Last 30 Days)**: 438 cycles | **41.55% Win Rate** | +3.36% Avg Win vs. -2.62% Avg Loss (Win/Loss ratio 1.29).
* **All-Time Baseline (3,223 Cycles)**: **44.65% Win Rate** | +1.74% Avg Win vs. -1.71% Avg Loss.
* **Primary Leakage Sources**:
  1. **Short-Duration Churn (0–2h hold)**: 61.4% of all trades exit within 2 hours with a **43.4% win rate** and **-0.267 USDT avg PnL** (cumulative -$510 USDT loss).
  2. **Toxic Asset Outliers**: A concentrated basket of recurring underperformers (notably **SOL, DOGE, AVAX, PEPE, PENDLE, NEAR, FET**) accounts for over **-$350 USDT** in aggregate drawdown.
  3. **Overfitting Sensitivity**: Previous forward tests conclusively showed that **hard binary exclusions for Time-of-Day (TOD) and Day-of-Week (DOW) degrade out-of-sample performance** by cutting off fat-tail breakout alpha.

---

## 2. Statistically Significant Filter Analysis

### A. Pair Exclusions (Highest Statistical Significance)
Filtering out chronically negative expectancy pairs provides the highest statistical confidence without distorting entry timing mechanics.

#### 🚫 Priority Blacklist Candidates (High Sample Size & Negative Skew)
| Symbol | Trades ($N$) | Win Rate | Avg PnL (USDT) | Total PnL (USDT) | Statistical Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **SOLUSDT** | 77 | 64.9% | -0.325 | **-25.02** (-98.56 All-Time) | High WR masked by catastrophic fat-tail negative skew / tail risk. |
| **DOGEUSDT** | 98 | 37.8% | -0.574 | **-56.24** | Sub-40% win rate, persistent bleed ($p < 0.001$). |
| **AVAXUSDT** | 116 | 45.7% | -0.448 | **-51.95** | Severe loss asymmetry across large sample size. |
| **PEPEUSDT** | 88 | 22.7% | -0.485 | **-42.69** (-14.23 All-Time) | Catastrophic win rate (22.7%), erratic wick stops. |
| **PENDLEUSDT** | 59 | 33.9% | -0.684 | **-40.35** | Poor win rate combined with large average loss. |
| **FETUSDT** | 191 | 44.5% | -0.212 | **-40.40** (-11.94 All-Time) | Chronic negative drag over 191 trades. |
| **NEARUSDT** | 250 | 51.6% | -0.163 | **-40.68** | Negative payoff ratio overrides nominal 51.6% WR. |
| **FILUSDT** | 96 | 45.8% | -0.253 | **-24.24** | Consistent downward slippage/bleed. |
| **LUNCUSDT** | 59 | 40.7% | -0.413 | **-24.36** | High volatility, poor momentum follow-through. |
| **DOTUSDT** | 79 | 45.6% | -0.281 | **-22.22** | Persistent underperformance across cycles. |

*Additional low-sample confirmed structural drains to exclude*: **POLYXUSDT** (-13.65), **AVAUSDT** (-10.82), **VETUSDT** (-13.88, 16.7% WR), and fundamental project cessations (**LSKUSDT, KDAUSDT, SAGAUSDT**).

#### ⭐ Core Whitelist Candidates (High Alpha / Positive Payoff)
* **ZENUSDT**: 10 trades, 60.0% WR, +4.128 avg PnL (**+41.28 USDT** total; All-Time leader at +27.01).
* **BICOUSDT**: 22 trades, 63.6% WR, +1.628 avg PnL (**+35.81 USDT** total).
* **ETHUSDT**: 72 trades, 43.1% WR, +0.400 avg PnL (**+28.83 USDT** total; strong positive asymmetric runups).
* **DASHUSDT**: 14 trades, 57.1% WR, +1.496 avg PnL (**+20.94 USDT** total).
* **CAKEUSDT**: 17 trades, 58.8% WR, +1.233 avg PnL (**+20.97 USDT** total).
* **STXUSDT**: 11 trades, 63.6% WR, +1.646 avg PnL (**+18.11 USDT** total).
* **PROMUSDT**: 27 trades, 55.6% WR, +0.425 avg PnL (**+11.47 USDT** total).

---

### B. Hold Time Optimization
| Hold Bucket | Trades ($N$) | Win Rate | Avg PnL (USDT) | Total Impact | Key Takeaway |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **0–2h** | 1,910 (61.4%) | 43.4% | -0.267 | **-510.0 USDT** | Premature noise stops & whipsaws represent 80%+ of losses. |
| **2–6h** | 612 (19.7%) | 48.0% | -0.178 | **-108.9 USDT** | Transition zone; win rate improves to near baseline. |
| **6–12h** | 307 (9.9%) | **54.1%** | **+0.324** | **+99.5 USDT** | Sweet spot: momentum confirms and trends develop. |
| **12–24h** | 145 (4.7%) | **58.6%** | **+0.439** | **+63.7 USDT** | Peak profitability and highest win rate. |
| **24h+** | 137 (4.4%) | 56.9% | -0.182 | **-24.9 USDT** | Win rate holds, but time decay/funding drags PnL negative. |

* **Filter Recommendation**:
  1. **Noise Buffer (0–2h)**: Do not choke trades with premature trailing stops or micro-tight stop losses in the first 2 hours.
  2. **24-Hour Stagnation Rule (Soft Limit)**: Trades remaining open past 24 hours flip to negative expectancy (-0.182 USDT). Introduce a **24h stagnation exit** (close position if profit is within $[-0.5\%, +0.5\%]$ after 24h) to release capital and eliminate late-stage funding bleed.

---

### C. Time-of-Day (Hour) & Day-of-Week (DOW) Patterns
* **Observed Data Anomalies**:
  * **Weakest Hours**: 
    * Hour 22 (26.9% WR, -0.750 avg)
    * Hour 20 (33.0% WR, -0.433 avg)
    * Hour 13 (34.7% WR, -0.537 avg)
    * Hour 17 (37.2% WR, -0.605 avg)
  * **Strongest Hours**: Hour 14 (56.2% WR, +0.032 avg), Hour 15 (53.7% WR), Hour 4 (+0.237 avg), Hour 23 (+0.307 avg).
  * **DOW Performance**: Friday (DOW 4) leads at **55.2% WR** (+0.223 avg), while Thursday (DOW 3: 43.9% WR, -0.413 avg) and Tuesday (DOW 1: 45.3% WR, -0.258 avg) represent heavy drag.
* **⚠️ Statistical Caveat & Learning Validation**:
  * **Do NOT implement hard binary exclusion filters on hours (13, 17, 20, 22) or DOW**.
  * Previous forward tests repeatedly proved that hard time blocks overfit past chop and inadvertently filter out explosive breakout moves that occur during NY open (13:00–14:00 UTC) or daily close rotations.
  * **Recommended Action**: Instead of hard bans, apply a **0.7x position size reduction** or require stricter confirmation (e.g. higher volume threshold) during high-volatility rollover hours (13:00, 17:00, 20:00, 22:00 UTC) rather than completely blocking entries.

---

## 3. Proposed Filter Rules Summary

1. **Static Pair Exclusion Filter (Immediate Impact)**:
   * **Exclude**: `SOLUSDT`, `DOGEUSDT`, `AVAXUSDT`, `PEPEUSDT`, `PENDLEUSDT`, `FETUSDT`, `NEARUSDT`, `FILUSDT`, `LUNCUSDT`, `DOTUSDT`, `POLYXUSDT`, `AVAUSDT`, `VETUSDT`.
   * *Expected Benefit*: Eliminates >$350 USDT in net drag and removes the lowest win-rate tails (<45%).

2. **Hold Time Stagnation Rule**:
   * **24-Hour Timeout**: If a position has been active for $>24$ hours and remains within breakeven range ($-0.5\% \le \text{PnL} \le +0.5\%$), execute an orderly time-based exit to prevent the negative drift observed in the $24\text{h}+$ bucket.

3. **Execution Sizing over Time-of-Day Exclusion**:
   * Maintain unrestricted entry capability across all hours to avoid out-of-sample curve-fitting, but throttle risk exposure (`risk_multiplier = 0.7`) during historically volatile transition hours (13, 17, 20, 22 UTC).
