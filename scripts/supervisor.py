#!/usr/bin/env python3
"""Permanent singleton lock, PID/start-time ownership and bounded quiet retries."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
def identity(pid):
    try:return Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return None

def alive(record):return identity(record['pid'])==record['start']
def competitors():
    found=[]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv=p.read_bytes().split(b'\0');text=b' '.join(argv)
            if (b'/push-ambient/src/' in text or b'/push-ambient/scripts/supervisor.py' in text or any(Path(a.decode(errors='replace')).name in ('Live','Push3','Push3Launcher') for a in argv if a)):
                found.append(int(p.parent.name))
        except OSError:pass
    return found

def main():
    p=argparse.ArgumentParser();p.add_argument('--home',default=str(ROOT));p.add_argument('--simulate',action='store_true');a=p.parse_args();home=Path(a.home);home.mkdir(parents=True,exist_ok=True)
    lock=(home/'supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    registry=home/'owner.json'
    if registry.exists() and alive(json.loads(registry.read_text())):raise RuntimeError('Prior hardware owner alive; registry retained')
    (home/'ready.json').unlink(missing_ok=True)
    (home/'recovery-request').unlink(missing_ok=True)
    running=True;child=None
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    (home/'supervisor.pid').write_text(str(os.getpid()))
    try:
        for attempt in range(3):
            if not running:break
            if not a.simulate and competitors():raise RuntimeError('Other hardware owner present; refusing takeover')
            read,write=os.pipe()
            cmd=[sys.executable,str(ROOT/'src/app.py'),'--home',str(home),'--start-fd',str(read)]
            if a.simulate:cmd+=['--simulate']
            logpath=home/'controller.log'
            if logpath.exists() and logpath.stat().st_size>2*1024*1024:os.replace(logpath,home/'controller.log.1')
            with logpath.open('ab',buffering=0) as log:
                child=subprocess.Popen(cmd,pass_fds=(read,),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            os.close(read)
            record=dict(pid=child.pid,start=identity(child.pid));temp=registry.with_suffix('.tmp');temp.write_text(json.dumps(record));os.replace(temp,registry)
            os.write(write,b'1');os.close(write)
            while running and child.poll() is None:time.sleep(.1)
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:raise RuntimeError('Child did not release hardware; owner retained')
            # wait() has reaped our exact child; another PID cannot be signalled.
            registry.unlink(missing_ok=True)
            request=home/'recovery-request'
            if request.exists():
                target=request.read_text().strip()
                if target not in ('stillwater','stock'):raise RuntimeError('Invalid recovery target')
                request.unlink()
                (home/'boot-target').write_text(target+'\n')
                original=home/'recovery'/('previous-init' if target=='stillwater' else 'stock-init')
                if not original.is_file():raise RuntimeError('Recovery init missing')
                if not a.simulate and competitors():raise RuntimeError('Competing hardware owner blocks recovery')
                subprocess.run([str(original),'start'],check=True)
                break
            if not running or child.returncode==0:break
            time.sleep(min(2**attempt,4))
        else:(home/'recovery-required').write_text('Repeated failure. Inspect controller.log; select Stillwater or stock deliberately.\n')
    finally:(home/'supervisor.pid').unlink(missing_ok=True)
if __name__=='__main__':main()
