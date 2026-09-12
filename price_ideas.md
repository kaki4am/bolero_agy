### Market Data Analysis
* **Volatility & Range:** Altcoins like NEAR (40.6% daily range) and LINK (27.7%) show explosive momentum and high volatility compared to BTC (13.1%). 
* **Squeeze Dynamics:** Majors (BTC, ETH, SOL) exhibit high Bollinger Band squeeze counts, indicating prolonged consolidations that align with the Reddit sentiment of macro "wait-and-see" periods.
* **Volume Profiling:** Capital rotation into low-volume/high-range assets during flat BTC conditions dictates that volume surges are the primary indicator of decoupling.
* **Previous Learnings Constraint:** Strict stop-losses (like the -3% cap or ATR-based dynamic stops) and time-based filters cause premature exits and overfitting. Defense must be achieved through asset selection rather than tight trade restrictions.

### Proposed Logic (Signals & Filters)

**1. Relative Volume (RVOL) Decoupling Filter (Entry)**
* **Logic:** Ensure entries into altcoins only occur when genuine capital rotation is confirmed by a volume surge, specifically during BTC consolidation or mild dips (-3% to +1%).
* **Indicators & Parameters:**
  * **BTC Condition:** BTC 4h Rate of Change (ROC) is between `-3.0%` and `+1.0%`.
  * **Altcoin Momentum:** Altcoin 4h ROC `> 3.0%`.
  * **Volume Confirmation:** Altcoin RVOL `> 2.0` (current volume is > 200% of its 24-period or 50-period Simple Moving Average of volume).

**2. Profit-Activated Trailing Stop (Exit)**
* **Logic:** Hard stops at -3% and continuous ATR trailing stops cause premature liquidations in highly volatile assets like NEAR and LINK. To survive routine chop but capture massive upside, keep the initial stop wide and only activate a trailing stop once a strong profit cushion is established.
* **Indicators & Parameters:**
  * **Initial Stop-Loss:** `-5.0%` to `-7.0%` (avoids the rejected -3% cap).
  * **Activation Threshold:** Trailing stop logic remains inactive until unrealized profit reaches `+8.0%` to `+10.0%`.
  * **Trailing Distance:** Once activated, trail the price by `-3.0%` to `-4.0%` from the peak to lock in momentum gains without choking the trade early.
