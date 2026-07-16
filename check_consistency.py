"""
Consistency Checker - Verifies bot.py and portfolio_backtester.py are logically aligned.
Run as part of verify_system.py or standalone.
"""
import re
import json
import os

def check_consistency():
    print("\n=== Consistency Check: Bot vs Backtester Alignment ===")
    
    if not os.path.exists('bot.py') or not os.path.exists('portfolio_backtester.py'):
        print("  [FAIL] Missing bot.py or portfolio_backtester.py")
        return False
    
    with open('bot.py') as f:
        bot = f.read()
    with open('portfolio_backtester.py') as f:
        bt = f.read()
    
    issues = []
    
    # 1. Entry signal alignment - check setup names exist in both
    bot_setups = set(re.findall(r'setup\s*=\s*"(V\d+_\w+)"', bot))
    bt_setups = set(re.findall(r'setup\s*=\s*"(V\d+_\w+)"', bt))
    
    if bot_setups != bt_setups:
        only_bot = bot_setups - bt_setups
        only_bt = bt_setups - bot_setups
        if only_bot:
            issues.append(f"Setups in bot.py but NOT in backtester: {only_bot}")
        if only_bt:
            issues.append(f"Setups in backtester but NOT in bot.py: {only_bt}")
    else:
        print(f"  [PASS] Entry setups aligned: {bot_setups}")
    
    # 2. RSI threshold alignment
    bot_rsi_thresholds = re.findall(r'rsi.*?>\s*(\d+)\s*and\s*rsi.*?<=\s*(\d+)', bot)
    bt_rsi_thresholds = re.findall(r'rsi\s*>\s*(\d+)\s*and\s*rsi.*?<=\s*(\d+)', bt)
    if bot_rsi_thresholds and bt_rsi_thresholds:
        if set(bot_rsi_thresholds) != set(bt_rsi_thresholds):
            issues.append(f"RSI thresholds mismatch - Bot: {bot_rsi_thresholds}, BT: {bt_rsi_thresholds}")
        else:
            print(f"  [PASS] RSI thresholds aligned: {bot_rsi_thresholds}")
    
    # 3. Time filter alignment
    bot_hours = re.findall(r'allowed_hours\s*=\s*\{([^}]+)\}', bot)
    bt_hours = re.findall(r'allowed_hours\s*=\s*\{([^}]+)\}', bt)
    if bot_hours and bt_hours:
        if bot_hours != bt_hours:
            issues.append(f"Allowed hours mismatch - Bot: {bot_hours}, BT: {bt_hours}")
        else:
            print(f"  [PASS] Time-of-day filter aligned")
    elif bool(bot_hours) != bool(bt_hours):
        issues.append(f"Time filter exists in {'bot' if bot_hours else 'backtester'} but not the other")
    
    bot_days = re.findall(r'blocked_days\s*=\s*\{([^}]+)\}', bot)
    bt_days = re.findall(r'blocked_days\s*=\s*\{([^}]+)\}', bt)
    if bot_days and bt_days:
        if bot_days != bt_days:
            issues.append(f"Blocked days mismatch - Bot: {bot_days}, BT: {bt_days}")
        else:
            print(f"  [PASS] Day-of-week filter aligned")
    
    # 4. Trailing stop params - check both use the same config keys
    bot_trail_keys = set(re.findall(r"(?:params|self\.config)\.get\('(TRAILING_\w+|BE_\w+)'", bot))
    bt_trail_keys = set(re.findall(r"params\.get\('(TRAILING_\w+|BE_\w+)'", bt))
    if bot_trail_keys and bt_trail_keys:
        if bot_trail_keys != bt_trail_keys:
            issues.append(f"Trailing/BE params mismatch - Bot: {bot_trail_keys}, BT: {bt_trail_keys}")
        else:
            print(f"  [PASS] Trailing stop params aligned: {bot_trail_keys}")
    
    # 5. Time-based exit alignment
    bot_time_exit = re.findall(r'(\d+)\s*\*\s*3600', bot)
    bt_time_exit = re.findall(r'>\s*(\d+).*?(?:time|48h)', bt, re.IGNORECASE)
    bot_has_time_exit = '48 * 3600' in bot or 'TIME EXIT' in bot
    bt_has_time_exit = '2880' in bt or 'TimeExit' in bt
    if bot_has_time_exit != bt_has_time_exit:
        issues.append(f"Time exit mismatch - Bot has: {bot_has_time_exit}, BT has: {bt_has_time_exit}")
    else:
        if bot_has_time_exit:
            print(f"  [PASS] Time-based exit present in both")
    
    # 6. Min hold alignment
    bot_min_hold = '6 * 3600' in bot or 'min_hold' in bot
    bt_min_hold = '360' in bt and 'min_hold' in bt
    if bot_min_hold != bt_min_hold:
        issues.append(f"Min hold mismatch - Bot has: {bot_min_hold}, BT has: {bt_min_hold}")
    else:
        if bot_min_hold:
            print(f"  [PASS] Minimum hold period in both")
    
    # 7. Config keys used by bot vs what tuner optimizes
    if os.path.exists('tuner.py'):
        with open('tuner.py') as f:
            tuner = f.read()
        tuner_keys = set(re.findall(r"'(\w+)':\s*\[", tuner))
        bot_config_gets = set(re.findall(r"self\.config\.get\('(\w+)'", bot) + re.findall(r"self\.config\['(\w+)'\]", bot))
        
        tuner_not_used = tuner_keys - bot_config_gets - {'EMA_FAST', 'EMA_SLOW', 'VOLUME_SMA_WINDOW'}  # backtester-only is OK
        if tuner_not_used:
            issues.append(f"Tuner optimizes params not used by bot: {tuner_not_used}")
        else:
            print(f"  [PASS] All tuner params are used by bot or backtester")
    
    # 8. Config.json keys vs bot usage
    if os.path.exists('config.json'):
        with open('config.json') as f:
            config = json.load(f)
        config_keys = set(config.keys())
        bot_config_gets = set(re.findall(r"self\.config\.get\('(\w+)'", bot) + re.findall(r"self\.config\['(\w+)'\]", bot))
        bt_config_gets = set(re.findall(r"params\.get\('(\w+)'", bt) + re.findall(r"params\['(\w+)'\]", bt) + re.findall(r"params\.get\('(\w+)'", bt))
        all_used = bot_config_gets | bt_config_gets
        
        unused_config = config_keys - all_used
        if unused_config:
            # Not a hard fail, just a warning
            print(f"  [WARN] config.json keys not used anywhere: {unused_config}")
    
    # 9. Portfolio guard alignment
    bot_has_guard = 'PORTFOLIO_EJECT' in bot and 'PORTFOLIO_HARVEST' in bot
    bt_has_guard = 'PORTFOLIO_EJECT' in bt and 'PORTFOLIO_HARVEST' in bt
    if bot_has_guard and bt_has_guard:
        print(f"  [PASS] Portfolio guard (eject/harvest) in both")
    elif bot_has_guard != bt_has_guard:
        issues.append("Portfolio guard exists in one but not the other")
    
    # 10. Version string consistency
    bot_version = re.search(r'Strategy (V\d+)', bot)
    if os.path.exists('GEMINI.md'):
        with open('GEMINI.md') as f:
            gemini_version = re.search(r'Strategy (V\d+)', f.readline())
        if bot_version and gemini_version:
            if bot_version.group(1) != gemini_version.group(1):
                issues.append(f"Version mismatch: bot.py={bot_version.group(1)}, GEMINI.md={gemini_version.group(1)}")
            else:
                print(f"  [PASS] Version consistent: {bot_version.group(1)}")
    
    # Summary
    if issues:
        print(f"\n  [FAIL] Found {len(issues)} consistency issues:")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
        return False
    else:
        print(f"\n  [PASS] All consistency checks passed!")
        return True

if __name__ == "__main__":
    import sys
    success = check_consistency()
    sys.exit(0 if success else 1)
