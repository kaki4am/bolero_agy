with open("/root/portfolio_backtester.py", "r") as f:
    bt = f.read()

# Fix the dict lookup
bt = bt.replace(
    "params['DECOUPLE_BTC_MIN']", "params.get('DECOUPLE_BTC_MIN', -3.0)"
).replace(
    "params['DECOUPLE_BTC_MAX']", "params.get('DECOUPLE_BTC_MAX', 1.0)"
).replace(
    "params['DECOUPLE_ALT_RET']", "params.get('DECOUPLE_ALT_RET', 3.0)"
).replace(
    "params['VOL_THRESHOLD']", "params.get('VOL_THRESHOLD', 1.5)"
).replace(
    "params['RDR_MIN']", "params.get('RDR_MIN', 1.6)"
).replace(
    "params['PROFIT_LOCK_TIME_H']", "params.get('PROFIT_LOCK_TIME_H', 18)"
).replace(
    "params['PROFIT_LOCK_PCT']", "params.get('PROFIT_LOCK_PCT', 0.0025)"
).replace(
    "params['STALENESS_TIME_H']", "params.get('STALENESS_TIME_H', 24)"
).replace(
    "params['STALENESS_EXIT_MIN']", "params.get('STALENESS_EXIT_MIN', -0.005)"
).replace(
    "params['STALENESS_EXIT_MAX']", "params.get('STALENESS_EXIT_MAX', 0.005)"
).replace(
    "params['MIN_PROFIT_TRIGGER']", "params.get('MIN_PROFIT_TRIGGER', 0.1)"
).replace(
    "params['BB_EXTENSION_PCT']", "params.get('BB_EXTENSION_PCT', 1.02)"
).replace(
    "params['CLIMAX_VOL_MULT']", "params.get('CLIMAX_VOL_MULT', 2.5)"
)

# 24H Profit Protection
bt = bt.replace(
    "if hold_time_m > params.get('PROFIT_LOCK_TIME_H', 18) * 60:\n                        pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + params.get('PROFIT_LOCK_PCT', 0.0025)))",
    "if hold_time_m > params.get('PROFIT_LOCK_TIME_H', 18) * 60:\n                        pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + params.get('PROFIT_LOCK_PCT', 0.0025)))\n                    if hold_time_m > 24 * 60 and current_profit_pct >= 0.01:\n                        pos['sl'] = max(pos['sl'], pos['entry_price'] * 1.003)"
)

with open("/root/portfolio_backtester.py", "w") as f:
    f.write(bt)

with open("/root/bot.py", "r") as f:
    bot = f.read()

bot = bot.replace(
    "if hold_seconds > self.config.get('PROFIT_LOCK_TIME_H', 18) * 3600:\n                        profit_lock = pos['entry_price'] * (1.0 + self.config.get('PROFIT_LOCK_PCT', 0.0025))\n                        sl = max(sl, profit_lock)\n                        self.positions[pair]['sl'] = sl",
    "if hold_seconds > self.config.get('PROFIT_LOCK_TIME_H', 18) * 3600:\n                        profit_lock = pos['entry_price'] * (1.0 + self.config.get('PROFIT_LOCK_PCT', 0.0025))\n                        sl = max(sl, profit_lock)\n                        self.positions[pair]['sl'] = sl\n                    if hold_seconds > 24 * 3600 and profit_pct >= 0.01:\n                        sl = max(sl, pos['entry_price'] * 1.003)\n                        self.positions[pair]['sl'] = sl"
)

with open("/root/bot.py", "w") as f:
    f.write(bot)
