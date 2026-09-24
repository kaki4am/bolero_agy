I have completed the system audit and applied the requested repairs to fix performance leaks and dead code. 

Here is a summary of the repairs:

1. **Dead Indicator Math & Performance Leaks**: 
   - Found a critical CPU performance leak in `bot.py` where `ta.bbands` was being calculated inside the `handle_socket` listener for every single websocket tick. I rewrote this logic to retrieve the already calculated `bb_upper` value from the `self.current_indicators` cache (which is efficiently updated once per minute by `analyze()`). 
   - Audited the indicator math in `bot.py` and `portfolio_backtester.py`. No leftover MACD, ADX, or SMA logic from older strategies was found (the `sma20_series` is required for calculating Bollinger Band Width).
2. **Unused Imports & Variables**: 
   - Cleaned up the orphan variable `df_pair` in `bot.py` that resulted from the aforementioned optimization.
   - Removed unused `import re` from `audit_invariants.py`.
   - Removed unused `import numpy as np` and orphan variable `fee_ratio` from `reflect.py`.
   - Removed unused variable `search_space` from `verify_system.py`.
3. **Clean Code**: 
   - Verified that all active loops across the system (e.g. `usdt_pairs` and `positions.items()`) are actively used. 
   - Audited `bot.py` for redundant database calls, ensuring that `sync_positions_from_db()` uses its internal `db_df is None` guard to hit `sqlite3` efficiently only once when restoring state, preventing redundant I/O waits.

I have written the final summary to [hygiene_report.md](file:///root/hygiene_report.md) as requested. Let me know if you need any further analysis of this trading system!
.items()`) across the system. All are actively contributing to the portfolio logic. No unused loops were found.
- **Database Calls**: Audited the `sync_positions_from_db()` in `bot.py`. The `sqlite3.connect` and `read_sql_query` logic is guarded properly (`if db_df is None`) ensuring it's only executed once and cached, eliminating any redundant or expensive repeated database queries.

The autonomous trading system is now optimized, clean, and functioning without dead overhead.
