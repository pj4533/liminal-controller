#!/usr/bin/env python3
"""Device-only explicit deployment after independently trusted SSH authentication.
Preserves existing music/recordings; never enrolls keys, resets, or reboots.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import signal
import subprocess
import tarfile
import time

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def recordings():
    root=Path('/data/push-ambient/recordings')
    if not root.is_dir():raise RuntimeError('Expected existing recordings directory')
    return {str(p.relative_to(root)):dict(size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,inode=p.stat().st_ino) for p in sorted(root.rglob('*')) if p.is_file()}
def state_hashes():
    root=Path('/data/push-ambient/sessions')
    if not root.is_dir():raise RuntimeError('Expected Stillwater sessions')
    return {str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file()}
def preflight(init,qualify):
    data=Path(init).read_bytes()
    if not qualify and b'liminal-controller dispatcher' not in data:
        raise RuntimeError('Autostart requires designated primary controller dispatcher; qualify stock session without installing')
    if qualify and b'liminal-controller dispatcher' not in data and hashlib.sha256(data).hexdigest()!='af43fdc1987b3e5a7f6a4854e9d954483fb2ce37e1cc3716e5e709e325f3fb7d':
        raise RuntimeError('Unknown active init; inspect before releasing hardware')
    return data

def graceful_release(owner,init):
    if b'liminal-controller dispatcher' in Path(init).read_bytes():
        subprocess.run([str(init),'stop'],check=True,timeout=30);return
    # Stock documents SIGTERM to Live as graceful quit. Stop its launcher first
    # so no new child can race the release; never use stock init's kill -9.
    targets=[]
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv=path.read_bytes().split(b'\0');names=[Path(x.decode()).name for x in argv if x]
            if 'push3-launcher.pyc' in names or any(x in ('Live','Push3') for x in names):
                pid=int(path.parent.name);targets.append(dict(pid=pid,start=owner.identity(pid),launcher='push3-launcher.pyc' in names))
        except (OSError,UnicodeError):pass
    for record in sorted(targets,key=lambda r:not r['launcher']):
        if owner.alive(record):os.kill(record['pid'],signal.SIGTERM)
    deadline=time.monotonic()+30
    while any(owner.alive(r) for r in targets) and time.monotonic()<deadline:time.sleep(.1)
    if any(owner.alive(r) for r in targets):raise RuntimeError('Stock did not exit gracefully; no takeover')

def recover(home,init,previous,owner):
    # Roll back only after proving new hardware owners exited. Never force kill.
    record=home/'supervisor-owner.json'
    if record.exists():
        r=json.loads(record.read_text())
        if owner.alive(r):os.kill(r['pid'],signal.SIGTERM)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        live=[]
        for name in ('owner.json','supervisor-owner.json'):
            path=home/name
            if path.exists() and owner.alive(json.loads(path.read_text())):live.append(name)
        if not live:break
        time.sleep(.1)
    else:raise RuntimeError('Rollback blocked by live native owner; retain checkpoint')
    if owner.competitors():raise RuntimeError('Rollback blocked by competing owner')
    tmp=Path(init).with_name('push3.liminal-rollback');tmp.write_bytes(previous);tmp.chmod(Path(init).stat().st_mode);os.replace(tmp,init)
    subprocess.run([str(init),'start'],check=True,timeout=15)

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--qualify-only',action='store_true');a=p.parse_args()
    if os.geteuid()!=0 or os.uname().machine!='x86_64':raise RuntimeError('Device root/x86_64 required')
    if digest(a.archive)!=a.sha256:raise RuntimeError('Archive hash mismatch')
    home=Path('/data/liminal');stage=Path('/data/liminal.stage-'+a.sha256[:12]);checkpoint=Path('/data/liminal-checkpoint-'+a.sha256[:12])
    if any(path.exists() for path in (home,stage,checkpoint)):raise RuntimeError('Existing home/stage/checkpoint: inspect, do not overwrite')
    with tarfile.open(a.archive) as tar:
        members=tar.getmembers();total=0
        for entry in members:
            path=PurePosixPath(entry.name)
            if path.is_absolute() or '..' in path.parts or not entry.isfile():raise RuntimeError('Unsafe archive member')
            total+=entry.size
        if shutil.disk_usage('/data').free<total+1024**3:raise RuntimeError('Need payload plus1GiB free; never remove recordings')
        stage.mkdir()
        for entry in members:
            target=stage/entry.name;target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(entry) as source,target.open('wb') as destination:shutil.copyfileobj(source,destination,1024*1024)
            target.chmod(entry.mode&0o777)
    manifest=json.loads((stage/'manifest.json').read_text());actual={str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file()}
    if actual!=set(manifest['files'])|{'manifest.json'}:raise RuntimeError('Payload file whitelist mismatch')
    for name,expected in manifest['files'].items():
        if digest(stage/name)!=expected:raise RuntimeError('Payload file hash mismatch '+name)
    engine=(stage/'engine.so').read_bytes()
    if engine[:4]!=b'\x7fELF' or engine[18:20]!=b'\x3e\x00':raise RuntimeError('Native architecture mismatch')
    previous=preflight('/etc/init.d/push3',a.qualify_only)
    spec=importlib.util.spec_from_file_location('owner',stage/'scripts/standalone-supervisor.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    checkpoint.mkdir();shutil.copy2('/etc/init.d/push3',checkpoint/'push3.previous')
    if Path('/data/liminal-controller/recovery').is_dir():shutil.copytree('/data/liminal-controller/recovery',checkpoint/'controller-recovery')
    for name in ('boot-target','owner.json','supervisor-owner.json'):
        source=Path('/data/liminal-controller')/name
        if source.exists():shutil.copy2(source,checkpoint/('controller-'+name))
    try:
        graceful_release(owner,Path('/etc/init.d/push3'))
        if owner.competitors():raise RuntimeError('Previous hardware owner still alive; preserve registry')
        before=recordings();states=state_hashes()
        (checkpoint/'recordings-inventory.json').write_text(json.dumps(before,indent=2));(checkpoint/'sessions-hashes.json').write_text(json.dumps(states,indent=2))
        historical=Path('/data/push-ambient/recovery')
        inventory={str(p.relative_to(historical)):dict(size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,inode=p.stat().st_ino) for p in sorted(historical.rglob('*')) if p.is_file()}
        (checkpoint/'historical-recovery-inventory.json').write_text(json.dumps(inventory,indent=2))
        # Checkpoint current source/state; preserve historical backups in place.
        with tarfile.open(checkpoint/'stillwater-core.tar.gz','w:gz',compresslevel=1) as backup:
            for path in sorted(Path('/data/push-ambient').rglob('*')):
                relative=path.relative_to('/data/push-ambient')
                if relative.parts[0] in ('recordings','recovery') or not path.is_file() or path.is_symlink():continue
                backup.add(path,arcname=str(relative),recursive=False)
        stage.rename(home)
        if a.qualify_only:
            subprocess.run(['python3',str(home/'scripts/standalone-boot.py'),'start'],check=True,timeout=10)
        else:
            subprocess.run(['python3',str(home/'scripts/install-standalone.py')],check=True,timeout=10)
            subprocess.run(['/etc/init.d/push3','start'],check=True,timeout=10)
        deadline=time.monotonic()+45;initial=None
        while time.monotonic()<deadline:
            try:
                ready=json.loads((home/'ready.json').read_text())
                if ready.get('ready') and ready.get('alive') and ready.get('written',0)>0:initial=ready;break
            except (OSError,ValueError):pass
            time.sleep(.2)
        if initial is None:raise RuntimeError('Readiness/ALSA not established; inspect logs, do not start competing software')
        # Observe one uninterrupted minute; no programmatic audible notes.
        end=time.monotonic()+60
        while time.monotonic()<end:
            ready=json.loads((home/'ready.json').read_text())
            if ready.get('playing') or ready.get('peak',1)>1e-8 or ready.get('xruns') or not ready.get('alive'):raise RuntimeError('Stopped/silent/healthy acceptance failed')
            time.sleep(.5)
        if ready['written']<=initial['written'] or ready['display_frames']<=initial['display_frames']:raise RuntimeError('Audio/display counters did not advance')
        if before!=recordings() or states!=state_hashes():raise RuntimeError('Protected music inventory changed; preserve checkpoint and inspect')
    except Exception:
        recover(home,Path('/etc/init.d/push3'),previous,owner)
        raise
    report=dict(qualify_only=a.qualify_only,active_init_unchanged=Path('/etc/init.d/push3').read_bytes()==previous,source_commit=manifest['source_commit'],archive_sha256=a.sha256,initial=initial,final=ready,protected_recordings=len(before),protected_bytes=sum(x['size'] for x in before.values()),sessions_unchanged=True,reboot_tested=False,physical_audio_heard=False,checkpoint=str(checkpoint))
    (checkpoint/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
