I have successfully audited the codebase and completed the requested hygiene checks. 

Here is a summary of the findings:
- **Dead Indicator Math:** I performed a comprehensive scan of the entry/exit logic in both `bot.py` and `portfolio_backtester.py`. All mathematical calculations (including the SMA middle band) directly contribute to variables explicitly evaluated in the trading logic. There were no leftover or unused indicators like MACD or ADX being unnecessarily calculated in `calc_indicators` or the backtester.
- **Unused Variables & Imports:** I scanned for orphan variables and unused python imports in both scripts. They are clean; all imported modules (including `sqlite3` and `pandas_ta`) and declared variables are actively utilized.
- **Clean Code & DB Calls:** `bot.py`'s `sync_positions_from_db()` method efficiently queries the database using a lazy evaluation, preventing redundant fetching for cached symbols. The loops in `portfolio_backtester.py` for simulation and numpy-based data conversions are tightly written and entirely utilized.

The detailed audit summary has been successfully written to `/root/hygiene_report.md` as requested. The codebase is remarkably clean of performance leaks in this regard! Let me know if you need any other optimizations or code reviews.
`ta.bbands` (the middle band) is required and strictly used to compute the Bollinger Band Width percentage (`bbw = (bb_upper - bb_lower) / sma20`), so it is not an unused artifact.

## 2. Unused Variables & Imports
- Scanned for orphan variables and unused python imports in `bot.py` and `portfolio_backtester.py`.
- No unused imports or orphan variables were found. `sqlite3` is actively used in `bot.py` for reading the local database, and `pandas_ta` is actively used for the aforementioned indicator calculations. 

## 3. Clean Code (Unused Loops & Redundant Database Calls)
- Scanned for redundant database calls and unused loops.
- `bot.py`'s `sync_positions_from_db()` method efficiently queries the database using a lazy evaluation (`if db_df is None: db_df = read_db()`), preventing redundant fetching for cached symbols. The query uses an optimized `SELECT MAX(id) ... GROUP BY pair`.
- The loops in `portfolio_backtester.py` for simulation and numpy-based data conversions are tightly written and entirely utilized. No redundant/unused loops were found.

**Conclusion:** The codebase was found to be exceptionally clean regarding dead code and performance hygiene. No files required deletion of dead logic during this audit pass.
