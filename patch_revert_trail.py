import re, json

with open('/root/bot.py', 'r') as f:
    code = f.read()

code = re.sub(r"if profit_pct > trail_trigger:", "if min_hold_passed:\n                        if profit_pct > trail_trigger:", code)

with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

code = re.sub(r"if True:\n                        if high_profit_pct > trail_trigger:", "if min_hold_passed:\n                        if high_profit_pct > trail_trigger:", code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)

with open('/root/config.json', 'r') as f:
    c = json.load(f)

if 'TRAILING_TRIGGER' in c: del c['TRAILING_TRIGGER']
if 'TRAILING_DIST' in c: del c['TRAILING_DIST']

with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)
