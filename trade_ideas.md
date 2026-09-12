Based on the provided trade data and previous learnings, here are the statistically significant filters proposed to improve win rate:

**1. Pair Exclusions (High Priority)**
Exclude assets that demonstrate both exceptionally low win rates (< 40%) and significant total PnL drag:
*   **PEPEUSDT**: 22.7% win rate | -42.69 USDT Total PnL
*   **PENDLEUSDT**: 33.9% win rate | -40.35 USDT Total PnL
*   **DOGEUSDT**: 37.8% win rate | -56.24 USDT Total PnL
*   **Structurally Unprofitable/Low Win-Rate Pairs (<30%)**: ENSUSDT (0%), VETUSDT (16.7%), PEOPLEUSDT (16.7%), HFTUSDT (16.7%), ONGUSDT (20%), DEXEUSDT (25%), SYNUSDT (25%), HEIUSDT (27.3%), COTIUSDT (28.6%).

**2. Time-of-Day Filters (Use with Caution)**
*Previous learnings indicate broad time filters cause overfitting, but the following specific hours severely underperform:*
*   **Hour 13**: 35.3% win rate | -0.465 Avg PnL
*   **Hour 17**: 37.8% win rate | -0.547 Avg PnL
*   **Hour 20**: 33.7% win rate | -0.340 Avg PnL
*   **Hour 22**: 26.9% win rate | -0.750 Avg PnL
*Recommendation*: Consider a filter excluding new entries exclusively during hours 13, 17, 20, and 22. 

**3. Hold Time Adjustments**
*   **0-2h Hold Time**: 43.7% win rate | -0.231 Avg PnL
*   **12-24h Hold Time**: 59.4% win rate | +0.509 Avg PnL
*Recommendation*: Trades exiting within 0-2 hours are the least profitable. Given previous learnings rejecting hard stop-loss caps, avoid overly aggressive early exit criteria. Allow trades breathing room to develop into the more profitable 6h+ hold buckets.

**4. Day-of-Week Filters**
*Recommendation*: **Reject all Day-of-Week filters**. Days 0, 1, 2, 3, 5, and 6 perform similarly (44-47% win rate), and Day 4 is an outlier (55.2%). Filtering these risks severe overfitting, aligning with previous forward-testing observations.
