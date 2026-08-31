import json
import os
import sqlite3
from blessed import Terminal

def main():
    term = Terminal()
    print(term.home + term.clear)
    print(term.bold_yellow("    👀 Asset Tracking Dashboard"))
    print(term.bold_yellow("    ═══════════════════════════\n"))
    
    # 1. Read Restricted Pairs
    restricted = []
    if os.path.exists('/root/restricted_pairs.json'):
        try:
            with open('/root/restricted_pairs.json', 'r') as f:
                restricted = json.load(f)
        except: pass
        
    print(term.bold_red("  [ Blacklisted Pairs ]"))
    if restricted:
        for i in range(0, len(restricted), 5):
            print("    " + ", ".join(restricted[i:i+5]))
    else:
        print("    None")
    print("\n")
    
    # 2. Read Active Positions
    active = {}
    if os.path.exists('/root/active_positions.json'):
        try:
            with open('/root/active_positions.json', 'r') as f:
                active = json.load(f).get('active_positions', {})
        except: pass
    
    # Fallback to DB if empty
    if not active and os.path.exists('/root/trading_bot.db'):
        try:
            conn = sqlite3.connect('/root/trading_bot.db')
            cursor = conn.cursor()
            cursor.execute("SELECT pair, price, timestamp FROM active_trades")
            for r in cursor.fetchall():
                active[r[0]] = {"entry_price": r[1], "entry_time": r[2]}
            conn.close()
        except: pass
        
    print(term.bold_green("  [ Active Positions ]"))
    if active:
        from datetime import datetime
        for pair, data in active.items():
            entry_price = data.get('entry_price', 'Unknown')
            t_val = data.get('time', 'Unknown')
            if isinstance(t_val, (int, float)):
                t_str = datetime.fromtimestamp(t_val).strftime('%Y-%m-%d %H:%M:%S')
            else:
                t_str = str(t_val)
            print(f"    {term.bold(pair)}: Entry @ {entry_price} (Time: {t_str})")
    else:
        print("    No active positions.")
        
    # 3. Read Tracked Pairs
    tracked = []
    if os.path.exists('/root/tracked_pairs.json'):
        try:
            with open('/root/tracked_pairs.json', 'r') as f:
                tracked = json.load(f).get('tracked', [])
        except: pass
        
    print("\n" + term.bold_cyan(f"  [ Tradable Assets / Tracked Universe ({len(tracked)}) ]"))
    if tracked:
        for i in range(0, len(tracked), 8):
            print("    " + ", ".join(tracked[i:i+8]))
    else:
        print("    None or bot is still initializing.")
        
    print("\n\n" + term.red("Press any key to return..."))
    term.inkey()

if __name__ == "__main__":
    main()
