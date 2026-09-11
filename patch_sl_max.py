import re, json

with open('/root/bot.py', 'r') as f:
    code = f.read()

code = re.sub(r"sl_dist = max\(sl_dist, cp \* sl_min_pct\)", "sl_dist = max(sl_dist, cp * sl_min_pct)\n                    sl_max_pct = self.config.get('SL_MAX_PCT', 0.05)\n                    sl_dist = min(sl_dist, cp * sl_max_pct)", code)

with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

code = re.sub(r"sl_dist_price = max\(sl_dist_price, price \* sl_min_pct\)", "sl_dist_price = max(sl_dist_price, price * sl_min_pct)\n                            sl_max_pct = params.get('SL_MAX_PCT', 0.05)\n                            sl_dist_price = min(sl_dist_price, price * sl_max_pct)", code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)

with open('/root/config.json', 'r') as f:
    c = json.load(f)

c['SL_MAX_PCT'] = 0.05

with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)

