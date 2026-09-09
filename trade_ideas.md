Based on the provided statistical data and prior forward-testing learnings, here are the proposed filter recommendations to improve the overall win rate and expectancy:

### 1. Pair Exclusions (Statistically Significant Drag)
The following pairs have large sample sizes (>50 trades) with highly negative total PnL and poor expectancy. They should be added to the exclusion list/blacklist:
*   **DOGEUSDT**: 98 trades, 37.8% win rate, Total PnL: -56.24
*   **AVAXUSDT**: 116 trades, 45.7% win rate, Total PnL: -51.95
*   **PEPEUSDT**: 88 trades, 22.7% win rate, Total PnL: -42.69
*   **FETUSDT**: 191 trades, 44.5% win rate, Total PnL: -40.40
*   **PENDLEUSDT**: 59 trades, 33.9% win rate, Total PnL: -40.35
*   **NEARUSDT**: 250 trades, 51.6% win rate, Total PnL: -40.68 *(Despite >50% WR, poor risk/reward creates massive drag)*

### 2. Time-of-Day & Day-of-Week Filters (Recommendation: DO NOT APPLY)
While specific hours (13, 17, 20, 22) show heavy losses, **do not implement time or day filters**. The `PREVIOUS LEARNINGS` explicitly state that applying DOW/Hour filters caused severe overfitting and degraded out-of-sample forward testing performance. 

### 3. Hold Time Dynamics (Avoid Premature Exits)
*   **0 - 6 Hours:** Represents the vast majority of losses and low win rates (43.8% - 48.3% WR, negative avg PnL).
*   **6+ Hours:** Profitability and win rates jump significantly (54.3% - 59.6% WR, positive avg PnL).
*   **Filter Action:** Do not apply a maximum hold-time cap (as 72h caps were previously rejected). Instead, ensure that your stop-loss and trailing mechanisms are loose enough during the first 6 hours to prevent premature stop-outs. Allow trades the necessary time to mature into the profitable >6h buckets.
