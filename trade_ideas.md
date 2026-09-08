### Proposed Filters for Win Rate Improvement

**1. Pair Exclusions (Strongest Recommendation)**
Blacklist the following pairs that are statistically dragging down the overall win rate and profitability:
* **Massive PnL Bleeders:** `SOLUSDT`, `DOGEUSDT`, `AVAXUSDT`, `PEPEUSDT`, `NEARUSDT`, `PENDLEUSDT`, `FETUSDT`.
* **Chronically Low Win-Rate (<30%):** `ENSUSDT` (0%), `HFTUSDT` (16.7%), `PEOPLEUSDT` (16.7%), `ONGUSDT` (20%), `PEPEUSDT` (22.7%), `SYNUSDT` (25%), `DEXEUSDT` (25%), `HEIUSDT` (27.3%), `COTIUSDT` (28.6%).

**2. Time-of-Day (TOD) & Day-of-Week (DOW) Filters**
* **Recommendation: NONE.** Per previous learnings, applying TOD and DOW filters strictly causes overfitting and severely degrades out-of-sample forward testing performance. These should be avoided entirely.

**3. Hold Time Limits**
* **Recommendation: NONE.** Previous backtesting already rejected hard hold limits (like 72h). Furthermore, the current data shows that trades held for longer durations (12-24h and 24h+) have the highest win rates (~60%) and the best average PnL. The vast majority of losses occur in the 0-2h bucket, indicating premature stop-outs, meaning capping hold times would prematurely cut winners rather than save losers.
