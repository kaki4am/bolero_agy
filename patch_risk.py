import json

with open('/root/tactical_overrides.json', 'r') as f:
    t = json.load(f)

t['RISK_MULTIPLIER'] = 0.8

with open('/root/tactical_overrides.json', 'w') as f:
    json.dump(t, f, indent=4)

