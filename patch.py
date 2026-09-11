import json

# 1. Update tactical_overrides.json
with open('/root/tactical_overrides.json', 'r') as f:
    t = json.load(f)

if 'LAPTOPUSDT' in t.get('whitelist_add', []):
    t['whitelist_add'].remove('LAPTOPUSDT')
t['RISK_MULTIPLIER'] = 0.5

# We will just write it back
with open('/root/tactical_overrides.json', 'w') as f:
    json.dump(t, f, indent=4)

# 2. Update config.json
with open('/root/config.json', 'r') as f:
    c = json.load(f)
c['PORTFOLIO_EJECT'] = -5.0
with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)
