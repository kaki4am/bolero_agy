I have completed the coherence audit of the trading system. 

Here is a summary of the repairs made:

1. **System Cleanup Whitelist Fixes:**
   I checked `/root` against the `WHITELIST` in `/root/cleanup_system.py` and discovered that some critical active files were missing and at risk of being deleted. I added the following missing files to the whitelist:
   - `check_gemini_credits.sh`
   - `gemini_credit_gate.log`
   - `.dashboard_cache.json`
   - `.positions_cache.json`

2. **Strategy Version Consistency:**
   Although the current active strategy as per `/root/GEMINI.md` is **V161**, multiple files in the system (e.g., `bot.py`, `portfolio_backtester.py`, `ai_manager.py`, `audit_invariants.py`, and markdown docs) were hardcoded to older versions (`V160` and `V158`). I updated all of these to correctly reference `V161`.

3. **Dashboard and Live Bot UI Coherence:**
   The V161 strategy introduces specific logic around `BTC 1h BB width` (relaxing volume threshold for entry logic) and `BTC 24h return` (for risk scaling). However, `bot.py` was not exporting these particular indicators, and they were missing from the UI dashboard. 
   - I updated `/root/bot.py` to extract `btc_1h_bb_width` and `btc_24h_ret` and expose them to the `current_indicators` dictionary. 
   - I then updated `/root/dashboard.py` to pull these exact metrics and display them properly in the real-time financial performance panel so it aligns identically with the bot's true evaluation criteria.

I have generated the clean summary of this audit and successfully written it to [/root/coherence_report.md](file:///root/coherence_report.md). Let me know if there's anything else you need!
