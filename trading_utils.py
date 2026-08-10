import sqlite3
import pandas as pd
import os
from datetime import datetime
from binance import Client
from dotenv import load_dotenv

load_dotenv()

def get_binance_client():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    return Client(api_key, api_secret)

def init_db(db_path='trading_bot.db'):
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT,
            side TEXT,
            price REAL,
            quantity REAL,
            fee REAL DEFAULT 0,
            fee_asset TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            config_snapshot TEXT DEFAULT NULL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN config_snapshot TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS failed_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT,
            error TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_pnl (
            date TEXT PRIMARY KEY,
            pnl REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_trade(pair, side, price, quantity, fee=0, fee_asset=None, config_snapshot=None, db_path='trading_bot.db'):
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO trades (pair, side, price, quantity, fee, fee_asset, config_snapshot) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (pair, side, price, quantity, fee, fee_asset, config_snapshot))
    conn.commit()
    conn.close()

def log_failed_trade(pair, error, db_path='trading_bot.db'):
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO failed_trades (pair, error) VALUES (?, ?)', (pair, error))
    conn.commit()
    conn.close()

def humanize_time(timestamp_str):
    try:
        from datetime import timezone
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60: return "just now"
        if seconds < 3600: return f"{int(seconds // 60)}m ago"
        if seconds < 86400: return f"{int(seconds // 3600)}h ago"
        return f"{diff.days}d ago"
    except:
        return timestamp_str

def get_trade_data(db_path='trading_bot.db', limit=None):
    conn = sqlite3.connect(db_path, timeout=30.0)
    if limit:
        trades_df = pd.read_sql_query(f"SELECT * FROM trades ORDER BY timestamp DESC LIMIT {limit}", conn)
    else:
        trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    conn.close()
    return trades_df

def calculate_detailed_pnl(df, client=None):
    if df.empty: return 0.0, 0.0, []
    
    # Ensure dataframe is sorted by timestamp for PnL calculation
    df = df.sort_values('timestamp', ascending=True)
    
    realized_pnl = 0.0
    total_fees_usdt = 0.0
    open_positions = {}
    
    if client is None:
        client = get_binance_client()

    try:
        bnb_price = float(client.get_symbol_ticker(symbol="BNBUSDT")['price'])
    except:
        bnb_price = 600.0

    for _, row in df.iterrows():
        fee = row.get('fee') or 0
        fee_asset = row.get('fee_asset') or 'USDT'
        if fee_asset == 'BNB': fee_in_usdt = fee * bnb_price
        elif fee_asset != 'USDT' and fee_asset: fee_in_usdt = fee * row['price']
        else: fee_in_usdt = fee
        
        # Sane cap on fee (max 1% of trade value) to prevent commission asset logging bugs
        # from inflating PnL with phantom fees (e.g. cheap altcoin fee qty multiplied by BNB price).
        trade_val = row['price'] * row['quantity']
        fee_in_usdt = min(fee_in_usdt, trade_val * 0.01)
        
        total_fees_usdt += fee_in_usdt

        val = row['price'] * row['quantity']
        pair = row['pair']
        asset = pair.replace('USDT', '')
        
        if row['side'] == 'BUY':
            if pair not in open_positions: open_positions[pair] = {'qty': 0.0, 'cost': 0.0}
            qty_inc = row['quantity']
            if fee_asset == asset:
                qty_inc -= fee
            open_positions[pair]['qty'] += qty_inc
            open_positions[pair]['cost'] += val
        else:
            if pair in open_positions:
                cost_per_unit = open_positions[pair]['cost'] / open_positions[pair]['qty'] if open_positions[pair]['qty'] > 0 else 0
                qty_dec = row['quantity']
                if fee_asset == asset:
                    qty_dec += fee # If fee was taken from asset during sell (uncommon)
                
                qty_to_remove = min(qty_dec, open_positions[pair]['qty'])
                cost_of_sold_qty = cost_per_unit * qty_to_remove
                realized_pnl += (row['price'] * qty_to_remove - cost_of_sold_qty)
                open_positions[pair]['qty'] -= qty_to_remove
                open_positions[pair]['cost'] -= cost_of_sold_qty
                if open_positions[pair]['qty'] <= 0.0001: del open_positions[pair]

    unrealized_pnl = 0.0
    current_positions_data = []
    if open_positions:
        try:
            # Reconcile with actual Binance balances if client is provided
            if client:
                acc = client.get_account()
                actual_balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
                
                pairs_to_remove = []
                for pair in open_positions:
                    asset = pair.replace('USDT', '')
                    if asset not in actual_balances:
                        pairs_to_remove.append(pair)
                    else:
                        # Ensure we don't report more than we actually have
                        actual_qty = actual_balances[asset]
                        if open_positions[pair]['qty'] > actual_qty:
                            fraction = actual_qty / open_positions[pair]['qty']
                            open_positions[pair]['cost'] *= fraction
                            open_positions[pair]['qty'] = actual_qty
                
                for p in pairs_to_remove:
                    del open_positions[p]

            prices = client.get_all_tickers() if client else []
            price_map = {p['symbol']: float(p['price']) for p in prices}
            for pair, data in open_positions.items():
                if data['qty'] > 0:
                    current_price = price_map.get(pair, 0.0)
                    market_value = current_price * data['qty']
                    
                    # Skip tiny dust positions (less than $0.50)
                    if market_value < 0.50:
                        continue
                        
                    u_pnl = market_value - data['cost']
                    unrealized_pnl += u_pnl
                    current_positions_data.append({
                        'pair': pair, 
                        'qty': data['qty'], 
                        'cost': data['cost'], 
                        'value': market_value, 
                        'pnl': u_pnl
                    })
        except Exception as e:
            print(f"Error fetching prices or balances: {e}")

    return realized_pnl - total_fees_usdt, unrealized_pnl, current_positions_data
