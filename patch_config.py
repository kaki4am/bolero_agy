import json

with open('config.json', 'r') as f:
    config = json.load(f)

config['TRAILING_TRIGGER'] = 0.06
config['TRAILING_DIST'] = 0.035
config['SL_MAX_PCT'] = 0.06

with open('config.json', 'w') as f:
    json.dump(config, f, indent=4)
print("config updated")
