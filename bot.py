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
        self.ema_cache = {} # pair: {'atr_1h': float, 'er': float}
        self.market_trend = {'btc_uptrend_15m': True}
        self.exchange_info = {} # pair: filters
        self.last_trade_time = {} # pair: timestamp
        self.last_dust_time = 0 # Track dust conversion frequency
        self.last_positions_save = 0 # Throttle position saves
        self._pair_last_loss = {} # Per-pair loss tracking for adaptive cooldown
        self.failed_trades_history = []
        self.circuit_breaker_until = 0
        self.trade_lock = asyncio.Lock()
        
        # Strategy V160 - Volatile Momentum & Decoupling Squeeze
        self.config = {}
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
            # TTL: the AI Manager runs hourly, so overrides should be refreshed each hour.
            # If the file is older than TACTICAL_OVERRIDES_TTL_SEC (default 90 min = one missed
            # cycle of grace), treat it as stale and revert to neutral baseline risk rather than
            # applying an outdated posture/whitelist indefinitely (e.g. when ai_manager is skipped
            # due to the credit gate).
            ttl_sec = self.base_config.get('TACTICAL_OVERRIDES_TTL_SEC', 5400)
            overrides_fresh = False
            if os.path.exists(overrides_path):
                try:
                    age_sec = time.time() - os.path.getmtime(overrides_path)
                    overrides_fresh = age_sec <= ttl_sec
                    if not overrides_fresh:
                        print(f"Ignoring tactical_overrides.json: stale ({int(age_sec)}s old > {ttl_sec}s TTL). Using neutral baseline.")
                except Exception as ae:
                    print(f"Could not determine tactical_overrides age: {ae}")
            if os.path.exists(overrides_path) and overrides_fresh:
                try:
                    with open(overrides_path, 'r') as f:
                        overrides = json.load(f)
                    risk_mult = overrides.get('RISK_MULTIPLIER', 1.0)
                    sl_offset = overrides.get('SL_MULT_OFFSET', 0.0)
                    self.config['BASE_RISK_PERCENT'] = self.base_config['BASE_RISK_PERCENT'] * risk_mult
                    self.config['ATR_SL_MULT'] = self.base_config['ATR_SL_MULT'] + sl_offset
                    self.config['PORTFOLIO_EJECT'] = self.base_config['PORTFOLIO_EJECT'] + overrides.get('PORTFOLIO_EJECT_OFFSET', 0.0)
                    self.config['VOL_SPIKE_MULTIPLIER'] = self.base_config.get('VOL_SPIKE_MULTIPLIER', 1.5) + overrides.get('VOL_SPIKE_MULT_OFFSET', 0.0)
                    print(f"Loaded config with tactical overrides: Risk Mult={risk_mult}, SL Offset={sl_offset}")
                except Exception as oe:
                    print(f"Error loading tactical overrides: {oe}")
            else:
                print("Loaded configuration from config.json (No fresh overrides active)")
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
        
        self.last_free_usdt = usdt_free
        total_val = usdt_free
        for pair, pos in self.positions.items():
            if pos.get('entries', 0) > 0:
                price = price_map.get(pair, pos['entry_price'])
                total_val += pos['qty'] * price
        
        self.last_total_equity = total_val
        print(f"Current USDT Balance: {usdt_free} | Initialized Total Portfolio Equity: {self.last_total_equity}")
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        
        # Non-tradeable pairs (stablecoins, fiat, tokenized-equity products) come from
        # config.json ("EXCLUDED_PAIRS"). Fallback keeps the bot safe if the key is missing.
        blacklisted = self.config.get('EXCLUDED_PAIRS', [
            'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT',
            'XAUTUSDT', 'QQQBUSDT'
        ])
        candidates = []
        min_vol = self.config.get('MIN_VOLATILITY', 0.002)
        for p in usdt_pairs:
            symbol = p['symbol']
            if symbol in blacklisted or symbol in self.restricted_pairs: continue
            if any(symbol.endswith(sfx) for sfx in ['UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT']): continue
            if symbol in self.exchange_info and not self.exchange_info[symbol]['isAllowed']: continue
            # Automatic volatility filter: drop non-volatile pairs (e.g. stablecoin/fiat pairs
            # like USDCUSDT, DAIUSDT) by principle rather than by a manual blacklist. Uses the
            # 24h high/low range as a cheap proxy from data already in the ticker.
            try:
                hi = float(p.get('highPrice', 0))
                lo = float(p.get('lowPrice', 0))
                last = float(p.get('lastPrice', 0)) or hi
                if last > 0 and ((hi - lo) / last) < min_vol:
                    continue
            except (TypeError, ValueError, ZeroDivisionError):
                pass
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
        
        # Check tactical_overrides.json for AI Manager whitelisting (social sentiment / news hypes)
        try:
            overrides_path = 'tactical_overrides.json'
            ttl_sec = self.base_config.get('TACTICAL_OVERRIDES_TTL_SEC', 5400)
            overrides_fresh = os.path.exists(overrides_path) and (time.time() - os.path.getmtime(overrides_path)) <= ttl_sec
            if os.path.exists(overrides_path) and not overrides_fresh:
                print("Ignoring stale tactical_overrides.json whitelist (past TTL).")
            if overrides_fresh:
                with open(overrides_path, 'r') as f:
                    overrides = json.load(f)
                # Build a 24h volatility lookup so whitelist pairs face the same filter as candidates.
                vol_by_symbol = {}
                for p in usdt_pairs:
                    try:
                        hi = float(p.get('highPrice', 0)); lo = float(p.get('lowPrice', 0))
                        last = float(p.get('lastPrice', 0)) or hi
                        if last > 0:
                            vol_by_symbol[p['symbol']] = (hi - lo) / last
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
                whitelist = overrides.get('whitelist_add', [])
                for pair in whitelist:
                    # Exclusions take priority over the whitelist: never re-add a pair that is
                    # blacklisted, learned-restricted, or below the strategy's volatility floor.
                    if pair in blacklisted or pair in self.restricted_pairs:
                        print(f"Ignoring whitelist pair {pair}: excluded (blacklist/restricted).")
                        continue
                    if vol_by_symbol.get(pair, 1.0) < min_vol:
                        print(f"Ignoring whitelist pair {pair}: below MIN_VOLATILITY.")
                        continue
                    if pair not in valid_pairs and await self.test_symbol_permission(pair):
                        print(f"Force tracking AI Manager whitelist pair: {pair}")
                        valid_pairs.append(pair)
        except Exception as e:
            print(f"Error loading AI Manager whitelist: {e}")

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
                    
                    # Dynamically spawn websockets for new whitelisted pairs.
                    # Only honor the whitelist while overrides are fresh (within TTL); a stale
                    # whitelist must not keep force-tracking outdated hyped pairs. (Blacklist_add
                    # above is left unguarded since dropping pairs is always the conservative action.)
                    ttl_sec = self.base_config.get('TACTICAL_OVERRIDES_TTL_SEC', 5400)
                    whitelist_fresh = (time.time() - os.path.getmtime(overrides_path)) <= ttl_sec
                    whitelist = overrides.get('whitelist_add', []) if whitelist_fresh else []
                    for pair in whitelist:
                        if pair not in self.tracked_pairs and pair not in self.restricted_pairs:
                            if await self.test_symbol_permission(pair):
                                print(f"Dynamic Whitelist: Spawning live stream for {pair}...")
                                self.tracked_pairs.append(pair)
                                try:
                                    klines = await self.client.get_historical_klines(pair, AsyncClient.KLINE_INTERVAL_1MINUTE, "6 hours ago UTC")
                                    if len(klines) > 1: klines = klines[:-1]
                                    if klines:
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
                                        
                                        with open('/root/tracked_pairs.json', 'w') as f:
                                            json.dump({'tracked': self.tracked_pairs}, f)
                                            
                                        stream = self.bm.kline_socket(pair, interval='1m')
                                        asyncio.create_task(self.handle_socket(stream, pair))
                                except Exception as e:
                                    print(f"Error initializing dynamic pair {pair}: {e}")

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
        import re
        if not re.match(r'^[A-Z0-9]{2,10}USDT$', symbol):
            return False
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
            klines_15m = await self.client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, "10 days ago UTC")
            if len(klines_15m) > 1: klines_15m = klines_15m[:-1]
            closes_15m = pd.Series([float(k[4]) for k in klines_15m])
            btc_cp_15m = closes_15m.iloc[-1]
            btc_ret_4h = (btc_cp_15m - closes_15m.iloc[-17]) / closes_15m.iloc[-17] * 100 if len(closes_15m) > 16 else 0.0
            btc_ret_24h = (btc_cp_15m - closes_15m.iloc[-97]) / closes_15m.iloc[-97] * 100 if len(closes_15m) > 96 else 0.0

            if len(closes_15m) >= 96:
                high_24h = max([float(k[2]) for k in klines_15m[-96:]])
                low_24h = min([float(k[3]) for k in klines_15m[-96:]])
                btc_daily_range_pct = (high_24h - low_24h) / low_24h * 100
            else:
                btc_daily_range_pct = 1.0
            self.market_trend['btc_daily_range_pct'] = btc_daily_range_pct

            self.market_trend = {
                'btc_4h_return': btc_ret_4h,
                'btc_24h_return': btc_ret_24h
            }
            print("--- Market Status Update (Strategy V160 - Volatile Momentum & Decoupling Squeeze) ---")
            print(f"BTC 4h Return: {btc_ret_4h:+.2f}% | 24h: {btc_ret_24h:+.2f}%")
            
            # Fetch 15m and 1h context data for all pairs in parallel batches
            async def fetch_pair_ema(p):
                try:
                    kl_1h = await self.client.get_historical_klines(p, AsyncClient.KLINE_INTERVAL_1HOUR, "10 days ago UTC")
                    if len(kl_1h) > 1: kl_1h = kl_1h[:-1]
                    high_1h = pd.Series([float(k[2]) for k in kl_1h])
                    low_1h = pd.Series([float(k[3]) for k in kl_1h])
                    close_1h = pd.Series([float(k[4]) for k in kl_1h])
                    vol_1h_series = pd.Series([float(k[5]) for k in kl_1h])
                    
                    cache_data = {}
                    if len(close_1h) >= 20:
                        atr_1h = ta.atr(high_1h, low_1h, close_1h, length=14)
                        cache_data.update({'atr_1h': atr_1h.iloc[-1]})
                        
                    if len(close_1h) >= 25 and 'atr_1h' in cache_data:
                        cache_data.update({'hourly_volume': vol_1h_series.iloc[-1]})
                        cache_data.update({'vol_1h_avg_24h': vol_1h_series.iloc[-24:].mean()})

                        if len(close_1h) >= 5:
                            cache_data.update({'altcoin_4h_return': (close_1h.iloc[-1] - close_1h.iloc[-5]) / close_1h.iloc[-5] * 100})
                        else:
                            cache_data.update({'altcoin_4h_return': 0.0})
                            
                        cache_data.update({'high_1h': high_1h.iloc[-1], 'low_1h': low_1h.iloc[-1], 'close_1h': close_1h.iloc[-1]})
                        
                        if len(close_1h) >= 24:
                            high_24h_alt = high_1h.iloc[-24:].max()
                            low_24h_alt = low_1h.iloc[-24:].min()
                            cache_data.update({'alt_daily_range_pct': (high_24h_alt - low_24h_alt) / low_24h_alt * 100})
                        else:
                            cache_data.update({'alt_daily_range_pct': 0.0})
                            
                        ema_fast_len = self.config.get('EMA_FAST', 20)
                        ema_slow_len = self.config.get('EMA_SLOW', 50)
                        if len(close_1h) >= ema_slow_len:
                            ema20 = ta.ema(close_1h, length=ema_fast_len)
                            ema50 = ta.ema(close_1h, length=ema_slow_len)
                            if ema20 is not None and not ema20.empty:
                                cache_data.update({'ema_20_1h': ema20.iloc[-1]})
                            if ema50 is not None and not ema50.empty:
                                cache_data.update({'ema_50_1h': ema50.iloc[-1]})
                        
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
                
            db_df = None
            
            for asset, actual_qty in balances.items():
                if asset in ('USDT', 'BNB', 'FDUSD', 'USDC'):
                    continue
                pair = f"{asset}USDT"
                
                if pair in cached_positions:
                    cache = cached_positions[pair]
                    entry_p = float(cache.get('entry_price', 0.0) or 0.0)
                    if actual_qty * entry_p < 4.0:
                        continue
                    self.positions[pair] = {
                        'entries': 1,
                        'entry_price': cache.get('entry_price'),
                        'qty': actual_qty,
                        'max_p': cache.get('max_p', cache.get('entry_price')),
                        'sl': cache.get('sl'),
                        'time': cache.get('time', time.time()),
                        'setup': cache.get('setup'),
                        'entry_atr': cache.get('entry_atr')
                    }
                    print(f"Synced {pair} from cache. SL: {self.positions[pair]['sl']:.6f}")
                else:
                    if db_df is None:
                        db_df = await asyncio.to_thread(read_db)
                        
                    row = db_df[db_df['pair'] == pair]
                    if not row.empty and row.iloc[0]['side'] == 'BUY':
                        r = row.iloc[0]
                        if actual_qty * float(r['price']) < 4.0:
                            continue
                        fallback_time = time.time()
                        try:
                            if 'timestamp' in r and pd.notna(r['timestamp']):
                                dt = pd.to_datetime(r['timestamp'])
                                if dt.tzinfo is None:
                                    dt = dt.tz_localize('UTC')
                                fallback_time = dt.timestamp()
                        except: pass
                        
                        self.positions[pair] = {
                            'entries': 1, 'entry_price': r['price'], 'qty': actual_qty,
                            'max_p': r['price'], 'sl': r['price'] * 0.98, 'time': fallback_time
                        }
                        print(f"Synced {pair} from DB (no cache). Fallback Entry: {r['price']}, Qty: {actual_qty}")
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
                    trail_trigger = self.config.get('TRAILING_TRIGGER', 0.08)
                    trail_dist = self.config.get('TRAILING_DIST', 0.035)
                    
                    hold_seconds = time.time() - pos.get('time', time.time())
                    
                    if profit_pct > trail_trigger:
                        sl = max(sl, cp * (1.0 - trail_dist))
                        self.positions[pair]['sl'] = sl
                    
                    if sl != old_sl or self.positions[pair].get('max_p', 0) != old_max_p:
                        if time.time() - self.last_positions_save > 30:
                            self.save_active_positions()
                            self.last_positions_save = time.time()

                    take_profit = self.config.get('TAKE_PROFIT', 0.0)
                    

                    exit_reason = None
                    
                    if hold_seconds > self.config.get('PROFIT_LOCK_TIME_H', 18) * 3600 and profit_pct >= self.config.get('PROFIT_LOCK_PCT', 0.005):
                        profit_lock = pos['entry_price'] * (1.0 + self.config.get('PROFIT_LOCK_PCT', 0.005))
                        sl = max(sl, profit_lock)
                        self.positions[pair]['sl'] = sl
                    if hold_seconds > 24 * 3600 and profit_pct >= 0.01:
                        sl = max(sl, pos['entry_price'] * 1.003)
                        self.positions[pair]['sl'] = sl
                        
                    if hold_seconds > self.config.get('STALENESS_TIME_H', 24) * 3600:
                        if self.config.get('STALENESS_EXIT_MIN', -0.005) <= profit_pct <= self.config.get('STALENESS_EXIT_MAX', 0.005):
                            exit_reason = 'StalenessExit'

                    in_profit = profit_pct >= self.config.get('MIN_PROFIT_TRIGGER', 0.10)
                    
                    bb_upper_cp = cp * 1.1
                    if hasattr(self, 'current_indicators') and pair in self.current_indicators:
                        bb_upper_cp = self.current_indicators[pair].get('bb_upper', cp * 1.1)
                            
                    price_stretched = cp >= bb_upper_cp * self.config.get('BB_EXTENSION_PCT', 1.02)
                    
                    ema_data = self.ema_cache.get(pair, {})
                    hourly_vol = ema_data.get('hourly_volume', 0.0)
                    avg_vol = ema_data.get('vol_1h_avg_24h', 1.0)
                    volume_climax = hourly_vol >= self.config.get('CLIMAX_VOL_MULT', 2.5) * avg_vol
                    
                    high_1h = ema_data.get('high_1h', cp)
                    low_1h = ema_data.get('low_1h', cp)
                    close_1h = ema_data.get('close_1h', cp)
                    
                    exhaustion_candle = False
                    if (high_1h - low_1h) > 0:
                        exhaustion_candle = (high_1h - close_1h) > (close_1h - low_1h)
                        
                    if in_profit and price_stretched and volume_climax and exhaustion_candle:
                        exit_reason = 'Volume_Climax_Harvest'
                    
                    
                            
                    if exit_reason:
                        print(f"⚠️ FORCE EXIT: {pair} Reason: {exit_reason}")
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
        
        # Calculate current equity exactly: cash + current value of positions
        current_equity = getattr(self, 'last_free_usdt', getattr(self, 'last_total_equity', 1000.0))
        
        for p in active:
            pos = self.positions[p]
            current_p = pos.get('current_price', pos['entry_price'])
            if hasattr(self, 'last_free_usdt'):
                current_equity += pos['qty'] * current_p
            total_unrealized_usd += (current_p - pos['entry_price']) * pos['qty']
            
        if not hasattr(self, 'last_free_usdt'):
            current_equity += total_unrealized_usd
            
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
            
        circuit_breaker_dd = self.config.get('CIRCUIT_BREAKER_1H_DD', 0.035)
        if drawdown_1h > circuit_breaker_dd or len([t for t in self.failed_trades_history if time.time() - t <= 3600]) >= 3:
            if self.circuit_breaker_until < time.time():
                print(f"🛑 CIRCUIT BREAKER TRIPPED! Drawdown: {drawdown_1h*100:.2f}%, Fails: {len([t for t in self.failed_trades_history if time.time() - t <= 3600])}")
                self.circuit_breaker_until = time.time() + 4 * 3600
        
        pnl_pct = (total_unrealized_usd / current_equity) * 100 if current_equity > 0 else 0
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
            c = data['close']
            
            bb = ta.bbands(c, length=20, std=2.0)
            if bb is not None and not bb.empty:
                bb_upper = bb['BBU_20_2.0_2.0'].iloc[-1]
                
                sma20_series = bb['BBM_20_2.0_2.0']
                
                bbw = (bb['BBU_20_2.0_2.0'] - bb['BBL_20_2.0_2.0']) / sma20_series
                bb_width = bbw.iloc[-1]
                bb_width_prev = bbw.iloc[-2] if len(bbw) >= 2 else bb_width
            else:
                bb_upper = c.iloc[-1] * 1.1
                bb_width = 0.0
                bb_width_prev = 0.0
                
            return bb_upper, bb_width, bb_width_prev

        try:
            bb_upper, bb_width, bb_width_prev = await asyncio.to_thread(calc_indicators, df)
        except Exception as e:
            print(f"Indicator calculation error {pair}: {e}")
            return
            
        ema_data = self.ema_cache.get(pair, {})
        atr = cp * 0.01
        if ema_data:
            atr = ema_data.get('atr_1h', cp * 0.01)
            
        if not hasattr(self, 'current_indicators'):
            self.current_indicators = {}
        self.current_indicators[pair] = {
            'atr': float(atr),
            'bb_upper': float(bb_upper),
            'btc_4h_ret': float(self.market_trend.get('btc_4h_return', 0.0)),
            'alt_4h_ret': float(ema_data.get('altcoin_4h_return', 0.0)),
            'hourly_vol': float(ema_data.get('hourly_volume', 0.0)),
            'avg_vol': float(ema_data.get('vol_1h_avg_24h', 0.0)),
            'bb_width': float(bb_width),
            'bb_width_prev': float(bb_width_prev)
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

            hourly_vol = ema_data.get('hourly_volume', 0.0)
            avg_vol = ema_data.get('vol_1h_avg_24h', 0.0)
            
            btc_4h_ret = self.market_trend.get('btc_4h_return', 0.0)
            alt_4h_ret = ema_data.get('altcoin_4h_return', 0.0)
            
            is_macro_decoupled = self.config.get('DECOUPLE_BTC_MIN', -3.0) <= btc_4h_ret <= self.config.get('DECOUPLE_BTC_MAX', 1.0) and alt_4h_ret > (btc_4h_ret + self.config.get('DECOUPLE_ALT_RET', 3.0))
            
            if is_macro_decoupled:
                if hourly_vol > self.config.get('VOL_THRESHOLD', 1.5) * avg_vol:
                    if cp > bb_upper and bb_width > bb_width_prev:
                        setup = "Decoupled_Squeeze_Breakout"
            
            alt_daily_range_pct = ema_data.get('alt_daily_range_pct', 0.0)
            btc_daily_range_pct = self.market_trend.get('btc_daily_range_pct', 1.0)
            relative_range = alt_daily_range_pct / max(btc_daily_range_pct, 1.0)
            is_high_beta_decoupler = relative_range >= self.config.get('RDR_MIN', 1.6)
            
            ema_20_1h = ema_data.get('ema_20_1h', 0.0)
            ema_50_1h = ema_data.get('ema_50_1h', 0.0)
            trend_aligned = cp > ema_20_1h > ema_50_1h if ema_50_1h > 0 else False
            volume_confirmed = hourly_vol > self.config.get('VOL_THRESHOLD', 1.5) * avg_vol
            
            if is_high_beta_decoupler and is_macro_decoupled and trend_aligned and volume_confirmed:
                setup = "Decoupled_Trend_Continuation"

            if setup:
                volatility = atr / cp
                mx_v = self.config.get('VOLATILITY_CAP', 0.015)
                if volatility > mx_v or volatility < self.config.get('MIN_VOLATILITY', 0.001): return
                
                # Dynamic portfolio strength scaling
                size_strength = 1.0
                if active_count == 1: size_strength = self.config.get('SCALE_1_POS', 0.8)
                elif active_count == 2: size_strength = self.config.get('SCALE_2_POS', 0.6)
                elif active_count >= 3: size_strength = self.config.get('SCALE_3_POS', 0.4)
                
                
                    
                await self.execute_trade(pair, 'BUY', strength=size_strength, entry_atr=atr, setup_name=setup)
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
                    if hasattr(self, 'market_trend'):
                        btc_24h_ret_risk = self.market_trend.get('btc_24h_return', 0.0)
                        if btc_24h_ret_risk <= -3.0:
                            risk_pct *= 0.5
                        elif btc_24h_ret_risk < -1.0:
                            risk_pct *= 0.8
                    risk_usd = total_eq * risk_pct
                    cp = self.data_1m[pair]['close'].iloc[-1]
                    
                    mult = self.config.get('ATR_SL_MULT', 2.5)
                    sl_min_pct = self.config.get('SL_MIN_PCT', 0.06)
                    sl_dist = (mult * entry_atr) if entry_atr else (cp * 0.02)
                    sl_dist = max(sl_dist, cp * sl_min_pct)
                    sl_max_pct = self.config.get('SL_MAX_PCT', 0.07)
                    sl_dist = min(sl_dist, cp * sl_max_pct)
                    
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
                if side == 'BUY': self.positions[pair] = {'entries': 1, 'entry_price': ep, 'qty': eq, 'max_p': ep, 'time': time.time(), 'sl': ep - sl_dist, 'setup': setup_name or 'V158', 'entry_atr': entry_atr}
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
                    self.last_free_usdt = free_balance
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
