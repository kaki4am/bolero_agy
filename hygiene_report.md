I have completed the requested audit and fixed the performance leaks in the codebase. 

Here is a summary of the actions I took:

1. **Dead Indicator Math Removed:**
   - I audited the `calc_indicators` function in `bot.py` and the indicator calculation blocks in `portfolio_backtester.py`.
   - The strategy's entry and exit logic relies purely on the 1-minute Bollinger Band measurements (`bb_width`, `bb_width_prev`, `bb_upper`) and some 24-hour baseline volumes/returns. 
   - I discovered several CPU-heavy indicators being computed using `pandas_ta` and moving averages that were never evaluated in the `IF` logic. 
   - Removed computations for **`rsi_1h`**, **`sma20_1h`**, **`altcoin_4h_return`**, **`bb_1h`**, **`bbw_1h`**, and **`min_bbw_24_1h`** across both files, along with their related cached dictionaries and Numpy initializations.

2. **Unused Variables & Syntax Cleanup:**
   - I pruned out all remaining orphaned variables tied to the deleted indicators.
   - Cleaned up empty syntax blocks (e.g., empty `if/else` statements that were left behind) to ensure the scripts can parse correctly without syntax errors. 
   - Checked Python imports to ensure everything included was actively being used. The `sqlite3` import was confirmed to be actively used within a local scope (`read_db`) inside `bot.py` for syncing database state to active caches.

3. **Clean Code (Loops & Databases):**
   - I checked the loops inside `bot.py` and `portfolio_backtester.py` to make sure there were no empty iterations. Every loop was populated and performed critical side effects (calculating equity, parsing dust, populating timestamp indices, executing callbacks, etc.). 
   - I verified the only external database call (`read_db` inside `bot.py`) retrieves just the `MAX(id)` for positions via SQLite. This is well-optimized and is additionally wrapped in a cache-check mechanism to prevent redundant database queries during operations.

I have generated the requested report detailing these findings and wrote it directly to [`/root/hygiene_report.md`](file:///root/hygiene_report.md). Let me know if you would like me to review anything else!
debase is now significantly lighter, resulting in less RAM/CPU overhead and improved speed for the backtester!
