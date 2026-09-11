import re

with open('/root/bot.py', 'r') as f:
    code = f.read()
code = re.sub(r"Strategy V154", "Strategy V155", code)
code = re.sub(r"V154", "V155", code)
with open('/root/bot.py', 'w') as f:
    f.write(code)

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()
code = re.sub(r"Strategy V154", "Strategy V155", code)
code = re.sub(r"V154", "V155", code)
with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
