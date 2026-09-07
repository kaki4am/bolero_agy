with open('/root/bot.py', 'r') as f:
    bot = f.read()

bot = bot.replace("'bbw_breakout_valid': bool(bbw_breakout_valid)", "'bbw_breakout_valid': bool(bbw_breakout_valid),\n            'vol_surge': bool(vol_surge)")

with open('/root/bot.py', 'w') as f:
    f.write(bot)

with open('/root/dashboard.py', 'r') as f:
    dash = f.read()

# Add vol_surge to dashboard UI if it's there
dash = dash.replace("Vol: {data.get('vol_24h', 0)*100:.1f}%", "Vol: {data.get('vol_24h', 0)*100:.1f}% | Vol Surge: {data.get('vol_surge', False)}")

with open('/root/dashboard.py', 'w') as f:
    f.write(dash)
