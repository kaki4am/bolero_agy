import re

with open('/root/bot.py', 'r') as f:
    code = f.read()
code = re.sub(r"min_hold_passed = hold_seconds > 360 \* 60  # 6 hours", "min_hold_passed = hold_seconds > 15 * 60  # 15 minutes", code)
with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()
code = re.sub(r"hold_time_m > 360", "hold_time_m > 15", code)
with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
