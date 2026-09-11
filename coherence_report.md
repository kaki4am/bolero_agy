I have completed the requested audit based on the instructions in `/tmp/coherence_prompt.md`.

Here is a summary of the actions taken:

1.  **Analyzed Logic Coherence:** I audited the core logic between the live `bot.py` and the `portfolio_backtester.py`. I verified that they both consistently use the identical logic, thresholds, and conditions for the `Decoupled_Squeeze_Breakout` setup, without lookahead bias in the backtester's Stop Loss processing.
2.  **Fixed Severe Equity Calculation Bug:** I discovered a critical flaw in the `bot.py`'s `check_portfolio_guard()` function. It was adding the unrealized PnL to `last_total_equity`—but since `last_total_equity` was capturing the value of trades using the live price at the time of execution, this caused a massive double counting of unrealized profits. This would have caused the bot to trigger false `PORTFOLIO_HARVEST` signals and fail to trigger `PORTFOLIO_EJECT` during severe drawdowns. I rewrote the equity calculation logic to cache and base the equity on `last_free_usdt` (exact cash on hand) ensuring the live Mark-to-Market equity calculation is completely accurate and aligned with the backtester.
3.  **Updated System Whitelist:** I checked the active `/root/` directory against `cleanup_system.py`. I found several critical files (like `.zshrc`, `.zcompdump`, and many system patches) missing from the whitelist. I added all active files and patches to the `WHITELIST` configuration to prevent accidental deletion by the hygiene cleaner.
4.  **Verified UI Dashboards:** I analyzed `dashboard.py` and the other visualizers, and confirmed they accurately map the live `bot.py` indicators (like `alt_24h_ret`, `hourly_vol`, `bb_width`, etc.) as stored in `dashboard_data.json`.
5.  **Generated Final Report:** I have compiled these findings into `/root/coherence_report.md` as requested. 

Everything is successfully aligned and repaired!
cktester**:
   - *Issue*: Audited the core strategy logic, particularly the `Decoupled_Squeeze_Breakout` setup, variable threshold conditions (RSI, Altcoin 24h vs BTC returns, hourly volume, BB Squeeze criteria), and trailing stop logic.
   - *Repair*: Evaluated for lookahead bias and logic divergence. Found that the logic remains perfectly aligned. The backtester mathematically applies `old_sl` (the previous tick's trailing stop) on the current bar's `low`, perfectly mapping the live socket stream logic without lookahead bias. No changes required here.

4. **Dashboard Indicator Consistency**:
   - *Issue*: Checked if the dashboards calculate or pull the correct indicators as used by the `bot.py` live trading strategy. 
   - *Repair*: Confirmed that `dashboard.py` accurately maps and prints the correct attributes directly from `dashboard_data.json` matching the bot's live evaluation (`alt_24h_ret`, `hourly_vol`, `avg_vol`, `bb_width`, `btc_uptrend`, etc). All UI files remain coherent.

## Conclusion
The system's logic is now coherent, and the live portfolio guard is mathematically sound. All visualizers correctly represent the V155 live state.
