import re

with open('bot.py', 'r') as f:
    content = f.read()

# 1. Update Blacklist
content = re.sub(
    r"'HFTUSDT', 'PEOPLEUSDT', 'ONGUSDT', 'SYNUSDT', 'COTIUSDT', 'CRVUSDT'",
    "'HFTUSDT', 'PEOPLEUSDT', 'ONGUSDT', 'SYNUSDT', 'COTIUSDT', 'CRVUSDT',\n                       'ENSUSDT', 'DEXEUSDT', 'HEIUSDT'",
    content
)

# 2. Add altcoin_4h_return to fetch_macro_trends
content = re.sub(
    r"cache_data.update\(\{'altcoin_24h_return': 0\.0\}\)",
    "cache_data.update({'altcoin_24h_return': 0.0})\n\n                        if len(close_1h) >= 5:\n                            cache_data.update({'altcoin_4h_return': (close_1h.iloc[-1] - close_1h.iloc[-5]) / close_1h.iloc[-5] * 100})\n                        else:\n                            cache_data.update({'altcoin_4h_return': 0.0})",
    content
)
content = re.sub(
    r"'alt_24h_vol': float\(ema_data.get\('altcoin_24h_volume', 0.0\)\),",
    "'alt_24h_vol': float(ema_data.get('altcoin_24h_volume', 0.0)),\n            'alt_4h_ret': float(ema_data.get('altcoin_4h_return', 0.0)),",
    content
)

# 3. Setup logic in analyze
setup_old = """            if alt_24h_ret > (btc_ret + 2.5) and alt_24h_vol > alt_24h_vol_sma7:
                if hourly_vol > 1.5 * avg_vol:
                    if cp > bb_upper and bb_width > bb_width_prev:
                        setup = "Decoupled_Squeeze_Breakout\""""
setup_new = """            btc_4h_ret = self.market_trend.get('btc_4h_return', 0.0)
            alt_4h_ret = ema_data.get('altcoin_4h_return', 0.0)
            if -3.0 <= btc_4h_ret <= 1.0 and alt_4h_ret > 3.0:
                if hourly_vol > 2.0 * avg_vol:
                    if cp > bb_upper and bb_width > bb_width_prev:
                        setup = "Decoupled_Squeeze_Breakout\""""
content = content.replace(setup_old, setup_new)

# 4. ProfitGuard & TimeDecay
old_profit_guard = """                    # Minimum hold period: don't tighten stops in first 15 minutes
                    trail_trigger = self.config.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = self.config.get('TRAILING_DIST', 0.020)
                    be_trigger = self.config.get('BE_TRIGGER', 0.020)
                    be_lock = self.config.get('BE_LOCK', 0.002)
                    
                    hold_seconds = time.time() - pos.get('time', time.time())
                    min_hold_passed = hold_seconds > 360 * 60  # 6 hours
                    
                    if min_hold_passed:
                        if profit_pct > trail_trigger:
                            sl = max(sl, cp * (1.0 - trail_dist))
                            self.positions[pair]['sl'] = sl
                        elif profit_pct > be_trigger:
                            sl = max(sl, pos['entry_price'] * (1.0 + be_lock))
                            self.positions[pair]['sl'] = sl"""

new_profit_guard = """                    trail_trigger = self.config.get('TRAILING_TRIGGER', 0.08)
                    trail_dist = self.config.get('TRAILING_DIST', 0.035)
                    
                    hold_seconds = time.time() - pos.get('time', time.time())
                    
                    if profit_pct > trail_trigger:
                        sl = max(sl, cp * (1.0 - trail_dist))
                        self.positions[pair]['sl'] = sl"""
content = content.replace(old_profit_guard, new_profit_guard)

time_decay = """                    if hold_seconds > 48 * 3600:
                        alt_24h_ret_c = self.ema_cache.get(pair, {}).get('altcoin_24h_return', 0.0)
                        alt_24h_vol_c = self.ema_cache.get(pair, {}).get('altcoin_24h_volume', 0.0)
                        alt_24h_vol_sma7_c = self.ema_cache.get(pair, {}).get('altcoin_24h_vol_sma7', 0.0)
                        if alt_24h_ret_c < 1.0 or alt_24h_vol_c < alt_24h_vol_sma7_c * 0.8:
                            exit_reason = 'TimeDecay'
                            
                    if hold_seconds > 24 * 3600 and profit_pct <= -0.07:"""
content = re.sub(r"if hold_seconds > 24 \* 3600 and profit_pct <= -0.07:", time_decay, content)

# 5. Risk alignment in execute_trade
risk_old = """                if side == 'BUY':
                    risk_pct = (self.config['BASE_RISK_PERCENT'] / 100.0) * strength
                    if hasattr(self, 'market_trend') and not self.market_trend.get('btc_uptrend_15m', True):
                        risk_pct *= 0.5"""
risk_new = """                if side == 'BUY':
                    risk_pct = (self.config['BASE_RISK_PERCENT'] / 100.0) * strength
                    if hasattr(self, 'market_trend') and not self.market_trend.get('btc_uptrend_15m', True):
                        btc_4h_ret_risk = self.market_trend.get('btc_4h_return', 0.0)
                        if btc_4h_ret_risk < -1.5:
                            risk_pct *= 0.75
                        elif btc_4h_ret_risk < -1.0:
                            risk_pct *= 0.9"""
content = content.replace(risk_old, risk_new)

with open('bot.py', 'w') as f:
    f.write(content)
print("patched bot.py")
