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
    print(f"\n--- AI Manager Execution: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
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

    prompt = f"""You are the dynamic AI Risk Manager for a live Binance spot trading bot that uses a short-term momentum strategy (6-48h holds).

INPUT TELEMETRY:
- Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- BTCUSDT Current Price: ${btc_price:.2f} (24h Change: {btc_change:+.2f}%)
- Current Active Bot Positions: {", ".join(active_positions) if active_positions else "None"}
- Recent Crypto News Headlines:
{news}

RISK MANAGEMENT PRINCIPLES (follow these strictly):
1. During sell-offs: REDUCE position size (lower RISK_MULTIPLIER) and TIGHTEN stops (negative SL_MULT_OFFSET). The goal is to LOSE LESS per trade, not give trades "more room". Wider stops in a downtrend = bigger losses.
2. During stable/bullish conditions: Return to full risk (RISK_MULTIPLIER=1.0) and normal stops (SL_MULT_OFFSET=0.0).
3. Portfolio eject should be TIGHTER (POSITIVE offset) in sell-offs to protect capital faster (e.g., base -5.0 + 1.0 = -4.0%). Do not use negative offsets for eject as it widens the loss limit!
4. Only blacklist pairs with specific negative catalysts (delistings, hacks, regulatory action). Do NOT blacklist pairs just because BTC is down — that's what RISK_MULTIPLIER is for.
5. NEVER blacklist a pair the bot currently holds an active position on.
6. Default state is neutral (1.0, 0.0, 0.0, 0.0, []) — only deviate if there's a clear reason.

    DECISION MATRIX:
    - BTC -1% to -3%: RISK_MULTIPLIER 0.7-0.9, SL_MULT_OFFSET -0.2 to 0.0 (tighter)
    - BTC -3% to -5%: RISK_MULTIPLIER 0.3-0.5, SL_MULT_OFFSET -0.3 to -0.2 (much tighter)
    - BTC < -5%: RISK_MULTIPLIER 0.0 (pause all entries)
    - BTC flat or positive: RISK_MULTIPLIER 1.0, SL_MULT_OFFSET 0.0

    PREVIOUS LEARNINGS / RESEARCH NOTES:
    {open('/root/research_notes.md').read() if os.path.exists('/root/research_notes.md') else 'No previous learnings.'}

    OUTPUT FORMAT:
    Output ONLY a raw JSON block (no markdown backticks, no explanatory text) matching this schema:
    {{
      "RISK_MULTIPLIER": float (0.0 to 1.2, default 1.0),
      "SL_MULT_OFFSET": float (-0.5 to 0.5, default 0.0, NEGATIVE = tighter stops, POSITIVE = wider),
      "VOL_SPIKE_MULT_OFFSET": float (0.0 to 0.5, default 0.0),
      "PORTFOLIO_EJECT_OFFSET": float (0.0 to 2.0, default 0.0, POSITIVE = tighter/more defensive stop),
      "blacklist_add": list of strings (only for specific news catalysts, NOT for general market moves),
      "rationale": string (brief, 1-sentence strategic rationale),
      "confidence": float (0.0 to 1.0, 1.0 being highly confident),
      "learning_to_persist": string (optional, 1-sentence note to append to research_notes.md if you learned something new or rejected a specific action, otherwise empty string)
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
        confidence = float(overrides.get('confidence', 1.0))
        if confidence < 0.8:
            print(f"AI Confidence too low ({confidence:.2f}). Keeping existing risk configuration.")
            return

        overrides['RISK_MULTIPLIER'] = max(0.0, min(1.5, float(overrides.get('RISK_MULTIPLIER', 1.0))))
        overrides['SL_MULT_OFFSET'] = max(-0.5, min(0.5, float(overrides.get('SL_MULT_OFFSET', 0.0))))
        overrides['VOL_SPIKE_MULT_OFFSET'] = max(0.0, min(0.5, float(overrides.get('VOL_SPIKE_MULT_OFFSET', 0.0))))
        overrides['PORTFOLIO_EJECT_OFFSET'] = max(-2.0, min(0.0, float(overrides.get('PORTFOLIO_EJECT_OFFSET', 0.0))))
        
        # Validate blacklist_add is a list of strings
        blacklist = overrides.get('blacklist_add', [])
        if not isinstance(blacklist, list):
            blacklist = []
        overrides['blacklist_add'] = [s for s in blacklist if isinstance(s, str) and s.endswith('USDT')]
        
        # Save to tactical overrides
        with open('tactical_overrides.json', 'w') as f:
            json.dump(overrides, f, indent=4)
            
        learning = overrides.get('learning_to_persist', '').strip()
        if learning:
            with open('/root/research_notes.md', 'a') as f:
                f.write(f"- [AI Manager {datetime.now().strftime('%Y-%m-%d %H:%M')}] {learning}\n")
            print(f"Appended learning to research_notes.md: {learning}")

        print("Tactical overrides updated successfully:")
        print(json.dumps(overrides, indent=2))
        
    except Exception as e:
        print(f"Error running AI Manager: {e}")
        if 'proc' in locals():
            print(f"Proc Stderr: {proc.stderr}")

if __name__ == "__main__":
    main()
