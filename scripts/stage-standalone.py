#!/usr/bin/env python3
"""Whitelist clean x86_64 runtime plus explicitly authorized PRIVATE assets.
No keys, recorded music, settings, private history or vendor scripts are copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=('src/image_worker.py','src/standalone_app.py','src/standalone.py','src/standalone_render.py','src/sampler.py','src/composition.py','src/dialogue_ledger.py','src/hardware.py','src/midi.py','src/canvas.py','scripts/standalone-supervisor.py','scripts/standalone-boot.py','scripts/install-standalone.py','scripts/deploy-staged.py','LICENSE','LICENSE.push-hack','NOTICE','docs/lofi-samples.md')
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing existing destination')
    engine=(ROOT/'.build/engine-device.so').read_bytes()
    if engine[:4]!=b'\x7fELF' or engine[18:20]!=b'\x3e\x00':raise ValueError('x86_64 ELF required')
    a.out.mkdir(parents=True)
    for name in SOURCE:
        target=a.out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    (a.out/'engine.so').write_bytes(engine)
    tools=a.out/'tools';tools.mkdir()
    for name in ('ffmpeg','ffprobe','LICENSE.txt','provenance.json'):shutil.copy2(ROOT/'.build/tools'/name,tools/name)
    # Deliberately private; catalog itself records protected source archive locations.
    shutil.copytree(a.assets,a.out/'private-assets',ignore=shutil.ignore_patterns('*.tmp','dialogue-lines.json'))
    files={str(p.relative_to(a.out)):digest(p) for p in sorted(a.out.rglob('*')) if p.is_file()}
    manifest=dict(abi=1,architecture='x86_64-linux-gnu.2.35',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),upstream_liminal='67fde8da0c18bb8ace86d0a03a866f5670f141d6',files=files,private_commercial_assets=True)
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=a.out.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in sorted(a.out.rglob('*')):
            if path.is_file():tar.add(path,arcname=str(path.relative_to(a.out)),recursive=False)
    print(json.dumps(dict(files=len(files),bytes=sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file()),archive=str(archive),archive_bytes=archive.stat().st_size,sha256=digest(archive))))
if __name__=='__main__':main()
