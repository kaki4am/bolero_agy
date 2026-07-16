import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta

def export_report():
    conn = sqlite3.connect('trading_bot.db')
    
    # Load ALL trades to perform full FIFO cycle matching (including buys > 24h ago)
    trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    
    realized_trades = []
    
    # Group by pair to find completed cycles
    for pair in trades_df['pair'].unique():
        pair_trades = trades_df[trades_df['pair'] == pair].sort_values('timestamp')
        buys = []
        
        for _, row in pair_trades.iterrows():
            if row['side'] == 'BUY':
                buys.append({
                    'qty': row['quantity'],
                    'price': row['price'],
                    'timestamp': pd.to_datetime(row['timestamp'])
                })
            elif row['side'] == 'SELL':
                sell_qty = row['quantity']
                sell_price = row['price']
                sell_ts = pd.to_datetime(row['timestamp'])
                
                cycle_qty = 0
                cycle_cost = 0
                first_buy_ts = None
                
                while sell_qty > 0 and buys:
                    buy = buys[0]
                    match_qty = min(sell_qty, buy['qty'])
                    cycle_qty += match_qty
                    cycle_cost += match_qty * buy['price']
                    if first_buy_ts is None:
                        first_buy_ts = buy['timestamp']
                    
                    buy['qty'] -= match_qty
                    sell_qty -= match_qty
                    if buy['qty'] <= 0.0001:
                        buys.pop(0)
                        
                if cycle_qty > 0:
                    avg_buy_price = cycle_cost / cycle_qty
                    trade_pnl = (sell_price - avg_buy_price) * cycle_qty
                    pnl_percent = ((sell_price - avg_buy_price) / avg_buy_price) * 100
                    duration = sell_ts - first_buy_ts
                    
                    duration_secs = int(duration.total_seconds())
                    if duration_secs < 60:
                        dur_str = f"{duration_secs}s"
                    elif duration_secs < 3600:
                        dur_str = f"{duration_secs // 60}m {duration_secs % 60}s"
                    else:
                        dur_str = f"{duration_secs // 3600}h {(duration_secs % 3600) // 60}m"
                        
                    realized_trades.append({
                        "pair": pair,
                        "buy_price": avg_buy_price,
                        "sell_price": sell_price,
                        "pnl": trade_pnl,
                        "pnl_percent": pnl_percent,
                        "timestamp": row['timestamp'],
                        "buy_timestamp": first_buy_ts.strftime('%Y-%m-%d %H:%M:%S'),
                        "duration": dur_str,
                        "duration_secs": duration_secs
                    })

    # Filter for trades completed in the last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    last_24h_completed_trades = [
        t for t in realized_trades 
        if datetime.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S') > yesterday
    ]
    
    pnl = sum([t['pnl'] for t in last_24h_completed_trades])

    # Sort and pick best/worst from last 24h completed trades
    completed_df = pd.DataFrame(last_24h_completed_trades)
    best_trade = None
    worst_trade = None
    if not completed_df.empty:
        best_trade = completed_df.loc[completed_df['pnl_percent'].idxmax()].to_dict()
        worst_trade = completed_df.loc[completed_df['pnl_percent'].idxmin()].to_dict()

    # Get last 24h failed trades
    yesterday_str = yesterday.strftime('%Y-%m-%d %H:%M:%S')
    failed_df = pd.read_sql_query(f"SELECT * FROM failed_trades WHERE timestamp > '{yesterday_str}'", conn)
    
    # Get total trades (buys + sells) in the last 24h for reporting count
    trades_count_df = pd.read_sql_query(f"SELECT * FROM trades WHERE timestamp > '{yesterday_str}'", conn)

    report = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "total_trades": len(trades_count_df),
        "failed_trades_count": len(failed_df),
        "total_realized_pnl": pnl,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "completed_trades": last_24h_completed_trades,
        "failures": failed_df.to_dict(orient='records')
    }
    
    with open('daily_report.json', 'w') as f:
        json.dump(report, f, indent=4)
    
    conn.close()

if __name__ == "__main__":
    export_report()
