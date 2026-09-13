Based on the statistical data and strict adherence to the previous system learnings, here are the proposed filters:

**1. Time-of-Day & Day-of-Week Filters: NONE**
*   **Data shows:** Hours 13, 17, 20, 22 and Days 1, 3 have the lowest win rates.
*   **Recommendation:** **DO NOT APPLY.** Previous strategy learnings explicitly reject TOD/DOW filters, proving they cause severe out-of-sample overfitting, fail to adapt to shifting regimes, and inadvertently block highly profitable breakouts. 

**2. Hold Time Limits: 24-HOUR HARD EXIT**
*   **Data shows:** Trades held in the `24h+` bucket have a high win rate (57.8%) but a **negative average PnL (-0.146)**. 
*   **Recommendation:** Implement a 24-hour maximum hold time limit. The data indicates that trades failing to resolve within 24 hours turn into heavy "bleeders" where outsized losses erase smaller, long-duration wins. 

**3. Pair Exclusions (Blacklist): PEPE, DOGE, PENDLE, LUNC, VET**
*   **Data shows:** These pairs have statistically significant sample sizes with atrocious win rates and severe negative expectancy.
*   **Recommendation:** Blacklist the following pairs to immediately boost aggregate win rate and preserve capital:
    *   **PEPEUSDT:** 22.7% Win Rate (88 trades, -42.69 PnL)
    *   **DOGEUSDT:** 37.8% Win Rate (98 trades, -56.24 PnL)
    *   **PENDLEUSDT:** 33.9% Win Rate (59 trades, -40.35 PnL)
    *   **LUNCUSDT:** 40.7% Win Rate (59 trades, -24.36 PnL)
    *   **VETUSDT:** 16.7% Win Rate (Worst 30-day performer, -13.88 PnL)
    *   *(Note: SOLUSDT has the worst all-time PnL, but is intentionally omitted from this blacklist because recent AI Manager logs explicitly target SOL as a key decoupled momentum asset for the current market regime).*
