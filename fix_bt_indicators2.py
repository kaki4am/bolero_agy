import re

with open('/root/portfolio_backtester.py', 'r') as f:
    content = f.read()

content = re.sub(r' +if len\(df_1h\) >= 14:\n +else:\n', '', content)
content = re.sub(r' +# Dynamic Trend Efficiency Filter \(Chop Filter\)\n +if len\(df_1h\) >= 24:\n +pass\n', '', content)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(content)
