#!/usr/bin/env python3
"""Whitelist release payload: stdlib sources and packed artwork only, no private state."""
import hashlib
import json
from pathlib import Path
import tarfile
import sys
ROOT=Path(__file__).resolve().parents[1]
files=sorted([p for d in ('src','scripts') for p in (ROOT/d).glob('*.py') if p.name not in ('fake_server.py','demo.py','prepare-art.py','native-acceptance.py','preview.py')]+[ROOT/f for f in ('assets/film-table.bin','LICENSE','LICENSE.push-hack','NOTICE')])
output=ROOT/'.build';output.mkdir(exist_ok=True)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest.update({'runtime':'Python >=3.10 (Push target 3.10.14), Linux x86_64; no native binaries'})
(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(output/'liminal-controller.tar.gz','w:gz') as tar:
    for p in files:tar.add(p,arcname=str(p.relative_to(ROOT)))
    tar.add(output/'manifest.json',arcname='manifest.json')
print(output/'liminal-controller.tar.gz')
