#!/usr/bin/env python3
"""Explicit reversible installer. Never starts/stops/reboots hardware or copies vendor files publicly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

def install(home,init,stock):
    home=Path(home).resolve();init=Path(init);stock=Path(stock);recovery=home/'recovery';recovery.mkdir(parents=True,exist_ok=True)
    previous=recovery/'previous-init';backup=recovery/'stock-init'
    if previous.exists() or backup.exists():raise RuntimeError('Recovery already exists; inspect rather than overwrite')
    if not init.is_file() or not stock.is_file():raise ValueError('Both verified init files required')
    if b'liminal-controller dispatcher' in init.read_bytes():raise ValueError('Already installed')
    shutil.copy2(init,previous);shutil.copy2(stock,backup)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (previous,backup)}
    (recovery/'init-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # No embedded vendor code. Quoted paths support spaces; prohibit shell syntax.
    if any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_-.' for ch in str(home)):raise ValueError('Unsafe installation path')
    text='#!/bin/sh\n# liminal-controller dispatcher\nexport LIMINAL_HOME='+str(home)+'\nexec /usr/bin/python3 '+str(home)+'/scripts/dispatch.py "$@"\n'
    temp=init.with_name(init.name+'.liminal-new');temp.write_text(text);temp.chmod(init.stat().st_mode);os.replace(temp,init)
    (home/'boot-target').write_text('stillwater\n')
    return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',default='/data/liminal-controller');p.add_argument('--init',default='/etc/init.d/push3');p.add_argument('--stock-init',required=True);a=p.parse_args();print(json.dumps(install(a.home,a.init,a.stock_init),indent=2))
