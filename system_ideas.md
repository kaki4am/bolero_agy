Based on the provided telemetry, logs, and previous learnings, here are the structural and risk management proposals:

### 1. Risk Management & Execution
* **Exclude Unsupported Pairs:** Immediately add `ORCAUSDT` and `METISUSDT` to the restricted pairs list. They are causing API "-2010" permission errors and wasting execution cycles.
* **Review Short-Duration Stop-Outs:** `GRTUSDT` (-2.26% in 42m) and `WOOUSDT` (-1.96% in 7m) indicate potential vulnerability to sudden wicks, spread, or liquidity issues upon entry. Consider implementing a minimum volume/liquidity threshold filter for candidate pairs to avoid erratic price action on low-cap coins.
* **Capital Velocity Monitoring:** `EPICUSDT` tied up capital for 463 hours (19 days) only to close at a -3.65% loss. Since hard time limits (e.g., 72h) were previously rejected, consider a **time-based trailing stop** that slowly tightens after a significant duration (e.g., 150+ hours) to free up stagnant capital.

### 2. System Health & Structural
* **Investigate Service Restarts:** The `trading-bot.service` restarted cleanly twice within 10 minutes (02:44 and 02:54). While harmless if triggered by config updates, ensure this isn't an unintended restart loop causing missed 15-minute candle closes.
* **Optuna Tuning Progression:** The Bayesian optimizer found a new best training score (38.99%). Given recent rejections of ATR stops and time filters causing out-of-sample degradation, ensure the tuner is strictly using out-of-sample forward validation before deploying these new parameters to production.
