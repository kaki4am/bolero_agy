### Analysis of Market Data Characteristics

1. **High Variance in Volatility:** Hourly volatility varies drastically across the basket (0.42% for BTC up to 1.00% for NEAR). This explains why your previous attempt at a fixed 3.0% hard stop-loss failed; fixed percentages cause premature liquidations on high-volatility assets during routine fluctuations.
2. **Strong Directional Trends:** The 30-day trend percentages are extremely strong across the board (24% to 51%). The market is in a clear expansion phase, meaning mean-reversion strategies or tight trailing stops (like the rejected ADX stop) will likely underperform due to trend momentum.
3. **Squeeze Discrepancy:** Major caps (BTC, ETH) exhibit a high frequency of Bollinger Band squeezes (450+), indicating periods of consolidation. Smaller caps (NEAR, LINK) have very few squeezes, indicating sustained trending action.

### Proposed Signals & Filters

**1. ATR-Based Dynamic Stop-Loss (Replaces Hard % Stop)**
*   **Logic:** Since routine volatility triggers fixed stop-losses, adapt the stop distance to the asset's specific volatility using Average True Range (ATR). 
*   **Parameters:** `Stop Loss = Entry Price - (3.0 * 14-period ATR)`. 
*   **Why it improves the strategy:** It gives volatile assets like NEAR a wider buffer to breathe during pullbacks, while keeping a tighter leash on lower-volatility assets like BTC, directly solving the premature liquidation issue.

**2. Volume-Confirmed BB Squeeze Breakout (Entry Filter)**
*   **Logic:** Because BTC and ETH show hundreds of squeezes, many are likely false breakouts (whipsaws). Add a volume multiplier requirement to confirm the breakout of a squeeze.
*   **Parameters:** `Condition: Squeeze Breakout AND (Current Volume > 1.5 * 20-period SMA of Volume)`.
*   **Why it improves the strategy:** Filters out low-momentum, low-liquidity fakeouts in BTC and ETH, ensuring entries are only taken when institutional/heavy volume steps in to drive the trend.
