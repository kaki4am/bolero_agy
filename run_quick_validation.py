import pickle
import glob
import os
import sys
import json

if len(sys.argv) > 1 and sys.argv[1] == '--baseline':
    import importlib.util
    import shutil
    shutil.copy2('/root/backups/portfolio_backtester.py.bak', '/tmp/pb_temp.py')
    spec = importlib.util.spec_from_file_location('pb', '/tmp/pb_temp.py')
    pb = importlib.util.module_from_spec(spec)
    sys.modules['pb'] = pb
    spec.loader.exec_module(pb)
    PortfolioBacktester = pb.PortfolioBacktester
    
    try:
        with open('/root/backups/config.json.bak', 'r') as f:
            params = json.load(f)
    except:
        with open('/root/config.json', 'r') as f:
            params = json.load(f)
else:
    from portfolio_backtester import PortfolioBacktester
    with open('/root/config.json', 'r') as f:
        params = json.load(f)

def main():
    cache_files = glob.glob('/root/.backtester_cache/segment_*_UTC_*.pkl')
    if not cache_files:
        import traceback; traceback.print_exc(); print("-999.0")
        return
        
    latest_cache = max(cache_files, key=os.path.getmtime)
    
    try:
        with open(latest_cache, 'rb') as f:
            cached = pickle.load(f)
            
        tester = PortfolioBacktester(symbols=list(cached['pair_data'].keys()))
        tester.pair_data = cached['pair_data']
        tester.btc_df = cached.get('btc_df')
        tester.btc_15m = cached.get('btc_15m')
            
        tester.precalculate_all(params)
        res = tester.run(params)
        print(f"{res:.4f}")
    except Exception:
        import traceback; traceback.print_exc(); print("-999.0")

if __name__ == "__main__":
    main()
