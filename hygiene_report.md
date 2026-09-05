I've completed the hygiene audit and successfully applied the necessary optimizations.

Here's a breakdown of what I repaired:

1. **Dead Indicator Math (Performance Leak)**: 
   - I identified a redundant `ta.sma` call for the 20-period moving average in both `bot.py` and `portfolio_backtester.py`. This was redundant because the subsequent `ta.bbands` call natively calculates and returns the SMA-20 as its middle band (`BBM_20_2.0_2.0`). I updated both scripts to use the native BB output to save CPU cycles.
   - I audited all other indicators (`sma30`, `atr14`, `bb_upper`, `bb_squeeze`, `er`, etc.). Every single one currently computed is strictly utilized in the strategy logic. (There are no remnant ADX or MACD calculations left).

2. **Redundant Database Calls**:
   - `bot.py` contained an unconditional `sqlite3` call on startup in `sync_positions_from_db()` that downloaded the latest trades—*even when* the state could be perfectly reconstructed from `active_positions.json`. 
   - I refactored this synchronization logic so it first relies on the local cache. The database is now loaded lazily and only queries as a strict fallback when an unrecognized asset is held on Binance.

3. **Code Cleanliness (Loops/Imports)**:
   - I audited the codebase for unused imports, orphan variables, and unused loops. All `for` loops across the files are currently performing necessary state updates, parallel IO operations, or backtest processing.

I have generated the final [hygiene_report.md](file:///root/hygiene_report.md) with a detailed overview of the audit and fixes applied. Let me know if you'd like to adjust any other logic!
ot.py` and `portfolio_backtester.py` (e.g., aggregating `total_val`, fetching batched macro trends, iterating active combinations in backtests) are strictly required for the core business logic. No empty or unreferenced loops were present. No unused variables or imports were found.
