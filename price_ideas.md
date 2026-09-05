**Market Data Analysis:**
* **Volatility vs. Squeeze Correlation:** Assets with lower hourly volatility and daily ranges (BTC, ETH) exhibit significantly more Bollinger Band (BB) squeezes (541 and 471, respectively) than high-volatility assets like NEAR (115). This indicates BTC and ETH spend more time in consolidation, while NEAR/LINK are in persistent trending or volatile states.
* **Strong Directional Bias:** All assets show strong 30-day upward trends (23% to 43%), meaning counter-trend strategies will likely underperform and long-biased trend-following or breakout strategies will excel.

**Proposed Signals & Filters:**

**1. Squeeze-Breakout Entry Signal (Targeting BTC/ETH)**
Capitalizes on the frequent consolidation periods observed in the major cap assets.
* **Logic:** Enter LONG when the price closes above the Upper Bollinger Band following a period of compression.
* **Indicators:** Bollinger Bands (20, 2), Bollinger Band Width (BBW).
* **Condition:** `Close > Upper BB(20, 2)` AND `BBW < SMA(BBW, 20)`.

**2. Volatility-Adjusted Trailing Stop Exit (Targeting SOL/LINK/NEAR)**
Addresses the high daily ranges (21%-32%) and strong trends (28%-43%) to avoid premature exits during high-volatility pullbacks.
* **Logic:** Use an Average True Range (ATR) trailing stop that widens during strong trends and tightens in chop.
* **Indicators:** Average True Range (ATR, 14), Average Directional Index (ADX, 14).
* **Condition:** 
  * If `ADX(14) > 25` (Strong Trend): Trail stop at `Highest High (20) - (3 * ATR(14))`
  * If `ADX(14) <= 25` (Weak Trend): Trail stop at `Highest High (20) - (1.5 * ATR(14))`
