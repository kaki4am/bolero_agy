import asyncio
import itertools
import os
import json
import time
import random
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta, timezone
from portfolio_backtester import PortfolioBacktester
from binance import AsyncClient
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
USE_TESTNET = os.getenv('USE_TESTNET', 'True') == 'True'

STATUS_FILE = 'backtest_status.json'

SEARCH_SPACE = {
    'EMA_FAST': [50],
    'EMA_SLOW': [200],
    'MIN_VOLATILITY': [0.0010],
    'BASE_RISK_PERCENT': [2.0],
    'MAX_RISK_PER_TRADE_PERCENT': [10.0, 15.0, 20.0],
    'COOLDOWN_PERIOD': [600],
    'ATR_SL_MULT': [2.5, 3.0, 3.5],
    'PORTFOLIO_EJECT': [-5.0],
    'PORTFOLIO_HARVEST': [4.0, 5.0],
    'VOL_SPIKE_MULTIPLIER': [1.5, 1.8],
    'SL_MIN_PCT': [0.015],
    'SL_MAX_PCT': [0.030, 0.040],
    'BE_TRIGGER': [0.010, 0.015, 0.020],
    'BE_LOCK': [0.002],
    'TRAILING_TRIGGER': [0.020, 0.030, 0.040],
    'TRAILING_DIST': [0.010, 0.015, 0.020],
    'VOLATILITY_CAP': [0.015, 0.020],
    'SCALE_1_POS': [0.8],
    'SCALE_2_POS': [0.6],
    'SCALE_3_POS': [0.4],
    'VOLUME_SMA_WINDOW': [20]
}

def save_config(params):
    with open('config.json', 'w') as f:
        json.dump(params, f, indent=4)

def save_status(status):
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=4)

def get_status():
    if not os.path.exists(STATUS_FILE):
        return None
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def log_event(status, message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    full_msg = f"[{timestamp}] {message}"
    if 'logs' not in status:
        status['logs'] = []
    status['logs'].append(full_msg)
    if len(status['logs']) > 15:
        status['logs'].pop(0)
    save_status(status)

async def get_top_pairs(limit=50):
    client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
    tickers = await client.get_ticker()
    await client.close_connection()
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
    
    # Filter stablecoins and restricted pairs
    blacklisted = ['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT']
    
    if os.path.exists('restricted_pairs.json'):
        try:
            with open('restricted_pairs.json', 'r') as f:
                restricted = json.load(f)
                blacklisted.extend(restricted)
        except:
            pass

    filtered_pairs = [p for p in usdt_pairs if p['symbol'] not in blacklisted]
    
    sorted_pairs = sorted(filtered_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
    return [p['symbol'] for p in sorted_pairs[:limit]]

def update_bot_config(best_params):
    save_config(best_params)
    os.system("systemctl restart trading-bot.service")

async def fetch_historical_segment(client, start_str, end_str, symbols):
    import os
    import pickle
    import hashlib
    
    sym_hash = hashlib.md5("".join(sorted(symbols)).encode('utf-8')).hexdigest()
    cache_dir = "/root/.backtester_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    clean_start = start_str.replace(' ', '_').replace(':', '-')
    clean_end = end_str.replace(' ', '_').replace(':', '-')
    cache_file = f"{cache_dir}/segment_{sym_hash}_{clean_start}_{clean_end}.pkl"
    
    if os.path.exists(cache_file):
        try:
            print(f"Loading cached historical segment: {cache_file}")
            with open(cache_file, 'rb') as f:
                cached = pickle.load(f)
            tester = PortfolioBacktester(symbols=symbols)
            tester.pair_data = cached['pair_data']
            tester.btc_df = cached['btc_df']
            tester.btc_15m = cached.get('btc_15m')
            tester.symbols = list(tester.pair_data.keys())
            return tester
        except Exception as e:
            print(f"Segment cache load failed: {e}. Fetching live segment...")

    tester = PortfolioBacktester(symbols=symbols)
    try:
        # Calculate warmup dates (12 days for BTC 1h, 5 days for 15m)
        start_date = datetime.strptime(start_str.split(' ')[0], "%Y-%m-%d")
        btc_1h_start = (start_date - timedelta(days=12)).strftime("%Y-%m-%d") + " UTC"
        btc_15m_start = (start_date - timedelta(days=5)).strftime("%Y-%m-%d") + " UTC"

        # Fetch BTC hourly and 15m
        btc_1h = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1HOUR, btc_1h_start, end_str)
        tester.btc_df = pd.DataFrame(btc_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        tester.btc_df['close'] = tester.btc_df['close'].astype(float)
        tester.btc_df['timestamp'] = pd.to_datetime(tester.btc_df['timestamp'], unit='ms')
        tester.btc_df['ema200'] = ta.ema(tester.btc_df['close'], length=200)
        tester.btc_df['rsi'] = ta.rsi(tester.btc_df['close'], length=14)
        
        btc_15m = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, btc_15m_start, end_str)
        tester.btc_15m = pd.DataFrame(btc_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        tester.btc_15m['close'] = tester.btc_15m['close'].astype(float)
        tester.btc_15m['timestamp'] = pd.to_datetime(tester.btc_15m['timestamp'], unit='ms')
        tester.btc_15m['ema200'] = ta.ema(tester.btc_15m['close'], length=200)

        active_symbols = []
        for s in symbols:
            try:
                kl_1m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_1MINUTE, start_str, end_str)
                kl_15m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_15MINUTE, btc_15m_start, end_str)
                if not kl_1m or len(kl_1m) < 100:
                    continue
                
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
                pass
                
        tester.symbols = active_symbols
        
        # Cache the fetched segment data
        if tester.pair_data:
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump({
                        'pair_data': tester.pair_data,
                        'btc_df': tester.btc_df,
                        'btc_15m': tester.btc_15m
                    }, f)
                print(f"Saved segment to cache: {cache_file}")
            except Exception as e:
                print(f"Failed to save segment to cache: {e}")
                
        return tester
    except Exception as e:
        print(f"Error fetching historical segment: {e}")
        return None

async def optimize():
    keys = SEARCH_SPACE.keys()
    values = SEARCH_SPACE.values()
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    prev_status = get_status()
    resume_index = 0
    best_score = -float('inf')
    best_params = None
    pairs = []

    if prev_status and prev_status.get('total_combinations') == len(combinations) and prev_status.get('progress', 0) < len(combinations):
        resume_index = prev_status.get('progress', 0)
        best_score = prev_status.get('best_profit', -float('inf'))
        best_params = prev_status.get('best_params')
        pairs = prev_status.get('pairs', [])
        status = prev_status
        if "run_started" not in status:
            status["run_started"] = "Unknown"
        status["last_run"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status["status"] = "Resuming..."
        log_event(status, f"Resuming optimization from index {resume_index}/{len(combinations)}. Current Best Score: {best_score:.2f}%")
    else:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = {
            "last_run": now_str,
            "run_started": now_str,
            "status": "Initializing...",
            "progress": 0,
            "total_combinations": len(combinations),
            "best_profit": -100.0,
            "best_params": None,
            "pairs": [],
            "eta": "Calculating...",
            "logs": []
        }
        log_event(status, f"Starting Weighted Cross-Regime Optimization with {len(combinations)} combinations.")

    if not pairs:
        pairs = await get_top_pairs(limit=50)
        status["pairs"] = pairs
        save_status(status)

    # 1. Initialize Main 5-Day Recency Backtester
    bt_main = PortfolioBacktester(pairs, lookback='5 days ago UTC')
    
    # 2. Select 3 Random Historical Weeks from the last 6 months (30 to 180 days ago)
    # Use 10 altcoins + BTC for meaningful historical validation
    sampled_alts = random.sample([p for p in pairs if p != 'BTCUSDT'], min(10, len(pairs)-1))
    hist_symbols = ['BTCUSDT'] + sampled_alts
    
    client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
    
    log_event(status, "Fetching current 5-day market data...")
    await bt_main.fetch_data(status_callback=lambda msg: log_event(status, msg))
    
    log_event(status, f"Fetching 3 historical segments for robust checks on: {', '.join([s.replace('USDT', '') for s in hist_symbols])}...")
    hist_testers = []
    for idx in range(3):
        days_back = random.randint(30, 180)
        start_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
        end_dt = start_dt + timedelta(days=7)
        start_str = start_dt.strftime("%Y-%m-%d UTC")
        end_str = end_dt.strftime("%Y-%m-%d UTC")
        
        log_event(status, f"  Loading Segment #{idx+1}: {start_dt.strftime('%B %Y')} ({days_back} days ago)...")
        tester = await fetch_historical_segment(client, start_str, end_str, hist_symbols)
        if tester and len(tester.symbols) > 1:
            hist_testers.append(tester)
            
    await client.close_connection()

    status["status"] = "Pre-calculating Indicators..."
    bt_main.precalculate_all(SEARCH_SPACE, status_callback=lambda msg: log_event(status, msg))
    for idx, ht in enumerate(hist_testers):
        ht.precalculate_all(SEARCH_SPACE, status_callback=lambda msg: log_event(status, f"  Calculating indicators for Segment #{idx+1}..."))

    status["status"] = "Running Weighted Grid Search"
    log_event(status, f"Simulation started. Active Segments: Current + {len(hist_testers)} Historical Weeks.")
    
    start_time = time.time()
    for i, params in enumerate(combinations):
        if i < resume_index:
            continue

        # Run Current 5-Day
        cur_profit = bt_main.run(params)
        
        # Run Historical Segments
        hist_profits = []
        for ht in hist_testers:
            h_prof = ht.run(params)
            hist_profits.append(h_prof)
            
        hist_avg = sum(hist_profits) / len(hist_profits) if hist_profits else 0.0
        
        # Weighted Score Formula: 50% recency + 50% historical average
        weighted_score = (0.50 * cur_profit) + (0.50 * hist_avg)
        
        if weighted_score > best_score:
            best_score = weighted_score
            best_params = params
            status['best_profit'] = best_score
            status['best_params'] = best_params
            log_event(status, f"New Best! Score: {weighted_score:.2f}% (Cur: {cur_profit:+.1f}%, Hist: {hist_avg:+.1f}%) | SL: {params.get('ATR_SL_MULT')} | Harvest: {params.get('PORTFOLIO_HARVEST')}%")

        if 'all_scores' not in status:
            status['all_scores'] = []
        status['all_scores'].append(round(weighted_score, 3))

        if 'recent_scores' not in status:
            status['recent_scores'] = []
        status['recent_scores'].append(round(weighted_score, 3))
        if len(status['recent_scores']) > 60:
            status['recent_scores'].pop(0)

        if i % 5 == 0:
            elapsed = time.time() - start_time
            processed = (i - resume_index) + 1
            avg_time = elapsed / processed
            remaining = (len(combinations) - i) * avg_time
            eta_time = datetime.now() + timedelta(seconds=remaining)
            status["eta"] = eta_time.strftime('%H:%M:%S')
            status["progress"] = i
            save_status(status)

    status["status"] = "Idle"
    status["progress"] = len(combinations)
    status["eta"] = "Complete"
    log_event(status, "Weighted optimization complete. Overwriting config.json and restarting bot.")

    if best_params:
        if best_score > 0:
            update_bot_config(best_params)
            log_event(status, f"Deployed new config with score {best_score:.2f}%. Restarted bot.")
        else:
            log_event(status, f"Best score {best_score:.2f}% is negative. Keeping existing config (no deploy).")
            save_status(status)

async def main_loop():
    while True:
        try:
            await optimize()
        except Exception as e:
            print(f"Optimization error: {e}")
            status = get_status() or {}
            status["status"] = "Error"
            log_event(status, f"CRITICAL ERROR: {str(e)}")
            save_status(status)
        await asyncio.sleep(6 * 3600)

if __name__ == "__main__":
    asyncio.run(main_loop())
