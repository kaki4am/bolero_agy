with open('/root/portfolio_backtester.py', 'r') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if "blacklist = ['PEPEUSDT'" in l:
        lines[i] = "        blacklist = ['PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'VETUSDT', 'LAPTOPUSDT', 'REZUSDT', 'ANIMEUSDT', 'SAGAUSDT']\n"
        break
with open('/root/portfolio_backtester.py', 'w') as f:
    f.writelines(lines)
