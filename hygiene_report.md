I have completed the requested audit and fixes for the trading system based on the instructions in `/tmp/hygiene_prompt.md`.

Here is a summary of the actions taken:

### 1. Dead Indicator Math 
- **`bot.py`**: I discovered that the system was fetching `BTCUSDT` klines, calculating `ema200_15m` with `pandas_ta`, and using it to determine `btc_uptrend_15m`. However, this was purely decorative and pushed into telemetry; it was completely ignored by the entry and exit IF statement logic. I stripped these calculations entirely from `fetch_macro_trends` and removed the variable from the `current_indicators` data structure in `analyze()` to conserve CPU cycles.
- **`portfolio_backtester.py`**: The backtester similarly computed an `uptrend_15m` variable using an `ema200` shift. Since the simulation loop was not checking this variable, I removed it from the alignment logic and cleaned it out from the core `np_data` structure.

### 2. Unused Variables & Imports 
- Verified `bot.py` and `portfolio_backtester.py` for orphan variables and unused python imports. 
- Utility functions imported (`init_db`, `log_trade`, `log_failed_trade`), modules (`sqlite3`, `time`, `pandas`, `pandas_ta`), and data variables inside `calc_indicators()` were checked and verified to be actively invoked in the active logic (e.g. `sqlite3` connects internally inside `sync_positions_from_db`). 
- There were no leftover MACD, ADX, or orphaned SMA dependencies dragging on CPU performance.

### 3. Clean Code (Loops & DB Calls)
- Reviewed the implementation for redundant database calls and iteration. The loop inside `sync_positions_from_db()` lazy-loads from sqlite on first cache miss and does not make extraneous calls. The `portfolio_backtester.py` leverages vectorized `numpy` calculations internally before hitting simulation steps rather than loop-based recomputation. 

I've documented these findings and repairs in a cleanly formatted summary located at [hygiene_report.md](file:///root/hygiene_report.md). Let me know if there's anything else you need me to adjust!
