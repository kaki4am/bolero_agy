# Trade Data Analysis: Statistically Significant Filters & Recommendations

Based on the 3,244 all-time completed cycles and 30-day database metrics, here is the statistical evaluation and actionable filter proposals.

---

### 1. Pair Exclusions (Statistically Significant Blacklist)

Filtering underperforming pairs with substantial trade samples ($N \ge 50$), persistently depressed win rates ($< 40\%$), and severe cumulative PnL drag yields the most statistically robust improvement without curve-fitting temporal noise.

#### **Primary Blacklist Recommendations (High Sample Size & Negative Expectancy):**
1. **`PEPEUSDT`**
   - **Metrics:** 88 trades | **22.7% Win Rate** | **-42.69 USDT** PnL (Avg: -0.485%)
   - **Rationale:** Lowest win rate among actively traded pairs; severe trend slippage.
2. **`DOGEUSDT`**
   - **Metrics:** 98 trades | **37.8% Win Rate** | **-56.24 USDT** PnL (Avg: -0.574%)
   - **Rationale:** Single largest cumulative PnL drain in the active trade log.
3. **`PENDLEUSDT`**
   - **Metrics:** 59 trades | **33.9% Win Rate** | **-40.35 USDT** PnL (Avg: -0.684%)
   - **Rationale:** Consistently fails momentum continuation; high per-trade loss.
4. **`AVAXUSDT`**
   - **Metrics:** 116 trades | 45.7% Win Rate | **-51.95 USDT** PnL (Avg: -0.448%)
   - **Rationale:** Large sample with chronic negative expectancy.
5. **`SOLUSDT` (Severe Asymmetric Tail-Risk Exclusion)**
   - **Metrics:** 77 trades | 64.9% Win Rate | **-25.02 USDT** recent | **-98.56 USDT All-Time Worst**
   - **Rationale:** High win rate masked by severe left-tail blowups (average loss vastly exceeds average win). Requires exclusion or stricter position-level stop architecture.

#### **Secondary Blacklist (Persistent Drag / Structural Flaws):**
- **`POLYXUSDT`** (-13.65 USDT, persistent bottom-5 performer in 30D and All-Time).
- **`VETUSDT`** (16.7% Win Rate, -13.88 USDT PnL).
- **Confirmed Fundamental Cessations (Carryover from Learnings):**
  - **`LSKUSDT`** (blockchain shutdown October 31, 2026).
  - **`SAGAUSDT`** (project pivot away from crypto).
  - **`KDAUSDT`** (project cessation).

---

### 2. Hold Time Limits & Duration Analysis

| Hold Time Bucket | Completed Trades | Win Rate | Average PnL |
| :--- | :---: | :---: | :---: |
| **0 – 2 hours** | 1,917 (59.1%) | **43.4%** | **-0.261%** |
| **2 – 6 hours** | 617 (19.0%) | **48.1%** | **-0.149%** |
| **6 – 12 hours** | 312 (9.6%) | **54.5%** | **+0.450%** |
| **12 – 24 hours** | 149 (4.6%) | **59.1%** | **+0.501%** |
| **24+ hours** | 140 (4.3%) | **57.1%** | **-0.000%** |

#### **Findings & Recommendation:**
- **Win rate scales positively with hold time:** Win rates rise from **43.4% (<2h)** up to **59.1% (12–24h)**. The 30-day metrics confirm that winning trades achieve +3.97% average gain over a 36.1-hour average hold.
- **DO NOT impose a maximum hold time cap (e.g., 24h or 72h limit):** Cutting trades by arbitrary time limits truncates the right tail (+3.0% winners: 83 trades in 30D, 293 all-time) and degrades forward expectancy.
- **Proposed Filter:** Address the **0–2h churn bottleneck** (1,917 trades generating negative expectancy). Rather than exiting early by time, tighten minimum entry confirmation thresholds (e.g., breakout volume/ADX confirmation) to prevent whipsaw entries that get immediately stopped out within 2 hours.

---

### 3. Time-of-Day (TOD) Analysis

| Window (UTC) | Trades | Win Rate | Average PnL | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Hour 22** | 78 | **26.9%** | -0.750% | Worst statistical performance |
| **Hour 20** | 92 | **32.6%** | -0.449% | Low liquidity / US close churn |
| **Hour 13** | 177 | **35.0%** | -0.529% | Pre-US equity open volatility |
| **Hour 17** | 124 | **37.9%** | -0.390% | London fix / chop |
| **Hours 01–04, 12, 14–15** | 1,044 | **50.3% – 56.2%** | Positive/Flat | Highest expectancy periods |

#### **Statistical Evaluation & Precaution:**
- **Overfitting Alert:** While hours 13, 17, 20, and 22 display poor raw historical metrics, previous forward tests confirmed that **hard binary TOD exclusion filters severely degraded out-of-sample performance** by missing major trend-reversal entries.
- **Proposed Filter:** **REJECT hard binary hour blocks.** If temporal risk control is desired, use **soft sizing modulation only** (e.g., reduce position risk multiplier to 0.7x during hours 20:00–22:59 UTC) rather than completely disallowing entries.

---

### 4. Day-of-Week (DOW) Analysis

| Day of Week | Trades | Win Rate | Average PnL |
| :--- | :---: | :---: | :---: |
| **Sunday (0)** | 455 | 45.5% | -0.006% |
| **Monday (1)** | 823 | 45.3% | -0.258% |
| **Tuesday (2)** | 323 | 45.2% | -0.324% |
| **Wednesday (3)** | 497 | 44.3% | -0.361% |
| **Thursday (4 / Fri UTC)** | 434 | **55.3%** | **+0.305%** |
| **Friday (5 / Sat UTC)** | 259 | 46.7% | +0.087% |
| **Saturday (6 / Sun UTC)** | 344 | 46.5% | -0.097% |

#### **Findings & Recommendation:**
- Mid-week days (Tue–Thu) hover consistently around 44.3%–45.3% win rates with small negative averages, while Fridays outperform at 55.3%.
- **Proposed Filter:** **REJECT Day-of-Week entry restrictions.** DOW anomalies in crypto show high regime drift; previous validation runs proved DOW filters overfit historical sampling and fail forward testing.

---

### Summary of Proposed Filter Rules

1. **Active Pair Exclusions (Immediate Win Rate & PnL Boost):**
   - Blacklist: `PEPEUSDT`, `DOGEUSDT`, `PENDLEUSDT`, `AVAXUSDT`, `POLYXUSDT`.
   - Structural risk exclusion: `SOLUSDT` (due to asymmetric tail loss ratio).
   - Maintain fundamental blacklists: `LSKUSDT`, `SAGAUSDT`, `KDAUSDT`.
2. **Hold Time Policy:**
   - **No maximum hold time cap.** Preserve 12h–36h holds where win rate peaks (57%–59%).
3. **Temporal Policy (TOD / DOW):**
   - **No hard binary exclusions** for hours or days of week (avoids known out-of-sample forward testing degradation).
   - Optional: Soft risk dampener (0.7x size) during the low-liquidity US-close window (20:00–22:59 UTC).
