I have completed the requested audit based on the instructions from `/tmp/coherence_prompt.md`. Here is a summary of the analysis and the repairs I made across the trading system:

1. **Strategy Logic Alignment (`bot.py` vs `portfolio_backtester.py`)**
   - **Issue Detected**: In `portfolio_backtester.py`, the `Pullback_RSI` setup logic incorrectly used the `btc_uptrend_15m` flag to validate the macro trend, whereas `bot.py` correctly checked if the specific pair's price was above its own 1-hour 200 EMA (`cp > ema200`). 
   - **Fix Applied**: Updated `portfolio_backtester.py` to correctly calculate and use the `ema200_1h` for the specific trading pair as the macro trend confirmation for the `Pullback_RSI` signal, perfectly aligning the backtester logic with the live `bot.py` implementation.

2. **Dashboard UI Updates (`bot.py` & `dashboard.py`)**
   - **Issue Detected**: The `dashboard.py` script was not displaying the new `vol_surge` metric used by the `Trend_BB_Squeeze` setup, nor was it showing the RSI indicators newly used by the `Pullback_RSI` setup.
   - **Fix Applied**: 
     - Modified `bot.py` to persist `rsi_1h`, `rsi_1h_prev`, `rsi_min_5`, and `ema200_1h` into the `self.current_indicators` dictionary, ensuring they are written to `dashboard_data.json`.
     - Updated `dashboard.py` to read these values and accurately display the `vol_surge` boolean flag alongside the new RSI and EMA metrics in the live UI.

3. **Cleanup System Safeguards (`cleanup_system.py`)**
   - **Issue Detected**: Several active files and temporary JSON state files were missing from the `WHITELIST` in `cleanup_system.py`, leaving them vulnerable to accidental deletion by the cleanup routine. 
   - **Fix Applied**: I added the following items to the whitelist:
     - Temporary state files (`active_positions.json.tmp`, `dashboard_data.json.tmp`).
     - Script artifacts (`fix_bot_entry.py`, `update_dashboard.py`, `update_gemini.py`).
     - AI committee notes (`price_ideas.md`, `system_ideas.md`, `trade_ideas.md`).
     *(Note: `active_positions.json`, `tactical_overrides.json`, and `ai_manager.log` were already safely whitelisted).*

I have documented these findings and repairs inside `coherence_report.md`, which is now available in your `/root` directory.
It looks like the system verification tests just finished running in the background and all tests passed successfully! The syntax, code quality, alignment consistency, and historical stress tests all check out perfectly. Let me know if there's anything else you need.
