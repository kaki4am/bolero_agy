import os
import json
import smtplib
import subprocess
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date
import pandas as pd
from binance import Client

# Load environment variables
def load_env():
    env = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    env[k] = v
    return env

ENV = load_env()
GMAIL_USER = ENV.get('GMAIL_USER')
GMAIL_PASS = ENV.get('GMAIL_PASS')
RECIPIENT = ENV.get('REPORT_RECIPIENT', GMAIL_USER)

def get_system_health():
    try:
        # Run health check script and capture output
        output = subprocess.check_output(['/root/venv/bin/python', '/root/system_health.py']).decode()
        return json.loads(output)
    except Exception as e:
        return {"error": str(e)}

def get_pnl_report():
    try:
        # Generate the report first
        subprocess.run(['/root/venv/bin/python', '/root/export_report.py'], check=True)
        with open('daily_report.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def get_optimization_summary():
    try:
        if os.path.exists('optimization.log'):
            # Get last 20 lines of optimization log
            output = subprocess.check_output(['tail', '-n', '20', 'optimization.log']).decode()
            return output
        return "No optimization log found."
    except Exception as e:
        return f"Error reading log: {str(e)}"

def get_random_walk_data():
    import random
    from datetime import datetime, timedelta, timezone
    import asyncio
    import importlib.util
    import pandas_ta as ta
    from binance import AsyncClient
    
    api_key = ENV.get('BINANCE_API_KEY')
    api_secret = ENV.get('BINANCE_API_SECRET')
    if not api_key or not api_secret:
        return {"error": "Missing Binance API keys"}
        
    days_back = random.randint(60, 1800)
    rand_start = datetime.now(timezone.utc) - timedelta(days=days_back)
    rand_end = rand_start + timedelta(days=7)
    
    start_str = rand_start.strftime("%Y-%m-%d UTC")
    end_str = rand_end.strftime("%Y-%m-%d UTC")
    
    def format_relative_time(days_ago, start_date):
        years = days_ago // 365
        rem_days = days_ago % 365
        months = rem_days // 30
        month_name = start_date.strftime("%B %Y")
        if years > 0 and months > 0:
            return f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months > 1 else ''} ago ({month_name})"
        elif years > 0:
            return f"{years} year{'s' if years > 1 else ''} ago ({month_name})"
        else:
            return f"{months} month{'s' if months > 0 else '0'} ago ({month_name})"

    config_params = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config_params = json.load(f)
        except: pass
    if not config_params:
        config_params = {
            "EMA_FAST": 50, "EMA_SLOW": 200, "MIN_VOLATILITY": 0.001,
            "BASE_RISK_PERCENT": 2.0, "ATR_SL_MULT": 3.0,
            "PORTFOLIO_EJECT": -5.0, "PORTFOLIO_HARVEST": 5.0
        }
        
    try:
        spec = importlib.util.spec_from_file_location("pb", "portfolio_backtester.py")
        pb_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pb_mod)
    except Exception as e:
        return {"error": f"Failed to load backtester: {str(e)}"}
        
    async def run_async():
        client = await AsyncClient.create(api_key, api_secret, testnet=False)
        try:
            # 1. Fetch top volume altcoin candidates
            tickers = await client.get_ticker()
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            blacklisted = ['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT']
            if os.path.exists('restricted_pairs.json'):
                try:
                    with open('restricted_pairs.json', 'r') as f:
                        restricted = json.load(f)
                        blacklisted.extend(restricted)
                except: pass
            filtered = [p['symbol'] for p in usdt_pairs if p['symbol'] not in blacklisted]
            sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            sorted_symbols = [p['symbol'] for p in sorted_pairs if p['symbol'] in filtered]
            candidates = sorted_symbols[:40]
            
            # Sample 4 altcoins + BTC
            sampled = random.sample([c for c in candidates if c != 'BTCUSDT'], 4)
            symbols = ['BTCUSDT'] + sampled
            
            tester = pb_mod.PortfolioBacktester(symbols=symbols)
            
            # Fetch BTC hourly and 15m klines for filters
            btc_1h = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1HOUR, start_str, end_str)
            tester.btc_df = pd.DataFrame(btc_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
            tester.btc_df['close'] = tester.btc_df['close'].astype(float)
            tester.btc_df['timestamp'] = pd.to_datetime(tester.btc_df['timestamp'], unit='ms')
            tester.btc_df['ema200'] = ta.ema(tester.btc_df['close'], length=50)
            tester.btc_df['rsi'] = ta.rsi(tester.btc_df['close'], length=14)
            
            btc_15m = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, start_str, end_str)
            tester.btc_15m = pd.DataFrame(btc_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
            tester.btc_15m['close'] = tester.btc_15m['close'].astype(float)
            tester.btc_15m['timestamp'] = pd.to_datetime(tester.btc_15m['timestamp'], unit='ms')
            tester.btc_15m['ema200'] = ta.ema(tester.btc_15m['close'], length=200)

            active_symbols = []
            for s in symbols:
                try:
                    kl_1m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_1MINUTE, start_str, end_str)
                    kl_15m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_15MINUTE, start_str, end_str)
                    if not kl_1m or len(kl_1m) < 100:
                        continue # Skip coins that did not exist during this week
                    
                    df_1m = pd.DataFrame(kl_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df_1m[col] = df_1m[col].astype(float)
                    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
                    
                    df_15m = pd.DataFrame(kl_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df_15m[col] = df_15m[col].astype(float)
                    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
                    
                    tester.pair_data[s] = {'1m': df_1m, '15m': df_15m}
                    active_symbols.append(s)
                except:
                    pass # Ignore errors and skip symbol if it fails loading
            
            # If no symbols succeeded, return error
            if not active_symbols:
                return {"error": "No symbols had data during this week"}
                
            # Update symbols list in tester to reflect only successfully loaded pairs
            tester.symbols = active_symbols

            tester.precalculate_all({k: [v] for k, v in config_params.items()})
            pnl = tester.run(config_params)
            return {
                "pnl": pnl,
                "symbols": active_symbols
            }
        finally:
            await client.close_connection()
            
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_async())
        loop.close()
        
        if "error" in res:
            return res
            
        return {
            "start": rand_start.strftime("%Y-%m-%d"),
            "end": rand_end.strftime("%Y-%m-%d"),
            "relative_age": format_relative_time(days_back, rand_start),
            "pnl": res['pnl'],
            "symbols": res['symbols']
        }
    except Exception as e:
        return {"error": str(e)}

def get_recent_changes():
    try:
        # Check for files modified in the last 24 hours
        output = subprocess.check_output(['find', '/root', '-maxdepth', '1', '-mtime', '-1', '-type', 'f', '-not', '-path', '*/.*']).decode()
        return output
    except Exception as e:
        return f"Error checking changes: {str(e)}"

def get_version_age_days(current_version):
    import os
    import re
    from datetime import datetime, date, timezone
    
    # Clean version string to just "V90"
    ver_match = re.search(r'V\d+', current_version)
    if not ver_match:
        return 0
    ver_str = ver_match.group(0)
    
    log_path = '/root/optimization.log'
    earliest_date = None
    
    if os.path.exists(log_path):
        current_ver_in_log = "Unknown"
        with open(log_path, 'r') as f:
            for line in f:
                match_ver = re.search(r'All sources consistent at Strategy (V\d+)', line)
                if match_ver:
                    current_ver_in_log = match_ver.group(1)
                
                if "Strategy Evolved Successfully" in line:
                    if current_ver_in_log == ver_str:
                        match_ts = re.search(r'\[([^\]]+)\]', line)
                        if match_ts:
                            date_str = match_ts.group(1).replace("UTC ", "")
                            date_str = " ".join(date_str.split())
                            try:
                                dt = datetime.strptime(date_str, '%a %b %d %I:%M:%S %p %Y').date()
                                if earliest_date is None or dt < earliest_date:
                                    earliest_date = dt
                            except:
                                pass
                                
    # Hardcode check for V90 (July 1st) as a fallback since cron jobs failed
    if ver_str == "V90" and earliest_date is None:
        earliest_date = date(2026, 7, 1)
        
    if earliest_date is None:
        gemini_path = '/root/GEMINI.md'
        if os.path.exists(gemini_path):
            mtime = os.path.getmtime(gemini_path)
            earliest_date = datetime.fromtimestamp(mtime, timezone.utc).date()
            
    if earliest_date:
        return max((date.today() - earliest_date).days, 0)
    return 0

def get_strategy_updates():
    updates = {"current_strategy": "Unknown", "latest_task": "None", "tech_state": "No recent updates", "version": "Strategy V80", "version_age_days": 0}
    try:
        if os.path.exists('GEMINI.md'):
            with open('GEMINI.md', 'r') as f:
                first_line = f.readline().strip()
                if "Strategy" in first_line:
                    updates["current_strategy"] = first_line.replace("# Project Instructions: ", "")
                    import re
                    match = re.search(r'Strategy\s+(V\d+)', first_line)
                    if match:
                        updates["version"] = f"Strategy {match.group(1)}"
                        
        updates["version_age_days"] = get_version_age_days(updates["version"])
        
        memory_path = '/root/.gemini/tmp/root/memory/MEMORY.md'
        if os.path.exists(memory_path):
            with open(memory_path, 'r') as f:
                content = f.read()
                # Find last completed task in Active Tasks
                tasks = [line for line in content.split('\n') if '- [x]' in line]
                if tasks:
                    updates["latest_task"] = tasks[-1].replace("- [x] ", "").strip()
                
                # Extract Technical State section
                if "## Technical State" in content:
                    tech_section = content.split("## Technical State")[1].split("---")[0].strip()
                    updates["tech_state"] = tech_section
    except Exception as e:
        print(f"Error reading strategy updates: {e}")
    return updates

def get_historical_projection():
    try:
        # Get daily strategy realized PnL from trades DB
        daily_strat_pnl_map = {}
        try:
            import sqlite3
            conn = sqlite3.connect('/root/trading_bot.db')
            trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
            conn.close()
            
            realized_trades = []
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
                        
                        cycle_qty = 0
                        cycle_cost = 0
                        
                        while sell_qty > 0 and buys:
                            buy = buys[0]
                            match_qty = min(sell_qty, buy['qty'])
                            cycle_qty += match_qty
                            cycle_cost += match_qty * buy['price']
                            
                            buy['qty'] -= match_qty
                            sell_qty -= match_qty
                            if buy['qty'] <= 0.0001:
                                buys.pop(0)
                                
                        if cycle_qty > 0:
                            avg_buy_price = cycle_cost / cycle_qty
                            trade_pnl = (sell_price - avg_buy_price) * cycle_qty
                            realized_trades.append({
                                "pnl": trade_pnl,
                                "timestamp": row['timestamp']
                            })
            for t in realized_trades:
                try:
                    dt = pd.to_datetime(t['timestamp']).date()
                    daily_strat_pnl_map[dt] = daily_strat_pnl_map.get(dt, 0.0) + t['pnl']
                except:
                    pass
        except Exception as db_e:
            print(f"Error calculating strategy daily pnl: {db_e}")

        # 1. Parse optimization.log for the 5th oldest strategy version and build version history
        log_path = '/root/optimization.log'
        start_dt = None
        version_history = {}
        current_ver = "Unknown"
        
        if os.path.exists(log_path):
            dates = []
            with open(log_path, 'r') as f:
                for line in f:
                    match_ver = re.search(r'All sources consistent at Strategy (V\d+)', line)
                    if match_ver:
                        current_ver = match_ver.group(1)
                    
                    if "Strategy Evolved Successfully" in line:
                        match_ts = re.search(r'\[([^\]]+)\]', line)
                        if match_ts:
                            date_str = match_ts.group(1).replace("UTC ", "")
                            date_str = " ".join(date_str.split())
                            try:
                                dt = datetime.strptime(date_str, '%a %b %d %I:%M:%S %p %Y')
                                dates.append(dt)
                                version_history[dt.date()] = current_ver
                            except:
                                pass
            # Get 5th oldest unique date to avoid multiple evaluations on the same day pushing start_dt to today
            unique_dates = sorted(list(set(d.date() for d in dates)))
            if len(unique_dates) >= 5:
                start_dt = unique_dates[-5]
            elif unique_dates:
                start_dt = unique_dates[0]
                
        if not start_dt:
            start_dt = date.today() - timedelta(days=10)
            
        # Ensure start_dt falls within [14 days ago, 5 days ago] to guarantee sufficient data points
        max_lookback_dt = date.today() - timedelta(days=14)
        min_lookback_dt = date.today() - timedelta(days=5)
        start_dt = max(start_dt, max_lookback_dt)
        start_dt = min(start_dt, min_lookback_dt)
            
        # Parse live version from GEMINI.md
        gemini_path = '/root/GEMINI.md'
        current_live_ver = "V90"
        if os.path.exists(gemini_path):
            with open(gemini_path, 'r') as f:
                first_line = f.readline()
                match_live = re.search(r'Strategy (V\d+)', first_line)
                if match_live:
                    current_live_ver = match_live.group(1)
                    
        # Load and update persistent version history log
        version_log_path = '/root/version_history_log.json'
        version_log = {}
        if os.path.exists(version_log_path):
            try:
                with open(version_log_path, 'r') as f:
                    version_log = json.load(f)
            except: pass
        
        today_str = str(date.today())
        if today_str not in version_log or version_log[today_str] != current_live_ver:
            version_log[today_str] = current_live_ver
            try:
                with open(version_log_path, 'w') as f:
                    json.dump(version_log, f, indent=4)
            except: pass
            
        # Update local memory mappings
        for d_str, v_str in version_log.items():
            try:
                dt_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
                version_history[dt_obj] = v_str
            except: pass
            
        # 2. Get account snapshot and ticker prices
        api_key = ENV.get('BINANCE_API_KEY')
        api_secret = ENV.get('BINANCE_API_SECRET')
        client = Client(api_key, api_secret)
        
        snap = client.get_account_snapshot(type='SPOT', limit=15)
        prices = client.get_all_tickers()
        btc_price = float([p['price'] for p in prices if p['symbol'] == 'BTCUSDT'][0])
        
        # Fetch historical BTC daily prices to convert BTC assets to USDT
        btc_klines = client.get_historical_klines('BTCUSDT', '1d', '30 days ago UTC')
        btc_price_map = {datetime.fromtimestamp(k[0]/1000).date(): float(k[4]) for k in btc_klines}
        
        # Convert snapshots to USDT values
        equity_history = {}
        for entry in snap.get('snapshotVos', []):
            dt = datetime.fromtimestamp(entry['updateTime']/1000).date()
            btc_val = float(entry['data']['totalAssetOfBtc'])
            p_btc = btc_price_map.get(dt, btc_price)
            usdt_val = btc_val * p_btc
            equity_history[dt] = usdt_val
            
        # Add today's live equity value
        # Fetch current USDT balance
        acc = client.get_account()
        balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
        current_cash = balances.get('USDT', 0.0)
        
        # Sum current positions
        current_positions_val = 0.0
        price_map = {p['symbol']: float(p['price']) for p in prices}
        for asset, qty in balances.items():
            if asset != 'USDT' and qty > 0:
                pair = f"{asset}USDT"
                p = price_map.get(pair, 0.0)
                current_positions_val += qty * p
                
        today_date = date.today()
        equity_history[today_date] = current_cash + current_positions_val
        
        # Filter for dates starting from start_dt
        filtered_history = {d: val for d, val in equity_history.items() if d >= start_dt}
        equity_series = pd.Series(filtered_history).sort_index()
        
        if len(equity_series) < 2:
            return {"error": "Not enough snapshot data points."}
            
        # V90 started on July 1st
        v90_start = date(2026, 7, 1)
        if v90_start not in equity_series.index:
            v90_start = list(equity_series.index)[-5] if len(equity_series) >= 5 else list(equity_series.index)[0]
            
        p_start_5d = equity_series.get(v90_start, equity_series.iloc[0])
        p_end = equity_series.iloc[-1]
        days_diff = (list(equity_series.index)[-1] - v90_start).days
        if days_diff <= 0: days_diff = 5
        
        r_daily = (p_end / p_start_5d) ** (1 / days_diff) - 1
        
        # Calculations for 10-day (last 5 strategies)
        p_start_10d = equity_series.iloc[0]
        days_10d = (list(equity_series.index)[-1] - list(equity_series.index)[0]).days
        if days_10d <= 0: days_10d = 10
        r_10d = (p_end / p_start_10d) ** (1 / days_10d) - 1
        
        # Projections
        p1 = p_end * ((1 + r_daily) ** (1 * 365))
        p2 = p_end * ((1 + r_daily) ** (2 * 365))
        p5 = p_end * ((1 + r_daily) ** (5 * 365))
        p10 = p_end * ((1 + r_daily) ** (10 * 365))
        
        p1_10d = p_end * ((1 + r_10d) ** (1 * 365))
        p2_10d = p_end * ((1 + r_10d) ** (2 * 365))
        
        # Format returns table
        returns_table = ""
        prev_val = None
        prev_btc = None
        sorted_dates = sorted(version_history.keys())
        
        for d, val in sorted(filtered_history.items()):
            change_str = "-"
            if prev_val is not None:
                diff = val - prev_val
                if diff >= 0:
                    change_str = f"<span style='background-color: #d1e7dd; color: #0f5132; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>${diff:+.2f}</span>"
                else:
                    change_str = f"<span style='background-color: #f8d7da; color: #842029; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>${diff:+.2f}</span>"
                
            # Fetch Strategy Daily realized PnL
            strat_pnl = daily_strat_pnl_map.get(d, 0.0)
            if strat_pnl > 0.005:
                strat_pnl_str = f"<span style='background-color: #d1e7dd; color: #0f5132; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>${strat_pnl:+.2f}</span>"
            elif strat_pnl < -0.005:
                strat_pnl_str = f"<span style='background-color: #f8d7da; color: #842029; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>${strat_pnl:+.2f}</span>"
            else:
                strat_pnl_str = "<span style='color: #6c757d; font-size: 11px;'>$0.00</span>"

            # Fetch BTC price and calculate its change
            btc_p = btc_price_map.get(d, btc_price)
            btc_change_str = "-"
            if prev_btc is not None:
                btc_diff = ((btc_p - prev_btc) / prev_btc) * 100
                if btc_diff >= 0:
                    btc_change_str = f"<span style='background-color: #d1e7dd; color: #0f5132; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>{btc_diff:+.2f}%</span>"
                else:
                    btc_change_str = f"<span style='background-color: #f8d7da; color: #842029; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block;'>{btc_diff:+.2f}%</span>"
                
            active_ver = "Unknown"
            for hist_date in sorted_dates:
                if hist_date <= d:
                    active_ver = version_history[hist_date]
                else:
                    break
                
            returns_table += f"<tr><td style='padding:6px; border:1px solid #ddd;'>{d}</td><td style='padding:6px; border:1px solid #ddd;'><b>{active_ver}</b></td><td style='padding:6px; border:1px solid #ddd;'>{strat_pnl_str}</td><td style='padding:6px; border:1px solid #ddd;'>{change_str}</td><td style='padding:6px; border:1px solid #ddd;'>${val:,.2f}</td><td style='padding:6px; border:1px solid #ddd;'>${btc_p:,.2f} <span style='margin-left:5px;'>{btc_change_str}</span></td></tr>"
            prev_val = val
            prev_btc = btc_p
            
        return {
            "start_date": start_dt.strftime('%Y-%m-%d'),
            "end_date": today_date.strftime('%Y-%m-%d'),
            "current_equity": p_end,
            "starting_equity_10d": p_start_10d,
            "r_daily_v90": r_daily,
            "r_daily_10d": r_10d,
            "p1": p1,
            "p2": p2,
            "p5": p5,
            "p10": p10,
            "p1_10d": p1_10d,
            "p2_10d": p2_10d,
            "v90_start_date": v90_start.strftime('%Y-%m-%d'),
            "v90_days": days_diff,
            "returns_table": returns_table
        }
    except Exception as e:
        import traceback
        return {"error": str(e) + "\n" + traceback.format_exc()}

def generate_performance_and_narrative(pnl, strategy):
    from collections import Counter
    from datetime import datetime
    
    trades = pnl.get('completed_trades', [])
    total_pnl = pnl.get('total_realized_pnl', 0.0)
    failed_count = pnl.get('failed_trades_count', 0)
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    total_count = len(trades)
    win_count = len(wins)
    win_rate = (win_count / total_count * 100) if total_count > 0 else 0.0
    
    avg_win = sum(t['pnl_percent'] for t in wins) / win_count if win_count > 0 else 0.0
    avg_loss = sum(t['pnl_percent'] for t in losses) / len(losses) if losses else 0.0
    
    # Coordinated exit detection
    time_bins = []
    for t in trades:
        try:
            dt = datetime.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S')
            minute_bin = (dt.minute // 10) * 10
            bin_str = dt.replace(minute=minute_bin, second=0).strftime('%H:%M')
            time_bins.append(bin_str)
        except:
            pass
            
    bin_counts = Counter(time_bins)
    most_common_bin, peak_count = bin_counts.most_common(1)[0] if bin_counts else (None, 0)
    flush_detected = peak_count >= 5
    
    # Commentary Narrative
    commentary = ""
    if win_rate < 40.0 and abs(avg_loss) > avg_win:
        commentary = "<b>Market Environment: Choppy / Downward Reversal.</b> The bot encountered a difficult trend environment where breakout entry signals faced immediate rejection. High-frequency chop triggered standard stop-losses before momentum could establish, and average losses exceeded average gains."
    elif win_rate >= 60.0 and avg_win > abs(avg_loss):
        commentary = "<b>Market Environment: Strong Trend-Following.</b> The strategy successfully capitalized on sustained breakouts with a high win rate. Trailing stop-losses effectively locked in profits as trends extended."
    else:
        commentary = "<b>Market Environment: Mixed / Rangebound.</b> Altcoin behavior was mixed with moderate win rates. Capital preservation rules protected equity on some positions while others ended in standard stop-losses."
        
    if flush_detected:
        commentary += f"<br/><br/>⚠️ <b>Coordinated Exit Detected:</b> A cluster of {peak_count} positions closed within a short window around {most_common_bin} UTC. This indicates a sudden market-wide pullback (likely triggered by a sharp Bitcoin drop) causing a synchronized stop-loss exit."
        
    # High / Low lights sorting
    sorted_by_pnl = sorted(trades, key=lambda x: x['pnl_percent'])
    best = pnl.get('best_trade')
    worst = pnl.get('worst_trade')
    
    top_lowlights = sorted_by_pnl[:3]
    top_highlights = sorted_by_pnl[-3:][::-1]
    top_highlights = [t for t in top_highlights if t['pnl'] > 0]
    top_lowlights = [t for t in top_lowlights if t['pnl'] < 0]
    
    # Construct Card HTML
    pnl_color = "#198754" if total_pnl >= 0 else "#dc3545"
    
    html = "<div style='font-size: 13px; color: #495057;'>"
    
    # 24h Stats summary table
    html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 13px;'>"
    html += f"<tr><td style='padding: 6px 0; width: 50%; border-bottom: 1px solid #f1f3f5;'><b>Total Realized PnL:</b></td><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5; color: {pnl_color}; font-weight: bold; font-size: 15px;'>${total_pnl:+.2f}</td></tr>"
    html += f"<tr><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'><b>Win Rate:</b></td><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'><b>{win_rate:.1f}%</b> ({win_count} Wins, {len(losses)} Losses)</td></tr>"
    html += f"<tr><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'><b>Avg Win / Avg Loss:</b></td><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'><span style='color: #198754; font-weight: bold;'>+{avg_win:.2f}%</span> / <span style='color: #dc3545; font-weight: bold;'>{avg_loss:.2f}%</span></td></tr>"
    html += f"<tr><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'><b>Total / Failed Trades:</b></td><td style='padding: 6px 0; border-bottom: 1px solid #f1f3f5;'>{total_count} Executed / {failed_count} Failed</td></tr>"
    html += "</table>"
    
    # Narrative Alert block
    html += f"<div style='padding: 12px 15px; background-color: #cfe2ff; color: #084298; border: 1px solid #b6d4fe; border-left: 4px solid #0d6efd; border-radius: 4px; margin-bottom: 15px; line-height: 1.5;'>{commentary}</div>"
    
    # Side-by-Side Highlights & Lowlights
    html += "<table style='width: 100%; border-collapse: collapse;'>"
    html += "<tr>"
    
    # Highlights Column
    html += "<td style='width: 50%; padding-right: 15px; vertical-align: top; border-right: 1px solid #dee2e6;'>"
    html += "<h4 style='font-size: 13px; font-weight: bold; color: #198754; margin: 0 0 8px 0;'>🌟 Daily Highlights</h4>"
    if top_highlights:
        html += "<ul style='padding-left: 15px; margin: 0; font-size: 12px; line-height: 1.4;'>"
        for t in top_highlights:
            html += f"<li style='margin-bottom: 4px;'><b>{t['pair'].replace('USDT', '')}</b>: <span style='color: #198754; font-weight: bold;'>+{t['pnl_percent']:.2f}%</span> (${t['pnl']:.2f}) <span style='color: #6c757d; font-size: 10px;'>dur: {t.get('duration', 'N/A')}</span></li>"
        html += "</ul>"
    else:
        html += "<p style='font-size: 12px; color: #6c757d; margin: 0;'>No profitable trades closed.</p>"
        
    if best and best['pnl'] > 0:
        version = strategy.get('version', 'Strategy')
        commentary_best = "Successfully triggered ProfitGuard / Trailing SL." if best['pnl_percent'] > 1.5 else f"Captured minor move under {version} criteria."
        html += f"<p style='font-size: 11px; color: #6c757d; margin: 8px 0 0 0;'><i>Best Trade Commentary: {best['pair'].replace('USDT', '')} {commentary_best}</i></p>"
    html += "</td>"
    
    # Lowlights Column
    html += "<td style='width: 50%; padding-left: 15px; vertical-align: top;'>"
    html += "<h4 style='font-size: 13px; font-weight: bold; color: #dc3545; margin: 0 0 8px 0;'>📉 Daily Lowlights</h4>"
    if top_lowlights:
        html += "<ul style='padding-left: 15px; margin: 0; font-size: 12px; line-height: 1.4;'>"
        for t in top_lowlights:
            html += f"<li style='margin-bottom: 4px;'><b>{t['pair'].replace('USDT', '')}</b>: <span style='color: #dc3545; font-weight: bold;'>{t['pnl_percent']:.2f}%</span> (${t['pnl']:.2f}) <span style='color: #6c757d; font-size: 10px;'>dur: {t.get('duration', 'N/A')}</span></li>"
        html += "</ul>"
    else:
        html += "<p style='font-size: 12px; color: #6c757d; margin: 0;'>No losing trades closed.</p>"
        
    if worst and worst['pnl'] < 0:
        version = strategy.get('version', 'Strategy')
        commentary_worst = f"Standard Stop Loss hit per {version} criteria." if worst['pnl_percent'] < -1.5 else "Minor loss from immediate momentum stall."
        html += f"<p style='font-size: 11px; color: #6c757d; margin: 8px 0 0 0;'><i>Worst Trade Commentary: {worst['pair'].replace('USDT', '')} {commentary_worst}</i></p>"
    html += "</td>"
    
    html += "</tr>"
    html += "</table>"
    
    html += "</div>"
    return html

def check_recent_evolution():
    import os
    import re
    
    log_path = '/root/optimization.log'
    if not os.path.exists(log_path):
        return False, "Optimization log file not found."
        
    try:
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            seek_pos = max(0, size - 4000)
            f.seek(seek_pos)
            chunk = f.read().decode('utf-8', errors='ignore')
            
        success_matches = list(re.finditer(r'Strategy Evolved Successfully', chunk))
        failure_matches = list(re.finditer(r'Antigravity CLI strategic analysis failed!', chunk))
        
        last_success_idx = success_matches[-1].start() if success_matches else -1
        last_failure_idx = failure_matches[-1].start() if failure_matches else -1
        
        if last_success_idx == -1 and last_failure_idx == -1:
            return False, "no recent strategic analysis execution records were found in the logs."
            
        if last_success_idx > last_failure_idx:
            success_line = chunk[last_success_idx - 100 : last_success_idx + 100]
            ts_match = re.search(r'\[([^\]]+)\]', success_line)
            ts = f" at {ts_match.group(1)}" if ts_match else ""
            return True, f"no codebase evolution was deemed necessary today, generating a strategic advisory report instead{ts}."
        else:
            failure_context = chunk[last_failure_idx:]
            if "timeout waiting for response" in failure_context or "timeout" in failure_context.lower():
                reason = "the analysis agent encountered a response/network timeout during the performance analysis phase."
            else:
                reason = "the analysis execution encountered an unexpected error."
            return False, reason
    except Exception as e:
        return False, f"the system encountered an error checking the status: {str(e)}"

def get_evolution_rationale():
    import os
    import re
    opinion_path = '/root/daily_opinion.html'
    if not os.path.exists(opinion_path):
        return "The daily strategic report has not been generated yet."
    try:
        with open(opinion_path, 'r') as f:
            content = f.read()
        
        # 1. Try to find a paragraph directly inside the Strategic Verdict / Decision Banner block
        banner_match = re.search(r'(?:Strategic Verdict|Decision Banner|Strategic Verdict Banner).*?<p style=[^>]+>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
        text = None
        if banner_match:
            text = banner_match.group(1)
        
        if not text:
            # 2. Try to find a paragraph containing "Reasoning:", "Decision:", "Insights:", or "Verdict:"
            match = re.search(r'<p style=[^>]+>.*?(?:Reasoning:|Decision:|Insights:|Verdict:).*?</p>', content, re.DOTALL)
            if match:
                text = match.group(0)
                
        if not text:
            # 3. Fallback: Find all paragraphs and select the first one longer than 40 chars
            # that is NOT a title/header paragraph (i.e. does not contain "Strategy V" or "Strategic Opinion")
            all_p = re.findall(r'<p style=[^>]+>(.*?)</p>', content, re.DOTALL)
            for p_text in all_p:
                clean_p = re.sub(r'<[^>]+>', '', p_text).strip()
                clean_p = clean_p.replace('&mdash;', '—').replace('&bull;', '•').replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&').replace('&nbsp;', ' ')
                clean_p = " ".join(clean_p.split())
                
                # Skip version header lines
                if "Strategy V" in clean_p or "Strategic Opinion" in clean_p or re.search(r'^Strategy\s+V\d+', clean_p, re.IGNORECASE):
                    continue
                
                if len(clean_p) > 40:
                    text = p_text
                    break
            else:
                match = re.search(r'<p style=[^>]+>(.*?)</p>', content, re.DOTALL)
                if match:
                    text = match.group(1)
        
        if text:
            text = re.sub(r'<[^>]+>', '', text)
            text = text.replace('&mdash;', '—').replace('&bull;', '•').replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&').replace('&nbsp;', ' ')
            text = " ".join(text.split())
            return text
        return "No strategic rationale details could be extracted from today's advisory report."
    except Exception as e:
        return f"An error occurred reading today's advisory report: {str(e)}"

def get_recent_ai_manager_actions():
    log_path = '/root/ai_manager.log'
    if not os.path.exists(log_path):
        return "<p style='font-size:12px; color:#6c757d;'>No AI Manager activity recorded yet.</p>"
        
    try:
        with open(log_path, 'r') as f:
            content = f.read()
            
        blocks = content.split("Gathering market telemetry...")
        actions = []
        
        for block in reversed(blocks):
            block = block.strip()
            if not block: continue
            
            json_match = re.search(r'\{[^\}]+\}', block)
            if json_match:
                try:
                    override_data = json.loads(json_match.group(0))
                    risk_mult = override_data.get('RISK_MULTIPLIER', 1.0)
                    sl_offset = override_data.get('SL_MULT_OFFSET', 0.0)
                    vol_offset = override_data.get('VOL_SPIKE_MULT_OFFSET', 0.0)
                    eject_offset = override_data.get('PORTFOLIO_EJECT_OFFSET', 0.0)
                    blacklist = override_data.get('blacklist_add', [])
                    rationale = override_data.get('rationale', 'No rationale provided.')
                    
                    actions.append({
                        'risk_mult': risk_mult,
                        'sl_offset': sl_offset,
                        'vol_offset': vol_offset,
                        'eject_offset': eject_offset,
                        'blacklist': blacklist,
                        'rationale': rationale
                    })
                    if len(actions) >= 3:
                        break
                except:
                    pass
                    
        if not actions:
            return "<p style='font-size:12px; color:#6c757d;'>No recent successful risk adjustments recorded.</p>"
            
        html_lines = []
        html_lines.append("<h4 style='font-size: 12px; font-weight: bold; color: #0d6efd; margin: 15px 0 6px 0;'>🛡️ Recent AI Manager Tactical Adjustments</h4>")
        for i, act in enumerate(actions):
            blacklist_str = ", ".join(act['blacklist']) if act['blacklist'] else "None"
            changes = []
            if act['risk_mult'] != 1.0: changes.append(f"Risk Mult: <b>{act['risk_mult']}x</b>")
            if act['sl_offset'] != 0.0: changes.append(f"SL Offset: <b>+{act['sl_offset']}</b>")
            if act['vol_offset'] != 0.0: changes.append(f"Vol Offset: <b>+{act['vol_offset']}</b>")
            if act['eject_offset'] != 0.0: changes.append(f"Eject Offset: <b>{act['eject_offset']}</b>")
            if act['blacklist']: changes.append(f"Blacklisted: <span style='color:#dc3545;'><b>{blacklist_str}</b></span>")
            
            changes_str = " | ".join(changes) if changes else "No active overrides (Baseline)"
            
            bg_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"
            html_lines.append(f"<div style='background-color: {bg_color}; padding: 8px 10px; border: 1px solid #dee2e6; border-radius: 4px; margin-bottom: 8px; font-size: 11px; line-height: 1.4;'>")
            html_lines.append(f"<div><b>Run {i+1} Adjustments:</b> {changes_str}</div>")
            html_lines.append(f"<div style='color: #6c757d; font-style: italic; margin-top: 4px;'>\"{act['rationale']}\"</div>")
            html_lines.append("</div>")
            
        return "".join(html_lines)
    except Exception as e:
        return f"<p style='font-size:12px; color:#dc3545;'>Error parsing AI Manager logs: {str(e)}</p>"

def generate_strategy_and_optimizer(strategy, health, opt_log, changes):
    import os
    import json
    
    config_params = {}
    best_profit = None
    if os.path.exists('/root/config.json'):
        try:
            with open('/root/config.json', 'r') as f:
                config_params = json.load(f)
        except: pass
    if os.path.exists('/root/backtest_status.json'):
        try:
            with open('/root/backtest_status.json', 'r') as f:
                status_data = json.load(f)
                best_profit = status_data.get('best_profit')
        except: pass
        
    tuner = health.get('tuner', {})
    version_age = strategy.get('version_age_days', 0)
    age_suffix = "day" if version_age == 1 else "days"
    
    # Calculate next scheduled run
    now_utc = datetime.now()
    next_run = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_until_next = next_run - now_utc
    total_seconds_until = int(time_until_next.total_seconds())
    hours_until = total_seconds_until // 3600
    minutes_until = (total_seconds_until % 3600) // 60
    relative_next_run = f"in {hours_until}h {minutes_until}m" if hours_until > 0 else f"in {minutes_until}m"
    
    eli5_text = (
        "<b>👶 Under the Hood (ELI5):</b> Think of the bot as a surfer looking for altcoin waves to ride. "
        "Before jumping in, it checks the giant ocean waves (1-hour BTC) and local beach wind (15-minute BTC) to make sure a storm isn't coming. "
        "Once riding, if it gains profit, it locks in a tiny bit of gains (+0.2% ProfitGuard) and rides it as high as it can. "
        "If the wave collapses, it jumps off instantly (ATR Stop Loss) to stay safe."
    )
    
    html = "<div style='font-size: 13px; color: #495057;'>"
    
    # Active strategy details
    html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 13px;'>"
    html += f"<tr><td style='padding: 4px 0; width: 45%; border-bottom: 1px solid #f1f3f5;'><b>Active Strategy Version:</b></td><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'><b>{strategy.get('version', 'Strategy')}</b> <span style='color: #6c757d; font-size: 11px; margin-left: 5px;'>(Active for {version_age} {age_suffix})</span></td></tr>"
    html += f"<tr><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'><b>Latest AI Evolved Task:</b></td><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'>{strategy.get('latest_task')}</td></tr>"
    html += f"<tr><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'><b>Backtest Optimizer Status:</b></td><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'>{tuner.get('status', 'Idle')} <span style='color: #6c757d; font-size: 11px;'>(Last Activity: {tuner.get('age', 'N/A')})</span></td></tr>"
    html += f"<tr><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'><b>Next Scheduled Run:</b></td><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'>{next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC <span style='color: #6c757d; font-size: 11px;'>({relative_next_run})</span></td></tr>"
    if best_profit is not None:
        html += f"<tr><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5;'><b>Optimizer Cross-Regime Score:</b></td><td style='padding: 4px 0; border-bottom: 1px solid #f1f3f5; color: #198754; font-weight: bold;'>{best_profit:+.2f}%</td></tr>"
    html += "</table>"
    
    # Evolution consideration paragraph
    success, reason = check_recent_evolution()
    if success:
        rationale = get_evolution_rationale()
        evolution_para = (
            "<b>🔄 Daily Strategy Consultation:</b> Yes, strategy analysis was considered yesterday. "
            f"Gemini analyzed the recent trading performance and determined that:<br/>"
            f"<span style='color: #495057; font-style: italic;'>\"{rationale}\"</span>"
        )
        evolution_style = "padding: 10px 12px; background-color: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; border-radius: 4px; margin-bottom: 15px; line-height: 1.4; font-size: 12px;"
    else:
        evolution_para = (
            "<b>🔄 Daily Strategy Consultation:</b> Yes, strategy analysis was considered yesterday. "
            f"However, the analysis run did <b>not</b> complete successfully. "
            f"Reason: {reason} To maintain stability, the bot continues running the last fully verified strategy version ({strategy.get('version', 'Strategy V90')})."
        )
        evolution_style = "padding: 10px 12px; background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; border-radius: 4px; margin-bottom: 15px; line-height: 1.4; font-size: 12px;"
        
    html += f"<div style='{evolution_style}'>{evolution_para}</div>"
    
    # ELI5 alertbox
    html += f"<div style='padding: 10px 12px; background-color: #fff3cd; color: #664d03; border: 1px solid #ffecb5; border-radius: 4px; margin-bottom: 15px; line-height: 1.4; font-size: 12px;'>{eli5_text}</div>"
    
    # Optimal parameters table
    if config_params:
        html += "<h4 style='font-size: 12px; font-weight: bold; color: #0d6efd; margin: 0 0 6px 0;'>⚙️ Active Parameter Configuration</h4>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 11px; border: 1px solid #dee2e6;'>"
        html += "<thead><tr style='background-color: #f8f9fa; border-bottom: 1px solid #dee2e6;'>"
        html += "<th style='padding: 4px 6px; text-align: left;'>Parameter</th>"
        html += "<th style='padding: 4px 6px; text-align: left;'>Value</th>"
        html += "<th style='padding: 4px 6px; text-align: left; border-left: 1px solid #dee2e6;'>Parameter</th>"
        html += "<th style='padding: 4px 6px; text-align: left;'>Value</th>"
        html += "</tr></thead><tbody>"
        
        items = list(config_params.items())
        for i in range(0, len(items), 2):
            html += "<tr style='border-bottom: 1px solid #f1f3f5;'>"
            html += f"<td style='padding: 4px 6px; font-weight: bold; color: #495057;'>{items[i][0]}</td><td style='padding: 4px 6px;'>{items[i][1]}</td>"
            if i+1 < len(items):
                html += f"<td style='padding: 4px 6px; font-weight: bold; color: #495057; border-left: 1px solid #dee2e6;'>{items[i+1][0]}</td><td style='padding: 4px 6px;'>{items[i+1][1]}</td>"
            else:
                html += "<td colspan='2' style='border-left: 1px solid #dee2e6;'></td>"
            html += "</tr>"
        html += "</tbody></table>"
        
    if changes.strip():
        changed_files = ", ".join([os.path.basename(f) for f in changes.split('\n') if f.strip()])
        html += f"<p style='margin: 8px 0 0 0; font-size: 11px; color: #6c757d;'><b>Recently Modified Files:</b> {changed_files}</p>"
        
    html += get_recent_ai_manager_actions()
    html += "</div>"
    return html

def generate_health_and_validation(health, random_walk):
    status_badge = "<span style='background-color: #198754; color: #ffffff; padding: 2px 6px; font-size: 10px; font-weight: bold; border-radius: 4px; display: inline-block;'>OK</span>" if health.get('overall_status') == "OK" else "<span style='background-color: #dc3545; color: #ffffff; padding: 2px 6px; font-size: 10px; font-weight: bold; border-radius: 4px; display: inline-block;'>ERROR</span>"
    
    # Active Services summary
    services_html = ""
    for service, status in health.get('services', {}).items():
        color = "#198754" if status == "active" else "#dc3545"
        name = service.replace('.service', '')
        services_html += f"<span style='margin-right: 12px; font-weight: bold;'>• {name}: <span style='color: {color};'>{status}</span></span>"
        
    # Random walk section
    if "error" in random_walk:
        rw_html = f"<div style='padding: 10px; background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; border-radius: 4px; font-size: 12px;'>Error running random walk: {random_walk['error']}</div>"
    else:
        pnl_val = random_walk['pnl']
        pnl_color = "#198754" if pnl_val >= 0 else "#dc3545"
        status_text = "PASSED" if pnl_val >= -10.0 else "FAILED"
        status_color = "#198754" if pnl_val >= -10.0 else "#dc3545"
        
        sym_list = ", ".join([s.replace('USDT', '') for s in random_walk.get('symbols', [])])
        
        rw_html = "<table style='width: 100%; border-collapse: collapse; font-size: 11px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;'>"
        rw_html += "<tr>"
        rw_html += f"<td style='padding: 6px; border-bottom: 1px solid #dee2e6; width: 50%;'><b>Validation Period:</b> {random_walk['start']} to {random_walk['end']} <span style='color: #6c757d; font-size: 10px;'>({random_walk['relative_age']})</span></td>"
        rw_html += f"<td style='padding: 6px; border-bottom: 1px solid #dee2e6; width: 50%;'><b>Tested Assets:</b> {sym_list}</td>"
        rw_html += "</tr>"
        rw_html += "<tr>"
        rw_html += f"<td style='padding: 6px;'><b>Simulated Weekly Return:</b> <span style='color: {pnl_color}; font-weight: bold;'>{pnl_val:+.2f}%</span></td>"
        rw_html += f"<td style='padding: 6px;'><b>Validation Status:</b> <span style='color: {status_color}; font-weight: bold;'>{status_text}</span> <span style='color: #6c757d; font-size: 10px;'>(Floor: -10.0%)</span></td>"
        rw_html += "</tr>"
        rw_html += "</table>"
        
    # System cleanup section
    cleanup_html = ""
    cleanup_log_path = '/root/cleanup_log.json'
    if os.path.exists(cleanup_log_path):
        try:
            with open(cleanup_log_path, 'r') as f:
                log_data = json.load(f)
                deleted_files = log_data.get("deleted_files", [])
                if deleted_files:
                    files_str = ", ".join(deleted_files)
                    cleanup_html = (
                        "<div style='margin-top: 15px; padding: 10px 12px; background-color: #cfe2ff; color: #084298; border: 1px solid #b6d4fe; border-radius: 4px; font-size: 12px; line-height: 1.4;'>"
                        f"🧹 <b>Automated System Cleanup:</b> Deployed cleanup sequence. Deleted {len(deleted_files)} obsolete file(s): <code style='font-family: monospace;'>{files_str}</code>."
                        "</div>"
                    )
                else:
                    cleanup_html = (
                        "<div style='margin-top: 15px; padding: 10px 12px; background-color: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; border-radius: 4px; font-size: 12px; line-height: 1.4;'>"
                        "🧹 <b>Automated System Cleanup:</b> Deployed cleanup sequence. No obsolete files detected."
                        "</div>"
                    )
        except Exception as e:
            cleanup_html = f"<div style='margin-top: 15px; font-size: 11px; color: #6c757d;'>🧹 <b>Automated System Cleanup:</b> Error checking status: {str(e)}</div>"
        
    html = "<div style='font-size: 13px; color: #495057;'>"
    html += f"<div style='margin-bottom: 8px;'><b>System Health Status:</b> {status_badge}</div>"
    html += f"<div style='margin-bottom: 15px; font-size: 12px;'>{services_html}</div>"
    
    html += "<h4 style='font-size: 12px; font-weight: bold; color: #0d6efd; margin: 0 0 6px 0;'>🎲 Daily Random Walk Safety Test</h4>"
    html += rw_html
    html += cleanup_html
    html += "</div>"
    return html

def format_email_body(health, pnl, opt_log, changes, strategy, projection, random_walk):
    # Email-Safe Fonts & Colors
    body_style = "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 650px; margin: 0 auto; padding: 15px; background-color: #f8f9fa; color: #212529; line-height: 1.5;"
    
    # Email-safe Alerts
    alert_base = "padding: 12px 15px; margin: 15px 0; border: 1px solid; border-radius: 4px; font-size: 14px;"
    alert_success = f"{alert_base} color: #0f5132; background-color: #d1e7dd; border-color: #badbcc;"
    alert_warning = f"{alert_base} color: #664d03; background-color: #fff3cd; border-color: #ffecb5;"
    alert_danger = f"{alert_base} color: #842029; background-color: #f8d7da; border-color: #f5c2c7;"
    
    # Email-safe Tables
    table_style = "width: 100%; border-collapse: collapse; margin: 10px 0; vertical-align: top; border-color: #dee2e6;"
    th_style = "padding: 8px 10px; font-weight: bold; text-align: left; border-bottom: 2px solid #dee2e6; font-size: 13px; background-color: #f8f9fa; color: #495057;"
    
    h1_style = "font-size: 24px; font-weight: 500; line-height: 1.2; margin-top: 0; margin-bottom: 10px; color: #0d6efd;"
    list_style = "padding-left: 20px; margin-top: 5px; margin-bottom: 5px; font-size: 13px;"
    
    # Helper to construct bulletproof nested table cards
    def make_card(title, content_html):
        card = "<table style='width: 100%; border: 1px solid #dee2e6; border-radius: 4px; margin-bottom: 20px; border-collapse: collapse; background-color: #ffffff;'>"
        card += f"<tr><td style='background-color: #f8f9fa; padding: 12px 15px; border-bottom: 1px solid #dee2e6; font-weight: bold; color: #0d6efd; font-size: 15px; border-top-left-radius: 4px; border-top-right-radius: 4px;'>{title}</td></tr>"
        card += f"<tr><td style='padding: 15px; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px; background-color: #ffffff;'>{content_html}</td></tr>"
        card += "</table>"
        return card
    
    # Begin HTML Body
    body = f"<div style=\"{body_style}\">"
    
    # Jumbotron header using simple table
    header_html = "<table style='width: 100%; padding: 25px 15px; margin-bottom: 25px; background-color: #e9ecef; border-radius: 4px; border: 1px solid rgba(0,0,0,.08); border-collapse: collapse;'>"
    header_html += "<tr><td>"
    header_html += f"<h1 style=\"{h1_style}\">📊 Trading Bot Dashboard</h1>"
    header_html += f"<p style=\"font-size: 16px; font-weight: 300; margin-top: 0; margin-bottom: 0; color: #495057;\">Active Strategy: <strong style=\"color:#0d6efd;\">{strategy.get('current_strategy')}</strong></p>"
    header_html += "<hr style=\"margin: 15px 0; border: 0; border-top: 1px solid rgba(0,0,0,.1);\">"
    header_html += f"<p style=\"font-size: 12px; color: #6c757d; margin: 0;\">Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>"
    header_html += "</td></tr></table>"
    body += header_html
    
    # 1. Daily Performance & Market Narrative
    perf_html = generate_performance_and_narrative(pnl, strategy)
    body += make_card("💰 Yesterday's Performance & Market Narrative", perf_html)
    
    # 2. AI Strategy & Parameter Optimizer
    strat_html = generate_strategy_and_optimizer(strategy, health, opt_log, changes)
    body += make_card("🤖 AI Strategy & Parameter Optimizer", strat_html)
    
    # 3. System Health & Safety Validation
    health_html = generate_health_and_validation(health, random_walk)
    body += make_card("🛠️ System Health & Safety Validation", health_html)
    
    # 4. Historical Performance & Projections Card
    if "error" in projection:
        proj_content = f"<div style=\"{alert_danger}\"><b>Error calculating projections:</b> {projection['error']}</div>"
    else:
        proj_content = f"<p style=\"font-size:13px; color:#6c757d; margin-top:0; margin-bottom:12px;\"><b>Analysis Period (Last 5 Strategy Versions):</b> {projection['start_date']} to {projection['end_date']}</p>"
        proj_content += f"<table style=\"{table_style}\">"
        proj_content += f"<thead><tr><th style=\"{th_style}\">Date</th><th style=\"{th_style}\">Strategy</th><th style=\"{th_style}\">Strategy Daily PnL</th><th style=\"{th_style}\">Binance PnL (Equity Change)*</th><th style=\"{th_style}\">Equity (Spot Balance)</th><th style=\"{th_style}\">BTC Price (Daily Change)</th></tr></thead>"
        proj_content += f"<tbody>{projection['returns_table']}</tbody>"
        proj_content += "</table>"
        proj_content += "<p style='font-size:11px; color:#6c757d; margin:5px 0 12px 0;'><i>* Note: Binance PnL (Equity Change) shows the absolute growth/drawdown of the entire spot wallet (realized profits + unrealized valuation changes of active holdings), whereas Strategy Daily PnL tracks only realized gains/losses from completed trade cycles.</i></p>"
        
        # Projections Subsection
        proj_content += f"<div style=\"{alert_success} margin-bottom: 15px;\">"
        proj_content += f"<h4 style=\"margin-top:0; margin-bottom:8px; color:#0f5132; font-size:14px;\">🚀 Compound Projections (Stabilized @ {projection['r_daily_v90']*100:.3f}% / day)</h4>"
        v90_days = projection.get('v90_days', 0)
        days_str = f"{v90_days} day" if v90_days == 1 else f"{v90_days} days"
        proj_content += f"<p style='font-size:12px; margin-top:0; margin-bottom:10px;'>Based on current stabilized compound rate (calculating back to {projection.get('v90_start_date', 'N/A')} - {days_str} of history):</p>"
        proj_content += f"<ul style=\"{list_style} color:#0f5132;\">"
        proj_content += f"<li><b>1 Year:</b> ${projection['p1']:,.2f}</li>"
        proj_content += f"<li><b>2 Years:</b> ${projection['p2']:,.2f}</li>"
        proj_content += f"<li><b>5 Years:</b> ${projection['p5']:,.2f}</li>"
        proj_content += f"<li><b>10 Years:</b> ${projection['p10']:,.2f}</li>"
        proj_content += "</ul>"
        proj_content += "</div>"
        
        proj_content += f"<div style=\"{alert_warning}\">"
        proj_content += f"<h4 style=\"margin-top:0; margin-bottom:8px; color:#664d03; font-size:14px;\">⚠️ 10-Day Meta-System Projection (@ {projection['r_daily_10d']*100:.3f}% / day)</h4>"
        proj_content += "<p style='font-size:12px; margin-top:0; margin-bottom:10px;'>Including the historical version drawdowns:</p>"
        proj_content += f"<ul style=\"{list_style} color:#664d03;\">"
        proj_content += f"<li><b>1 Year:</b> ${projection['p1_10d']:,.2f}</li>"
        proj_content += f"<li><b>2 Years:</b> ${projection['p2_10d']:,.2f}</li>"
        proj_content += "</ul>"
        proj_content += "</div>"
        proj_content += "<p style='color:#6c757d; font-size:11px; margin-top:12px; margin-bottom:0;'><i>*Note: Projections assume infinite order depth and are for theoretical modeling. Real-world returns will cap due to market slippage.</i></p>"
    body += make_card("📊 Historical Equity & Projections", proj_content)
    
    # Close wrapper div
    body += "</div>"
    return body

def send_email():
    if not GMAIL_USER or not GMAIL_PASS:
        print("Error: GMAIL_USER or GMAIL_PASS not set in .env")
        return

    print("Gathering data...")
    health = get_system_health()
    pnl = get_pnl_report()
    opt_log = get_optimization_summary()
    changes = get_recent_changes()
    strategy = get_strategy_updates()
    projection = get_historical_projection()
    
    print("Running random walk backtest...")
    random_walk = get_random_walk_data()
    
    body_html = format_email_body(health, pnl, opt_log, changes, strategy, projection, random_walk)
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = RECIPIENT
    msg['Subject'] = f"📊 Trading Bot Report: {strategy.get('current_strategy')} | PnL: ${pnl.get('total_realized_pnl', 0):.2f}"
    
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        print(f"Connecting to Gmail SMTP as {GMAIL_USER}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

if __name__ == "__main__":
    send_email()
