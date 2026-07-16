import asyncio
import sys
sys.path.append('/root')
from portfolio_backtester import PortfolioBacktester

async def main():
    pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'APTUSDT', 'GTCUSDT', 'CRVUSDT', 'INJUSDT', 'NEARUSDT', 'WLDUSDT']
    bt = PortfolioBacktester(pairs)
    print("Fetching data...")
    await bt.fetch_data()
    print("Precalculating...")
    bt.precalculate_all({'EMA_FAST': [50], 'EMA_SLOW': [200], 'ST_PERIOD': [7, 10], 'ST_MULT': [2.5, 3.0], 'BB_LENGTH': [20, 30], 'BB_STD': [2.0, 2.5]})

    print("Running Baseline V26...")
    pnl = bt.run({'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0})
    print(f"Base PnL: {pnl}%")

    print("Running V27 (Relaxed Stagnant Limits)...")
    pnl_v27 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008
    })
    print(f"V27 PnL: {pnl_v27}%")

    print("Running V28 (Relaxed PG + Relaxed Stagnant)...")
    pnl_v28 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'PG_LVL_1': 0.010, 'PG_LOCK_1': 1.002,
        'PG_LVL_2': 0.020, 'PG_LOCK_2': 1.008,
        'PG_LVL_3': 0.035, 'PG_LOCK_3': 1.015,
        'PG_LVL_4': 0.050, 'PG_LOCK_4': 1.025
    })
    print(f"V28 PnL: {pnl_v28}%")

    print("Running V29 (V27 + Relaxed Volatility Shield 2.5% + SL Cap 3.5%)...")
    pnl_v29 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'VOL_SHIELD': 0.025, 'MAX_SL_CAP': 0.035
    })
    print(f"V29 PnL: {pnl_v29}%")

    print("Running V30 (V27 + Stricter Volume)...")
    pnl_v30 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'VOL_MULT_TREND': 1.5, 'VOL_MULT_BREAK': 2.0
    })
    print(f"V30 PnL: {pnl_v30}%")

    print("Running V31 (V30 + MACD > 0)...")
    pnl_v31 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'VOL_MULT_TREND': 1.5, 'VOL_MULT_BREAK': 2.0,
        'MACD_ZERO': True
    })
    print(f"V31 PnL: {pnl_v31}%")

    print("Running V32 (V27 + ST 10/3.0)...")
    pnl_v32 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 10, 'ST_MULT': 3.0, 'BB_LENGTH': 20, 'BB_STD': 2.0,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008
    })
    print(f"V32 PnL: {pnl_v32}%")

    print("Running V33 (V27 + BB 30/2.5)...")
    pnl_v33 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008
    })
    print(f"V33 PnL: {pnl_v33}%")

    print("Running V34 (V33 + ADX 35)...")
    pnl_v34 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'ADX_THRESHOLD': 35
    })
    print(f"V34 PnL: {pnl_v34}%")

    print("Running V35 (V33 + ST 10/3.0)...")
    pnl_v35 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 10, 'ST_MULT': 3.0, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008
    })
    print(f"V35 PnL: {pnl_v35}%")

    print("Running V36 (V34 + ADX 40)...")
    pnl_v36 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'ADX_THRESHOLD': 40
    })
    print(f"V36 PnL: {pnl_v36}%")

    print("Running V37 (V34 + Pullback ADX 25)...")
    pnl_v37 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'ADX_THRESHOLD': 35, 'PULLBACK_ADX': 25
    })
    print(f"V37 PnL: {pnl_v37}%")

    print("Running V38 (V36 + ADX 45)...")
    pnl_v38 = bt.run({
        'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 2.5, 'BB_LENGTH': 30, 'BB_STD': 2.5,
        'STAG_U_TIME': 15, 'STAG_U_LOSS': -0.010,
        'STAG_F_TIME': 25, 'STAG_F_LOSS': -0.012,
        'STAG_S_TIME': 40, 'STAG_S_LOSS': -0.008,
        'ADX_THRESHOLD': 45
    })
    print(f"V38 PnL: {pnl_v38}%")

asyncio.run(main())