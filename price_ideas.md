**MARKET ANALYSIS**
The data reveals a stark divergence between high-liquidity majors (BTC/ETH) and mid-cap altcoins (LINK/NEAR). BTC and ETH show prolonged consolidation (high BB squeeze counts: 542/471, lower 30d trends: ~21-30%), while altcoins exhibit massive momentum and volatility (LINK/NEAR 30d trends: 44-52%, hourly volatility: 0.8-1.1). Recent sentiment data repeatedly validates capturing "decoupled, high-volume altcoin breakouts" while BTC flatlines or dips mildly (< 1%). 

**PROPOSED FILTERS/SIGNALS**

**1. Relative Strength Decoupling Filter (Entry Filter)**
*   **Logic:** Since the most profitable strategy right now is targeting altcoins that ignore macro BTC weakness, we should explicitly filter for structural decoupling before entry. 
*   **Indicators & Parameters:** 
    *   `Altcoin 24h Return % > (BTC 24h Return % + 2.5%)`
    *   `Altcoin 24h Volume > SMA(Altcoin 24h Volume, 7)`
    *   *Purpose:* Ensures capital is only deployed into altcoins actively demonstrating relative strength and institutional/retail rotation, avoiding stagnant assets.

**2. Volume-Anomaly Squeeze Breakout (Entry Signal)**
*   **Logic:** Given the high number of BB squeezes across the board and the retail "wait-and-see" fatigue, many breakouts will be false or lack follow-through unless backed by immediate, localized capital rotation.
*   **Indicators & Parameters:**
    *   `Current Hourly Volume > 1.5 * SMA(Hourly Volume, 24)` 
    *   Must occur concurrently with a **Bollinger Band Squeeze Exit** (e.g., price closing outside the upper Bollinger Band while Bands are expanding).
    *   *Purpose:* Filters out low-conviction fake-outs during flat BTC consolidation, ensuring we only enter momentum trades when significant volume confirms the move.
