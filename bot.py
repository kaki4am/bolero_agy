import asyncio
import os
import json
import sqlite3
import time
import math
import pandas as pd
import pandas_ta as ta
import warnings
from dotenv import load_dotenv
from binance import AsyncClient, BinanceSocketManager

from trading_utils import init_db, log_trade, log_failed_trade

load_dotenv()

# Suppress annoying pandas_ta warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
USE_TESTNET = os.getenv('USE_TESTNET', 'True') == 'True'

def floor_step(n, step):
    n = float(n)
    step = float(step)
    if step == 0: return n
    return float(int(n / step) * step)

class TradingBot:
    def __init__(self):
        self.client = None
        self.bm = None
        self.tracked_pairs = []
        self.restricted_pairs = set()
        self.positions = {}
        # Data buffers
        self.data_1m = {}  # pair: DataFrame
        self.ema_cache = {} # pair: {'ema_f': float, 'ema_s': float, 'slope': float}
        self.market_trend = {'btc_uptrend_15m': True}
        self.exchange_info = {} # pair: filters
        self.last_trade_time = {} # pair: timestamp
        self.last_dust_time = 0 # Track dust conversion frequency
        self.last_positions_save = 0 # Throttle position saves
        self._pair_last_loss = {} # Per-pair loss tracking for adaptive cooldown
        self.failed_trades_history = []
        self.circuit_breaker_until = 0
        self.trade_lock = asyncio.Lock()
        
        # Strategy V148 Trend Pullback
        self.config = {
            'EMA_FAST': 50,
            'EMA_SLOW': 200,
            'MIN_VOLATILITY': 0.001,
            'BASE_RISK_PERCENT': 4.611576631674215,
            'MAX_RISK_PER_TRADE_PERCENT': 23.138107035164726,
            'COOLDOWN_PERIOD': 600,
            'MAX_PAIRS': 40,
            'PORTFOLIO_EJECT': -8.751258110934428,
            'PORTFOLIO_HARVEST': 9.393994286109903,
            'VOL_SPIKE_MULTIPLIER': 1.5,
            'SL_MIN_PCT': 0.021986122119325817,
            'SL_MAX_PCT': 0.03535344813215079,
            'BE_TRIGGER': 0.012051454522992245,
            'BE_LOCK': 0.004301968436203864,
            'TRAILING_TRIGGER': 0.04467886111874062,
            'TRAILING_DIST': 0.0093455106121612,
            'VOLATILITY_CAP': 0.01954279481897226,
            'ATR_SL_MULT': 2.9973558371275932,
            'SCALE_1_POS': 0.9910534826442084,
            'SCALE_2_POS': 0.405864442890098,
            'SCALE_3_POS': 0.13940060952542122,
            'TAKE_PROFIT': 0.0926288409374077
        }
        self.base_config = self.config.copy()
        self.load_config()
        self.load_restricted_pairs()

    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    new_base = json.load(f)
                    self.base_config.update(new_base)
            
            self.config.update(self.base_config)
            
            overrides_path = 'tactical_overrides.json'
            if os.path.exists(overrides_path):
                try:
                    with open(overrides_path, 'r') as f:
                        overrides = json.load(f)
                    risk_mult = overrides.get('RISK_MULTIPLIER', 1.0)
                    sl_offset = overrides.get('SL_MULT_OFFSET', 0.0)
                    
                    if hasattr(self, 'market_trend') and not self.market_trend.get('btc_uptrend_15m', True):
                        risk_mult = 0.0
                        sl_offset = min(sl_offset, -0.5)
                        
                    self.config['BASE_RISK_PERCENT'] = self.base_config['BASE_RISK_PERCENT'] * risk_mult
                    self.config['ATR_SL_MULT'] = self.base_config['ATR_SL_MULT'] + sl_offset
                    self.config['PORTFOLIO_EJECT'] = self.base_config['PORTFOLIO_EJECT'] + overrides.get('PORTFOLIO_EJECT_OFFSET', 0.0)
                    print(f"Loaded config with tactical overrides: Risk Mult={risk_mult}, SL Offset={sl_offset}")
                except Exception as oe:
                    print(f"Error loading tactical overrides: {oe}")
            else:
                print("Loaded configuration from config.json (No overrides active)")
        except Exception as e:
            print(f"Error loading config.json: {e}")

    def load_restricted_pairs(self):
        try:
            if os.path.exists('restricted_pairs.json'):
                with open('restricted_pairs.json', 'r') as f:
                    self.restricted_pairs = set(json.load(f))
                    print(f"Loaded {len(self.restricted_pairs)} restricted pairs.")
        except Exception as e:
            print(f"Error loading restricted_pairs.json: {e}")

    def save_restricted_pairs(self):
        try:
            with open('restricted_pairs.json', 'w') as f:
                json.dump(list(self.restricted_pairs), f)
        except Exception as e:
            print(f"Error saving restricted_pairs.json: {e}")

    def save_active_positions(self):
        try:
            active_data = {}
            for p, pos in self.positions.items():
                if pos.get('entries', 0) > 0:
                    active_data[p] = {
                        'entry_price': pos.get('entry_price'),
                        'qty': pos.get('qty'),
                        'max_p': pos.get('max_p'),
                        'sl': pos.get('sl'),
                        'time': pos.get('time'),
                        'setup': pos.get('setup'),
                        'entry_atr': pos.get('entry_atr')
                    }
            payload = {
                'active_positions': active_data,
                'last_trade_time': self.last_trade_time,
                'pair_last_loss': self._pair_last_loss
            }
            tmp_path = '/root/active_positions.json.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(payload, f, indent=4)
            os.replace(tmp_path, '/root/active_positions.json')
        except Exception as e:
            print(f"Error saving active positions: {e}")

    async def start(self):
        self.client = await AsyncClient.create(API_KEY, API_SECRET, testnet=USE_TESTNET)
        await self.sync_positions_from_db()
        await self.fetch_exchange_info()
        await self.liquidate_stray_assets()

        asyncio.create_task(self.cleanup_routine())
        asyncio.create_task(self.update_macro_trends_task())

        balance = await self.client.get_asset_balance(asset='USDT')
        usdt_free = float(balance['free'])
        
        self.bm = BinanceSocketManager(self.client)
        
        tickers = await self.client.get_ticker()
        price_map = {t['symbol']: float(t['lastPrice']) for t in tickers}
        
        total_val = usdt_free
        for pair, pos in self.positions.items():
            if pos.get('entries', 0) > 0:
                price = price_map.get(pair, pos['entry_price'])
                total_val += pos['qty'] * price
        
        self.last_total_equity = total_val
        print(f"Current USDT Balance: {usdt_free} | Initialized Total Portfolio Equity: {self.last_total_equity}")
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        
        blacklisted = ['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT', 
                       'SOLUSDT', 'AVAXUSDT', 'PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'LUNCUSDT',
                       'FETUSDT', 'INJUSDT', 'NEARUSDT', 'DOTUSDT', 'FILUSDT', 'LDOUSDT', 'XECUSDT', 'SHIBUSDT', 'DODOUSDT',
                       'WLDUSDT', 'ADAUSDT', 'LINKUSDT', 'XRPUSDT', 'LTCUSDT',
                       'HFTUSDT', 'PEOPLEUSDT', 'ONGUSDT', 'SYNUSDT', 'COTIUSDT', 'CRVUSDT']
        candidates = []
        for p in usdt_pairs:
            symbol = p['symbol']
            if symbol in blacklisted or symbol in self.restricted_pairs: continue
            if any(symbol.endswith(sfx) for sfx in ['UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT']): continue
            if symbol in self.exchange_info and not self.exchange_info[symbol]['isAllowed']: continue
            candidates.append(p)

        sorted_candidates = sorted(candidates, key=lambda x: float(x['quoteVolume']), reverse=True)
        
        print("Verifying permissions for top candidates...")
        valid_pairs = []
        max_p = self.config.get('MAX_PAIRS', 40)
        for p in sorted_candidates[:max_p * 2]:
            symbol = p['symbol']
            if await self.test_symbol_permission(symbol):
                valid_pairs.append(symbol)
                if len(valid_pairs) >= max_p: break
            else:
                self.restricted_pairs.add(symbol)
        
        self.save_restricted_pairs()
        
        # Force-track any pair with an active position from DB so stop losses work
        for pair, pos in list(self.positions.items()):
            if pos.get('entries', 0) > 0 and pair not in valid_pairs:
                print(f"Force tracking open position: {pair}")
                valid_pairs.append(pair)

        self.tracked_pairs = valid_pairs
        print(f"Tracking {len(self.tracked_pairs)} pairs.")
        
        try:
            with open('/root/tracked_pairs.json', 'w') as f:
                json.dump({'tracked': self.tracked_pairs}, f)
        except Exception as e:
            print(f"Failed to save tracked pairs: {e}")

        streams = [self.bm.kline_socket(pair, interval='1m') for pair in self.tracked_pairs]
        
        for pair in self.tracked_pairs:
            try:
                klines = await self.client.get_historical_klines(pair, AsyncClient.KLINE_INTERVAL_1MINUTE, "6 hours ago UTC")
                if len(klines) > 1: klines = klines[:-1]
                if not klines: continue
                df = pd.DataFrame(klines, columns=['t','o','h','l','c','v','ct','qav','nt','tbb','tbq','i'])
                self.data_1m[pair] = pd.DataFrame({
                    'timestamp': pd.to_datetime([int(x) for x in df['t']], unit='ms'),
                    'high': df['h'].astype(float),
                    'low': df['l'].astype(float),
                    'close': df['c'].astype(float)
                })
                if pair not in self.positions:
                    self.positions[pair] = {'entries': 0, 'qty': 0.0}
                if pair not in self.last_trade_time:
                    self.last_trade_time[pair] = 0
            except Exception as e:
                print(f"Init error {pair}: {e}")

        await self.fetch_macro_trends()
        asyncio.create_task(self.config_reloader_loop())
        asyncio.create_task(self.portfolio_guard_loop())
        await asyncio.gather(*(self.handle_socket(s, p) for s, p in zip(streams, self.tracked_pairs)))

    async def config_reloader_loop(self):
        """Periodically reloads config.json and tactical_overrides.json to apply AI Manager changes without downtime."""
        while True:
            try:
                self.load_config()
                self.load_restricted_pairs()
                
                # Check for restricted_pairs additions from tactical overrides
                overrides_path = 'tactical_overrides.json'
                added_any = False
                if os.path.exists(overrides_path):
                    with open(overrides_path, 'r') as f:
                        overrides = json.load(f)
                    for pair in overrides.get('blacklist_add', []):
                        if pair not in self.restricted_pairs:
                            self.restricted_pairs.add(pair)
                            added_any = True
                            print(f"Tactically blacklisted by AI Manager: {pair}")
                if added_any:
                    self.save_restricted_pairs()
            except Exception as e:
                print(f"Config reloader loop error: {e}")
            await asyncio.sleep(300) # Reload every 5 minutes

    async def portfolio_guard_loop(self):
        """Dedicated background loop for Global Eject/Harvest to keep websocket processing fast."""
        while True:
            try:
                await self.check_portfolio_guard()
                if hasattr(self, 'current_indicators'):
                    tmp_path = '/root/dashboard_data.json.tmp'
                    with open(tmp_path, 'w') as f:
                        json.dump(self.current_indicators, f)
                    os.replace(tmp_path, '/root/dashboard_data.json')
            except Exception as e:
                print(f"PortfolioGuard Loop error: {e}")
            await asyncio.sleep(2) # Check every 2 seconds

    async def test_symbol_permission(self, symbol):
        try:
            await self.client.create_test_order(symbol=symbol, side='BUY', type='MARKET', quoteOrderQty=10.1)
            return True
        except Exception as e:
            err = str(e).lower()
            if "-2010" in err or "not permitted" in err or "illegal characters" in err:
                return False
            return True

    async def fetch_exchange_info(self):
        try:
            info = await self.client.get_exchange_info()
            for s in info['symbols']:
                if s['symbol'].endswith('USDT'):
                    f = {flt['filterType']: flt for flt in s['filters']}
                    self.exchange_info[s['symbol']] = {
                        'stepSize': float(f['LOT_SIZE']['stepSize']),
                        'minNotional': float(f.get('NOTIONAL', f.get('MIN_NOTIONAL'))['minNotional']),
                        'isAllowed': s['status'] == 'TRADING' and 'MARKET' in s['orderTypes']
                    }
        except Exception as e:
            print(f"Exchange info error: {e}")

    async def fetch_macro_trends(self):
        try:
            klines_15m = await self.client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, "6 days ago UTC")
            if len(klines_15m) > 1: klines_15m = klines_15m[:-1]
            closes_15m = pd.Series([float(k[4]) for k in klines_15m])
            ema200_15m = ta.ema(closes_15m, length=200).iloc[-1]
            btc_cp_15m = closes_15m.iloc[-1]

            self.market_trend = {
                'btc_uptrend_15m': btc_cp_15m > ema200_15m
            }
            print("--- Market Status Update (Strategy V148 Trend Pullback) ---")
            print(f"BTC 15m Trend: {'UP' if btc_cp_15m > ema200_15m else 'DOWN'}")
            
            # Fetch 15m and 1h context data for all pairs in parallel batches
            async def fetch_pair_ema(p):
                try:
                    kl = await self.client.get_historical_klines(p, AsyncClient.KLINE_INTERVAL_15MINUTE, "6 days ago UTC")
                    if len(kl) > 1: kl = kl[:-1]
                    cl = pd.Series([float(k[4]) for k in kl])
                    
                    kl_1h = await self.client.get_historical_klines(p, AsyncClient.KLINE_INTERVAL_1HOUR, "6 days ago UTC")
                    if len(kl_1h) > 1: kl_1h = kl_1h[:-1]
                    high_1h = pd.Series([float(k[2]) for k in kl_1h])
                    low_1h = pd.Series([float(k[3]) for k in kl_1h])
                    close_1h = pd.Series([float(k[4]) for k in kl_1h])
                    
                    cache_data = {}
                    if len(close_1h) >= 20:
                        atr_1h = ta.atr(high_1h, low_1h, close_1h, length=14).iloc[-1]
                        cache_data.update({'atr_1h': atr_1h})
                        
                    if cache_data:
                        self.ema_cache[p] = cache_data
                except Exception:
                    pass

            # Process in batches of 10 to avoid rate limits
            for i in range(0, len(self.tracked_pairs), 10):
                batch = self.tracked_pairs[i:i+10]
                await asyncio.gather(*(fetch_pair_ema(p) for p in batch))
        except Exception as e:
            print(f"Macro error: {e}")

    async def update_macro_trends_task(self):
        while True:
            now = time.time()
            next_15m = math.ceil(now / 900) * 900
            sleep_time = next_15m - now + 5
            if sleep_time < 0: sleep_time = 900
            await asyncio.sleep(sleep_time)
            await self.fetch_macro_trends()

    async def sync_positions_from_db(self):
        try:
            acc = await self.client.get_account()
            balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances'] if (float(b['free']) + float(b['locked'])) > 0}
            
            cached_positions = {}
            if os.path.exists('/root/active_positions.json'):
                try:
                    with open('/root/active_positions.json', 'r') as f:
                        data = json.load(f)
                        if 'active_positions' in data:
                            cached_positions = data['active_positions']
                            if 'last_trade_time' in data:
                                self.last_trade_time = data['last_trade_time']
                            if 'pair_last_loss' in data:
                                self._pair_last_loss = data['pair_last_loss']
                        else:
                            cached_positions = data
                except Exception as e:
                    print(f"Error reading active_positions.json: {e}")
            
            def read_db():
                conn = sqlite3.connect('trading_bot.db')
                query = 'SELECT pair, side, price, quantity, timestamp FROM trades WHERE id IN (SELECT MAX(id) FROM trades GROUP BY pair)'
                df = pd.read_sql_query(query, conn)
                conn.close()
                return df
                
            df = await asyncio.to_thread(read_db)
            for _, row in df.iterrows():
                pair = row['pair']
                asset = pair.replace('USDT', '')
                if row['side'] == 'BUY' and balances.get(asset, 0) > 0:
                    # Sync with actual quantity from Binance
                    actual_qty = balances.get(asset, 0)
                    
                    fallback_time = time.time()
                    try:
                        if 'timestamp' in row and pd.notna(row['timestamp']):
                            dt = pd.to_datetime(row['timestamp'])
                            if dt.tzinfo is None:
                                dt = dt.tz_localize('UTC')
                            fallback_time = dt.timestamp()
                    except:
                        pass
                    
                    if pair in cached_positions:
                        cache = cached_positions[pair]
                        self.positions[pair] = {
                            'entries': 1,
                            'entry_price': cache.get('entry_price', row['price']),
                            'qty': actual_qty,
                            'max_p': cache.get('max_p', row['price']),
                            'sl': cache.get('sl', row['price'] * 0.98),
                            'time': cache.get('time', fallback_time),
                            'setup': cache.get('setup'),
                            'entry_atr': cache.get('entry_atr')
                        }
                        print(f"Synced {pair} from DB and restored trailing stop-loss from cache. SL: {self.positions[pair]['sl']:.6f}")
                    else:
                        self.positions[pair] = {
                            'entries': 1, 'entry_price': row['price'], 'qty': actual_qty,
                            'max_p': row['price'], 'sl': row['price'] * 0.98, 'time': fallback_time
                        }
                        print(f"Synced {pair} from DB (no cache). Fallback Entry: {row['price']}, Qty: {actual_qty}")
            self.save_active_positions()
        except Exception as e:
            print(f"Sync error: {e}")

    async def cleanup_routine(self):
        while True:
            await asyncio.sleep(3600)
            await self.liquidate_stray_assets()

    async def liquidate_stray_assets(self):
        try:
            acc = await self.client.get_account()
            dust_candidates = []
            for b in acc['balances']:
                asset, free = b['asset'], float(b['free'])
                if asset in ['USDT', 'BNB'] or free <= 0: continue
                pair = f"{asset}USDT"
                if self.positions.get(pair, {'entries': 0})['entries'] == 0:
                    if pair in self.exchange_info:
                        try:
                            p_res = await self.client.get_symbol_ticker(symbol=pair)
                            price = float(p_res['price'])
                            if free * price > self.exchange_info[pair]['minNotional']:
                                q = self.format_quantity(pair, free)
                                await self.client.create_order(symbol=pair, side='SELL', type='MARKET', quantity=q)
                            else:
                                dust_candidates.append(asset)
                        except: dust_candidates.append(asset)
            if dust_candidates and (time.time() - self.last_dust_time) > 5400:
                d_info = await self.client.get_dust_assets()
                if 'details' in d_info:
                    elg = [item['asset'] for item in d_info['details']]
                    to_c = ",".join([a for a in dust_candidates if a in elg])
                    if to_c:
                        await self.client.transfer_dust(asset=to_c)
                        self.last_dust_time = time.time()
        except: pass

    async def handle_socket(self, socket, pair):
        async with socket as stream:
            while True:
                res = await stream.recv()
                if res['e'] == 'error': break
                k = res['k']
                cp = float(k['c'])
                if pair in self.positions and self.positions[pair]['entries'] > 0:
                    self.positions[pair]['current_price'] = cp
                
                pos = self.positions.get(pair, {'entries': 0})
                if pos['entries'] > 0:
                    sl = pos.get('sl', 0)
                    old_sl = sl
                    old_max_p = pos.get('max_p', 0)
                    
                    if cp > old_max_p:
                        self.positions[pair]['max_p'] = cp
                    
                    profit_pct = (cp - pos['entry_price']) / pos['entry_price']
                    
                    # V106 ProfitGuard (Parameterized Trailing)
                    # Minimum hold period: don't tighten stops in first 15 minutes
                    trail_trigger = self.config.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = self.config.get('TRAILING_DIST', 0.020)
                    be_trigger = self.config.get('BE_TRIGGER', 0.020)
                    be_lock = self.config.get('BE_LOCK', 0.002)
                    
                    hold_seconds = time.time() - pos.get('time', time.time())
                    min_hold_passed = hold_seconds > 360 * 60  # 6 hours
                    
                    setup = pos.get('setup')
                    
                    if setup == 'Trend_BB_Squeeze':
                        # Trailing stop based on 3.0x ATR
                        atr = self.positions[pair].get('entry_atr', cp * 0.001)
                        mult = self.config.get('ATR_SL_MULT', 3.0)
                        trail_dist_price = max(mult * atr, cp * self.config.get('SL_MIN_PCT', 0.015))
                        sl = max(sl, cp - trail_dist_price)
                        self.positions[pair]['sl'] = sl
                    else:
                        if profit_pct > trail_trigger:
                            sl = max(sl, cp * (1.0 - trail_dist))
                            self.positions[pair]['sl'] = sl
                        elif profit_pct > be_trigger and min_hold_passed:
                            # Only move to breakeven after minimum hold period
                            sl = max(sl, pos['entry_price'] * (1.0 + be_lock))
                            self.positions[pair]['sl'] = sl
                    
                    if sl != old_sl or self.positions[pair].get('max_p', 0) != old_max_p:
                        if time.time() - self.last_positions_save > 30:
                            self.save_active_positions()
                            self.last_positions_save = time.time()

                    if setup == 'V148_Downtrend_Scalp':
                        take_profit = 0.02
                    else:
                        take_profit = self.config.get('TAKE_PROFIT', 0.0)
                    
                    if hold_seconds > 86400: # 24h limit
                        print(f"⏰ TIME EXIT: {pair} 24h limit reached")
                        await self.execute_trade(pair, 'SELL')
                    elif take_profit > 0 and profit_pct >= take_profit:
                        print(f"💰 TAKE PROFIT: {pair} reached TP target")
                        await self.execute_trade(pair, 'SELL')
                    elif sl > 0 and cp <= sl:
                        await self.execute_trade(pair, 'SELL')
                if k['x']:
                    async def process_and_analyze():
                        def update_data(df, t, h, l, c_val):
                            new_row = pd.DataFrame({'timestamp':[pd.to_datetime(t, unit='ms')],'high':[float(h)],'low':[float(l)],'close':[float(c_val)]})
                            return pd.concat([df, new_row], ignore_index=True).iloc[-300:]
                        self.data_1m[pair] = await asyncio.to_thread(update_data, self.data_1m[pair], k['t'], k['h'], k['l'], k['c'])
                        await self.analyze(pair)
                    asyncio.create_task(process_and_analyze())

    async def check_portfolio_guard(self):
        active = [p for p in self.positions if self.positions[p]['entries'] > 0]
        if not active: return
        total_unrealized_usd = 0.0
        current_equity = 0.0
        try:
            bal_r = await self.client.get_asset_balance(asset='USDT')
            current_equity = float(bal_r['free'])
        except:
            current_equity = self.last_total_equity
            
        for p in active:
            pos = self.positions[p]
            current_p = pos.get('current_price', pos['entry_price'])
            total_unrealized_usd += (current_p - pos['entry_price']) * pos['qty']
            current_equity += current_p * pos['qty']
            
            if pos.get('time') and (time.time() - pos['time']) > 24 * 3600:
                print(f"⏰ TIME EXIT: {p} held for >24h, closing position from central loop")
                await self.execute_trade(p, 'SELL')
            
        # Circuit breaker based on equity drawdown
        if not hasattr(self, 'equity_history'):
            self.equity_history = []
        self.equity_history.append((time.time(), current_equity))
        
        # Keep only last 1 hour
        self.equity_history = [e for e in self.equity_history if time.time() - e[0] <= 3600]
        
        drawdown_1h = 0.0
        if len(self.equity_history) > 1:
            old_equity = self.equity_history[0][1]
            drawdown_1h = (old_equity - current_equity) / old_equity
            
        if drawdown_1h > 0.01 or len([t for t in self.failed_trades_history if time.time() - t <= 3600]) >= 3:
            if self.circuit_breaker_until < time.time():
                print(f"🛑 CIRCUIT BREAKER TRIPPED! Drawdown: {drawdown_1h*100:.2f}%, Fails: {len([t for t in self.failed_trades_history if time.time() - t <= 3600])}")
                self.circuit_breaker_until = time.time() + 4 * 3600
        
        pnl_pct = (total_unrealized_pnl if 'total_unrealized_pnl' in locals() else total_unrealized_usd / current_equity) * 100 if current_equity > 0 else 0
        reason = None
        if pnl_pct <= self.config.get('PORTFOLIO_EJECT', -5.0): reason = "GLOBAL_EJECT"
        elif pnl_pct >= self.config.get('PORTFOLIO_HARVEST', 4.0): reason = "GLOBAL_HARVEST"
        if reason:
            print(f"⚠️ {reason} TRIGGERED! Total PnL: {pnl_pct:.2f}%")
            for p in active: await self.execute_trade(p, 'SELL')

    async def analyze(self, pair):
        if pair in self.restricted_pairs or pair not in self.data_1m: return
        df = self.data_1m[pair]
        if len(df) < 250: return

        pos = self.positions.get(pair, {'entries': 0})
        cp = df['close'].iloc[-1]

        def calc_indicators(data):
            c, h, l = data['close'], data['high'], data['low']
            
            sma30 = ta.sma(c, length=30).iloc[-1]
            
            bb = ta.bbands(c, length=20, std=2.0)
            if bb is not None and not bb.empty:
                bb_upper = bb['BBU_20_2.0_2.0'].iloc[-1]
                bb_bandwidth = bb['BBB_20_2.0_2.0']
                bb_bandwidth_sma20 = ta.sma(bb_bandwidth, length=20)
                if bb_bandwidth_sma20 is not None and not bb_bandwidth_sma20.empty:
                    bb_squeeze = bb_bandwidth.iloc[-1] < bb_bandwidth_sma20.iloc[-1]
                else:
                    bb_squeeze = False
            else:
                bb_upper = c.iloc[-1] * 1.1
                bb_squeeze = False
                
            return sma30, bb_upper, bb_squeeze

        try:
            sma30, bb_upper, bb_squeeze = await asyncio.to_thread(calc_indicators, df)
        except Exception as e:
            print(f"Indicator calculation error {pair}: {e}")
            return
            
        ema_data = self.ema_cache.get(pair)
        atr = cp * 0.01
        if ema_data:
            atr = ema_data.get('atr_1h', cp * 0.01)
            
        btc_uptrend_15m = self.market_trend.get('btc_uptrend_15m', True)
        time_since_last = time.time() - self.last_trade_time.get(pair, 0)
        stagnation = time_since_last > 86400 # 24h

        if not hasattr(self, 'current_indicators'):
            self.current_indicators = {}
        self.current_indicators[pair] = {
            'atr': float(atr),
            'sma30': float(sma30),
            'bb_upper': float(bb_upper),
            'bb_squeeze': bool(bb_squeeze),
            'btc_uptrend': bool(btc_uptrend_15m)
        }

        # Strategy Trend BB Squeeze
        if pos['entries'] == 0:
            if time.time() < self.circuit_breaker_until:
                return

            base_cooldown = self.config.get('COOLDOWN_PERIOD', 600)
            pair_had_loss = self._pair_last_loss.get(pair, False)
            cooldown = base_cooldown if not pair_had_loss else self.config.get('LOSS_COOLDOWN_PERIOD', base_cooldown * 4)
            if (time.time() - self.last_trade_time.get(pair, 0)) < cooldown: return
            active_count = len([p for p in self.positions if self.positions[p]['entries'] > 0])
            
            max_concurrent = self.config.get('MAX_PAIRS', 40) // 4
            if active_count >= max_concurrent: return
            
            setup = None
            
            if cp > sma30 and bb_squeeze and cp > bb_upper:
                setup = "Trend_BB_Squeeze"
                        
            if setup:
                volatility = atr / cp
                mx_v = self.config.get('VOLATILITY_CAP', 0.015)
                if volatility > mx_v or volatility < self.config.get('MIN_VOLATILITY', 0.001): return
                
                # Dynamic portfolio strength scaling
                size_strength = 1.0
                if active_count == 1: size_strength = self.config.get('SCALE_1_POS', 0.8)
                elif active_count == 2: size_strength = self.config.get('SCALE_2_POS', 0.6)
                elif active_count >= 3: size_strength = self.config.get('SCALE_3_POS', 0.4)
                
                if await self.execute_trade(pair, 'BUY', strength=size_strength, entry_atr=atr, setup_name=setup):
                    pass
        else:
            if cp > pos.get('max_p', 0):
                self.positions[pair]['max_p'] = cp

    async def execute_trade(self, pair, side, strength=1.0, entry_atr=None, setup_name=None):
        async with self.trade_lock:
            try:
                if side == 'BUY' and pair in self.restricted_pairs: return False
                if pair not in self.exchange_info: await self.fetch_exchange_info()
                
                # Guard against double-sell/buy: re-check position state under lock
                pos_entries = self.positions.get(pair, {}).get('entries', 0)
                if side == 'SELL' and pos_entries == 0:
                    return False
                if side == 'BUY' and pos_entries > 0:
                    return False
                
                try:
                    bal_r = await self.client.get_asset_balance(asset='USDT')
                    free_balance = float(bal_r['free'])
                    total_eq = free_balance
                    for p, pos_val in self.positions.items():
                        if pos_val.get('entries', 0) > 0:
                            curr_p = pos_val.get('current_price', pos_val.get('entry_price', 0.0))
                            total_eq += pos_val['qty'] * curr_p
                except Exception:
                    free_balance = 0.0
                    total_eq = getattr(self, 'last_total_equity', 1000.0)
                if side == 'BUY':
                    risk_pct = (self.config['BASE_RISK_PERCENT'] / 100.0) * strength
                    risk_usd = total_eq * risk_pct
                    cp = self.data_1m[pair]['close'].iloc[-1]
                    
                    # Sync SL distance logic with analyze() for accurate sizing
                    mult = self.config.get('ATR_SL_MULT', 2.5)
                    if setup_name == 'V148_Downtrend_Scalp':
                        mult = min(mult, 1.5)
                    sl_min_pct = self.config.get('SL_MIN_PCT', 0.015)
                    sl_max_pct = self.config.get('SL_MAX_PCT', 0.030)
                    sl_dist = (mult * entry_atr) if entry_atr else (cp * 0.02)
                    sl_dist = min(max(sl_dist, cp * sl_min_pct), cp * sl_max_pct)
                    
                    amt = (risk_usd / sl_dist) * cp
                    max_risk_cap = total_eq * (self.config['MAX_RISK_PER_TRADE_PERCENT'] / 100.0) * strength
                    amt = min(amt, max_risk_cap)
                    amt = max(amt, self.exchange_info[pair]['minNotional'] * 1.1)
                    
                    if amt > free_balance * 0.99:
                        amt = free_balance * 0.99
                    
                    amt_rounded = math.floor(amt * 100) / 100.0
                    if amt_rounded < self.exchange_info[pair]['minNotional'] or amt_rounded > free_balance:
                        return False
                    order = await self.client.create_order(symbol=pair, side='BUY', type='MARKET', quoteOrderQty=amt_rounded)
                else:
                    asset = pair.replace('USDT', '')
                    q_r = await self.client.get_asset_balance(asset=asset)
                    q = float(q_r['free'])
                    fq = self.format_quantity(pair, q)
                    if float(fq) * self.data_1m[pair]['close'].iloc[-1] > self.exchange_info[pair]['minNotional']:
                        order = await self.client.create_order(symbol=pair, side='SELL', type='MARKET', quantity=fq)
                    else:
                        self.positions[pair] = {'entries': 0, 'qty': 0.0}
                        self.save_active_positions()
                        return True
                if side == 'SELL':
                    self.last_trade_time[pair] = time.time()
                if order.get('fills') and len(order['fills']) > 0:
                    total_f_qty = sum(float(f['qty']) for f in order['fills'])
                    ep = sum(float(f['price']) * float(f['qty']) for f in order['fills']) / total_f_qty if total_f_qty > 0 else float(order['fills'][0]['price'])
                else:
                    ep = self.data_1m[pair]['close'].iloc[-1]
                eq = float(order['executedQty'])
                
                # Correctly calculate total fee in USDT to prevent database corruption from phantom fees
                total_fee_usdt = 0.0
                if order.get('fills'):
                    bnb_price = 600.0
                    try:
                        ticker = await self.client.get_symbol_ticker(symbol="BNBUSDT")
                        bnb_price = float(ticker['price'])
                    except Exception:
                        pass

                    for f in order['fills']:
                        comm = float(f.get('commission', 0))
                        comm_asset = f.get('commissionAsset')
                        if comm_asset == 'USDT':
                            total_fee_usdt += comm
                        elif comm_asset == 'BNB':
                            total_fee_usdt += comm * bnb_price
                        elif comm_asset == pair.replace('USDT', ''):
                            fill_price = float(f.get('price', ep))
                            total_fee_usdt += comm * fill_price
                        else:
                            fill_price = float(f.get('price', ep))
                            total_fee_usdt += comm * fill_price
                
                config_snapshot = json.dumps(self.config)
                await asyncio.to_thread(log_trade, pair, side, ep, eq, total_fee_usdt, 'USDT', config_snapshot)
                if side == 'BUY': self.positions[pair] = {'entries': 1, 'entry_price': ep, 'qty': eq, 'max_p': ep, 'time': time.time(), 'sl': ep - sl_dist, 'setup': setup_name or 'V144', 'entry_atr': entry_atr}
                else:
                    # Track if this was a winning or losing trade for adaptive cooldown (per-pair)
                    entry_price = self.positions[pair].get('entry_price', ep)
                    self._pair_last_loss[pair] = (ep < entry_price)
                    if ep < entry_price:
                        self.failed_trades_history.append(time.time())
                        # clean up old ones
                        self.failed_trades_history = [t for t in self.failed_trades_history if time.time() - t <= 3600]
                    self.positions[pair] = {'entries': 0, 'qty': 0.0}
                self.save_active_positions()
                
                # Dynamic update of last_total_equity to reflect current assets + cash
                try:
                    bal_r = await self.client.get_asset_balance(asset='USDT')
                    free_balance = float(bal_r['free'])
                    total_val = free_balance
                    for p, pos_val in self.positions.items():
                        if pos_val.get('entries', 0) > 0:
                            price = pos_val.get('current_price', pos_val.get('entry_price', 0.0))
                            total_val += pos_val['qty'] * price
                    self.last_total_equity = total_val
                    print(f"Updated last_total_equity after trade: {self.last_total_equity:.2f}")
                except Exception as e:
                    print(f"Error updating total equity: {e}")
                
                return True
            except Exception as e:
                err = str(e).lower()
                if "-2010" in err or "not permitted" in err:
                    self.restricted_pairs.add(pair)
                    self.save_restricted_pairs()
                    if pair in self.tracked_pairs: self.tracked_pairs.remove(pair)
                    if side == 'SELL':
                        self.positions[pair] = {'entries': 0, 'qty': 0.0}
                        self.save_active_positions()
                await asyncio.to_thread(log_failed_trade, pair, err)
                return False

    def format_quantity(self, pair, q):
        ss = self.exchange_info[pair]['stepSize']
        prec = len(format(ss, 'f').split('.')[-1].rstrip('0')) if ss < 1.0 else 0
        return format(floor_step(q, ss), f'.{prec}f')

if __name__ == "__main__":
    init_db()
    asyncio.run(TradingBot().start())
