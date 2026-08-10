import subprocess
import sys
import os
import importlib.util
import pandas as pd
import pandas_ta as ta
import numpy as np
import asyncio
import re
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from dotenv import load_dotenv
from binance import AsyncClient

def check_syntax():
    print("Step 1: Syntax Check")
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'verify_system.py' and not f.startswith('experiment') and not f.startswith('test')]
    for file in py_files:
        try:
            subprocess.check_output([sys.executable, '-m', 'py_compile', file], stderr=subprocess.STDOUT)
            print(f"  [PASS] {file}")
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] {file}: Syntax Error detected!")
            print(e.output.decode())
            return False
    return True

def check_bot_logic():
    print("\nStep 2: Bot Logic Dry-Run")
    try:
        spec = importlib.util.spec_from_file_location("bot", "bot.py")
        bot_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_mod)
        
        bot = bot_mod.TradingBot()
        bot.config['MIN_VOLATILITY_PCT'] = 0.01 
        bot.client = MagicMock()
        bot.bm = MagicMock()
        
        mock_df = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-05-10', periods=250, freq='min'),
            'open': np.random.uniform(100, 110, 250),
            'high': np.random.uniform(110, 120, 250),
            'low': np.random.uniform(90, 100, 250),
            'close': np.random.uniform(100, 110, 250),
            'volume': np.random.uniform(1000, 5000, 250)
        })
        
        bot.data_1m['TESTUSDT'] = mock_df
        bot.exchange_info['TESTUSDT'] = {'isAllowed': True}
        
        if not hasattr(bot, 'portfolio_guard_loop'):
            print("  [FAIL] bot.logic: Missing portfolio_guard_loop (V86 requirement)")
            return False
            
        asyncio.run(bot.analyze('TESTUSDT'))
        print("  [PASS] bot.analyze executed without runtime errors.")
        return True
    except Exception as e:
        print(f"  [FAIL] bot.logic: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_backtester():
    print("\nStep 3: Backtester Smoke Test")
    try:
        spec = importlib.util.spec_from_file_location("pb", "portfolio_backtester.py")
        pb_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pb_mod)
        
        tester = pb_mod.PortfolioBacktester(symbols=['TESTUSDT'])
        
        search_space = {
            'EMA_FAST': [50], 'EMA_SLOW': [200], 'ST_PERIOD': [7], 'ST_MULT': [3.0],
            'CHOP_PERIOD': [14], 'ADX_PERIOD': [14], 'BB_LENGTH': [20], 'BB_STD': [2.0],
            'ATR_PERIOD': [14], 'STOCH_K': [14], 'STOCH_D': [3], 'MFI_PERIOD': [14],
            'CMF_PERIOD': [20], 'OBV_EMA_PERIOD': [30], 'KC_PERIOD': [20], 'KC_MULT': [2.0],
            'VWMA_PERIOD': [20]
        }
        
        mock_df_1m = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-05-10', periods=1000, freq='min'),
            'open': np.random.uniform(100, 110, 1000),
            'high': np.random.uniform(110, 120, 1000),
            'low': np.random.uniform(90, 100, 1000),
            'close': np.random.uniform(100, 110, 1000),
            'volume': np.random.uniform(1000, 5000, 1000)
        })
        mock_df_15m = pd.DataFrame({
            'timestamp': pd.date_range(start='2026-05-10', periods=100, freq='15min'),
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        })
        
        tester.pair_data = {'TESTUSDT': {'1m': mock_df_1m, '15m': mock_df_15m}}
        tester.precalculate_all(search_space)
        results = tester.run({
            'EMA_FAST': 50, 'EMA_SLOW': 200, 'ST_PERIOD': 7, 'ST_MULT': 3.0,
            'CHOP_PERIOD': 14, 'ADX_PERIOD': 14, 'BB_LENGTH': 20, 'BB_STD': 2.0,
            'ATR_PERIOD': 14, 'STOCH_K': 14, 'STOCH_D': 3, 'MFI_PERIOD': 14,
            'CMF_PERIOD': 20, 'OBV_EMA_PERIOD': 30, 'KC_PERIOD': 20, 'KC_MULT': 2.0,
            'VWMA_PERIOD': 20, 'RSI_PERIOD': 14, 'CHOP_THRESHOLD': 50, 'ADX_THRESHOLD': 25,
            'STOCH_OVERSOLD': 20, 'PRICE_DROP_THRESHOLD': 0.03, 'MAX_ENTRIES_PER_PAIR': 2,
            'VOL_SPIKE_MULT': 2.0
        })
        
        print(f"  [PASS] Backtester finished test run. Profit: {results}%")
        return True
    except Exception as e:
        print(f"  [FAIL] backtester.logic: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_monitoring():
    print("\nStep 4: Monitoring Scripts Check")
    scripts = ['system_health.py', 'export_report.py', 'check_pnl.py']
    for script in scripts:
        if not os.path.exists(script): continue
        try:
            subprocess.check_output([sys.executable, script], stderr=subprocess.STDOUT)
            print(f"  [PASS] {script} executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] {script} failed execution!")
            print(e.output.decode())
            return False
    return True

def check_version_consistency():
    print("\nStep 5: Strategy Version Consistency Check")
    strategy_v_pattern = r'Strategy V(\d+)'
    versions = {}
    
    if os.path.exists('GEMINI.md'):
        with open('GEMINI.md', 'r') as f:
            first_line = f.readline()
            match = re.search(strategy_v_pattern, first_line)
            if match:
                versions['GEMINI.md'] = match.group(1)
    
    memory_path = '/root/.gemini/tmp/root/memory/MEMORY.md'
    if os.path.exists(memory_path):
        with open(memory_path, 'r') as f:
            content = f.read()
            matches = re.findall(strategy_v_pattern, content)
            if matches:
                versions['MEMORY.md'] = max(matches, key=int)
    
    if os.path.exists('bot.py'):
        with open('bot.py', 'r') as f:
            content = f.read()
            match = re.search(strategy_v_pattern, content)
            if match:
                versions['bot.py'] = match.group(1)
                
    if not versions:
        print("  [WARN] No Strategy Version (Vxx) found in GEMINI.md, MEMORY.md, or bot.py")
        return True
        
    if 'GEMINI.md' in versions and 'bot.py' in versions:
        if versions['GEMINI.md'] != versions['bot.py']:
            print(f"  [FAIL] Strategy Version Mismatch between GEMINI.md (V{versions['GEMINI.md']}) and bot.py (V{versions['bot.py']})!")
            return False
            
    if 'MEMORY.md' in versions and 'GEMINI.md' in versions:
        if versions['MEMORY.md'] != versions['GEMINI.md']:
            target_ver = versions['GEMINI.md']
            print(f"  [WARN] MEMORY.md version (V{versions['MEMORY.md']}) is out of sync with GEMINI.md (V{target_ver}). Auto-updating MEMORY.md...")
            try:
                with open(memory_path, 'r') as f:
                    mem_content = f.read()
                new_mem_content = re.sub(
                    r'- \*\*Stable Version\*\*: Strategy V\d+',
                    f'- **Stable Version**: Strategy V{target_ver}',
                    mem_content
                )
                ver_log_entry = f"- [x] Strategy V{target_ver}: Auto-aligned version via verify_system.py"
                if ver_log_entry not in new_mem_content:
                    new_mem_content = new_mem_content.replace(
                        f'- **Stable Version**: Strategy V{target_ver}',
                        f'{ver_log_entry}\n- **Stable Version**: Strategy V{target_ver}'
                    )
                with open(memory_path, 'w') as f:
                    f.write(new_mem_content)
                print("  [PASS] MEMORY.md auto-aligned successfully.")
                versions['MEMORY.md'] = target_ver
            except Exception as e:
                print(f"  [WARN] Failed to auto-update MEMORY.md: {e}")
                
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        print(f"  [FAIL] Strategy Version Mismatch detected!")
        for source, v in versions.items():
            print(f"    - {source}: V{v}")
        return False
        
    print(f"  [PASS] All sources consistent at Strategy V{list(unique_versions)[0]}")
    return True

async def run_single_stress(client, tester, params, period, symbols):
    # Calculate warmup dates (12 days for BTC 1h, 5 days for 15m)
    start_date = datetime.strptime(period['start'].split(' ')[0], "%Y-%m-%d")
    btc_1h_start = (start_date - timedelta(days=12)).strftime("%Y-%m-%d") + " UTC"
    btc_15m_start = (start_date - timedelta(days=5)).strftime("%Y-%m-%d") + " UTC"

    # Fetch BTC hourly and 15m klines for filters
    btc_1h = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_1HOUR, btc_1h_start, period['end'])
    tester.btc_df = pd.DataFrame(btc_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
    tester.btc_df['close'] = tester.btc_df['close'].astype(float)
    tester.btc_df['timestamp'] = pd.to_datetime(tester.btc_df['timestamp'], unit='ms')
    tester.btc_df['ema200'] = ta.ema(tester.btc_df['close'], length=200)
    tester.btc_df['rsi'] = ta.rsi(tester.btc_df['close'], length=14)
    
    btc_15m = await client.get_historical_klines("BTCUSDT", AsyncClient.KLINE_INTERVAL_15MINUTE, btc_15m_start, period['end'])
    tester.btc_15m = pd.DataFrame(btc_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
    tester.btc_15m['close'] = tester.btc_15m['close'].astype(float)
    tester.btc_15m['timestamp'] = pd.to_datetime(tester.btc_15m['timestamp'], unit='ms')
    tester.btc_15m['ema200'] = ta.ema(tester.btc_15m['close'], length=200)

    for s in symbols:
        kl_1m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_1MINUTE, period['start'], period['end'])
        kl_15m = await client.get_historical_klines(s, AsyncClient.KLINE_INTERVAL_15MINUTE, btc_15m_start, period['end'])
        
        df_1m = pd.DataFrame(kl_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_1m[col] = df_1m[col].astype(float)
        df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
        
        df_15m = pd.DataFrame(kl_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_15m[col] = df_15m[col].astype(float)
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
        
        tester.pair_data[s] = {'1m': df_1m, '15m': df_15m}

    tester.precalculate_all({k: [v] for k, v in params.items()})
    return tester.run(params)

def check_historical_stress_tests():
    print("\nStep 6: Historical Stress Testing & Random Walk Validation")
    load_dotenv('/root/.env')
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("  [FAIL] Missing BINANCE_API_KEY/SECRET in .env!")
        return False

    spec = importlib.util.spec_from_file_location("pb", "portfolio_backtester.py")
    pb_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb_mod)
    
    import json
    config_params = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config_params = json.load(f)
        except: pass
    if not config_params:
        config_params = {
            "EMA_FAST": 50, "EMA_SLOW": 200, "MIN_VOLATILITY": 0.001,
            "BASE_RISK_PERCENT": 2.0, "ATR_SL_MULT": 3.0,
            "PORTFOLIO_EJECT": -5.0, "PORTFOLIO_HARVEST": 5.0
        }

    # Stress periods setup
    stress_periods = [
        {"name": "COVID Liquidations (March 2020)", "start": "2020-03-09 UTC", "end": "2020-03-16 UTC"},
        {"name": "FTX Collapse (November 2022)", "start": "2022-11-05 UTC", "end": "2022-11-13 UTC"},
        {"name": "Leverage Flush (August 2023)", "start": "2023-08-15 UTC", "end": "2023-08-22 UTC"}
    ]
    
    # Generate a completely random historical week from the last 9 years (between 60 days ago and 3280 days ago)
    days_back = random.randint(60, 3280)
    rand_start = datetime.now(timezone.utc) - timedelta(days=days_back)
    rand_end = rand_start + timedelta(days=7)
    
    rand_start_str = rand_start.strftime("%Y-%m-%d UTC")
    rand_end_str = rand_end.strftime("%Y-%m-%d UTC")
    
    stress_periods.append({
        "name": f"Random Walk Validation (Starting {rand_start.strftime('%Y-%m-%d')})",
        "start": rand_start_str,
        "end": rand_end_str,
        "is_random": True
    })
    
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    async def run_all_async():
        client = await AsyncClient.create(api_key, api_secret, testnet=False)
        results = {}
        try:
            for period in stress_periods:
                tester = pb_mod.PortfolioBacktester(symbols=symbols)
                pnl = await run_single_stress(client, tester, config_params, period, symbols)
                results[period['name']] = (pnl, period.get('is_random', False))
        finally:
            await client.close_connection()
        return results
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_all_async())
        loop.close()
    except Exception as e:
        print(f"  [FAIL] Error running historical stress tests: {e}")
        return False

    success = True
    for k, (pnl, is_random) in results.items():
        if pnl is None:
            print(f"  [FAIL] {k}: Fetch Error")
            success = False
        else:
            # Random walks must not experience catastrophic loss (safety limit of -10.0%)
            floor = -10.0 if is_random else -15.0
            if pnl < floor:
                print(f"  [FAIL] {k}: {pnl:+.2f}% (Violated safety floor of {floor}%)")
                success = False
            else:
                print(f"  [PASS] {k}: {pnl:+.2f}%")
            
    return success

def check_email_alignment():
    print("\nStep 6: Email Report Alignment Check")
    try:
        import json
        if not os.path.exists('config.json'):
            print("  [FAIL] config.json not found")
            return False
        with open('config.json', 'r') as f:
            active_config = json.load(f)
            
        gemini_path = 'GEMINI.md'
        active_ver = "Unknown"
        if os.path.exists(gemini_path):
            with open(gemini_path, 'r') as f:
                first_line = f.readline()
                match = re.search(r'Strategy (V\d+)', first_line)
                if match:
                    active_ver = match.group(1)
                    
        spec = importlib.util.spec_from_file_location("report", "send_daily_report.py")
        report_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report_mod)
        
        mock_health = {
            'overall_status': 'OK',
            'services': {'trading-bot': 'active', 'backtest-optimizer': 'active'}
        }
        mock_pnl = {
            'total_realized_pnl': 0.0,
            'completed_trades': [],
            'failed_trades_count': 0
        }
        mock_strategy = {
            'current_strategy': f'Binance Trading Bot (Strategy {active_ver})',
            'version': f'Strategy {active_ver}',
            'latest_task': 'None',
            'version_age_days': 0
        }
        mock_projection = {
            'start_date': '2026-07-01',
            'end_date': '2026-07-05',
            'returns_table': '<tr></tr>',
            'r_daily_v90': 0.0,
            'r_daily_10d': 0.0,
            'p1': 0.0, 'p2': 0.0, 'p5': 0.0, 'p10': 0.0,
            'p1_10d': 0.0, 'p2_10d': 0.0
        }
        mock_random_walk = {'pnl': 0.0, 'start': '2026-07-01', 'end': '2026-07-05', 'relative_age': '0 days', 'symbols': []}
        
        body_html = report_mod.format_email_body(
            mock_health, mock_pnl, "", "", mock_strategy, mock_projection, mock_random_walk
        )
        
        if active_ver != "Unknown" and f"Strategy {active_ver}" not in body_html:
            print(f"  [FAIL] Email content does not mention active version: Strategy {active_ver}")
            return False
            
        for key, val in active_config.items():
            if key not in body_html:
                print(f"  [FAIL] Email parameter table is missing active config key: {key}")
                return False
                
        if "+-" in body_html:
            print("  [FAIL] Email content contains display glitch '+-'")
            return False
            
        print("  [PASS] Email alignment check passed (verified version, parameters, and formatting).")
        return True
    except Exception as e:
        print(f"  [FAIL] Email alignment check error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_code_quality():
    print("\nStep 7: Code Quality & Dead Code Check (pyflakes & vulture)")
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'verify_system.py' and not f.startswith('experiment') and not f.startswith('test')]
    if not py_files:
        print("  [PASS] No Python files to check.")
        return True

    success = True

    # 1. Run pyflakes
    print("  Running pyflakes...")
    try:
        cmd = ['/root/venv/bin/pyflakes'] + py_files
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        print("    [PASS] pyflakes check passed.")
    except subprocess.CalledProcessError as e:
        print("    [FAIL] pyflakes detected code quality or import issues:")
        print(e.output.decode())
        success = False
    except Exception as e:
        print(f"    [FAIL] Failed to run pyflakes: {e}")
        success = False

    # 2. Run vulture
    print("  Running vulture...")
    try:
        cmd = ['/root/venv/bin/vulture'] + py_files
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        print("    [PASS] vulture check passed.")
    except subprocess.CalledProcessError as e:
        print("    [FAIL] vulture detected unused code:")
        print(e.output.decode())
        success = False
    except Exception as e:
        print(f"    [FAIL] Failed to run vulture: {e}")
        success = False

    return success

if __name__ == "__main__":
    print("\n--- Running System Verification ---")
    
    # 1. Independent Static Checks (always run all of these to aggregate errors)
    syntax_ok = check_syntax()
    quality_ok = check_code_quality()
    version_ok = check_version_consistency()
    email_ok = check_email_alignment()
    
    static_success = syntax_ok and quality_ok and version_ok and email_ok
    overall_success = static_success
    
    # 2. Runtime Checks (only run if static checks passed to prevent cascading tracebacks)
    if static_success:
        logic_ok = check_bot_logic()
        backtester_ok = check_backtester()
        
        try:
            from check_consistency import check_consistency
            consistency_ok = check_consistency()
        except Exception as e:
            print(f"  [FAIL] check_consistency error: {e}")
            consistency_ok = False
            
        monitoring_ok = check_monitoring()
        
        runtime_success = logic_ok and backtester_ok and consistency_ok and monitoring_ok
        overall_success = overall_success and runtime_success
        
        # 3. Slow API Checks (only run if runtime logic is sound)
        if runtime_success:
            stress_ok = check_historical_stress_tests()
            overall_success = overall_success and stress_ok
        else:
            print("\n[WARN] Skipping historical stress tests due to runtime check failures.")
    else:
        print("\n[WARN] Skipping runtime and stress tests due to static check failures.")
        
    if overall_success:
        print("\n[SUCCESS] System Verification Passed.")
        sys.exit(0)
    else:
        print("\n[CRITICAL] System Verification Failed! Please fix ALL the above errors.")
        sys.exit(1)
