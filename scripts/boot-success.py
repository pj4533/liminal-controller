#!/usr/bin/env python3
"""Acknowledge only a sustained healthy PRIMARY boot through stock's API.
Never acknowledges secondary, changes firmware, starts Live or forces reboot.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

def healthy(previous,current,pid):
    return (current.get('pid')==pid and current.get('ready') and current.get('alive')
            and isinstance(current.get('xruns'),int) and current['xruns']>=0
            and current['xruns']==previous.get('xruns') and not current.get('error')
            and current.get('written',0)>previous.get('written',0)
            and current.get('display_frames',0)>previous.get('display_frames',0))
def wait_ready(home,pid):
    deadline=time.monotonic()+120;baseline=None;since=None;previous={}
    while time.monotonic()<deadline:
        try:current=json.loads((home/'ready.json').read_text())
        except (OSError,ValueError):current={}
        now=time.monotonic();xruns=current.get('xruns')
        valid=(current.get('pid')==pid and current.get('ready') and current.get('alive')
               and isinstance(xruns,int) and xruns>=0 and not current.get('error')
               and 0<=now-current.get('monotonic',0)<=2)
        if not valid or (baseline is not None and not healthy(previous,current,pid)):
            baseline=None;since=None
        elif baseline is None:baseline=current;since=now
        elif now-since>=60:
            if not healthy(baseline,current,pid):raise RuntimeError('Counters failed; retain secondary fallback')
            return baseline,current,now-since
        previous=current;time.sleep(.5)
    raise RuntimeError('Primary readiness timeout; retain secondary fallback')
def main():
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,default=Path('/data/liminal'));p.add_argument('--pid',type=int,required=True);a=p.parse_args()
    if 'root=PARTLABEL=primary' not in Path('/proc/cmdline').read_text().split():return
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip();receipt=a.home/'boot-success.json'
    if receipt.exists() and json.loads(receipt.read_text()).get('boot_id')==boot_id:return
    baseline,current,elapsed=wait_ready(a.home,a.pid)
    dbus=['dbus-send','--system','--print-reply','--reply-timeout=5000','--dest=com.ableton.update','/com/ableton/Update']
    probe=subprocess.run(dbus+['org.freedesktop.DBus.Introspectable.Introspect'],capture_output=True,timeout=7)
    if probe.returncode:
        with (a.home/'update-service.log').open('ab',buffering=0) as log:
            subprocess.Popen(['/opt/push3/UpdateDBusService'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(20):
            probe=subprocess.run(dbus+['org.freedesktop.DBus.Introspectable.Introspect'],capture_output=True,timeout=7)
            if probe.returncode==0:break
            time.sleep(.25)
        else:raise RuntimeError('Stock update service unavailable; retain secondary fallback')
    if b'registerSuccessfulStartup' not in probe.stdout:raise RuntimeError('Unexpected stock API')
    result=subprocess.run(dbus+['com.ableton.update.registerSuccessfulStartup'],capture_output=True,text=True,check=True,timeout=7)
    env=subprocess.check_output(['grub-editenv','/boot/EFI/BOOT/grubenv','list'],text=True,timeout=5)
    values=dict(line.split('=',1) for line in env.splitlines() if '=' in line)
    if values.get('default_part')!='primary' or values.get('fallback_part')!='secondary':raise RuntimeError('Stock API did not confirm primary boot state')
    data=dict(boot_id=boot_id,pid=a.pid,baseline=baseline,final=current,healthy_seconds=elapsed,
              xruns_baseline=baseline['xruns'],xruns_final=current['xruns'],xruns_delta=current['xruns']-baseline['xruns'],
              grubenv=values,method_reply=result.stdout,service='stock UpdateDBusService without Live service')
    tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(receipt)
    print(json.dumps(data),flush=True)
if __name__=='__main__':main()
