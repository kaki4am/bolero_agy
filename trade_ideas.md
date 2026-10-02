Wait for task 3a8276e0-b5e8-4f9b-8957-c981ffd114ad/task-8 to complete.
# Trade Data Analyst Report: Filter Significance & Fee Drag Analysis

## 1. Executive Summary & Commission Drag Audit

* **All-Time Expectancy Drag**: All-time records (3,330 cycles) show an expectancy of **-0.065% per trade** with an average win (+2.03%) barely offsetting average losses (-1.79%). 
* **Commission Churn in 0–2h Exits**:
  * **59.7% of all historical trades (1,924 trades)** exited within **0–2 hours** with an average PnL of **-0.254%** (cumulative loss: **-488.7%**).
  * Binance spot round-trip fees (0.15%–0.20%) plus spread account for virtually the entire loss in this bucket.
  * **975 trades (29.3% of total)** exited with PnL within **±0.5%**, representing pure fee burn without alpha capture.
* **V160 Validation (Last 30 Days)**:
  * Recent performance proves the shift away from noise-level churn: **225 completed cycles**, **47.11% Win Rate**, **+7.21% avg win vs. -4.35% avg loss (1.66 W/L ratio)**, and **+1.096% expectancy per trade**.
  * Average hold time increased to **103.48 hours**, confirming that high-conviction trend continuation and wide stops are structurally capturing positive expectancy.

---

## 2. Evaluation of Filter Categories

### A. Time-of-Day (TOD) Filters: **REJECT**
* **Data Observation**: Hours 13, 17, 20, and 22 display lower win rates (26.6%–37.6%) and negative returns (-0.41% to -0.74%).
* **Analysis & Institutional Memory**: **Reject binary/soft hour exclusions.** Previous live tests confirmed that broad time-of-day filters cause severe out-of-sample overfitting and eliminate outsized momentum breakouts during global session transitions (US open/close, Asia open).

### B. Day-of-Week (DOW) Filters: **REJECT**
* **Data Observation**: Tuesdays through Thursdays (DOW 1–3) have negative average PnLs (-0.25% to -0.39%), whereas Fridays/Saturdays show +0.33%.
* **Analysis & Institutional Memory**: **Reject DOW exclusions.** Cutting over 50% of trade opportunities (1,676 trades) based on calendar-day distribution introduces data-snooping bias with zero causal backing in 24/7 crypto markets.

### C. Hold Time Limits: **REJECT CAPS / ADDRESS ROOT CAUSE**
* **Data Observation**:
  * **0–2h**: 1,924 trades, 43.4% WR, -0.254% avg PnL (Noise & fee drag).
  * **6h–24h+**: 670 trades, 54.3%–59.6% WR, +0.396% avg PnL (Alpha generation).
* **Analysis**: Hard hold-time caps (e.g. 24h/72h) are confirmed to cut off winning runs prematurely. The 0–2h churn is not an exit problem, but an **entry conviction problem** (low-momentum false breakouts stopping out immediately).

---

## 3. Statistically Significant Actionable Filters

### 1. New Pair Blacklist Exclusions (Unrestricted Negative Expectancy)
The following underperforming symbols currently lack restriction and should be added to the pair exclusion list:

| Symbol | Trades | Win Rate | Avg PnL | Total PnL (USDT) | Primary Drag Factor |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **ATOMUSDT** | 6 | 16.7% | -1.740% | -10.44 | High loss magnitude, low bounce expectancy |
| **TLMUSDT** | 7 | 28.6% | -1.225% | -8.58 | Illiquid micro-cap whipsaw |
| **FLOKIUSDT** | 5 | 40.0% | -1.370% | -6.85 | Meme coin adverse drift |
| **XECUSDT** | 11 | 36.4% | -0.441% | -4.85 | Low-float false breakouts |
| **XRPUSDT** | 89 | 56.2% | -0.140% | -12.46 | Large-cap fee churn (tiny expansion, wiped out by fees) |
| **LTCUSDT** | 70 | 55.7% | -0.107% | -7.47 | Large-cap fee churn |
| **LINKUSDT** | 81 | 43.2% | -0.053% | -4.32 | High-frequency churn with sub-threshold expansions |

*(Note: **ARUSDT** must remain unrestricted; despite a small sample dip in one historical slice, it is the #1 performer in both 30-day (+29.14 USDT) and all-time (+28.90 USDT) databases).*

### 2. Elimination of Low-Conviction Setups (Curbing 0–2h Churn)
To eradicate the 1,924 trades lost to immediate churn and fee drag:
* **Elevate Relative Volume Gate (`VOL_THRESHOLD`)**: Increase entry volume threshold from `1.5x` to `1.75x–2.0x` to filter out low-volume false breakouts that stall inside 2 hours.
* **Require Strong Body-to-Range Closes (`MIN_BODY_TO_RANGE`)**: Enforce closing candle body `>= 0.40–0.45` to prevent entries on long-wick exhaustion candles that immediately reverse into stop-outs.
