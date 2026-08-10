import os
import json
from datetime import datetime

# Whitelist of permanent allowed files directly under /root/
WHITELIST = {
    # Core system scripts
    'bot.py',
    'tuner.py',
    'portfolio_backtester.py',
    'trading_utils.py',
    'verify_system.py',
    'send_daily_report.py',
    'optimize.sh',
    'export_report.py',
    'system_health.py',
    'check_pnl.py',
    'run_quick_validation.py',
    'sell_all.py',
    'get_balance.py',
    'debug_pnl.py',
    'cleanup_system.py',
    'run_bt.py',
    'get_db_stats.py',
    'db_stats_summary.txt',
    'ai_manager.py',
    
    # Dashboards and visualizers
    'dashboard.py',
    'backtest_dashboard.py',
    'test_dashboards.py',
    'bolero.py',
    
    # Core tests
    'test_strategy.py',
    'test_pb.py',
    'test_backtest.py',
    'check_consistency.py',
    
    # Configurations and databases
    'config.json',
    'restricted_pairs.json',
    'version_history_log.json',
    'trading_bot.db',
    '.env',
    '.env.template',
    '.gitignore',
    '.bashrc',
    '.profile',
    '.bash_history',
    'GEMINI.md',
    'verify.log',
    'email_report.log',
    'strategy_evolver.log',
    'daily_opinion.html',
    'daily_report.json',
    'backtest_status.json',
    'cleanup_log.json',
    'trading-bot.service',
    'backtest-optimizer.service',
    
    # AI Manager Overrides & Logs
    'tactical_overrides.json',
    'ai_manager.log',
    'active_positions.json',
    'weekly_research.sh',
    'weekly_research.html',
    'weekly_research.log',
    'price_research.sh',
    'price_research.html',
    'price_research.log'
}

def run_cleanup():
    deleted_files = []
    
    # Iterate over files in current directory
    for item in os.listdir('.'):
        # We only check files directly in the root directory (skip subdirectories)
        if os.path.isfile(item):
            if item not in WHITELIST:
                try:
                    os.remove(item)
                    deleted_files.append(item)
                    print(f"Removed obsolete file: {item}")
                except Exception as e:
                    print(f"Failed to remove {item}: {e}")
                    
    # Log deleted files to JSON for send_daily_report.py
    log_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "deleted_files": deleted_files
    }
    
    try:
        with open('cleanup_log.json', 'w') as f:
            json.dump(log_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save cleanup log: {e}")

if __name__ == "__main__":
    run_cleanup()
