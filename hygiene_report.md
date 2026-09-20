I have completed the requested audit based on the instructions in `/tmp/hygiene_prompt.md`.

Here is a summary of the findings:

1.  **Dead Indicator Math**: I rigorously scanned the entry/exit logic in `bot.py` and `portfolio_backtester.py`. I verified that all calculated indicators (`ta.bbands`, `ta.atr`, and `ta.ema`) and custom volume/price derivatives are actively utilized in the strategy's IF conditions (e.g., Squeeze breakout, Trend alignment, Volatility caps). There are no leftover MACD, ADX, or unused SMA logic instances remaining in `calc_indicators` or the backtester.
2.  **Unused Variables & Imports**: I ran static analysis tools (`flake8`, `vulture`, and Python AST sweeps) against the code. The environment contains zero unused imports or orphan variables.
3.  **Clean Code (Loops & DB Calls)**: The loops inside `bot.py` (like the `portfolio_guard_loop` and `sync_positions_from_db`) are highly optimized. The `read_db()` operation is lazy-loaded (only fetched once during a cache miss) and avoids any redundant database calls. No unused iterations were found.

The codebase is exceptionally clean and well-optimized. I have compiled these details into a formal output report at `/root/hygiene_report.md`.
