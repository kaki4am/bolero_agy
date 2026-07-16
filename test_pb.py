import asyncio
from portfolio_backtester import PortfolioBacktester

async def main():
    symbols = ['HEIUSDT', 'WLDUSDT', 'EPICUSDT', 'BTCUSDT', 'ETHUSDT']
    pb = PortfolioBacktester(symbols)
    await pb.fetch_data()
    
    search_space = {
        'EMA_FAST': [50], 'EMA_SLOW': [200], 'ST_PERIOD': [7], 'ST_MULT': [3.0],
        'CHOP_PERIOD': [14], 'ADX_PERIOD': [14], 'BB_LENGTH': [20], 'BB_STD': [2.5],
        'ATR_PERIOD': [14], 'STOCH_K': [14], 'STOCH_D': [3], 'MFI_PERIOD': [14],
        'CMF_PERIOD': [20], 'OBV_EMA_PERIOD': [30], 'KC_PERIOD': [20], 'KC_MULT': [2.0],
        'VWMA_PERIOD': [20]
    }
    
    pb.precalculate_all(search_space)
    
    params = {
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'BB_LENGTH': 20, 'BB_STD': 2.5,
        'ADX_THRESHOLD': 25, 'CHOP_THRESHOLD': 50, 'VOL_TREND': 1.4,
        'MIN_VOLATILITY': 0.0015, 'BASE_RISK_PERCENT': 3.0
    }
    
    profit = pb.run(params)
    print(f"Profit: {profit}%")

if __name__ == "__main__":
    asyncio.run(main())
