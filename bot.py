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
        self.market_trend = {'btc_uptrend': True, 'btc_rsi': 50}
        self.exchange_info = {} # pair: filters
        self.last_trade_time = {} # pair: timestamp
        self.last_dust_time = 0 # Track dust conversion frequency
        self.last_positions_save = 0 # Throttle position saves
        self._pair_last_loss = {} # Per-pair loss tracking for adaptive cooldown
        self.trade_lock = asyncio.Lock()
        
        # Strategy V114 MACD Momentum
        self.config = {
            'EMA_FAST': 50,
            'EMA_SLOW': 200,
            'MIN_VOLATILITY': 0.0010,
            'BASE_RISK_PERCENT': 2.0,
            'MAX_RISK_PER_TRADE_PERCENT': 15.0,
            'COOLDOWN_PERIOD': 600,
            'MAX_PAIRS': 40,
            'PORTFOLIO_EJECT': -5.0,
            'PORTFOLIO_HARVEST': 4.0,
            'VOL_SPIKE_MULTIPLIER': 1.5,
            'SL_MIN_PCT': 0.015,
            'SL_MAX_PCT': 0.030,
            'BE_TRIGGER': 0.020,
            'BE_LOCK': 0.002,
            'TRAILING_TRIGGER': 0.040,
            'TRAILING_DIST': 0.020,
            'VOLATILITY_CAP': 0.015,
            'ATR_SL_MULT': 3.0,
            'SCALE_1_POS': 0.8,
            'SCALE_2_POS': 0.6,
            'SCALE_3_POS': 0.4
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
                    
                    self.config['BASE_RISK_PERCENT'] = self.base_config['BASE_RISK_PERCENT'] * overrides.get('RISK_MULTIPLIER', 1.0)
                    self.config['ATR_SL_MULT'] = self.base_config['ATR_SL_MULT'] + overrides.get('SL_MULT_OFFSET', 0.0)
                    self.config['PORTFOLIO_EJECT'] = self.base_config['PORTFOLIO_EJECT'] + overrides.get('PORTFOLIO_EJECT_OFFSET', 0.0)
                    print(f"Loaded config with tactical overrides: Risk Mult={overrides.get('RISK_MULTIPLIER', 1.0)}, SL Offset={overrides.get('SL_MULT_OFFSET', 0.0)}")
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
                       'FETUSDT', 'INJUSDT', 'NEARUSDT', 'DOTUSDT', 'FILUSDT', 'LDOUSDT', 'XECUSDT', 'SHIBUSDT', 'DODOUSDT']
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
                if not klines: continue
                df = pd.DataFrame(klines, columns=['t','o','h','l','c','v','ct','qav','nt','tbb','tbq','i'])
                self.data_1m[pair] = pd.DataFrame({
                    'timestamp': pd.to_datetime([int(x) for x in df['t']], unit='ms'),
                    'open': df['o'].astype(float),
                    'high': df['h'].astype(float),
                    'low': df['l'].astype(float),
                    'close': df['c'].astype(float),
                    'volume': df['v'].astype(float)
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
                        'tickSize': float(f['PRICE_FILTER']['tickSize']),
                        'minNotional': float(f.get('NOTIONAL', f.get('MIN_NOTIONAL'))['minNotional']),
                        'isAllowed': s['status'] == 'TRADING' and 'MARKET' in s['orderTypes']
                    }
        except Exception as e:
            print(f"Exchange info error: {e}")

    async def fetch_macro_trends(self):
        try:
            klines = await self.client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1HOUR, "10 days ago UTC")
            if len(klines) > 1: klines = klines[:-1]
            closes = pd.Series([float(k[4]) for k in klines])
            ema200 = ta.ema(closes, length=200).iloc[-1]
            rsi = ta.rsi(closes, length=14).iloc[-1]

            klines_15m = await self.client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, "3 days ago UTC")
            if len(klines_15m) > 1: klines_15m = klines_15m[:-1]
            closes_15m = pd.Series([float(k[4]) for k in klines_15m])
            ema200_15m = ta.ema(closes_15m, length=200).iloc[-1]
            btc_cp_15m = closes_15m.iloc[-1]

            self.market_trend = {
                'btc_uptrend': closes.iloc[-1] > ema200,
                'btc_rsi': rsi,
                'btc_uptrend_15m': btc_cp_15m > ema200_15m
            }
            print("--- Market Status Update (Strategy V114 - MACD Momentum) ---")
            print(f"BTC RSI: {rsi:.2f} | BTC 15m Trend: {'UP' if btc_cp_15m > ema200_15m else 'DOWN'}")
            
            # Fetch 15m EMA data for all pairs in parallel batches
            async def fetch_pair_ema(p):
                try:
                    kl = await self.client.get_historical_klines(p, AsyncClient.KLINE_INTERVAL_15MINUTE, "6 days ago UTC")
                    if len(kl) > 1: kl = kl[:-1]
                    cl = pd.Series([float(k[4]) for k in kl])
                    if len(cl) >= 200:
                        ef = ta.ema(cl, length=self.config['EMA_FAST']).iloc[-1]
                        es = ta.ema(cl, length=self.config['EMA_SLOW']).iloc[-1]
                        es_prev = ta.ema(cl, length=self.config['EMA_SLOW']).iloc[-5]
                        slope = (es - es_prev) / es_prev
                        self.ema_cache[p] = {'ema_f': ef, 'ema_s': es, 'slope': slope}
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
            await asyncio.sleep(900)
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
                    # Minimum hold period: don't tighten stops in first 6 hours
                    trail_trigger = self.config.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = self.config.get('TRAILING_DIST', 0.020)
                    be_trigger = self.config.get('BE_TRIGGER', 0.020)
                    be_lock = self.config.get('BE_LOCK', 0.002)
                    
                    hold_seconds = time.time() - pos.get('time', time.time())
                    min_hold_passed = hold_seconds > 6 * 3600  # 6 hours
                    
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

                    take_profit = self.config.get('TAKE_PROFIT', 0.0)
                    if take_profit > 0 and profit_pct >= take_profit:
                        print(f"💰 TAKE PROFIT: {pair} reached TP target")
                        await self.execute_trade(pair, 'SELL')
                        continue

                    if sl > 0 and cp <= sl:
                        await self.execute_trade(pair, 'SELL')
                        continue
                if k['x']:
                    def update_data(df, t, o, h, l, c_val, v):
                        new_row = pd.DataFrame({'timestamp':[pd.to_datetime(t, unit='ms')],'open':[float(o)],'high':[float(h)],'low':[float(l)],'close':[float(c_val)],'volume':[float(v)]})
                        return pd.concat([df, new_row], ignore_index=True).iloc[-300:]
                    self.data_1m[pair] = await asyncio.to_thread(update_data, self.data_1m[pair], k['t'], k['o'], k['h'], k['l'], k['c'], k['v'])
                    await self.analyze(pair)

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
            
            if pos.get('time') and (time.time() - pos['time']) > 12 * 3600:
                print(f"⏰ TIME EXIT: {p} held for >12h, closing position from central loop")
                await self.execute_trade(p, 'SELL')
            
        pnl_pct = (total_unrealized_usd / current_equity) * 100 if current_equity > 0 else 0
        reason = None
        if pnl_pct <= self.config.get('PORTFOLIO_EJECT', -5.0): reason = "GLOBAL_EJECT"
        elif pnl_pct >= self.config.get('PORTFOLIO_HARVEST', 4.0): reason = "GLOBAL_HARVEST"
        if reason:
            print(f"⚠️ {reason} TRIGGERED! Total PnL: {pnl_pct:.2f}%")
            for p in active: await self.execute_trade(p, 'SELL')
            bal = await self.client.get_asset_balance(asset='USDT')
            self.last_total_equity = float(bal['free'])

    async def analyze(self, pair):
        if pair in self.restricted_pairs or pair not in self.data_1m: return
        df = self.data_1m[pair]
        if len(df) < 250: return
        def calc_indicators(data):
            c, h, l, v = data['close'], data['high'], data['low'], data['volume']
            cp = c.iloc[-1]
            vol = v.iloc[-1]
            atr = ta.atr(h, l, c).iloc[-1]
            sma200_series = ta.sma(c, length=200)
            sma200 = sma200_series.iloc[-1] if sma200_series is not None and len(sma200_series) >= 200 else cp
            rsi_series = ta.rsi(c, length=14)
            rsi = rsi_series.iloc[-1]
            rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 else 50.0
            
            macd_data = ta.macd(c)
            macd = macd_data['MACD_12_26_9'].iloc[-1] if macd_data is not None and len(macd_data) >= 1 else 0.0
            hist_curr = macd_data['MACDh_12_26_9'].iloc[-1] if macd_data is not None and len(macd_data) >= 2 else 0.0
            hist_prev = macd_data['MACDh_12_26_9'].iloc[-2] if macd_data is not None and len(macd_data) >= 2 else 0.0
            
            adx_data = ta.adx(h, l, c)
            adx = adx_data['ADX_14'].iloc[-1] if adx_data is not None and len(adx_data) >= 1 else 0.0
            
            vol_sma_window = self.config.get('VOLUME_SMA_WINDOW', 20)
            vol_sma_series = v.rolling(window=vol_sma_window).mean()
            vol_sma = vol_sma_series.iloc[-1] if not vol_sma_series.empty else vol
            
            return cp, atr, sma200, rsi, rsi_prev, hist_curr, hist_prev, macd, adx, vol, vol_sma

        try:
            cp, atr, sma200, rsi, _, hist_curr, hist_prev, macd, adx, vol, vol_sma = await asyncio.to_thread(calc_indicators, df)
        except Exception as e:
            print(f"Indicator calculation error {pair}: {e}")
            return

        pos = self.positions.get(pair, {'entries': 0})

        # Strategy V114 MACD Momentum
        if pos['entries'] == 0:
            base_cooldown = self.config.get('COOLDOWN_PERIOD', 600)
            pair_had_loss = self._pair_last_loss.get(pair, False)
            cooldown = base_cooldown if not pair_had_loss else 4 * 3600
            if (time.time() - self.last_trade_time.get(pair, 0)) < cooldown: return
            active_count = len([p for p in self.positions if self.positions[p]['entries'] > 0])
            
            max_concurrent = self.config.get('MAX_PAIRS', 40) // 4
            if active_count >= max_concurrent: return
            
            setup = None
            
            ema_data = self.ema_cache.get(pair)
            pair_uptrend_15m = True
            if ema_data:
                pair_uptrend_15m = ema_data['ema_f'] > ema_data['ema_s'] and ema_data['slope'] > 0
            
            if self.market_trend.get('btc_uptrend') and self.market_trend.get('btc_uptrend_15m') and pair_uptrend_15m:
                if cp > sma200:
                    if hist_curr > 0 and hist_prev <= 0 and macd > 0 and adx > 25 and rsi > 40 and rsi < 70 and vol > vol_sma * 2.0:
                        setup = "V114_MACD_Mom"
                        
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
                
                # Guard against double-sell: re-check position state under lock
                if side == 'SELL' and self.positions.get(pair, {}).get('entries', 0) == 0:
                    return False
                
                total_eq = getattr(self, 'last_total_equity', 1000.0)
                if side == 'BUY':
                    risk_pct = (self.config['BASE_RISK_PERCENT'] / 100.0) * strength
                    risk_usd = total_eq * risk_pct
                    cp = self.data_1m[pair]['close'].iloc[-1]
                    
                    # Sync SL distance logic with analyze() for accurate sizing
                    mult = self.config.get('ATR_SL_MULT', 2.5)
                    sl_min_pct = self.config.get('SL_MIN_PCT', 0.015)
                    sl_max_pct = self.config.get('SL_MAX_PCT', 0.030)
                    sl_dist = (mult * entry_atr) if entry_atr else (cp * 0.02)
                    sl_dist = min(max(sl_dist, cp * sl_min_pct), cp * sl_max_pct)
                    
                    amt = (risk_usd / sl_dist) * cp
                    max_risk_cap = total_eq * (self.config['MAX_RISK_PER_TRADE_PERCENT'] / 100.0) * strength
                    amt = min(amt, max_risk_cap)
                    amt = max(amt, self.exchange_info[pair]['minNotional'] * 1.1)
                    bal_r = await self.client.get_asset_balance(asset='USDT')
                    free_balance = float(bal_r['free'])
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
                ep = float(order['fills'][0]['price']) if order.get('fills') else self.data_1m[pair]['close'].iloc[-1]
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
                if side == 'BUY': self.positions[pair] = {'entries': 1, 'entry_price': ep, 'qty': eq, 'max_p': ep, 'time': time.time(), 'sl': ep - sl_dist, 'setup': setup_name or 'V114', 'entry_atr': entry_atr}
                else:
                    # Track if this was a winning or losing trade for adaptive cooldown (per-pair)
                    entry_price = self.positions[pair].get('entry_price', ep)
                    self._pair_last_loss[pair] = (ep < entry_price)
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
                await asyncio.to_thread(log_failed_trade, pair, err)
                return False

    def format_quantity(self, pair, q):
        ss = self.exchange_info[pair]['stepSize']
        prec = len(format(ss, 'f').split('.')[-1].rstrip('0')) if ss < 1.0 else 0
        return format(floor_step(q, ss), f'.{prec}f')

if __name__ == "__main__":
    init_db()
    asyncio.run(TradingBot().start())
