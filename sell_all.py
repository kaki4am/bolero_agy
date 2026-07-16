import asyncio
import os
from dotenv import load_dotenv
from binance import AsyncClient
load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
USE_TESTNET = os.getenv('USE_TESTNET', 'True') == 'True'

async def main():
    client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
    acc = await client.get_account()
    for b in acc['balances']:
        asset, free = b['asset'], float(b['free'])
        if free > 0 and asset not in ['USDT', 'BNB']:
            pair = f"{asset}USDT"
            try:
                info = await client.get_exchange_info()
                s_info = next(s for s in info['symbols'] if s['symbol'] == pair)
                f = {flt['filterType']: flt for flt in s_info['filters']}
                ss = float(f['LOT_SIZE']['stepSize'])
                prec = len(format(ss, 'f').split('.')[-1].rstrip('0')) if ss < 1.0 else 0
                q = float(int(free / ss) * ss)
                fq = format(q, f'.{prec}f')
                print(f"Selling {fq} {pair}...")
                order = await client.create_order(symbol=pair, side='SELL', type='MARKET', quantity=fq)
                print(f"Sold {pair}: {order['status']}")
            except Exception as e:
                print(f"Failed to sell {pair}: {e}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
