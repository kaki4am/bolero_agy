### Analysis of Market Data & Previous Learnings

1.  **Strong Trend & High Volatility**: The 30-day trends are powerfully bullish across the board (22% for BTC up to 57% for LINK), with massive average daily ranges (up to 34% for NEAR). 
2.  **Tight Stops Are Detrimental**: The rejection of multiple restrictive stop-loss mechanisms (ADX trailing, 3.0% hard cap, 3x ATR) clearly indicates that the natural volatility of these assets routinely triggers tight stops before the broader upward trend can resolve. We must give trades room to breathe.
3.  **Bollinger Band Squeeze Imbalance**: BTC and ETH are experiencing high consolidation phases (465-539 squeezes), while altcoins (LINK, NEAR) are trending continuously with fewer squeezes but extreme hourly volatility.

### Proposed New Signals / Filters

Instead of restricting downside risk, we should optimize entry timing and capitalize on momentum.

**1. Trend-Aligned Pullback Filter (Entry Filter)**
*   **Logic**: Since we are in a massive uptrend and tight stops fail, we should improve our entry price by buying deep pullbacks rather than chasing breakouts, giving the trade a safer margin of error.
*   **Parameters**: Require the 1-Hour RSI (Length: 14) to drop below 35 (oversold) and cross back *above* 40, conditionally requiring the price to still be trading above the 200-period EMA to confirm the macro trend is intact.

**2. Volume-Confirmed BB Squeeze Breakout (Entry Signal for BTC/ETH)**
*   **Logic**: Capitalize on the high BB Squeeze frequency in the major caps (BTC/ETH). To filter out false breakouts common in high-volatility regimes, we mandate a volume surge concurrent with the squeeze resolution.
*   **Parameters**: Trigger a long entry when Price closes above the Upper Bollinger Band (Length: 20, StdDev: 2.0) **AND** the current candle's Volume is > 1.5x the 20-period Volume SMA.
