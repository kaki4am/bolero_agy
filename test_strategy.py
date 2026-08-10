import asyncio
import json
import os
from portfolio_backtester import PortfolioBacktester

async def main():
    tracked_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "XRPUSDT"]
    if os.path.exists('/root/tracked_pairs.json'):
        with open('/root/tracked_pairs.json', 'r') as f:
            data = json.load(f)
            tracked_pairs = data.get('tracked', tracked_pairs)
        
    print(f"Testing on {len(tracked_pairs)} pairs...")
    bt = PortfolioBacktester(tracked_pairs[:40], lookback="5 days ago UTC")
    await bt.fetch_data()
    
    with open('/root/config.json', 'r') as f:
        base_config = json.load(f)
        
    # Baseline
    bt.precalculate_all(base_config)
    pnl_base = bt.run(base_config)
    print(f"Baseline PnL: {pnl_base:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
