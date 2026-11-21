#!/usr/bin/env python3
"""Install only after explicit graceful release. No device start/reboot/deletion."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
def install(home,init):
    home=Path(home).resolve();init=Path(init)
    if (home/'recovery').exists():raise RuntimeError('Existing recovery; refuse overwrite')
    if b'liminal-controller dispatcher' not in init.read_bytes():raise RuntimeError('Expected previously installed controller dispatcher; inspect installation')
    spec=importlib.util.spec_from_file_location('owner',home/'scripts/standalone-supervisor.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    if owner.competitors():raise RuntimeError('Hardware owner exists; stop gracefully first')
    if str(home)!='/data/liminal':raise ValueError('Expected isolated /data/liminal')
    recovery=home/'recovery';recovery.mkdir();previous=recovery/'previous-init';shutil.copy2(init,previous)
    (recovery/'init-hashes.json').write_text(json.dumps({'previous-init':hashlib.sha256(previous.read_bytes()).hexdigest()}))
    text='#!/bin/sh\n# Liminal standalone reversible dispatcher\nexec /usr/bin/python3 /data/liminal/scripts/standalone-boot.py "$@"\n'
    tmp=init.with_name(init.name+'.liminal-standalone-new');tmp.write_text(text);tmp.chmod(init.stat().st_mode);os.replace(tmp,init);(home/'boot-target').write_text('liminal\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',default='/data/liminal');p.add_argument('--init',default='/etc/init.d/push3');a=p.parse_args();install(a.home,a.init)
