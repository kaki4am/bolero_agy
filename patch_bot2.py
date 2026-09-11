import re

with open('/root/bot.py', 'r') as f:
    code = f.read()

old_logic = r"btc_ret = self\.market_trend\.get\('btc_24h_return', 0\.0\)\n\s+alt_24h_ret = ema_data\.get\('altcoin_24h_return', 0\.0\)\n\s+alt_24h_vol = ema_data\.get\('altcoin_24h_volume', 0\.0\)\n\s+alt_24h_vol_sma7 = ema_data\.get\('altcoin_24h_vol_sma7', 0\.0\)\n\s+hourly_vol = ema_data\.get\('hourly_volume', 0\.0\)\n\s+avg_vol = ema_data\.get\('vol_1h_avg_24h', 0\.0\)\n\s+if alt_24h_ret > \(btc_ret \+ 2\.5\) and alt_24h_vol > alt_24h_vol_sma7:\n\s+if hourly_vol > 1\.5 \* avg_vol:\n\s+if cp > bb_upper and bb_width > bb_width_prev:\n\s+setup = \"Decoupled_Squeeze_Breakout\""

new_logic = """btc_ret = self.market_trend.get('btc_4h_return', 0.0)
            alt_4h_ret = ema_data.get('altcoin_4h_return', 0.0)
            hourly_vol = ema_data.get('hourly_volume', 0.0)
            avg_vol = ema_data.get('vol_1h_avg_24h', 0.0)
            bbw_1h = ema_data.get('bbw_1h', 0.0)
            min_bbw_24 = ema_data.get('min_bbw_24_1h', 0.0)
            rsi_1h = ema_data.get('rsi_1h', 0.0)
            
            if alt_4h_ret > (btc_ret + 2.5) and hourly_vol > 2.5 * avg_vol:
                if bbw_1h > 1.5 * min_bbw_24 and rsi_1h > 65:
                    if cp > bb_upper and bb_width > bb_width_prev:
                        setup = "Decoupled_Squeeze_Breakout" """

code = re.sub(old_logic, new_logic, code)

with open('/root/bot.py', 'w') as f:
    f.write(code)
