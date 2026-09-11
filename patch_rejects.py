import re

# Patch bot.py
with open('/root/bot.py', 'r') as f:
    code = f.read()

# Remove StaleTrend logic
code = re.sub(r"if not exit_reason and hold_seconds > 72 \* 3600:\n\s+ema_data = self.ema_cache.get\(pair, \{\}\)\n\s+sma20_1h = ema_data.get\('sma20_1h', cp\)\n\s+if cp < sma20_1h:\n\s+exit_reason = 'StaleTrend'", "", code)

# Remove decay
code = re.sub(r"if hold_seconds > 48 \* 3600:\n\s+decay = min\(1\.0, \(hold_seconds - 48 \* 3600\) / \(72 \* 3600\)\)\n\s+take_profit \*= \(1\.0 - decay\)", "", code)

with open('/root/bot.py', 'w') as f:
    f.write(code)

# Patch portfolio_backtester.py
with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

# Remove StaleTrend logic
code = re.sub(r"# Stale Trend Exposure \(> 72h and momentum negative\)\n\s+if not exit_reason and hold_time_m > 72 \* 60:\n\s+if price < s_data\['sma20_1h'\]\[idx\]:\n\s+exit_reason = \"StaleTrend\"\n\s+exit_price = price \* \(1\.0 - slippage_pct\)", "", code)

# Remove decay
code = re.sub(r"# Time-Decaying Take-Profit \(> 48h\)\n\s+if hold_time_m > 48 \* 60:\n\s+decay_factor = min\(1\.0, \(hold_time_m - 48\*60\) / \(72\*60\)\)\s+# Decays to 0 over 72h\n\s+take_profit = take_profit \* \(1\.0 - decay_factor\)", "", code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
