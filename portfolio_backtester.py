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
        if status_callback: status_callback("Calculating Strategy V152 Indicators...")
        total = len(self.pair_data)
        
        # Pre-align BTC Trend to 1m resolution
        if self.btc_15m is not None:
            btc_15m_shifted = self.btc_15m.copy()
            btc_15m_shifted['timestamp'] = btc_15m_shifted['timestamp'] + pd.Timedelta(minutes=15)
            btc_15m_indexed = btc_15m_shifted.set_index('timestamp')
                
            self.btc_trend_aligned = pd.DataFrame({
                'uptrend_15m': btc_15m_indexed['close'] > btc_15m_indexed['ema200']
            })
        else:
            self.btc_trend_aligned = None

        for i, (symbol, data) in enumerate(self.pair_data.items()):
            if status_callback:
                status_callback(f"[{i+1}/{total}] Processing {symbol}...")
            
            df_1m = data['1m'].copy()
            
            indicators = {}
            
            indicators['sma30'] = ta.sma(df_1m['close'], length=30)
            bb = ta.bbands(df_1m['close'], length=20, std=2.0)
            atr1m = ta.atr(df_1m['high'], df_1m['low'], df_1m['close'], length=14)
            
            if bb is not None and not bb.empty:
                sma20 = bb['BBM_20_2.0_2.0'].ffill()
                indicators['bb_upper'] = bb['BBU_20_2.0_2.0'].ffill()
                indicators['bb_lower'] = bb['BBL_20_2.0_2.0'].ffill()
                
                bbw = (indicators['bb_upper'] - indicators['bb_lower']) / sma20
                bbw_sma50 = ta.sma(bbw, length=50)
                indicators['bbw_breakout_valid'] = (bbw > (1.5 * bbw_sma50)).fillna(True)
                
                kc_upper = sma20 + 1.5 * atr1m
                kc_lower = sma20 - 1.5 * atr1m
                
                # Squeeze ON: BB inside KC
                sqz_on = (indicators['bb_upper'] < kc_upper) & (indicators['bb_lower'] > kc_lower)
                # Squeeze was recently on (last 15 minutes) but is now expanding
                sqz_recent = sqz_on.shift(1).rolling(15).max() > 0
                indicators['bb_squeeze'] = sqz_recent & (~sqz_on)
            else:
                indicators['bb_upper'] = df_1m['close'] * 1.1
                indicators['bb_squeeze'] = pd.Series(False, index=df_1m.index)
                indicators['bbw_breakout_valid'] = pd.Series(True, index=df_1m.index)
            indicators['bb_squeeze'] = indicators['bb_squeeze'].fillna(False)
                
            # Calculate 1h indicators
            df_1h = df_1m.resample('1h', on='timestamp').agg({
                'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna().reset_index()

            if len(df_1h) >= 15:
                df_1h['atr'] = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
            else:
                df_1h['atr'] = df_1h['close'] * 0.01
                
            # Dynamic Trend Efficiency Filter (Chop Filter)
            if len(df_1h) >= 24:
                trend_24h_pct = df_1h['close'].diff(24).abs() / df_1h['close'].shift(24)
                avg_hourly_range_pct = (df_1h['atr'] / df_1h['close']).rolling(24).mean()
                df_1h['er'] = (trend_24h_pct / avg_hourly_range_pct).fillna(1.0)
                
                df_1h['volatility_1h'] = df_1h['atr'] / df_1h['close']
                df_1h['volatility_24h'] = avg_hourly_range_pct
            else:
                df_1h['er'] = 1.0
                df_1h['volatility_1h'] = 0.01
                df_1h['volatility_24h'] = 0.01

            df_1h['timestamp'] = df_1h['timestamp'] + pd.Timedelta(hours=1)
            df_1h_idx = df_1h.set_index('timestamp')
            
            # Align BTC to this pair's 1m index
            df_1m_idx = df_1m.set_index('timestamp')
            if self.btc_trend_aligned is not None:
                indicators['btc_safe'] = self.btc_trend_aligned.reindex(df_1m_idx.index).ffill()
            else:
                indicators['btc_safe'] = pd.DataFrame({'uptrend_15m': [True]*len(df_1m)}, index=df_1m_idx.index)

            indicators['atr'] = df_1h_idx['atr'].reindex(df_1m_idx.index).ffill().bfill().fillna(df_1m['close'] * 0.01)
            indicators['er'] = df_1h_idx['er'].reindex(df_1m_idx.index).ffill().bfill().fillna(1.0)
            indicators['volatility_1h'] = df_1h_idx['volatility_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0.01)
            indicators['volatility_24h'] = df_1h_idx['volatility_24h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0.01)

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
                'er': ind['er'].values,
                'sma30': ind['sma30'].values,
                'bb_upper': ind['bb_upper'].values,
                'bb_squeeze': ind['bb_squeeze'].values,
                'btc_uptrend_15m': ind['btc_safe']['uptrend_15m'].values,
                'bbw_breakout_valid': ind['bbw_breakout_valid'].values,
                'volatility_1h': ind['volatility_1h'].values,
                'volatility_24h': ind['volatility_24h'].values
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
                    
                    trail_trigger = params.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = params.get('TRAILING_DIST', 0.020)
                    be_trigger = params.get('BE_TRIGGER', 0.020)
                    be_lock = params.get('BE_LOCK', 0.002)
                    
                    # Minimum hold: 360 candles (6h) before tightening to breakeven
                    min_hold_passed = (idx - pos['time']) > 360
                    
                    high_profit_pct = (high_price - pos['entry_price']) / pos['entry_price']
                    entry = pos['entry_price']
                    
                    old_sl = pos['sl']
                    
                    if pos.get('setup') == 'Trend_BB_Squeeze':
                        # Trailing stop based on 3.0 * ATR
                        mult = params.get('ATR_SL_MULT', 3.0)
                        if not s_data['btc_uptrend_15m'][idx]:
                            mult = mult * 0.5
                        entry_atr = pos.get('entry_atr', atr)
                        trail_dist_price = max(mult * entry_atr, high_price * params.get('SL_MIN_PCT', 0.015))
                        pos['sl'] = max(pos['sl'], high_price - trail_dist_price)
                    else:
                        if high_profit_pct > trail_trigger:
                            pos['sl'] = max(pos['sl'], high_price * (1.0 - trail_dist))
                        elif high_profit_pct > be_trigger and min_hold_passed:
                            pos['sl'] = max(pos['sl'], entry * (1.0 + be_lock))

                    exit_reason = None
                    take_profit = pos.get('tp', params.get('TAKE_PROFIT', 0.0))
                    
                    if s_data['low'][idx] <= old_sl:
                        exit_reason = "SL"
                        exit_price = old_sl * (1.0 - slippage_pct)
                    elif take_profit > 0 and high_profit_pct >= take_profit:
                        exit_reason = "TakeProfit"
                        exit_price = pos['entry_price'] * (1.0 + take_profit) * (1.0 - slippage_pct)
                    else:
                        current_vol = s_data['volatility_1h'][idx]
                        rolling_vol = s_data['volatility_24h'][idx]
                        max_hold_time = 1440
                        vol_spike_mult = params.get('VOL_SPIKE_MULTIPLIER', 1.5)
                        if current_vol > (vol_spike_mult * rolling_vol) and high_profit_pct < 0:
                            max_hold_time = 720
                            
                        if (idx - pos['time']) > max_hold_time:
                            exit_reason = "TimeExit"
                            exit_price = price * (1.0 - slippage_pct)

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
                    
                    sma30 = s_data['sma30'][idx]
                    bb_upper = s_data['bb_upper'][idx]
                    bb_squeeze = s_data['bb_squeeze'][idx]
                    er = s_data['er'][idx]
                    
                    min_er = params.get('MIN_EFFICIENCY_RATIO', 0.3)
                    breakout_mult = params.get('BREAKOUT_VOL_MULT', 1.5)
                    
                    if price > sma30 and bb_squeeze and price > bb_upper + (atr * breakout_mult) and er > min_er and s_data['bbw_breakout_valid'][idx]:
                        setup = "Trend_BB_Squeeze"
                            
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
                            
                            if ts.dayofweek == 4:
                                size_strength *= 1.5
                                
                            risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                            if not s_data['btc_uptrend_15m'][idx]:
                                risk_pct = risk_pct * 0.5
                            risk_usd = current_equity * risk_pct

                            mult = params.get('ATR_SL_MULT', 2.5)
                            sl_min_pct = params.get('SL_MIN_PCT', 0.015)
                            sl_max_pct = params.get('SL_MAX_PCT', 0.030)
                            sl_dist_price = mult * atr
                            # sl_max_pct
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
                                pos['entry_atr'] = atr
                                pos['tp'] = params.get('TAKE_PROFIT', 0.0)
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
