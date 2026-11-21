#!/usr/bin/env python3
"""Reversible standalone boot wrapper over the preserved remote/Stillwater selector."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owner',ROOT/'scripts/standalone-supervisor.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
def stopped(home):
    record=home/'supervisor-owner.json'
    if record.exists():
        r=json.loads(record.read_text())
        if owner.alive(r):
            os.kill(r['pid'],signal.SIGTERM);deadline=time.monotonic()+10
            while owner.alive(r) and time.monotonic()<deadline:time.sleep(.1)
            if owner.alive(r):raise RuntimeError('Supervisor still alive; retain ownership evidence')
    record=home/'owner.json'
    if record.exists() and owner.alive(json.loads(record.read_text())):raise RuntimeError('App still alive; no takeover')
def original(home):
    path=home/'recovery/previous-init';expected=json.loads((home/'recovery/init-hashes.json').read_text())['previous-init']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Recovery init hash mismatch')
    return path

def main():
    p=argparse.ArgumentParser();p.add_argument('op',choices=('start','stop','restart','status','select'));p.add_argument('target',nargs='?');p.add_argument('--home',type=Path,default=Path('/data/liminal'));a=p.parse_args();home=a.home
    with (home/'dispatcher.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);selection=home/'boot-target';target=selection.read_text().strip() if selection.exists() else 'liminal'
        if a.op=='select':
            if a.target not in ('liminal','controller','stillwater','stock'):raise ValueError('target')
            stopped(home)
            if target!='liminal':subprocess.run([str(original(home)),'stop'],check=True)
            if a.target!='liminal':
                subprocess.run([sys.executable,'/data/liminal-controller/scripts/dispatch.py','select',a.target],check=True)
            tmp=selection.with_suffix('.tmp');tmp.write_text(a.target+'\n');os.replace(tmp,selection);return
        if target!='liminal':os.execv(str(original(home)),[str(original(home)),a.op])
        if a.op=='stop':stopped(home);return
        if a.op=='status':print((home/'ready.json').read_text() if (home/'ready.json').exists() else 'Liminal stopped');return
        if a.op=='restart':stopped(home)
        record=home/'supervisor-owner.json'
        if record.exists() and owner.alive(json.loads(record.read_text())):return
        with (home/'supervisor.log').open('ab',buffering=0) as log:
            child=subprocess.Popen([sys.executable,str(home/'scripts/standalone-supervisor.py'),'--home',str(home)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        record.write_text(json.dumps(dict(pid=child.pid,start=owner.identity(child.pid))))
if __name__=='__main__':main()
