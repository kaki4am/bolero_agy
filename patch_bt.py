with open("/root/portfolio_backtester.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "if is_macro_decoupled:" in line and "if hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:" in lines[i+1]:
        skip = True
        new_lines.append(line)
        continue
    if skip:
        if "setup = \"Decoupled_Trend_Continuation\"" in line:
            # Done skipping
            indent = "                    "
            new_lines.append(indent + "h1, l1, c1 = s_data['high_1h'][idx], s_data['low_1h'][idx], s_data['close_1h'][idx]\n")
            new_lines.append(indent + "atr_1h = s_data['atr'][idx]\n")
            new_lines.append(indent + "vol = s_data['hourly_volume'][idx]\n")
            new_lines.append(indent + "vol_avg20 = s_data['vol_1h_avg_20h'][idx]\n")
            new_lines.append(indent + "range_expansion = (h1 - l1) > 1.5 * atr_1h\n")
            new_lines.append(indent + "close_strength = (c1 - l1) / (h1 - l1) >= 0.70 if (h1 - l1) > 0 else False\n")
            new_lines.append(indent + "current_hour = ts.hour\n")
            new_lines.append(indent + "vol_thresh = 1.8\n")
            new_lines.append(indent + "if current_hour in [13, 17, 20, 22]:\n")
            new_lines.append(indent + "    vol_thresh = 1.8 * 1.15\n")
            new_lines.append(indent + "vol_confirmed = vol > vol_thresh * vol_avg20\n")
            new_lines.append(indent + "if is_macro_decoupled and range_expansion and close_strength and vol_confirmed:\n")
            new_lines.append(indent + "    bb_width_prev = s_data['bb_width_prev'][idx]\n")
            new_lines.append(indent + "    bbw = s_data['bb_width'][idx]\n")
            new_lines.append(indent + "    if price > bb_upper and bbw > bb_width_prev:\n")
            new_lines.append(indent + "        setup = \"Decoupled_Squeeze_Breakout\"\n")
            new_lines.append(indent + "relative_range = s_data['alt_daily_range_pct'][idx] / max(s_data['btc_daily_range_pct'][idx], 1.0)\n")
            new_lines.append(indent + "is_high_beta = relative_range >= params.get('RDR_MIN', 1.6)\n")
            new_lines.append(indent + "ema20, ema50 = s_data['ema_20_1h'][idx], s_data['ema_50_1h'][idx]\n")
            new_lines.append(indent + "trend_aligned = price > ema20 > ema50 if ema50 > 0 else False\n")
            new_lines.append(indent + "if is_high_beta and is_macro_decoupled and trend_aligned and range_expansion and close_strength and vol_confirmed:\n")
            new_lines.append(indent + "    setup = \"Decoupled_Trend_Continuation\"\n")
            skip = False
        continue

    if "if price >= s_data['bb_upper'][idx] * params.get('BB_EXTENSION_PCT', 1.02):" in line:
        skip = True
        continue
    if skip and "exit_price = price * (1.0 - slippage_pct)" in line:
        indent = "                        "
        new_lines.append(indent + "h, l, c = s_data['high_1h'][idx], s_data['low_1h'][idx], s_data['close_1h'][idx]\n")
        new_lines.append(indent + "o = s_data['open_1h'][idx]\n")
        new_lines.append(indent + "vol = s_data['hourly_volume'][idx]\n")
        new_lines.append(indent + "vol_avg20 = s_data['vol_1h_avg_20h'][idx]\n")
        new_lines.append(indent + "highest_24h = s_data['high_24h_max'][idx]\n")
        new_lines.append(indent + "if h >= highest_24h and (h - l) > 0:\n")
        new_lines.append(indent + "    wick_pct = (h - max(o, c)) / (h - l)\n")
        new_lines.append(indent + "    if wick_pct >= 0.55 and vol > 2.5 * vol_avg20:\n")
        new_lines.append(indent + "        exit_reason = \"Climax_Wick_Rejection\"\n")
        new_lines.append(indent + "        exit_price = price * (1.0 - slippage_pct)\n")
        skip = False
        continue

    if "if hold_time_m > params.get('PROFIT_LOCK_TIME_H', 18) * 60:" in line:
        new_lines.append(line)
        new_lines.append("                        pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + params.get('PROFIT_LOCK_PCT', 0.0025)))\n")
        new_lines.append("                    if hold_time_m > 24 * 60 and high_profit_pct >= 0.01:\n")
        new_lines.append("                        pos['sl'] = max(pos['sl'], pos['entry_price'] * 1.003)\n")
        skip = True
        continue
    if skip and "pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + params.get('PROFIT_LOCK_PCT', 0.0025)))" in line:
        skip = False
        continue

    new_lines.append(line)

with open("/root/portfolio_backtester.py", "w") as f:
    f.writelines(new_lines)
