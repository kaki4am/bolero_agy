import os
import json
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import subprocess
from datetime import datetime
from binance import Client
from dotenv import load_dotenv

load_dotenv()

def get_news_headlines():
    headlines = []
    try:
        url = "https://cointelegraph.com/rss"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            headlines.append(f"- {title}")
    except Exception as e:
        headlines.append(f"Error fetching news: {e}")
    return "\n".join(headlines)

def get_market_telemetry():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    client = Client(api_key, api_secret)
    
    btc_ticker = client.get_ticker(symbol="BTCUSDT")
    btc_price = float(btc_ticker['lastPrice'])
    btc_change = float(btc_ticker['priceChangePercent'])
    
    # Get active positions from DB
    active_positions = []
    try:
        conn = sqlite3.connect('trading_bot.db')
        # We find open positions in database by inspecting trades log
        query = "SELECT pair, side, price, quantity FROM trades WHERE id IN (SELECT MAX(id) FROM trades GROUP BY pair)"
        import pandas as pd
        df = pd.read_sql_query(query, conn)
        acc = client.get_account()
        balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
        
        for _, row in df.iterrows():
            pair = row['pair']
            asset = pair.replace('USDT', '')
            if row['side'] == 'BUY' and balances.get(asset, 0) > 0.0001:
                active_positions.append(f"{pair} (Entry: {row['price']}, Qty: {balances[asset]:.4f})")
        conn.close()
    except Exception as e:
        print(f"Error reading positions from DB: {e}")
        
    return btc_price, btc_change, active_positions

def main():
    print("Gathering market telemetry...")
    try:
        btc_price, btc_change, active_positions = get_market_telemetry()
    except Exception as e:
        print(f"Error getting market telemetry: {e}")
        btc_price, btc_change, active_positions = 0.0, 0.0, []

    print("Fetching news headlines...")
    news = get_news_headlines()

    # Load baseline config
    base_config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                base_config = json.load(f)
        except Exception as e:
            print(f"Error reading config: {e}")

    prompt = f"""You are the dynamic AI Risk Manager for a live Binance Trading Bot.
Analyze the live market conditions and recent news to output tactical risk adjustments and symbol overrides for the next hour.

INPUT TELEMETRY:
- Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- BTCUSDT Current Price: ${btc_price:.2f} (24h Change: {btc_change:+.2f}%)
- Current Active Bot Positions: {", ".join(active_positions) if active_positions else "None"}
- Recent Crypto News Headlines:
{news}

CURRENT BASELINE CONFIGURATION:
{json.dumps(base_config, indent=2)}

GOAL:
Dampen downside risk during macro sell-offs/negative news and optimize parameter flexibility (Stop Losses, risk sizing, symbol blacklists).

OUTPUT FORMAT:
Output ONLY a raw JSON block (no markdown backticks, no explanatory text, no whitespace outside JSON) matching this schema:
{{
  "RISK_MULTIPLIER": float (multiplier for position sizing, default 1.0, scale down to 0.0 to pause entries, cap at 1.2),
  "SL_MULT_OFFSET": float (additive offset to ATR Stop Loss multiplier, e.g. 0.0 to 1.5, default 0.0 to widen SL in volatile conditions),
  "VOL_SPIKE_MULT_OFFSET": float (additive offset to entry volume spike threshold, default 0.0),
  "PORTFOLIO_EJECT_OFFSET": float (additive offset to global portfolio eject limit, e.g. positive to make it looser or negative to make it tighter/defensive, default 0.0),
  "blacklist_add": list of strings (symbols to blacklist immediately, e.g. ["SOLUSDT"]),
  "rationale": string (brief, 1-sentence strategic rationale)
}}
"""

    print("Invoking Antigravity AI Agent...")
    try:
        # Run agy to get LLM response
        proc = subprocess.run(
            ['/root/.local/bin/agy', '--print', prompt],
            capture_output=True,
            text=True,
            check=True
        )
        response_text = proc.stdout.strip()
        
        # Clean up any markdown backticks if the model returned them
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        # Parse and validate JSON
        overrides = json.loads(response_text)
        
        # Bounds validation - clamp values to safe ranges
        overrides['RISK_MULTIPLIER'] = max(0.0, min(1.5, float(overrides.get('RISK_MULTIPLIER', 1.0))))
        overrides['SL_MULT_OFFSET'] = max(0.0, min(2.0, float(overrides.get('SL_MULT_OFFSET', 0.0))))
        overrides['VOL_SPIKE_MULT_OFFSET'] = max(0.0, min(1.0, float(overrides.get('VOL_SPIKE_MULT_OFFSET', 0.0))))
        overrides['PORTFOLIO_EJECT_OFFSET'] = max(-3.0, min(3.0, float(overrides.get('PORTFOLIO_EJECT_OFFSET', 0.0))))
        
        # Validate blacklist_add is a list of strings
        blacklist = overrides.get('blacklist_add', [])
        if not isinstance(blacklist, list):
            blacklist = []
        overrides['blacklist_add'] = [s for s in blacklist if isinstance(s, str) and s.endswith('USDT')]
        
        # Save to tactical overrides
        with open('tactical_overrides.json', 'w') as f:
            json.dump(overrides, f, indent=4)
            
        print("Tactical overrides updated successfully:")
        print(json.dumps(overrides, indent=2))
        
    except Exception as e:
        print(f"Error running AI Manager: {e}")
        if 'proc' in locals():
            print(f"Proc Stderr: {proc.stderr}")

if __name__ == "__main__":
    main()
