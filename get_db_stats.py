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
                duration = ts - first_buy_ts
                cycles.append({
                    'pair': pair,
                    'pnl': pnl,
                    'pnl_pct': pct,
                    'duration_hours': duration.total_seconds() / 3600.0,
                    'buy_ts': first_buy_ts,
                    'sell_ts': ts
                })
                
    cycles_df = pd.DataFrame(cycles)
    
    summary = []
    
    def format_stats_section(df, title):
        lines = []
        lines.append(f"=== {title} ===")
        if df.empty:
            lines.append("No completed trades in this period.")
            return lines
            
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] <= 0]
        
        total = len(df)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total > 0 else 0
        avg_win_pct = wins['pnl_pct'].mean() if win_count > 0 else 0
        avg_loss_pct = losses['pnl_pct'].mean() if loss_count > 0 else 0
        wl_ratio = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else 0
        avg_hold_hours = df['duration_hours'].mean()
        
        lines.append(f"Total Completed Cycles: {total}")
        lines.append(f"Wins: {win_count} | Losses: {loss_count}")
        lines.append(f"Win Rate: {win_rate:.2f}%")
        lines.append(f"Average Win: +{avg_win_pct:.2f}%")
        lines.append(f"Average Loss: {avg_loss_pct:.2f}%")
        lines.append(f"Win/Loss Ratio: {wl_ratio:.2f}")
        lines.append(f"Average Holding Time: {avg_hold_hours:.2f} hours")
        
        lines.append("\nWinning Trades Profit Distribution:")
        lines.append(f"  Profit <= 0.5% (Tiny profits/breakeven): {len(wins[wins['pnl_pct'] <= 0.5])} trades")
        lines.append(f"  Profit > 0.5% and <= 1.5%: {len(wins[(wins['pnl_pct'] > 0.5) & (wins['pnl_pct'] <= 1.5)])} trades")
        lines.append(f"  Profit > 1.5% and <= 3.0%: {len(wins[(wins['pnl_pct'] > 1.5) & (wins['pnl_pct'] <= 3.0)])} trades")
        lines.append(f"  Profit > 3.0%: {len(wins[wins['pnl_pct'] > 3.0])} trades")
        
        lines.append("\nLosing Trades Loss Distribution:")
        lines.append(f"  Loss >= -0.5%: {len(losses[losses['pnl_pct'] >= -0.5])} trades")
        lines.append(f"  Loss < -0.5% and >= -1.5%: {len(losses[(losses['pnl_pct'] < -0.5) & (losses['pnl_pct'] >= -1.5)])} trades")
        lines.append(f"  Loss < -1.5% and >= -3.0%: {len(losses[(losses['pnl_pct'] < -1.5) & (losses['pnl_pct'] >= -3.0)])} trades")
        lines.append(f"  Loss < -3.0%: {len(losses[losses['pnl_pct'] < -3.0])} trades")
        
        lines.append("\nWorst Performing Symbols by Total PnL:")
        worst = df.groupby('pair')['pnl'].sum().sort_values(ascending=True).head(5)
        for pair, pnl_val in worst.items():
            lines.append(f"  {pair}: {pnl_val:.2f} USDT")
            
        lines.append("\nBest Performing Symbols by Total PnL:")
        best = df.groupby('pair')['pnl'].sum().sort_values(ascending=False).head(5)
        for pair, pnl_val in best.items():
            lines.append(f"  {pair}: +{pnl_val:.2f} USDT")
            
        return lines

    if not cycles_df.empty:
        # Last 30 Days
        last_30d = datetime.now() - timedelta(days=30)
        recent_cycles = cycles_df[cycles_df['sell_ts'] > last_30d]
        summary.extend(format_stats_section(recent_cycles, "Long-Term Database Trade Statistics (Last 30 Days)"))
        
        summary.append("\n" + "="*50 + "\n")
        
        # All-time
        summary.extend(format_stats_section(cycles_df, "All-Time Database Trade Statistics (Since May 5, 2026)"))
    else:
        summary.append("No completed trades in the database yet.")
        
    conn.close()
    
    with open('/root/db_stats_summary.txt', 'w') as f:
        f.write("\n".join(summary))

if __name__ == '__main__':
    get_stats()
