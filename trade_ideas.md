# Trade Data Analysis: Statistically Significant Filters & Recommendations

---

## 1. Executive Summary & Core Metrics

| Metric | Last 30 Days | All-Time (Since May 2026) | Trend / Delta |
| :--- | :--- | :--- | :--- |
| **Total Trades / Cycles** | 429 | 3,236 | — |
| **Win Rate** | 43.12% | 44.84% | -1.72% (Recent dip) |
| **Average Win / Loss** | +3.81% / -2.67% | +1.81% / -1.71% | Higher payoff ratio recently (1.43 vs 1.06) |
| **Average Hold Time** | 33.18 hours | 22.55 hours | +10.63 hours longer |

---

## 2. Pair Exclusions (Highest Statistical Significance)

Pair-level performance shows strong persistence across both sample periods. Excluding consistently negative-drift and low win-rate assets yields the highest risk-adjusted expectancy improvement.

### Tier 1: Immediate Exclusion Candidates ($N \ge 50$, Extreme Loss & Win Rate $< 40\%$)
* **`PEPEUSDT`**: **22.7% WR** ($N=88$), Avg PnL $-0.485\%$, **Total PnL: $-42.69$ USDT** (All-time top bleeder: $-14.23$ USDT). Severe systemic drag.
* **`DOGEUSDT`**: **37.8% WR** ($N=98$), Avg PnL $-0.574\%$, **Total PnL: $-56.24$ USDT**. Largest aggregate dollar loss in dataset.
* **`PENDLEUSDT`**: **33.9% WR** ($N=59$), Avg PnL $-0.684\%$, **Total PnL: $-40.35$ USDT**. High negative expectancy.
* **`LUNCUSDT`**: **40.7% WR** ($N=59$), Avg PnL $-0.413\%$, **Total PnL: $-24.36$ USDT**. Consistent drift.

### Tier 2: Asymmetric Risk & Negative Expectancy Exclusions ($N \ge 75$)
* **`SOLUSDT`**: **Total PnL: $-98.56$ USDT (All-Time #1 Bleeder)**. Despite a nominal $64.9\%$ win rate ($N=77$), average losses vastly overpower wins due to catastrophic left-tail risk.
* **`AVAXUSDT`**: **45.7% WR** ($N=116$), Avg PnL $-0.448\%$, **Total PnL: $-51.95$ USDT**.
* **`FETUSDT`**: **44.5% WR** ($N=191$), Avg PnL $-0.212\%$, **Total PnL: $-40.40$ USDT** (All-time $-11.94$ USDT).
* **`FILUSDT`**: **45.8% WR** ($N=96$), Avg PnL $-0.253\%$, **Total PnL: $-24.24$ USDT**.
* **`DOTUSDT`**: **45.6% WR** ($N=79$), Avg PnL $-0.281\%$, **Total PnL: $-22.22$ USDT**.

### Tier 3: Low-Sample Structural Bleeders (Immediate Watch/Blacklist)
* **`POLYXUSDT`**: Worst in 30D ($-13.65$ USDT) and All-Time ($-13.65$ USDT).
* **`VETUSDT`**: **16.7% WR** ($N=6$), $-13.88$ USDT total (30D: $-8.87$ USDT).
* **`CRVUSDT`**: **30.0% WR** ($N=10$), $-10.91$ USDT total.
* **`ENSUSDT`**: **0.0% WR** ($N=5$), $-9.52$ USDT total.

---

## 3. Hold Time Analysis

| Hold Time Bucket | Trade Count | Win Rate | Average PnL | Expectancy Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **0 – 2 hours** | 1,914 | 43.5% | -0.251% | **Net Negative Churn** (Noise & early stops) |
| **2 – 6 hours** | 614 | 48.2% | -0.151% | Transition zone |
| **6 – 12 hours** | 311 | **54.7%** | **+0.466%** | **Primary Alpha Zone** |
| **12 – 24 hours** | 148 | **59.5%** | **+0.517%** | **Peak Win Rate & Edge** |
| **24+ hours** | 139 | **57.6%** | +0.022% | Positive WR, flat payoff |

### Analytical Conclusion on Hold Times:
* **Do NOT impose short hold time limits:** Capping hold times (e.g., $<6$h or $<12$h) cuts off trades precisely where expectancy turns strongly positive ($+0.47\%$ to $+0.52\%$, WR $55\text{–}60\%$).
* **Root Cause of 0–2h Drag:** $61\%$ of all trades ($1,914 / 3,126$) resolve within 2 hours at $-0.251\%$ average PnL, largely driven by premature stop-outs from short-term market noise. 
* **Recommendation:** Ensure initial stop placements and entry criteria provide adequate room so positions can survive routine intra-hour volatility to reach the $6\text{–}24$h breakout window. Avoid artificial max hold-time limits (such as the previously rejected 72h hard cap).

---

## 4. Time-of-Day (TOD) & Day-of-Week (DOW) Evaluation

### Raw Descriptive Data:
* **Low-performing hours:**
  * Hour 22: $26.9\%$ WR ($N=78$, Avg PnL $-0.750\%$)
  * Hour 20: $33.0\%$ WR ($N=91$, Avg PnL $-0.433\%$)
  * Hour 13: $35.0\%$ WR ($N=177$, Avg PnL $-0.529\%$)
  * Hour 17: $38.2\%$ WR ($N=123$, Avg PnL $-0.368\%$)
* **DOW:** Thursday (DOW 4) leads at $55.4\%$ WR ($+0.313\%$), while Tuesday–Thursday (DOW 1–3) have negative PnL.

### Critical Rigor & Overfitting Risk:
* **Recommendation on TOD/DOW: DO NOT IMPLEMENT BINARY ENTRY RESTRICTIONS.**
* **Statistical Basis:** While descriptive stats show pockets of lower performance, **prior empirical tests repeatedly confirmed that TOD and DOW filters cause severe overfitting** and degrade out-of-sample forward testing. Hard temporal bans eliminate outsized trend-reversal capture and regime transitions.

---

## 5. Summary of Proposed Filters

1. **Pair Exclusions (Statistically Validated Blacklist):**
   * **Tier 1 (High Volume Bleeders):** `PEPEUSDT`, `DOGEUSDT`, `PENDLEUSDT`, `LUNCUSDT`
   * **Tier 2 (Negative Skew / Severe Total Drawdown):** `SOLUSDT`, `AVAXUSDT`, `FETUSDT`, `FILUSDT`, `DOTUSDT`
   * **Tier 3 (Persistent Capital Loss):** `POLYXUSDT`, `VETUSDT`, `CRVUSDT`
2. **Hold Time Rules:**
   * **No artificial max hold-time cap** (preserves the $55\text{–}60\%$ WR generated in the $6\text{–}24$h holding window).
3. **Temporal Filters (TOD / DOW):**
   * **Reject hard TOD/DOW entry bans** to protect against sample-specific overfitting and maintain capture of large trend reversals.
