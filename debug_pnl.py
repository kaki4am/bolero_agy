
import sqlite3
import pandas as pd

def check():
    conn = sqlite3.connect('trading_bot.db')
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()

    bnb_price = 600.0 # Approximate
    
    realized_pnl = 0.0
    total_fees = 0.0
    open_positions = {}

    for i, row in df.iterrows():
        fee = row.get('fee') or 0.0
        asset = row.get('fee_asset') or 'USDT'
        
        fee_usdt = 0
        if asset == 'BNB': fee_usdt = fee * bnb_price
        elif asset == 'USDT' or not asset: fee_usdt = fee
        else:
            # For other assets, use trade price as approximation
            fee_usdt = fee * row['price']
        
        total_fees += fee_usdt
        
        val = row['price'] * row['quantity']
        pair = row['pair']
        
        if row['side'] == 'BUY':
            if pair not in open_positions: open_positions[pair] = {'qty': 0.0, 'cost': 0.0}
            open_positions[pair]['qty'] += row['quantity']
            open_positions[pair]['cost'] += val
        else:
            if pair in open_positions and open_positions[pair]['qty'] > 0:
                cost_per_unit = open_positions[pair]['cost'] / open_positions[pair]['qty']
                qty_sold = min(row['quantity'], open_positions[pair]['qty'])
                cost_of_sold = cost_per_unit * qty_sold
                realized_pnl += (row['price'] * qty_sold - cost_of_sold)
                
                open_positions[pair]['qty'] -= qty_sold
                open_positions[pair]['cost'] -= cost_of_sold
            else:
                print(f"Warning: SELL without BUY for {pair} at trade {row['id']}")
                
        if fee_usdt > 1.0:
            print(f"High fee detected: Trade {row['id']}, {row['pair']} {row['side']}, Fee: {fee} {asset} ({fee_usdt:.2f} USDT)")

    print("\nSummary:")
    print(f"Gross Realized PnL: {realized_pnl:.2f}")
    print(f"Total Fees: {total_fees:.2f}")
    print(f"Net Realized PnL: {realized_pnl - total_fees:.2f}")
    
    print("\nOpen Positions PnL (Estimated at last trade price):")
    # This is just to see what the bot thinks
    for pair, pos in open_positions.items():
        if pos['qty'] > 0.000001:
            last_price = df[df['pair'] == pair]['price'].iloc[-1]
            u_pnl = (last_price * pos['qty']) - pos['cost']
            print(f"{pair}: Qty {pos['qty']:.6f}, Cost {pos['cost']:.2f}, Last Price {last_price}, Unrealized {u_pnl:.2f}")

if __name__ == "__main__":
    check()
