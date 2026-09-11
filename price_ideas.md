### Market Data & Sentiment Analysis
1. **Prolonged Macro Consolidation**: High Bollinger Band (BB) squeeze counts in major caps (BTC: 547, ETH: 476) perfectly align with the observed "wait-and-see" retail sentiment and flat BTC conditions.
2. **High-Beta Alpha Exists**: Altcoins like NEAR and LINK show massive 30-day trends (44% and 31%) and high daily ranges, confirming that capital is aggressively rotating into decoupled assets despite BTC's chop. 
3. **Avoid Over-Restriction**: Previous failures (time/day filters, tight trailing stops, rigid ATRs) prove the strategy needs room to breathe to capture massive decoupled moves without being prematurely stopped out by routine volatility.

### Proposed Signals/Filters

**1. Decoupled Relative Strength (DRS) Volume Filter (Entry Filter)**
*   **Concept**: Mechanically identify the "decoupled, high-volume altcoin breakouts" highlighted in the AI manager logs, specifically during BTC retracements (-1% to -3%).
*   **Indicators**: 4-hour Relative Return vs BTC, and 1-hour Volume Moving Average (VMA).
*   **Parameters**:
    *   `Altcoin_4h_Return > (BTC_4h_Return + 2.5%)` 
    *   `Current_1h_Volume > 2.5 * SMA(1h_Volume, 24)`
*   **Logic**: Only authorize aggressive altcoin long entries during BTC weakness if the asset proves it is completely ignoring macro gravity via a strict volume anomaly and significant price outperformance.

**2. Volatility Expansion Squeeze Breakout (Entry Signal)**
*   **Concept**: Capitalize on the high BB squeeze counts by catching the exact moment retail capital rotates into an asset, triggering a momentum explosion.
*   **Indicators**: Bollinger Bandwidth (BBB) (Length 20, Multiplier 2) + RSI (14).
*   **Parameters**:
    *   `BB_Bandwidth > 1.5 * Min(BB_Bandwidth, 24)` (Bandwidth expands by 50% from its 24-hour low).
    *   `RSI(14) > 65` (Confirming strong upward momentum).
*   **Logic**: Triggers an entry exactly when a prolonged consolidation (squeeze) breaks upward with strong retail momentum, capturing the narrative-driven runs before they hit peak saturation.
