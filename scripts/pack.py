#!/usr/bin/env python3
"""Whitelist release payload: stdlib sources and packed artwork only, no private state."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--liminal-commit',help='Full tested Liminal push3 commit paired with this payload');a=p.parse_args()
if a.liminal_commit and (len(a.liminal_commit)!=40 or any(c not in '0123456789abcdef' for c in a.liminal_commit)):p.error('liminal commit must be 40 lowercase hex digits')
files=sorted([p for d in ('src','scripts') for p in (ROOT/d).glob('*.py') if p.name not in ('fake_server.py','demo.py','prepare-art.py','native-acceptance.py','preview.py')]+[ROOT/f for f in ('assets/film-table.bin','LICENSE','LICENSE.push-hack','NOTICE')])
output=ROOT/'.build';output.mkdir(exist_ok=True)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest['source_commits']={'liminal-controller':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'Liminal_push3':a.liminal_commit}
manifest.update({'runtime':'Python >=3.10 (Push target 3.10.14), Linux x86_64; no native binaries'})
(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(output/'liminal-controller.tar.gz','w:gz') as tar:
    for p in files:tar.add(p,arcname=str(p.relative_to(ROOT)))
    tar.add(output/'manifest.json',arcname='manifest.json')
print(output/'liminal-controller.tar.gz')
