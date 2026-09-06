Based on the provided trade data and previous learnings, here are the proposed statistically significant filters to improve win rate and profitability:

**1. Pair Exclusions (Bottom Performers)**
*   **Action:** Blacklist `PEPEUSDT`, `DOGEUSDT`, `PENDLEUSDT`, `ENSUSDT`, and `PEOPLEUSDT`.
*   **Rationale:** These pairs have exceptionally low win rates (ranging from 0% to 37.8%) and contribute massively to total historical losses.

**2. Hold Time Limits (Let Winners Run)**
*   **Action:** Increase minimum hold time for standard take-profit triggers to at least 6 hours (unless a catastrophic stop-loss is hit).
*   **Rationale:** The 0-6 hour hold buckets account for the vast majority of volume but have negative average PnL. The "sweet spot" for profitability and win rate (54.6% - 60.9%) requires holding trades for 6 to 24 hours.

**3. Day-of-Week (DOW) Adjustments**
*   **Action:** Reduce position sizing or tighten entry requirements on **Days 1, 2, and 3**. 
*   **Rationale:** These days have the lowest win rates (44.1% - 46.0%) and highly negative average PnLs. Conversely, Day 4 is highly profitable (55.4% WR, +0.218 PnL).

**4. Time-of-Day (Hour) Filters**
*   **Action:** Pause new trade entries during **Hour 7** and **Hour 10**.
*   **Rationale:** Even keeping previous learnings in mind (which rejected filtering hours 13, 17, 20, 22), hours 7 and 10 show consistently poor metrics (41.5% and 40.8% win rates respectively, with significant negative average PnL) and should be avoided.
