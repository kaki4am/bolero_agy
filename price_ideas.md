### Market Data Analysis
- **Trend & Volatility Correlation**: All pairs exhibit strong positive 30-day trends (7.8% - 35.9%). Volatility and average daily ranges scale inversely with market cap (BTC is lowest at 11.9% daily range / 0.4% hourly vol; NEAR is highest at 30.6% daily range / 0.89% hourly vol).
- **Compression & Breakout Potential**: Bollinger Band squeeze counts are exceptionally high on larger caps (BTC: 566, ETH: 492) and lower on higher-volatility altcoins (NEAR: 155). This indicates structural consolidation in majors, ripe for explosive momentum, while altcoins are already experiencing expanded volatility.

### Proposed Dynamic Signals & Filters (Adhering to Anti-Curve-Fitting Constraints)

**1. Dynamic Volatility-Scaled Breakout (Entry Filter)**
*   **Rationale**: High BB squeeze counts suggest breakout strategies are viable, but static thresholds fail across different volatility profiles. We must use a dynamic threshold to validate momentum relative to the asset's own baseline.
*   **Indicators**: Bollinger Band Width (BBW) and a Simple Moving Average (SMA) of the BBW.
*   **Logic**: Only permit breakout entries when the current volatility exceeds its recent historical average. 
    *   `Entry Condition`: `Current BBW > (1.5 * SMA(BBW, 50))`
    *   *Effect*: Automatically adapts to each pair's inherent volatility without requiring static pair exclusions or hardcoded percentage thresholds.

**2. ATR-Normalized Dynamic Trailing Stop (Exit Signal)**
*   **Rationale**: A fixed percentage stop-loss will prematurely stop out highly volatile pairs (like NEAR) while taking too long to cut losses on stable pairs (like BTC).
*   **Indicators**: Average True Range (ATR) over a 14-period window.
*   **Logic**: Implement a trailing stop calculated as a multiple of the ATR, dynamically widening for volatile assets and tightening for stable ones.
    *   `Long Exit Condition`: `Price < (Highest High since Entry - (Multiplier * ATR(14)))`
    *   `Multiplier`: `3.0` (Standard baseline, dynamically scales since ATR inherently expands on pairs with higher `avg_daily_range_pct`).
    *   *Effect*: Allows high-volatility trends (like SOL and LINK) room to breathe while securely locking in profits on lower-volatility majors, avoiding the need to overfit exits per pair.
