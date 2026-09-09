Based on the provided health, performance, and log data, here are the proposed structural and risk management changes:

**1. Implement Time-Decaying Take-Profit (Capital Velocity Guard)**
*   **Observation:** Fast trades (e.g., ATOMUSDT: +5.8% in 3.5h, CAKEUSDT: +3.6% in 2.7h) are highly efficient. Conversely, assets like BICOUSDT (+4.2% in 221h), ETHUSDT (337h), and ETCUSDT (328h) tie up capital for weeks with minimal or negative returns.
*   **Proposal:** Since hard 72h hold limits were previously rejected, implement a *soft* time-based capital reallocation. Gradually lower the Take-Profit target threshold as hold duration increases beyond 48 hours to accelerate capital recycling into high-momentum targets like CREAM and ZEC. 

**2. Dynamic Drawdown Floor (Tail-Risk Stop Loss)**
*   **Observation:** While a hard -3.0% SL cap was rejected for causing premature exits, the RENDERUSDT trade resulted in a -7.01% loss over 41 hours. 
*   **Proposal:** Establish an absolute portfolio-level structural floor (e.g., -6.0% to -8.0%) specifically for extended-duration trades. This acts as a disaster guard for slow-bleeding assets without interfering with normal volatility during fast breakouts.

**3. Portfolio Guard: Stale Trend Exposure**
*   **Observation:** The 15m BTC trend is DOWN, yet baseline risk is maintained to catch altcoin decoupling (which is working well overall with ~29.3% train scores).
*   **Proposal:** Introduce a "Stale Asset" guard. If an asset is held for > 72 hours and its 15m/1h momentum turns negatively correlated with the targeted decoupled altcoin index, trigger an early exit. This frees up margin for the highly active 46-pair whitelist currently being tracked.
