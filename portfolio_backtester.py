import os
import pandas as pd
import pandas_ta as ta
from binance import AsyncClient
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
USE_TESTNET = os.getenv('USE_TESTNET', 'True') == 'True'

class PortfolioBacktester:
    def __init__(self, symbols, interval='1m', lookback='5 days ago UTC'):
        self.symbols = symbols
        self.interval = interval
        self.lookback = lookback
        self.pair_data = {} 
        self.precalculated_indicators = {} 
        self.btc_df = None
        self.btc_trend_aligned = None 

    async def fetch_data(self, status_callback=None):
        import hashlib
        import pickle
        from datetime import date
        
        # Set up cache directory and unique file name
        cache_dir = '/root/.backtester_cache'
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
        today_str = date.today().isoformat()
        sym_hash = hashlib.md5("".join(sorted(self.symbols)).encode('utf-8')).hexdigest()
        cache_file = f"{cache_dir}/cache_{sym_hash}_{self.interval}_{self.lookback.replace(' ', '_')}_{today_str}.pkl"
        
        if os.path.exists(cache_file):
            try:
                if status_callback: status_callback(f"Loading cached market data from {cache_file}...")
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                self.pair_data = cached_data['pair_data']
                self.btc_df = cached_data['btc_df']
                self.btc_15m = cached_data.get('btc_15m')
                self.symbols = list(self.pair_data.keys())
                if status_callback: status_callback(f"Successfully loaded {len(self.symbols)} symbols from local cache.")
                return
            except Exception as e:
                if status_callback: status_callback(f"Cache load failed: {e}. Falling back to live fetch.")

        client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
        if status_callback: status_callback("Fetching market data for portfolio...")
        
        # Fetch BTC for Macro Filter
        try:
            if status_callback: status_callback("Fetching BTCUSDT for Market Filter...")
            # 1h BTC
            btc_klines_1h = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1HOUR, "15 days ago UTC")
            self.btc_df = pd.DataFrame(btc_klines_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
            self.btc_df['close'] = self.btc_df['close'].astype(float)
            self.btc_df['timestamp'] = pd.to_datetime(self.btc_df['timestamp'], unit='ms')
            self.btc_df['ema200'] = ta.ema(self.btc_df['close'], length=200)
            self.btc_df['rsi'] = ta.rsi(self.btc_df['close'], length=14)
            
            # 15m BTC
            btc_klines_15m = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, "15 days ago UTC")
            self.btc_15m = pd.DataFrame(btc_klines_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
            self.btc_15m['close'] = self.btc_15m['close'].astype(float)
            self.btc_15m['timestamp'] = pd.to_datetime(self.btc_15m['timestamp'], unit='ms')
            self.btc_15m['ema200'] = ta.ema(self.btc_15m['close'], length=200)
        except Exception as e:
            if status_callback: status_callback(f"Critical Error: Failed to fetch BTC: {e}")
            self.btc_df = None
            self.btc_15m = None

        for i, symbol in enumerate(self.symbols):
            try:
                if i % 10 == 0 and status_callback:
                    status_callback(f"Downloading history: {i}/{len(self.symbols)} pairs loaded...")
                
                # Fetch more data for indicators to stabilize
                klines_1m = await client.get_historical_klines(symbol, self.interval, self.lookback)
                klines_15m = await client.get_historical_klines(symbol, AsyncClient.KLINE_INTERVAL_15MINUTE, "10 days ago UTC")
                
                if not klines_1m or len(klines_1m) < 500:
                    continue

                df_1m = pd.DataFrame(klines_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                df_1m['open'] = df_1m['open'].astype(float)
                df_1m['high'] = df_1m['high'].astype(float)
                df_1m['low'] = df_1m['low'].astype(float)
                df_1m['close'] = df_1m['close'].astype(float)
                df_1m['volume'] = df_1m['volume'].astype(float)
                df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
                
                df_15m = pd.DataFrame(klines_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
                df_15m['open'] = df_15m['open'].astype(float)
                df_15m['high'] = df_15m['high'].astype(float)
                df_15m['low'] = df_15m['low'].astype(float)
                df_15m['close'] = df_15m['close'].astype(float)
                df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
                
                self.pair_data[symbol] = {'1m': df_1m, '15m': df_15m}
            except Exception as e:
                if status_callback: status_callback(f"Warning: Failed to fetch {symbol}: {e}")
        await client.close_connection()

        # Cache the fetched data
        if self.pair_data:
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump({
                        'pair_data': self.pair_data,
                        'btc_df': self.btc_df,
                        'btc_15m': self.btc_15m
                    }, f)
                if status_callback: status_callback(f"Saved market data to local cache: {cache_file}")
            except Exception as e:
                if status_callback: status_callback(f"Warning: Failed to save to cache: {e}")

    def precalculate_all(self, search_space, status_callback=None):
        if status_callback: status_callback("Calculating Strategy V100 Indicators...")
        total = len(self.pair_data)
        
        # Pre-align BTC Trend to 1m resolution
        if self.btc_df is not None:
            btc_shifted = self.btc_df.copy()
            btc_shifted['timestamp'] = btc_shifted['timestamp'] + pd.Timedelta(hours=1)
            btc_indexed = btc_shifted.set_index('timestamp')
            
            if self.btc_15m is not None:
                btc_15m_shifted = self.btc_15m.copy()
                btc_15m_shifted['timestamp'] = btc_15m_shifted['timestamp'] + pd.Timedelta(minutes=15)
                btc_15m_indexed = btc_15m_shifted.set_index('timestamp')
            else:
                btc_15m_indexed = None
                
            self.btc_trend_aligned = pd.DataFrame({
                'uptrend': btc_indexed['close'] > btc_indexed['ema200'],
                'rsi': btc_indexed['rsi']
            })
            if btc_15m_indexed is not None:
                self.btc_trend_aligned['uptrend_15m'] = btc_15m_indexed['close'] > btc_15m_indexed['ema200']
            else:
                self.btc_trend_aligned['uptrend_15m'] = True
        else:
            self.btc_trend_aligned = None

        for i, (symbol, data) in enumerate(self.pair_data.items()):
            if status_callback:
                status_callback(f"[{i+1}/{total}] Processing {symbol}...")
            
            df_1m = data['1m'].copy()
            df_15m = data['15m'].copy()
            
            indicators = {}
            
            indicators['rsi'] = ta.rsi(df_1m['close'], length=14)
            indicators['atr'] = ta.atr(df_1m['high'], df_1m['low'], df_1m['close'], length=14)
            dmi = ta.adx(df_1m['high'], df_1m['low'], df_1m['close'], length=14)
            indicators['adx'] = dmi['ADX_14']
            indicators['dmp'] = dmi['DMP_14']
            indicators['dmn'] = dmi['DMN_14']

            # MACD
            macd = ta.macd(df_1m['close'])
            indicators['macd'] = macd['MACD_12_26_9']
            indicators['macds'] = macd['MACDs_12_26_9']
            indicators['macdh'] = macd['MACDh_12_26_9']
            
            # Bollinger Bands (for BB Lower Bounce setup)
            bb = ta.bbands(df_1m['close'], length=20, std=2.0)
            indicators['bb_lower'] = bb.iloc[:, 0]  # BBL
            
            # SMA 200 instead of VWAP for streaming-safe logic
            sma200_series = ta.sma(df_1m['close'], length=200)
            if sma200_series is not None:
                indicators['vwap'] = pd.Series(sma200_series.values).fillna(0.0)
            else:
                indicators['vwap'] = pd.Series([0.0]*len(df_1m))

            # Volume SMA
            vol_sma_window = search_space.get('VOLUME_SMA_WINDOW', 20)
            if isinstance(vol_sma_window, list):
                vol_sma_window = vol_sma_window[0]
            indicators['vol_sma'] = df_1m['volume'].rolling(window=vol_sma_window).mean()

            # Calculate 15m indicators
            ema_fast_len = search_space.get('EMA_FAST', 50)
            if isinstance(ema_fast_len, list): ema_fast_len = ema_fast_len[0]
            ema_slow_len = search_space.get('EMA_SLOW', 200)
            if isinstance(ema_slow_len, list): ema_slow_len = ema_slow_len[0]

            ema_f = ta.ema(df_15m['close'], length=ema_fast_len)
            ema_s = ta.ema(df_15m['close'], length=ema_slow_len)
            if ema_f is not None and ema_s is not None:
                df_15m['ema_fast'] = ema_f
                df_15m['ema_slow'] = ema_s
                df_15m['ema_slow_prev'] = ema_s.shift(5)
                df_15m['slope'] = (ema_s - df_15m['ema_slow_prev']) / df_15m['ema_slow_prev']
                df_15m['uptrend'] = (ema_f > ema_s) & (df_15m['slope'] > 0)
            else:
                df_15m['uptrend'] = True
            
            # Align BTC to this pair's 1m index
            df_1m_idx = df_1m.set_index('timestamp')
            if self.btc_trend_aligned is not None:
                indicators['btc_safe'] = self.btc_trend_aligned.reindex(df_1m_idx.index).ffill()
            else:
                indicators['btc_safe'] = pd.DataFrame({'uptrend': [True]*len(df_1m), 'rsi': [50.0]*len(df_1m), 'uptrend_15m': [True]*len(df_1m)}, index=df_1m_idx.index)

            # Align 15m uptrend to 1m index without lookahead
            df_15m_shift = df_15m.copy()
            df_15m_shift['timestamp'] = df_15m_shift['timestamp'] + pd.Timedelta(minutes=15)
            df_15m_idx = df_15m_shift.set_index('timestamp')
            indicators['pair_safe'] = df_15m_idx['uptrend'].reindex(df_1m_idx.index).ffill().fillna(True)

            self.precalculated_indicators[symbol] = indicators

    def run(self, params):
        balance = 1000.0
        initial_balance = balance
        active_positions = {s: {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': -99999} for s in self.pair_data.keys()}
        trades = []
        slippage_pct = params.get('SLIPPAGE_PCT', 0.0007)
        
        # Determine common time range
        all_timestamps = []
        for s in self.pair_data:
            all_timestamps.extend(self.pair_data[s]['1m']['timestamp'].tolist())
        
        unique_ts = sorted(list(set(all_timestamps)))
        if not unique_ts: return 0.0
        
        # Map timestamps to indices for fast lookup
        symbol_indices = {}
        for s in self.pair_data:
            df = self.pair_data[s]['1m']
            symbol_indices[s] = {ts: i for i, ts in enumerate(df['timestamp'])}

        # Pre-convert all Series/DataFrames to Numpy arrays for 50x speedup
        np_data = {}
        for s in self.pair_data:
            df = self.pair_data[s]['1m']
            ind = self.precalculated_indicators[s]
            np_data[s] = {
                'close': df['close'].values,
                'volume': df['volume'].values,
                'rsi': ind['rsi'].values,
                'atr': ind['atr'].values,
                'adx': ind['adx'].values,
                'macd': ind['macd'].values,
                'macdh': ind['macdh'].values,
                'bb_lower': ind['bb_lower'].values,
                'vwap': ind['vwap'].values,
                'vol_sma': ind['vol_sma'].values,
                'btc_rsi': ind['btc_safe']['rsi'].values,
                'btc_uptrend': ind['btc_safe']['uptrend'].values,
                'btc_uptrend_15m': ind['btc_safe']['uptrend_15m'].values,
                'pair_safe': ind['pair_safe'].values
            }

        # Simulation Loop
        for ts in unique_ts:
            # 1. Calculate Portfolio State
            total_unrealized_pnl = 0.0
            active_count = 0
            
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None: continue
                pos = active_positions[s]
                if pos['qty'] > 0:
                    active_count += 1
                    price = np_data[s]['close'][idx]
                    unrealized = (price - pos['entry_price']) * pos['qty']
                    total_unrealized_pnl += unrealized
            
            current_equity = balance
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None: continue
                pos = active_positions[s]
                if pos['qty'] > 0:
                    price = np_data[s]['close'][idx]
                    current_equity += pos['qty'] * price
                    
            portfolio_pnl_pct = (total_unrealized_pnl / current_equity) * 100 if current_equity > 0 else 0

            # 2. Portfolio Guard: Global Eject / Harvest
            global_exit_reason = None
            if portfolio_pnl_pct <= params.get('PORTFOLIO_EJECT', -5.0): global_exit_reason = "GlobalEject"
            elif portfolio_pnl_pct >= params.get('PORTFOLIO_HARVEST', 4.0): global_exit_reason = "GlobalHarvest"

            if global_exit_reason:
                for s in self.pair_data:
                    idx = symbol_indices[s].get(ts)
                    if idx is None: continue
                    pos = active_positions[s]
                    if pos['qty'] > 0:
                        price = np_data[s]['close'][idx]
                        exit_price = price * (1.0 - slippage_pct)
                        pnl = ((exit_price / pos['entry_price']) - 1) * 100
                        trades.append({'pair': s, 'pnl': pnl, 'reason': global_exit_reason, 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx}
                continue

            # 3. Individual Trade Analysis
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None or idx < 250: continue
                
                pos = active_positions[s]
                s_data = np_data[s]
                price = s_data['close'][idx]
                atr = s_data['atr'][idx]
                vwap = s_data['vwap'][idx]
                rsi = s_data['rsi'][idx]
                
                btc_uptrend = s_data['btc_uptrend'][idx]
                btc_uptrend_15m = s_data['btc_uptrend_15m'][idx]
                pair_safe = s_data['pair_safe'][idx]

                if pos['qty'] > 0:
                    pos['max_p'] = max(pos['max_p'], price)
                    profit_pct = (price - pos['entry_price']) / pos['entry_price']
                    entry = pos['entry_price']
                    
                    trail_trigger = params.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = params.get('TRAILING_DIST', 0.020)
                    be_trigger = params.get('BE_TRIGGER', 0.020)
                    be_lock = params.get('BE_LOCK', 0.002)
                    
                    # Minimum hold: 360 candles (6h) before tightening to breakeven
                    min_hold_passed = (idx - pos['time']) > 360
                    
                    if profit_pct > trail_trigger:
                        pos['sl'] = max(pos['sl'], price * (1.0 - trail_dist))
                    elif profit_pct > be_trigger and min_hold_passed:
                        pos['sl'] = max(pos['sl'], entry * (1.0 + be_lock))

                    exit_reason = None
                    if price <= pos['sl']:
                        exit_reason = "SL"
                    elif (idx - pos['time']) > 2880:  # 48h time-based exit
                        exit_reason = "TimeExit"

                    if exit_reason:
                        exit_price = price * (1.0 - slippage_pct)
                        pnl = ((exit_price / pos['entry_price']) - 1) * 100
                        trades.append({'pair': s, 'pnl': pnl, 'reason': exit_reason, 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx}

                else:
                    # Check trade cooldown period
                    cooldown_min = params.get('COOLDOWN_PERIOD', 600) / 60.0
                    if (idx - pos.get('last_close_time', -99999)) < cooldown_min:
                        continue
                    
                    setup = None
                    if btc_uptrend and btc_uptrend_15m and pair_safe:
                        if price > vwap:
                            macdh_curr = s_data['macdh'][idx]
                            macdh_prev = s_data['macdh'][idx-1] if idx > 0 else 0.0
                            macd = s_data['macd'][idx]
                            adx = s_data['adx'][idx]
                            if macdh_curr > 0 and macdh_prev <= 0 and macd > 0 and adx > 20 and rsi < 70:
                                setup = "V110_MACD_Mom"
                        
                    if setup:
                        volatility = atr / price
                        max_vol = params.get('VOLATILITY_CAP', 0.015)
                        min_vol = params.get('MIN_VOLATILITY', 0.0010)
                        if volatility > max_vol: setup = None
                        if volatility < min_vol: setup = None

                        if setup and balance > 10.1:
                            size_strength = 1.0
                            if active_count == 1: size_strength = params.get('SCALE_1_POS', 0.8)
                            elif active_count == 2: size_strength = params.get('SCALE_2_POS', 0.6)
                            elif active_count >= 3: size_strength = params.get('SCALE_3_POS', 0.4)
                            
                            risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                            risk_usd = current_equity * risk_pct

                            mult = params.get('ATR_SL_MULT', 2.5)
                            sl_min_pct = params.get('SL_MIN_PCT', 0.015)
                            sl_max_pct = params.get('SL_MAX_PCT', 0.030)
                            sl_dist_price = mult * atr
                            sl_dist_price = min(max(sl_dist_price, price * sl_min_pct), price * sl_max_pct)
                            
                            target_qty = risk_usd / sl_dist_price
                            trade_amount = target_qty * price

                            max_trade = current_equity * (params.get('MAX_RISK_PER_TRADE_PERCENT', 15.0) / 100.0) * size_strength
                            trade_amount = min(trade_amount, max_trade)
                            trade_amount = max(trade_amount, 10.1)

                            if trade_amount <= balance:
                                entry_price = price * (1.0 + slippage_pct)
                                pos['qty'] = (trade_amount * 0.999) / entry_price
                                pos['entry_price'] = entry_price
                                pos['max_p'] = entry_price
                                pos['sl'] = entry_price - sl_dist_price
                                pos['time'] = idx
                                pos['setup'] = setup
                                balance -= trade_amount
                                active_count += 1

        # Close all at end
        final_balance = balance
        for s in active_positions:
            pos = active_positions[s]
            if pos['qty'] > 0:
                final_price = np_data[s]['close'][-1]
                exit_price = final_price * (1.0 - slippage_pct)
                final_balance += pos['qty'] * exit_price * 0.9985
                pnl = ((exit_price / pos['entry_price']) - 1) * 100
                trades.append({'pair': s, 'pnl': pnl, 'reason': 'EOD', 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})

        self.trades = trades

        wins = len([t for t in trades if t['pnl'] > 0])
        losses = len([t for t in trades if t['pnl'] <= 0])
        reasons = {}
        for t in trades:
            r = t['reason']
            reasons[r] = reasons.get(r, 0) + 1
        print(f"Total Trades: {len(trades)} | Wins: {wins} | Losses: {losses}")
        print(f"Exit Reasons: {reasons}")
        if trades: print(f"Average Win: {sum([t['pnl'] for t in trades if t['pnl'] > 0])/max(1,wins):.2f}% | Average Loss: {sum([t['pnl'] for t in trades if t['pnl'] <= 0])/max(1,losses):.2f}%")
        
        return ((final_balance - initial_balance) / initial_balance) * 100
