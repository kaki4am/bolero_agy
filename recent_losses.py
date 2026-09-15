import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def get_stats():
    conn = sqlite3.connect('/root/trading_bot.db')
    trades = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    trades['timestamp'] = pd.to_datetime(trades['timestamp'])
    
    buys = {}
    cycles = []
    
    for idx, row in trades.iterrows():
        pair = row['pair']
        side = row['side']
        qty = row['quantity']
        price = row['price']
        ts = row['timestamp']
        
        if pair not in buys:
            buys[pair] = []
            
        if side == 'BUY':
            buys[pair].append({'qty': qty, 'price': price, 'ts': ts})
        elif side == 'SELL':
            sell_qty = qty
            cycle_qty = 0
            cycle_cost = 0
            first_buy_ts = None
            
            while sell_qty > 0 and buys[pair]:
                buy = buys[pair][0]
                match_qty = min(sell_qty, buy['qty'])
                cycle_qty += match_qty
                cycle_cost += match_qty * buy['price']
                if first_buy_ts is None:
                    first_buy_ts = buy['ts']
                buy['qty'] -= match_qty
                sell_qty -= match_qty
                if buy['qty'] <= 0.0001:
                    buys[pair].pop(0)
            
            if cycle_qty > 0:
                avg_buy_price = cycle_cost / cycle_qty
                pnl = (price - avg_buy_price) * cycle_qty
                pct = (price - avg_buy_price) / avg_buy_price * 100
                cycles.append({
                    'pair': pair,
                    'pnl': pnl,
                    'pnl_pct': pct,
                    'buy_ts': first_buy_ts,
                    'sell_ts': ts
                })
                
    cycles_df = pd.DataFrame(cycles)
    
    last_7d = datetime.now() - timedelta(days=7)
    recent = cycles_df[cycles_df['sell_ts'] >= last_7d]
    worst = recent.sort_values(by='pnl').head(20)
    print("Worst trades in last 7 days:")
    print(worst.to_string())
    print("\nTotal PnL in last 7 days: ", recent['pnl'].sum())

if __name__ == '__main__':
    get_stats()
