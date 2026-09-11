import json, re

# Revert config.json
with open('/root/config.json', 'r') as f:
    c = json.load(f)
c['ATR_SL_MULT'] = 1.0013095788655217
if 'TRAILING_TRIGGER' in c: del c['TRAILING_TRIGGER']
if 'TRAILING_DIST' in c: del c['TRAILING_DIST']
with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)

# Revert hold time for trailing stop
with open('/root/bot.py', 'r') as f:
    code = f.read()
code = re.sub(r"min_hold_passed = hold_seconds > 15 \* 60  # 15 minutes", "min_hold_passed = hold_seconds > 360 * 60  # 6 hours", code)
with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()
code = re.sub(r"hold_time_m > 15", "hold_time_m > 360", code)
with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)

