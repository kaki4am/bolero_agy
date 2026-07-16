import os
import json
import sqlite3
import subprocess
from datetime import datetime

def get_service_status(service_name):
    try:
        status = subprocess.check_output(['systemctl', 'is-active', service_name]).decode().strip()
        return status
    except:
        return 'inactive'

def get_last_trade():
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "Never"
    except:
        return "Error"

def get_tuner_info():
    if os.path.exists('backtest_status.json'):
        try:
            with open('backtest_status.json', 'r') as f:
                data = json.load(f)
                return {
                    "last_run": data.get('last_run', 'Unknown'),
                    "status": data.get('status', 'Unknown'),
                    "best_profit": data.get('best_profit', -100.0),
                    "progress": f"{data.get('progress', 0)}/{data.get('total_combinations', 0)}",
                    "last_log": data.get('logs', ["No logs"])[-1] if data.get('logs') else "No logs"
                }
        except:
            return {"last_run": "Error", "status": "Error", "best_profit": -100.0, "progress": "N/A", "last_log": "File Read Error"}
    return {"last_run": "N/A", "status": "N/A", "best_profit": -100.0, "progress": "N/A", "last_log": "N/A"}

def check_failed_trades():
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM failed_trades WHERE timestamp > datetime('now', '-1 hour')")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return -1

def get_age_str(last_update, is_utc=False):
    if last_update in ["Unknown", "Error", "N/A", "Never"]:
        return last_update
    try:
        from datetime import timezone
        last_dt = datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
        now = datetime.now(timezone.utc).replace(tzinfo=None) if is_utc else datetime.now()
        diff = now - last_dt
        hours = diff.total_seconds() / 3600
        return f"{hours:.2f} hours ago"
    except:
        return "Unknown"

def main():
    lt = get_last_trade()
    tuner_info = get_tuner_info()
    
    # Critical Check: Is the tuner in an Error state?
    tuner_status = tuner_info['status']
    tuner_health = "HEALTHY"
    if "Error" in tuner_status or "CRITICAL" in tuner_info['last_log']:
        tuner_health = "CRITICAL FAILURE"

    health = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "overall_status": "OK" if tuner_health == "HEALTHY" else "ERROR",
        "services": {
            "trading-bot": get_service_status('trading-bot'),
            "backtest-optimizer": get_service_status('backtest-optimizer')
        },
        "last_trade": lt,
        "last_trade_age": get_age_str(lt, is_utc=True),
        "tuner": {
            "health": tuner_health,
            "status": tuner_status,
            "last_run": tuner_info['last_run'],
            "age": get_age_str(tuner_info['last_run'], is_utc=False),
            "last_log": tuner_info['last_log']
        },
        "recent_failed_trades_1h": check_failed_trades()
    }
    print(json.dumps(health, indent=4))

if __name__ == "__main__":
    main()
