import asyncio
from portfolio_backtester import PortfolioBacktester

async def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'LINKUSDT', 'AVAXUSDT', 'DOGEUSDT', 'NEARUSDT', 'UNIUSDT', 'PEPEUSDT', 'FETUSDT', 'WLDUSDT', 'DEXEUSDT', 'SYNUSDT', 'BELUSDT']
    
    tester = PortfolioBacktester(symbols, interval='1m', lookback='14 days ago UTC')
    await tester.fetch_data(status_callback=print)
    
    baseline_params = {
        "EMA_FAST": 50,
        "EMA_SLOW": 200,
        "MIN_VOLATILITY": 0.001,
        "BASE_RISK_PERCENT": 2.0,
        "MAX_RISK_PER_TRADE_PERCENT": 15.0,
        "COOLDOWN_PERIOD": 600,
        "ATR_SL_MULT": 2.5,
        "PORTFOLIO_EJECT": -5.0,
        "PORTFOLIO_HARVEST": 4.0,
        "BTC_RSI_THRESHOLD": 30.0,
        "VOL_SPIKE_MULTIPLIER": 1.5,
        "SL_MIN_PCT": 0.015,
        "SL_MAX_PCT": 0.03,
        "BE_TRIGGER": 0.02,
        "BE_LOCK": 0.002,
        "TRAILING_TRIGGER": 0.04,
        "TRAILING_DIST": 0.02,
        "ADX_THRESHOLD": 25.0,
        "VOLATILITY_CAP": 0.015,
        "SCALE_1_POS": 0.8,
        "SCALE_2_POS": 0.6,
        "SCALE_3_POS": 0.4,
        "VOLUME_SMA_WINDOW": 20
    }
    
    tester.precalculate_all(baseline_params, status_callback=print)
    
    print("--- BASELINE ---")
    pnl = tester.run(baseline_params)
    print(f"Baseline PnL: {pnl:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
