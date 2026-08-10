import asyncio
from portfolio_backtester import PortfolioBacktester

async def main():
    # Load optimal config
    config = {
        "EMA_FAST": 50,
        "EMA_SLOW": 200,
        "MIN_VOLATILITY": 0.001,
        "BASE_RISK_PERCENT": 2.9168672489793552,
        "MAX_RISK_PER_TRADE_PERCENT": 22.00910984528415,
        "COOLDOWN_PERIOD": 600,
        "ATR_SL_MULT": 3.943450727160653,
        "PORTFOLIO_EJECT": -5.75725335746556,
        "PORTFOLIO_HARVEST": 9.205674111173586,
        "SL_MIN_PCT": 0.01371249198509283,
        "SL_MAX_PCT": 0.059997332938235684,
        "BE_TRIGGER": 0.026551251317468858,
        "BE_LOCK": 0.002350354116500405,
        "TRAILING_TRIGGER": 0.027395369359701865,
        "TRAILING_DIST": 0.0203330186386114,
        "TAKE_PROFIT": 0.07680278516339091,
        "VOLATILITY_CAP": 0.02072096532046158,
        "SCALE_1_POS": 0.9999337004004024,
        "SCALE_2_POS": 0.5674435386878007,
        "SCALE_3_POS": 0.14702031333346452,
        "VOLUME_SMA_WINDOW": 20
    }
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT']
    bt = PortfolioBacktester(symbols, interval='1m', lookback='5 days ago UTC')
    await bt.fetch_data()
    bt.precalculate_all(config)
    pnl = bt.run(config)
    print(f"BASELINE PNL: {pnl}%")

if __name__ == "__main__":
    asyncio.run(main())
