Based on the system health, logs, and performance data, here are the structural and risk management proposals:

**1. Critical System Fixes**
*   **Fix Config Reloader Crash:** The `trading-bot` logs show a recurring `UnboundLocalError` for `asyncio` in `bot.py` (`config_reloader_loop`). The `asyncio` module is not properly imported in that scope. This must be fixed to ensure the bot can dynamically reload configurations without background task failures.
*   **Blacklist Restricted Symbols:** Immediately add `CFGUSDT` and `IOUSDT` to the global blacklist. Both are throwing `apierror(code=-2010): this symbol is not permitted for this account`, causing wasted API calls and failed trade execution.

**2. Risk Management & Portfolio Guards**
*   **Maintain Defensive Baseline (BTC Trend: DOWN):** Keep current tactical overrides (`Risk Mult=0.8`, `SL Offset=-0.1`). Previous learnings confirm that a 0.5 risk exposure during downtrends performs better than 0.2, allowing the bot to catch sudden reversals without over-exposing capital.
*   **Avoid Over-Tightening Stops:** Do not implement hard stop-loss caps (e.g., -3.0%) or volatility-adjusted ADX trailing stops, as backtests and previous learnings show these cause premature exits during routine volatility and degrade performance.
*   **Target Decoupled Alpha:** As retail sentiment remains in a cautious "wait-and-see" accumulation phase, continue aggressively force-tracking and whitelisting decoupled, news-driven altcoins (e.g., `ZECUSDT`, `CREAMUSDT`). These assets are proving to generate localized momentum independent of the broader BTC consolidation. 

**3. Structural Observations**
*   **Performance Monitoring:** The last 24h PnL is negative (-$8.59), with the majority of completed trades hitting stop-losses. If the win rate continues to degrade under the current BTC 15m downtrend, consider temporarily pausing new entries for non-whitelisted pairs until the 15m trend flips neutral/up.
*   **Tuner Validation:** The Optuna tuner is healthy and recently found a new best train score of 12.09%. Ensure these parameters are rigorously forward-tested out-of-sample before deployment, as previous structural changes severely degraded live performance.
