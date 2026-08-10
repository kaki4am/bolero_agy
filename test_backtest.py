import asyncio
from portfolio_backtester import PortfolioBacktester
import json

async def run_test():
    with open('/root/daily_report.json', 'r') as f:
        data = json.load(f)
    params = data.get('tuner_optimal_config', {})
    
    if not params:
        params = {
            "EMA_FAST": 50,
            "EMA_SLOW": 200,
            "MIN_VOLATILITY": 0.001,
            "BASE_RISK_PERCENT": 2.22874205773196,
            "MAX_RISK_PER_TRADE_PERCENT": 23.775733323944632,
            "COOLDOWN_PERIOD": 600,
            "ATR_SL_MULT": 3.8319851901308395,
            "PORTFOLIO_EJECT": -4.2721352112657645,
            "PORTFOLIO_HARVEST": 9.695602527149607,
            "SL_MIN_PCT": 0.017101978306769898,
            "SL_MAX_PCT": 0.02715633612555158,
            "BE_TRIGGER": 0.012670370564885932,
            "BE_LOCK": 0.003422356925913073,
            "TRAILING_TRIGGER": 0.045321396369868164,
            "TRAILING_DIST": 0.024202599031040176,
            "TAKE_PROFIT": 0.03227762569725392,
            "VOLATILITY_CAP": 0.010664154697327672,
            "SCALE_1_POS": 0.5094440944744757,
            "SCALE_2_POS": 0.4815772455665372,
            "SCALE_3_POS": 0.10039819275935798,
            "VOLUME_SMA_WINDOW": 20
        }
    with open('/root/tracked_pairs.json', 'r') as f:
        symbols = json.load(f).get('tracked', [])
        
    bt = PortfolioBacktester(symbols[:40], interval='1m', lookback='5 days ago UTC')
    await bt.fetch_data(lambda x: None)
    bt.precalculate_all(params, lambda x: None)
    pnl = bt.run(params)
    print(f"PnL: {pnl:.2f}%")

asyncio.run(run_test())
