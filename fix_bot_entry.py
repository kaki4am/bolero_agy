with open('/root/bot.py', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'min_er = self.config.get(\'MIN_EFFICIENCY_RATIO\', 0.3)' in line:
        # replace the next few lines
        new_lines.append(line)
        i += 1
        new_lines.append(lines[i]) # breakout_mult
        i += 1
        
        insert = """            if cp > sma30 and bb_squeeze and cp > bb_upper + (atr * breakout_mult) and er > min_er and bbw_breakout_valid:
                if pair in ['BTCUSDT', 'ETHUSDT']:
                    if vol_surge:
                        setup = "Trend_BB_Squeeze"
                else:
                    setup = "Trend_BB_Squeeze"\n"""
        new_lines.append(insert)
        
        while i < len(lines) and 'if setup:' not in lines[i]:
            if 'if ema_data and \'rsi_1h\' in ema_data and \'ema200_1h\' in ema_data:' in lines[i]:
                # keep this block
                new_lines.append(lines[i])
            elif 'rsi = ema_data[\'rsi_1h\']' in lines[i]:
                new_lines.append(lines[i])
            elif 'rsi_prev = ema_data[\'rsi_1h_prev\']' in lines[i]:
                new_lines.append(lines[i])
            elif 'rsi_min_5 = ema_data[\'rsi_min_5\']' in lines[i]:
                new_lines.append(lines[i])
            elif 'ema200 = ema_data[\'ema200_1h\']' in lines[i]:
                new_lines.append(lines[i])
            elif 'if rsi > 40 and rsi_prev <= 40 and rsi_min_5 < 35 and cp > ema200:' in lines[i]:
                new_lines.append(lines[i])
            elif 'setup = "Pullback_RSI"' in lines[i]:
                new_lines.append(lines[i])
            i += 1
            
        new_lines.append(lines[i])
    else:
        new_lines.append(line)
    i += 1

with open('/root/bot.py', 'w') as f:
    f.writelines(new_lines)
