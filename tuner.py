import asyncio
import os
import json
import time
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
    
    # Clean up old cache files (older than 2 days)
    import time
    now = time.time()
    for f in os.listdir(cache_dir):
        f_path = os.path.join(cache_dir, f)
        if os.path.isfile(f_path) and f_path.endswith('.pkl'):
            if os.stat(f_path).st_mtime < now - 2 * 86400:
                try:
                    os.remove(f_path)
                except:
                    pass
    
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
        import asyncio
        async def fetch_symbol(s):
            try:
                kl_1m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_1MINUTE, start_str, end_str)
                kl_15m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_15MINUTE, btc_15m_start, end_str)
                if not kl_1m or len(kl_1m) < 100:
                    return s, None
                
                df_1m = pd.DataFrame(kl_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df_1m[col] = df_1m[col].astype(float)
                df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
                
                df_15m = pd.DataFrame(kl_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df_15m[col] = df_15m[col].astype(float)
                df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
                
                return s, {'1m': df_1m, '15m': df_15m}
            except:
                return s, None

        chunk_size = 10
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            results = await asyncio.gather(*(fetch_symbol(sym) for sym in chunk))
            for sym, data in results:
                if data is not None:
                    tester.pair_data[sym] = data
                    active_symbols.append(sym)
                
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
    import optuna
    
    best_score = -float('inf')
    best_params = None
    pairs = []

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = {
        "last_run": now_str,
        "run_started": now_str,
        "status": "Initializing...",
        "progress": 0,
        "total_combinations": 100,  # 100 trials for Optuna
        "best_profit": -100.0,
        "best_params": None,
        "pairs": [],
        "eta": "Calculating...",
        "logs": []
    }
    log_event(status, "Starting Bayesian Optimization (Optuna) with Walk-Forward Validation.")

    pairs = await get_top_pairs(limit=20)  # Use top 20 pairs for faster training
    status["pairs"] = pairs
    save_status(status)

    client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
    
    now_utc = datetime.now(timezone.utc)
    train_start = now_utc - timedelta(days=35)
    train_end = now_utc - timedelta(days=5)
    test_start = now_utc - timedelta(days=5)
    test_end = now_utc
    
    train_start_str = train_start.strftime("%Y-%m-%d UTC")
    train_end_str = train_end.strftime("%Y-%m-%d UTC")
    test_start_str = test_start.strftime("%Y-%m-%d UTC")
    test_end_str = test_end.strftime("%Y-%m-%d UTC")
    
    log_event(status, f"Fetching In-Sample (Train) data: {train_start_str} to {train_end_str}...")
    bt_train = await fetch_historical_segment(client, train_start_str, train_end_str, pairs)
    if not bt_train:
        log_event(status, "Failed to load train data. Aborting optimization.")
        await client.close_connection()
        return
        
    log_event(status, f"Fetching Out-Of-Sample (Test) data: {test_start_str} to {test_end_str}...")
    bt_test = await fetch_historical_segment(client, test_start_str, test_end_str, pairs)
    if not bt_test:
        log_event(status, "Failed to load test data. Aborting optimization.")
        await client.close_connection()
        return
        
    await client.close_connection()

    status["status"] = "Pre-calculating Indicators..."
    bt_train.precalculate_all(SEARCH_SPACE, status_callback=lambda msg: log_event(status, f"Train: {msg}"))
    bt_test.precalculate_all(SEARCH_SPACE, status_callback=lambda msg: log_event(status, f"Test: {msg}"))

    status["status"] = "Running Bayesian Optimization (Optuna)"
    log_event(status, "Simulation started. Running 100 trials on In-Sample data.")
    
    start_time = time.time()
    
    def objective(trial):
        params = {
            'EMA_FAST': trial.suggest_categorical('EMA_FAST', SEARCH_SPACE['EMA_FAST']),
            'EMA_SLOW': trial.suggest_categorical('EMA_SLOW', SEARCH_SPACE['EMA_SLOW']),
            'MIN_VOLATILITY': trial.suggest_categorical('MIN_VOLATILITY', SEARCH_SPACE['MIN_VOLATILITY']),
            'BASE_RISK_PERCENT': trial.suggest_float('BASE_RISK_PERCENT', 1.0, 5.0),
            'MAX_RISK_PER_TRADE_PERCENT': trial.suggest_float('MAX_RISK_PER_TRADE_PERCENT', 5.0, 25.0),
            'COOLDOWN_PERIOD': trial.suggest_categorical('COOLDOWN_PERIOD', SEARCH_SPACE['COOLDOWN_PERIOD']),
            'ATR_SL_MULT': trial.suggest_float('ATR_SL_MULT', 1.5, 4.5),
            'PORTFOLIO_EJECT': trial.suggest_float('PORTFOLIO_EJECT', -10.0, -2.0),
            'PORTFOLIO_HARVEST': trial.suggest_float('PORTFOLIO_HARVEST', 2.0, 10.0),
            'SL_MIN_PCT': trial.suggest_float('SL_MIN_PCT', 0.005, 0.025),
            'SL_MAX_PCT': trial.suggest_float('SL_MAX_PCT', 0.025, 0.060),
            'BE_TRIGGER': trial.suggest_float('BE_TRIGGER', 0.005, 0.030),
            'BE_LOCK': trial.suggest_float('BE_LOCK', 0.001, 0.005),
            'TRAILING_TRIGGER': trial.suggest_float('TRAILING_TRIGGER', 0.015, 0.050),
            'TRAILING_DIST': trial.suggest_float('TRAILING_DIST', 0.005, 0.025),
            'TAKE_PROFIT': trial.suggest_float('TAKE_PROFIT', 0.010, 0.100),
            'VOLATILITY_CAP': trial.suggest_float('VOLATILITY_CAP', 0.010, 0.030),
            'SCALE_1_POS': trial.suggest_float('SCALE_1_POS', 0.5, 1.0),
            'SCALE_2_POS': trial.suggest_float('SCALE_2_POS', 0.3, 0.8),
            'SCALE_3_POS': trial.suggest_float('SCALE_3_POS', 0.1, 0.6),
            'VOLUME_SMA_WINDOW': trial.suggest_categorical('VOLUME_SMA_WINDOW', SEARCH_SPACE['VOLUME_SMA_WINDOW'])
        }
        
        train_profit = bt_train.run(params)
        
        nonlocal best_score, best_params
        if train_profit > best_score:
            best_score = train_profit
            best_params = params
            status['best_profit'] = best_score
            status['best_params'] = best_params
            log_event(status, f"New Best Train Score: {train_profit:.2f}%")
            
        status["progress"] += 1
        
        if status["progress"] % 5 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / status["progress"]
            remaining = (100 - status["progress"]) * avg_time
            eta_time = datetime.now() + timedelta(seconds=remaining)
            status["eta"] = eta_time.strftime('%H:%M:%S')
            save_status(status)
            
        status.setdefault('all_scores', []).append(round(train_profit, 3))
        
        return train_profit
        
    study = optuna.create_study(
        study_name="v100_momentum",
        storage="sqlite:////root/optuna_study.db",
        load_if_exists=True,
        direction="maximize"
    )
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    study.optimize(objective, n_trials=100)
    
    best_params = study.best_params
    train_score = study.best_value
    
    log_event(status, f"Training complete. Best In-Sample Profit: {train_score:.2f}%. Running Out-Of-Sample Validation...")
    
    # Out of Sample Validation
    test_score = bt_test.run(best_params)
    log_event(status, f"Out-Of-Sample Validation Profit: {test_score:.2f}%")
    
    if train_score > 0 and test_score > 0:
        log_event(status, "Walk-Forward Validation PASSED. Deploying config.")
        update_bot_config(best_params)
    else:
        log_event(status, "Walk-Forward Validation FAILED (OOS or Train profit is negative). Discarding config.")
        
    status["status"] = "Idle"
    status["progress"] = 100
    status["eta"] = "Complete"
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
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
