import asyncio
from binance import AsyncClient
import pandas as pd
import pandas_ta as ta

async def main():
    client = await AsyncClient.create()
    kl = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    await client.close_connection()
    df = pd.DataFrame(kl, columns=['t', 'open', 'high', 'low', 'close', 'v', 'ct', 'qav', 'nt', 'tbb', 'tbq', 'i'])
    for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
    
    bb = ta.bbands(df['close'], length=20, std=2.0)
    sma20 = ta.sma(df['close'], length=20)
    atr1m = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    bb_upper = bb['BBU_20_2.0_2.0']
    bb_lower = bb['BBL_20_2.0_2.0']
    kc_upper = sma20 + 1.5 * atr1m
    kc_lower = sma20 - 1.5 * atr1m
    
    sqz_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    print(f"Squeeze ON count in 1 day (1440 mins): {sqz_on.sum()}")
    
    sqz_recent = sqz_on.shift(1).rolling(15).max() > 0
    sqz_fires = sqz_recent & (~sqz_on)
    print(f"Squeeze FIRES count: {sqz_fires.sum()}")

asyncio.run(main())
