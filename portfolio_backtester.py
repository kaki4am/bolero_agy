import pandas as pd
import pandas_ta as ta

class PortfolioBacktester:
    def __init__(self, symbols, interval='1m', lookback='5 days ago UTC'):
        self.symbols = symbols
        self.interval = interval
        self.lookback = lookback
        self.pair_data = {} 
        self.precalculated_indicators = {} 
        self.btc_15m = None
        self.btc_trend_aligned = None 


    def precalculate_all(self, status_callback=None):
        if status_callback: status_callback("Calculating Strategy V160 Indicators...")
        import json, os
        blacklist = []
        if os.path.exists("restricted_pairs.json"):
            with open("restricted_pairs.json", "r") as f: blacklist = json.load(f)
        self.pair_data = {k: v for k, v in self.pair_data.items() if k not in blacklist}
        total = len(self.pair_data)
        
        # Pre-align BTC Trend to 1m resolution
        if self.btc_15m is not None:
            btc_15m_shifted = self.btc_15m.copy()
            btc_15m_shifted['timestamp'] = btc_15m_shifted['timestamp'] + pd.Timedelta(minutes=15)
            btc_15m_indexed = btc_15m_shifted.set_index('timestamp')
            btc_15m_indexed['btc_4h_return'] = (btc_15m_indexed['close'] - btc_15m_indexed['close'].shift(16)) / btc_15m_indexed['close'].shift(16) * 100
            btc_15m_indexed['btc_24h_return'] = (btc_15m_indexed['close'] - btc_15m_indexed['close'].shift(96)) / btc_15m_indexed['close'].shift(96) * 100
            
            btc_daily_range_pct = (btc_15m_indexed['high'].rolling(96).max() - btc_15m_indexed['low'].rolling(96).min()) / btc_15m_indexed['low'].rolling(96).min() * 100
            self.btc_trend_aligned = pd.DataFrame({
                'btc_4h_return': btc_15m_indexed['btc_4h_return'],
                'btc_24h_return': btc_15m_indexed['btc_24h_return'],
                'btc_daily_range_pct': btc_daily_range_pct
            })
        else:
            self.btc_trend_aligned = None

        for i, (symbol, data) in enumerate(self.pair_data.items()):
            if status_callback:
                status_callback(f"[{i+1}/{total}] Processing {symbol}...")
            
            df_1m = data['1m'].copy()
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df_1m.columns:
                    df_1m[col] = df_1m[col].astype(float)
            
            indicators = {}
            
            bb = ta.bbands(df_1m['close'], length=20, std=2.0)
            
            if bb is not None and not bb.empty:
                sma20 = bb['BBM_20_2.0_2.0'].ffill()
                indicators['bb_upper'] = bb['BBU_20_2.0_2.0'].ffill()
                bb_lower = bb['BBL_20_2.0_2.0'].ffill()
                
                bbw = (indicators['bb_upper'] - bb_lower) / sma20
                indicators['bb_width'] = bbw
            else:
                indicators['bb_upper'] = df_1m['close'] * 1.1
                indicators['bb_width'] = pd.Series(0.0, index=df_1m.index)
                
            # Calculate 1h indicators
            df_1h = df_1m.resample('1h', on='timestamp').agg({
                'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()

            if len(df_1h) >= 15:
                df_1h['atr'] = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
            else:
                df_1h['atr'] = df_1h['close'] * 0.01

            df_1h['vol_1h_avg_24h'] = df_1h['volume'].rolling(24, min_periods=1).mean()
            
            df_1h['altcoin_4h_return'] = (df_1h['close'] - df_1h['close'].shift(4)) / df_1h['close'].shift(4) * 100
            
            # PVE-TP & RRD-TC
            df_1h['high_1h'] = df_1h['high']
            df_1h['low_1h'] = df_1h['low']
            df_1h['close_1h'] = df_1h['close']
            df_1h['alt_daily_range_pct'] = (df_1h['high'].rolling(24).max() - df_1h['low'].rolling(24).min()) / df_1h['low'].rolling(24).min() * 100
            df_1h['ema_20_1h'] = ta.ema(df_1h['close'], length=20)
            df_1h['ema_50_1h'] = ta.ema(df_1h['close'], length=50)
            
                

            df_1h['timestamp'] = df_1h['timestamp'] + pd.Timedelta(hours=1)
            df_1h_idx = df_1h.set_index('timestamp')
            
            # Align BTC to this pair's 1m index
            df_1m_idx = df_1m.set_index('timestamp')
            if self.btc_trend_aligned is not None:
                indicators['btc_safe'] = self.btc_trend_aligned.reindex(df_1m_idx.index).ffill()
            else:
                indicators['btc_safe'] = pd.DataFrame(index=df_1m_idx.index)

            indicators['atr'] = df_1h_idx['atr'].reindex(df_1m_idx.index).ffill().bfill().fillna(df_1m['close'] * 0.01)
            
            indicators['hourly_volume'] = df_1h_idx['volume'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['vol_1h_avg_24h'] = df_1h_idx['vol_1h_avg_24h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['altcoin_4h_return'] = df_1h_idx['altcoin_4h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['high_1h'] = df_1h_idx['high_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['low_1h'] = df_1h_idx['low_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['close_1h'] = df_1h_idx['close_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['alt_daily_range_pct'] = df_1h_idx['alt_daily_range_pct'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['ema_20_1h'] = df_1h_idx['ema_20_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['ema_50_1h'] = df_1h_idx['ema_50_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)

            self.precalculated_indicators[symbol] = indicators


    def run(self, params):
        balance = 1000.0
        initial_balance = balance
        active_positions = {s: {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': -99999, 'last_loss': False} for s in self.pair_data.keys()}
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
                'high': df['high'].values,
                'low': df['low'].values,
                'atr': ind['atr'].values,
                'bb_upper': ind['bb_upper'].values,
                'bb_width': ind['bb_width'].values,
                'hourly_volume': ind['hourly_volume'].values,
                'vol_1h_avg_24h': ind['vol_1h_avg_24h'].values,
                'btc_4h_return': ind['btc_safe']['btc_4h_return'].values if 'btc_4h_return' in ind['btc_safe'] else pd.Series(0.0, index=df.index).values,
                'btc_24h_return': ind['btc_safe']['btc_24h_return'].values if 'btc_24h_return' in ind['btc_safe'] else pd.Series(0.0, index=df.index).values,
                'altcoin_4h_return': ind['altcoin_4h_return'].values,
                'btc_daily_range_pct': ind['btc_safe']['btc_daily_range_pct'].values if 'btc_daily_range_pct' in ind['btc_safe'] else pd.Series(1.0, index=df.index).values,
                'high_1h': ind['high_1h'].values,
                'low_1h': ind['low_1h'].values,
                'close_1h': ind['close_1h'].values,
                'alt_daily_range_pct': ind['alt_daily_range_pct'].values,
                'ema_20_1h': ind['ema_20_1h'].values,
                'ema_50_1h': ind['ema_50_1h'].values,
                'bb_width_prev': pd.Series(ind['bb_width']).shift(1).fillna(0).values
            }

                # Simulation Loop
        equity_history = []
        failed_trades_history = []
        circuit_breaker_until_ts = None
        for ts in unique_ts:
            # 1. Calculate Portfolio State
            total_unrealized_pnl = 0.0
            active_count = 0
            current_equity = balance
            
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None: continue
                pos = active_positions[s]
                if pos['qty'] > 0:
                    active_count += 1
                    price = np_data[s]['close'][idx]
                    unrealized = (price - pos['entry_price']) * pos['qty']
                    total_unrealized_pnl += unrealized
                    current_equity += pos['qty'] * price
                    
            equity_history.append((ts, current_equity))
            if len(equity_history) > 60:
                equity_history.pop(0)
                
            # Circuit Breaker Logic
            drawdown_1h = 0.0
            if len(equity_history) == 60:
                old_equity = equity_history[0][1]
                drawdown_1h = (old_equity - current_equity) / old_equity
            
            recent_fails = [t for t in failed_trades_history if (ts - t).total_seconds() <= 3600]
            failed_trades_history = recent_fails
            
            # Note: idx is per pair, we need to block entries globally. 
            # We will use circuit_breaker_until_ts
            
                    
            if drawdown_1h > 0.01 or len(failed_trades_history) >= 3:
                circuit_breaker_until_ts = ts + pd.Timedelta(hours=4)
                
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
                        trades.append({'pair': s, 'pnl': pnl, 'reason': global_exit_reason, 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown'), 'hold_time': idx - pos['time']})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx, 'last_loss': pnl < 0}
                continue

            # 3. Individual Trade Analysis
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None or idx < 250: continue
                
                pos = active_positions[s]
                s_data = np_data[s]
                price = s_data['close'][idx]
                atr = s_data['atr'][idx]

                if pos['qty'] > 0:
                    high_price = s_data['high'][idx]
                    pos['max_p'] = max(pos['max_p'], high_price)
                    
                    
                    hold_time_m = idx - pos['time']
                    high_profit_pct = (high_price - pos['entry_price']) / pos['entry_price']
                    old_sl = pos['sl']
                    
                    if high_profit_pct > params['TRAILING_TRIGGER']:
                        pos['sl'] = max(pos['sl'], high_price * (1.0 - params['TRAILING_DIST']))

                    exit_reason = None
                    take_profit = pos.get('tp', params.get('TAKE_PROFIT'))
                    
                    
                        
                    # Dynamic Drawdown Floor for extended duration (-7%)
                    current_profit_pct = (price - pos['entry_price']) / pos['entry_price']
                    
                    if hold_time_m > params.get('PROFIT_LOCK_TIME_H', 18) * 60:
                        if current_profit_pct >= params.get('PROFIT_LOCK_PCT', 0.005):
                            pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + params.get('PROFIT_LOCK_PCT', 0.005)))
                    if hold_time_m > 24 * 60 and current_profit_pct >= 0.01:
                        pos['sl'] = max(pos['sl'], pos['entry_price'] * 1.003)
                        
                    if hold_time_m > params.get('STALENESS_TIME_H', 24) * 60:
                        if params.get('STALENESS_EXIT_MIN', -0.005) <= current_profit_pct <= params.get('STALENESS_EXIT_MAX', 0.005):
                            exit_reason = "StalenessExit"
                            exit_price = price * (1.0 - slippage_pct)

                    if current_profit_pct >= params.get('MIN_PROFIT_TRIGGER', 0.1):
                        if price >= s_data['bb_upper'][idx] * params.get('BB_EXTENSION_PCT', 1.02):
                            if s_data['hourly_volume'][idx] >= params.get('CLIMAX_VOL_MULT', 2.5) * s_data['vol_1h_avg_24h'][idx]:
                                h, l, c = s_data['high_1h'][idx], s_data['low_1h'][idx], s_data['close_1h'][idx]
                                if (h - l) > 0 and (h - c) > (c - l):
                                    exit_reason = "Volume_Climax_Harvest"
                                    exit_price = price * (1.0 - slippage_pct)
                        
                    
                    
                    if not exit_reason:
                        if s_data['low'][idx] <= old_sl:
                            exit_reason = "SL"
                            exit_price = min(old_sl, price) * (1.0 - slippage_pct)
                        elif take_profit > 0 and high_profit_pct >= take_profit:
                            exit_reason = "TakeProfit"
                            exit_price = pos['entry_price'] * (1.0 + take_profit) * (1.0 - slippage_pct)

                    if exit_reason:
                        pnl = ((exit_price / pos['entry_price']) - 1) * 100
                        if pnl <= 0:
                            failed_trades_history.append(ts)
                        trades.append({'pair': s, 'pnl': pnl, 'reason': exit_reason, 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown'), 'hold_time': idx - pos['time']})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx, 'last_loss': pnl < 0}

                else:
                    if circuit_breaker_until_ts and ts < circuit_breaker_until_ts:
                        continue

                    # Check trade cooldown period
                    cooldown_min = params.get('COOLDOWN_PERIOD', 600) / 60.0
                    if pos.get('last_loss', False):
                        cooldown_min = params.get('LOSS_COOLDOWN_PERIOD', params.get('COOLDOWN_PERIOD', 600) * 4) / 60.0
                    if (idx - pos.get('last_close_time', -99999)) < cooldown_min:
                        continue
                    
                    max_concurrent = params.get('MAX_PAIRS', 40) // 4
                    if active_count >= max_concurrent:
                        continue
                    
                    setup = None
                    
                    bb_upper = s_data['bb_upper'][idx]
                    
                    btc_4h_ret = s_data['btc_4h_return'][idx]
                    alt_4h_ret = s_data['altcoin_4h_return'][idx]
                    is_macro_decoupled = params.get('DECOUPLE_BTC_MIN', -3.0) <= btc_4h_ret <= params.get('DECOUPLE_BTC_MAX', 1.0) and alt_4h_ret > (btc_4h_ret + params.get('DECOUPLE_ALT_RET', 3.0))
                    hourly_vol = s_data['hourly_volume'][idx]
                    avg_vol = s_data['vol_1h_avg_24h'][idx]
                    
                    if is_macro_decoupled:
                        if hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout"  
                                
                    relative_range = s_data['alt_daily_range_pct'][idx] / max(s_data['btc_daily_range_pct'][idx], 1.0)
                    is_high_beta = relative_range >= params.get('RDR_MIN', 1.6)
                    ema20, ema50 = s_data['ema_20_1h'][idx], s_data['ema_50_1h'][idx]
                    trend_aligned = price > ema20 > ema50 if ema50 > 0 else False
                    
                    if is_high_beta and is_macro_decoupled and trend_aligned and hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:
                        setup = "Decoupled_Trend_Continuation"

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
                            btc_24h_ret_risk = s_data['btc_24h_return'][idx]
                            if btc_24h_ret_risk <= -3.0:
                                risk_pct = risk_pct * 0.5
                            elif btc_24h_ret_risk < -1.0:
                                risk_pct = risk_pct * 0.8
                            risk_usd = current_equity * risk_pct

                            mult = params.get('ATR_SL_MULT', 2.5)
                            sl_min_pct = params['SL_MIN_PCT']
                            sl_dist_price = mult * atr
                            sl_dist_price = max(sl_dist_price, price * sl_min_pct)
                            sl_max_pct = params['SL_MAX_PCT']
                            sl_dist_price = min(sl_dist_price, price * sl_max_pct)
                            
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
                                pos['entry_atr'] = atr
                                pos['tp'] = params.get('TAKE_PROFIT')
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
                trades.append({'pair': s, 'pnl': pnl, 'reason': 'EOD', 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown'), 'hold_time': len(np_data[s]['close']) - 1 - pos['time']})

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
