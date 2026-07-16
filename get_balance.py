import asyncio
import os
from binance import AsyncClient
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'True') == 'True'
    
    client = await AsyncClient.create(api_key, api_secret, testnet=use_testnet)
    try:
        balance = await client.get_asset_balance(asset='USDT')
        print(f"USDT_BALANCE:{balance['free']}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
