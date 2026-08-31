#!/usr/bin/env python3
import os, signal, time, subprocess
out = subprocess.check_output(["ps", "-eo", "pid,cmd"], text=True)
killed = []
for line in out.splitlines():
    if "python3 server.py" in line or "python3 server.py" in line:
        if "restart.py" in line:
            continue
        pid = int(line.split()[0])
        os.kill(pid, signal.SIGTERM)
        killed.append(pid)
print("killed", killed)
time.sleep(0.4)
