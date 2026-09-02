import json
import pandas as pd
from portfolio_backtester import PortfolioBacktester

with open('config.json', 'r') as f:
    params = json.load(f)

tester = PortfolioBacktester(symbols=['BTCUSDT'])
# This needs to fetch data, let's just see if we can do something simple or modify portfolio_backtester.py locally
