#!/usr/bin/env python3
"""Boot dispatcher; original existing init and stock init remain verbatim backups."""
import json
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from supervisor import identity, alive
HOME=Path(os.environ.get('LIMINAL_HOME','/data/liminal-controller'))

def stop_controller():
    pidfile=HOME/'supervisor.pid';recordfile=HOME/'supervisor-owner.json'
    if recordfile.exists():
        r=json.loads(recordfile.read_text())
        if alive(r):
            os.kill(r['pid'],signal.SIGTERM)
            until=time.monotonic()+7
            while alive(r) and time.monotonic()<until:time.sleep(.1)
            if alive(r):raise RuntimeError('Supervisor still alive; refusing another owner')
    owner=HOME/'owner.json'
    if owner.exists() and alive(json.loads(owner.read_text())):raise RuntimeError('Controller still alive; refusing another owner')

def main():
    HOME.mkdir(parents=True,exist_ok=True)
    lock=(HOME/'dispatcher.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
    op=sys.argv[1] if len(sys.argv)>1 else 'status';recovery=HOME/'recovery';selection=HOME/'boot-target'
    target=selection.read_text().strip() if selection.exists() else 'stillwater'
    if op=='select':
        target=sys.argv[2]
        if target not in ('controller','stillwater','stock'):raise ValueError('target')
        stop_controller()
        # Selection does not start another application. Operator proves release first.
        temp=selection.with_suffix('.tmp');temp.write_text(target+'\n');os.replace(temp,selection);return
    if target!='controller':
        script=recovery/('previous-init' if target=='stillwater' else 'stock-init')
        if not script.exists():raise RuntimeError('Verified recovery init missing')
        os.execv(str(script),[str(script),op])
    if op=='stop':stop_controller()
    elif op=='start':
        if (HOME/'supervisor-owner.json').exists() and alive(json.loads((HOME/'supervisor-owner.json').read_text())):return
        with (HOME/'supervisor.log').open('ab',buffering=0) as log:
            p=subprocess.Popen([sys.executable,str(HOME/'scripts/supervisor.py'),'--home',str(HOME)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        (HOME/'supervisor-owner.json').write_text(json.dumps(dict(pid=p.pid,start=identity(p.pid))))
    elif op=='restart':
        stop_controller();fcntl.flock(lock,fcntl.LOCK_UN);subprocess.run([sys.executable,__file__,'start'],check=True)
    elif op=='status':print((HOME/'ready.json').read_text() if (HOME/'ready.json').exists() else 'Controller stopped')
    else:raise ValueError('start|stop|restart|status|select')
if __name__=='__main__':main()
