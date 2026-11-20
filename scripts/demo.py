#!/usr/bin/env python3
"""Run the real app against a deterministic peer, without touching hardware."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fake_server import FakeServer
p=argparse.ArgumentParser();p.add_argument('--seconds',default=3,type=float);p.add_argument('--screenshot',default='.build/demo.ppm');a=p.parse_args();root=Path(__file__).resolve().parents[1];Path(a.screenshot).parent.mkdir(parents=True,exist_ok=True)
s=FakeServer(ambient=True).start()
try:
    with tempfile.TemporaryDirectory() as home:
        subprocess.run([sys.executable,str(root/'src/app.py'),'--simulate','--home',home,'--host','127.0.0.1','--port',str(s.port),'--seconds',str(a.seconds),'--screenshot',a.screenshot],check=True)
finally:s.close()
