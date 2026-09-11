import re, json

with open('/root/bot.py', 'r') as f:
    code = f.read()

code = re.sub(r"if min_hold_passed:\n\s+if profit_pct > trail_trigger:", "if profit_pct > trail_trigger:", code)
code = re.sub(r"elif profit_pct > be_trigger:", "elif profit_pct > be_trigger:", code)

with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

code = re.sub(r"if min_hold_passed:\n\s+if high_profit_pct > trail_trigger:", "if True:\n                        if high_profit_pct > trail_trigger:", code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)

with open('/root/config.json', 'r') as f:
    c = json.load(f)

c['TRAILING_TRIGGER'] = 0.015
c['TRAILING_DIST'] = 0.005

with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)
