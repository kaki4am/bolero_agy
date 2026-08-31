import os
from trading_utils import get_account_snapshot_data

print("Fetching 30-day Account Snapshots...")
data = get_account_snapshot_data()

if not data:
    print("No snapshot data available from Binance.")
    exit(0)

print(f"Current Live BTC Price: ${data['btc_price']:,.2f}")
print("-" * 50)

for entry in data['daily_history']:
    print(f"{entry['date']}: {entry['btc_val']:.6f} BTC (~${entry['usdt_val']:,.2f} USDT)")

print("-" * 50)
print("Active Assets:")
for a in data['active_assets']:
    if a['asset'] == 'USDT':
        print(f"USDT: ${a['qty']:,.2f}")
    else:
        print(f"{a['asset']}: {a['qty']} (~${a['val']:,.2f})")

print("-" * 50)
print("Binance Equity 30-Day PnL:")
print(f"Starting Equity ({data['start_date']}): ${data['start_val']:,.2f}")
print(f"Current Equity: ${data['current_total']:,.2f}")
print(f"Total Net PnL: ${data['abs_pnl']:+,.2f} ({data['pct_pnl']:+.2f}%)")
print(f"BTC Benchmark: {data['btc_pct']:+.2f}%")
print(f"Bot Alpha (vs BTC): {data['alpha']:+.2f}%")
