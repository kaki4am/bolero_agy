import subprocess
import time
import os
import signal

def test_dashboard(script_name):
    print(f"Testing {script_name}...")
    # Start the process with a pipe for stdout/stderr
    # We use a pseudo-terminal if possible, or just check for immediate exit
    process = subprocess.Popen(
        ['./venv/bin/python3', script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid
    )
    
    time.sleep(3)
    
    # Check if process is still running
    poll = process.poll()
    if poll is not None:
        stdout, stderr = process.communicate()
        print(f"  {script_name} crashed immediately with exit code {poll}")
        print(f"  Error: {stderr}")
        return False
    
    # Process is still running, let's try to terminate it gracefully
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        time.sleep(1)
        if process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        print(f"  {script_name} is running and didn't crash on startup.")
        return True
    except Exception as e:
        print(f"  Error while stopping {script_name}: {e}")
        return True # Still consider it a success if it was running

if __name__ == "__main__":
    d1 = test_dashboard('dashboard.py')
    d2 = test_dashboard('backtest_dashboard.py')
    
    if d1 and d2:
        print("\nAll dashboards are healthy.")
        exit(0)
    else:
        print("\nOne or more dashboards failed the smoke test.")
        exit(1)
