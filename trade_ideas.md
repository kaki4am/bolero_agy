Based on the provided trade data analysis, here are the proposed statistically significant filters to improve win rate:

**1. Pair Exclusions (High Volume, Low Win Rate, High Losses)**
*   **PEPEUSDT:** 22.7% WR, -42.69 PnL (88 trades)
*   **DOGEUSDT:** 37.8% WR, -56.24 PnL (98 trades)
*   **PENDLEUSDT:** 33.9% WR, -40.35 PnL (59 trades)
*   **HEIUSDT:** 27.3% WR, -6.5 PnL (Worst performer in last 30 days)
*   **Micro-cap/Low-volume exclusions:** ENSUSDT (0% WR), HFTUSDT (16.7% WR), PEOPLEUSDT (16.7% WR), ONGUSDT (20% WR).

**2. Hold Time Filters**
*   **Avoid Early Exits (0-6 hours):** Trades closed under 6 hours have the lowest win rates (43.9% - 48.1%) and negative average PnL. 
*   **Optimal Window:** Win rates peak significantly between 6-24 hours (54.3% - 60.9% WR). Consider implementing a minimum hold time or loosening take-profit/stop-loss parameters in the first 6 hours to let trades develop.

**3. Day-of-Week (DOW) Filters**
*   *Note: DOW filters were previously rejected for forward-testing degradation, but purely statistically:*
*   **Exclude DOW 2 (Tuesday) & DOW 3 (Wednesday):** These are the worst performing days (44.1% and 44.4% WR, both averaging < -0.3 PnL). 
*   **Focus on DOW 4 (Thursday):** Strongest performer by far (55.4% WR, +0.218 avg PnL).

**4. Time-of-Day Filters**
*   *Note: Hours 13, 17, 20, 22 were previously rejected for excluding profitable trades.*
*   **Exclude Hour 7 & Hour 10:** Outside of the rejected hours, Hour 7 (41.5% WR, -0.449 PnL) and Hour 10 (40.8% WR, -0.257 PnL) drag down the win rate the most.
