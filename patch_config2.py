import json

with open('/root/config.json', 'r') as f:
    c = json.load(f)

c['ATR_SL_MULT'] = 3.0
c['TRAILING_TRIGGER'] = 0.015
c['TRAILING_DIST'] = 0.005

with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)
