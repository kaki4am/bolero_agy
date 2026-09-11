import re

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

blacklist_code = """        blacklist = ['PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'VETUSDT', 'LAPTOPUSDT', 'REZUSDT', 'ANIMEUSDT', 'SAGAUSDT']
        self.pair_data = {k: v for k, v in self.pair_data.items() if k not in blacklist}
        total = len(self.pair_data)"""

code = re.sub(r"total = len\(self\.pair_data\)", blacklist_code, code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)

