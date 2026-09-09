I have completed the system hygiene audit and applied the necessary repairs to both `bot.py` and `portfolio_backtester.py`. Here's a breakdown of the optimizations made:

### 1. Dead Indicator Math Removed
* **`bot.py`:** Removed `sma20` and `bbw_sma30` calculations from `calc_indicators` because they weren't utilized in any entry or exit IF conditions. I also removed `vol_1h` and `vol_24h` variable updates inside the `fetch_pair_ema` function since their respective calculated values (`atr_pct` and `avg_hourly_range_pct`) were left hanging and never consumed by the bot. Finally, calculations for `altcoin_1h_volume` and `altcoin_avg_volume_usd` were also removed from `fetch_pair_ema` since they were unused.
* **`portfolio_backtester.py`:** Purged the unutilized calculations of `sma20`, `bbw_sma30`, `altcoin_1h_volume`, and `altcoin_avg_volume_usd` and prevented them from needlessly bloating the `np_data` arrays and dictionaries. 

### 2. Unused Variables & Imports 
* After inspecting both core scripts alongside running `flake8` within the bot's virtual environment, there were no unused imports found.
* All orphaned logic and unutilized intermediate variables discovered (e.g. `atr_pct`, `avg_hourly_range_pct`) during the removal of the dead indicator math above were scrubbed completely.

### 3. Redundant Database & API Calls
* **Critical API Redundancy Fixed:** The `check_portfolio_guard` loop in `bot.py` runs every 2 seconds. In it, the bot was fetching real-time balances using `await self.client.get_asset_balance(asset='USDT')` to recalculate total equity against the portfolio's unrealized profit. Hitting the Binance API every two seconds strictly for balances could cause aggressive rate-limiting in production. I updated this section to locally deduce the `current_equity` via `self.last_total_equity` (which updates perfectly fine downstream of any trade logic) and the real-time active prices tracked via WebSockets.

A summary report capturing these exact details has been successfully written to [hygiene_report.md](file:///root/hygiene_report.md). Let me know if you need any additional adjustments!
