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

def check_trading_bot_log_health():
    """Inspects journalctl logs for the currently running trading-bot.service for uncaught exceptions, tracebacks, or task failures."""
    try:
        start_ts = None
        try:
            ts_out = subprocess.check_output(['systemctl', 'show', '-p', 'ActiveEnterTimestamp', 'trading-bot.service'], text=True).strip()
            if '=' in ts_out:
                val = ts_out.split('=', 1)[1].strip()
                if val:
                    start_ts = val
        except Exception:
            pass

        cmd = ['journalctl', '-u', 'trading-bot.service']
        if start_ts:
            cmd.extend(['--since', start_ts])
        else:
            cmd.extend(['--since', '-15m'])
        cmd.extend(['--no-pager'])

        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        errors = []
        for line in res.splitlines():
            lower = line.lower()
            if any(err_word in lower for err_word in [
                'traceback (most recent call last)',
                'keyerror:',
                'attributeerror:',
                'nameerror:',
                'typeerror:',
                'task exception was never retrieved',
                'critical error in process_and_analyze',
                'asyncio background task failure'
            ]):
                errors.append(line.strip())
        if errors:
            return {
                "status": "CRITICAL_ERROR",
                "error_count": len(errors),
                "latest_error": errors[-1]
            }
        return {"status": "HEALTHY", "error_count": 0, "latest_error": None}
    except Exception as e:
        return {"status": "UNKNOWN", "error_count": 0, "latest_error": str(e)}

def main():
    lt = get_last_trade()
    tuner_info = get_tuner_info()
    bot_log_health = check_trading_bot_log_health()
    
    # Critical Check: Is the tuner or trading bot in an Error state?
    tuner_status = tuner_info['status']
    tuner_health = "HEALTHY"
    if "Error" in tuner_status or "CRITICAL" in tuner_info['last_log']:
        tuner_health = "CRITICAL FAILURE"

    if bot_log_health['status'] == "CRITICAL_ERROR":
        overall_status = "CRITICAL ERROR"
    elif tuner_health != "HEALTHY":
        overall_status = "ERROR"
    else:
        overall_status = "OK"

    health = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "overall_status": overall_status,
        "services": {
            "trading-bot": get_service_status('trading-bot'),
            "trading-bot-logs": bot_log_health['status'],
            "backtest-optimizer": get_service_status('backtest-optimizer')
        },
        "bot_log_health": bot_log_health,
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
