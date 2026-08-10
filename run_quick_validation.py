import asyncio
import json
import logging
import sys
from portfolio_backtester import PortfolioBacktester

logging.basicConfig(level=logging.ERROR)

async def main():
    try:
        with open('/root/config.json', 'r') as f:
            params = json.load(f)
            
        pb = PortfolioBacktester(symbols=[
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT', 
            'DOTUSDT', 'LTCUSDT', 'LINKUSDT', 'AVAXUSDT', 'POLUSDT', 'UNIUSDT', 'ATOMUSDT', 
            'INJUSDT', 'RNDRUSDT', 'NEARUSDT', 'FILUSDT', 'OPUSDT', 'APTUSDT'
        ])
        await pb.fetch_data()
        pb.precalculate_all(params)
        
        pnl = pb.run(params)
        trades_out = pb.trades
        
        wins = len([t for t in trades_out if t['pnl'] > 0])
        losses = len([t for t in trades_out if t['pnl'] <= 0])
        print(f"RECENT 5-DAY BACKTEST: {len(trades_out)} trades | {wins}W/{losses}L | PnL: {pnl:.2f}%")
    except Exception as e:
        print(f"RECENT 5-DAY BACKTEST: Failed ({e})")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
