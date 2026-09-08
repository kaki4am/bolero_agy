### Market Data Analysis
1. **Volatility vs. Consolidation:** There is a clear inverse relationship between asset market cap and both hourly volatility and 30-day trend percentages. High-cap assets (BTC, ETH) exhibit extremely high Bollinger Band squeeze counts (539 and 465, respectively), indicating prolonged consolidation periods. Low-cap assets (NEAR, LINK) show significantly higher volatility and trend momentum with very few squeezes.
2. **Decoupling Altcoins:** Recent learnings strongly emphasize that during periods of mild BTC consolidation or slight retracement (-1% to -3%), high-volume altcoins decouple and present major momentum opportunities driven by localized sentiment and fundamentals. 
3. **Failed Previous Attempts:** Relying on strict rigid filters (time-of-day, hard -3.0% stops, tight ADX trailing stops, 3.0*ATR stops) uniformly fails by causing premature exits during normal market noise. 

### Proposed New Signals / Filters

**1. BTC-Conditioned Altcoin Volume Breakout (Entry Filter)**
*   **Rationale:** Capitalizes on the observed altcoin decoupling during macro "wait-and-see" periods without applying rigid overarching stop-losses.
*   **Logic:** Allow aggressive altcoin entries only if BTC is in a mild consolidation or slight dip phase, confirming that the altcoin's move is a localized rotation rather than a macro pump.
*   **Proposed Parameters:** 
    *   `btc_24h_return` is between `-3.0%` and `+1.0%`.
    *   `altcoin_1h_volume` > `1.5 * altcoin_avg_volume_usd` (to confirm decoupling momentum).
    *   `altcoin_price` > `SMA(20)` (to ensure it's in an uptrend).

**2. Asset-Specific Bollinger Band Squeeze Breakout (Entry Signal)**
*   **Rationale:** BTC and ETH spend massive amounts of time in consolidation (BB Squeeze counts > 450). Instead of standard trend-following which may chop during these periods, wait for the squeeze to definitively break on high volume.
*   **Logic:** Trigger entries on high-cap assets when a prolonged squeeze resolves upward.
*   **Proposed Parameters:**
    *   Target Assets: `BTCUSDT`, `ETHUSDT` (or any asset with `bb_squeeze_count_30d > 400`).
    *   Condition: `BB_Width < 30-period average BB_Width` (identifies the squeeze).
    *   Trigger: Hourly candle closes above the `Upper Bollinger Band` AND `Hourly Volume > 1.5 * 24h_Avg_Hourly_Volume`.
