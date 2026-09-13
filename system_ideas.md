Based on the system health, logs, and recent performance, here are the proposed structural and risk management changes:

**1. Tactical Risk Reduction (Position Sizing)**
* **Observation:** The BTC 15m trend is currently DOWN, and the strategy has suffered 5 significant recent losses (-3.6% to -4.7%) resulting in a negative 24h PnL (-$23.06).
* **Proposal:** Temporarily reduce the `Risk Mult` from `1.0` to `0.5 - 0.7`. Maintain wider stop-losses (avoiding the previously rejected -3.0% hard cap) but reduce position sizing to defend equity during this short-term downward volatility.

**2. Portfolio Guards (Consecutive Loss Cooldown)**
* **Observation:** Recent losses occurred extremely rapidly (e.g., MTLUSDT stopped out in 3m 30s, PUNDIXUSDT in 11m 53s, ARPAUSDT in 14m 2s). 
* **Proposal:** Implement a system-level cooldown (e.g., 1-2 hours) on new entries after 3 consecutive stop-outs to prevent rapid "chop" and capital bleed during sudden market structural shifts.

**3. Structural Entry Filters (Timeframe Alignment)**
* **Observation:** The only highly successful recent trade (PROMUSDT, +3.85%) had an 83-hour hold time, while rapid momentum entries are failing quickly.
* **Proposal:** When the BTC 15m trend is DOWN, require higher-timeframe confirmation (e.g., 1H or 4H trend alignment) for altcoin entries to prevent buying into fake-out momentum spikes.

**4. Take Profit / Trailing Adjustments**
* **Observation:** The system successfully logged a Take Profit on MTLUSDT recently, indicating TP mechanisms are working when targets are reached.
* **Proposal:** Keep TP and trailing stop logic as-is, focusing risk management entirely on the entry criteria and initial position sizing reductions.
