import os
from datetime import datetime
from binance.client import Client
from dotenv import load_dotenv

load_dotenv('/root/.env')

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

client = Client(API_KEY, API_SECRET)

print("Fetching 30-day Account Snapshots...")
snap = client.get_account_snapshot(type='SPOT', limit=30)
prices = client.get_all_tickers()
btc_price = float([p['price'] for p in prices if p['symbol'] == 'BTCUSDT'][0])

# We need historical BTC prices to convert BTC snapshot values to USDT accurately
btc_klines = client.get_historical_klines('BTCUSDT', '1d', '35 days ago UTC')
btc_price_map = {datetime.fromtimestamp(k[0]/1000).date(): float(k[4]) for k in btc_klines}

print(f"Current Live BTC Price: ${btc_price:,.2f}")
print("-" * 50)

# Process snapshots
snapshots = snap.get('snapshotVos', [])
if not snapshots:
    print("No snapshot data available from Binance.")
else:
    for entry in snapshots:
        dt = datetime.fromtimestamp(entry['updateTime']/1000).date()
        btc_val = float(entry['data']['totalAssetOfBtc'])
        p_btc = btc_price_map.get(dt, btc_price)
        usdt_val = btc_val * p_btc
        print(f"{dt}: {btc_val:.6f} BTC (~${usdt_val:,.2f} USDT)")
        
    start_val = float(snapshots[0]['data']['totalAssetOfBtc']) * btc_price_map.get(datetime.fromtimestamp(snapshots[0]['updateTime']/1000).date(), btc_price)

print("-" * 50)
# Fetch live current balance
acc = client.get_account()
balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}

current_cash = balances.get('USDT', 0.0)
current_positions_val = 0.0
price_map = {p['symbol']: float(p['price']) for p in prices}

print("Active Assets:")
for asset, qty in balances.items():
    if asset == 'USDT':
        print(f"USDT: ${qty:,.2f}")
    else:
        pair = f"{asset}USDT"
        p = price_map.get(pair, 0.0)
        val = qty * p
        current_positions_val += val
        print(f"{asset}: {qty} (~${val:,.2f})")

current_total = current_cash + current_positions_val

print("-" * 50)
if snapshots:
    abs_pnl = current_total - start_val
    pct_pnl = (current_total / start_val - 1) * 100
    print("Binance Equity 30-Day PnL:")
    print(f"Starting Equity ({datetime.fromtimestamp(snapshots[0]['updateTime']/1000).date()}): ${start_val:,.2f}")
    print(f"Current Equity: ${current_total:,.2f}")
    print(f"Total Net PnL: ${abs_pnl:+,.2f} ({pct_pnl:+.2f}%)")
