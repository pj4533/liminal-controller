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
def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
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
    subprocess.run(['/etc/init.d/push3','stop'],check=True,timeout=30)
    spec=importlib.util.spec_from_file_location('owner',stage/'scripts/standalone-supervisor.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    if owner.competitors():raise RuntimeError('Previous hardware owner still alive; preserve registry')
    checkpoint.mkdir();shutil.copy2('/etc/init.d/push3',checkpoint/'push3.previous')
    if Path('/data/liminal-controller/recovery').is_dir():shutil.copytree('/data/liminal-controller/recovery',checkpoint/'controller-recovery')
    for name in ('boot-target','owner.json','supervisor-owner.json'):
        source=Path('/data/liminal-controller')/name
        if source.exists():shutil.copy2(source,checkpoint/('controller-'+name))
    before=recordings();states=state_hashes()
    (checkpoint/'recordings-inventory.json').write_text(json.dumps(before,indent=2));(checkpoint/'sessions-hashes.json').write_text(json.dumps(states,indent=2))
    # Full source/session/history/enabled checkpoint, excluding only large recordings.
    with tarfile.open(checkpoint/'stillwater-core.tar.gz','w:gz',compresslevel=1) as backup:
        for path in sorted(Path('/data/push-ambient').rglob('*')):
            relative=path.relative_to('/data/push-ambient')
            if relative.parts[0]=='recordings' or not path.is_file() or path.is_symlink():continue
            backup.add(path,arcname=str(relative),recursive=False)
    stage.rename(home)
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
    report=dict(source_commit=manifest['source_commit'],archive_sha256=a.sha256,initial=initial,final=ready,protected_recordings=len(before),protected_bytes=sum(x['size'] for x in before.values()),sessions_unchanged=True,reboot_tested=False,physical_audio_heard=False,checkpoint=str(checkpoint))
    (checkpoint/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
