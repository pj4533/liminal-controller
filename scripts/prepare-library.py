#!/usr/bin/env python3
"""Explicit private import. No source archive changes; commercial data stays out of git."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import wave
import zipfile

def inspect(data,name,source):
    normal=re.sub(r'^(?:A\.J\._HALL__?|@AJHALL89_)','AJ_HALL_',Path(name).stem)
    match=re.search(r'(?i)(\d{2,3}(?:\.\d+)?)\s*[-_ ]?\s*bpm\b',normal) or re.search(r'(?:^|[\s_-])(\d{2,3}(?:\.\d+)?)(?:[\s_)]*)$',normal)
    if not match:return None
    bpm=float(match[1])
    with wave.open(io.BytesIO(data)) as w:
        frames=w.getnframes();rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth()
    if not 45<=bpm<=120 or abs(frames-64*rate*60/bpm)>2:return None
    if rate!=44100 or channels!=2 or width!=2:raise ValueError('unexpected source format '+name)
    digest=hashlib.sha256(data).hexdigest()
    return dict(source=source,original_name=name,name=normal,bpm=bpm,frames=frames,rate=rate,channels=channels,sha256=digest,file=digest+'.wav')
def main():
    p=argparse.ArgumentParser();p.add_argument('--loose',type=Path,required=True);p.add_argument('--zip',type=Path,required=True);p.add_argument('--instruments',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('refusing existing destination')
    (a.out/'drums').mkdir(parents=True);entries=[];excluded=[];seen=set()
    def add(data,name,source):
        entry=inspect(data,name,source)
        if not entry:excluded.append(dict(source=source,name=name));return
        if entry['sha256'] in seen:raise ValueError('duplicate eligible source')
        seen.add(entry['sha256']);entries.append(entry);(a.out/'drums'/entry['file']).write_bytes(data)
    for path in sorted(a.loose.glob('*.wav')):add(path.read_bytes(),path.name,str(path))
    with zipfile.ZipFile(a.zip) as z:
        for name in sorted(z.namelist()):
            if 'FINAL BREAKS/' in name and name.lower().endswith('.wav') and not name.startswith('__MACOSX/'):add(z.read(name),Path(name).name,str(a.zip)+'!'+name)
    if len(entries)!=100:raise ValueError('expected 100 eligible, got '+str(len(entries)))
    (a.out/'drums.json').write_text(json.dumps(entries,indent=2));(a.out/'excluded.json').write_text(json.dumps(excluded,indent=2))
    shutil.copytree(a.instruments,a.out/'instruments');print(json.dumps(dict(eligible=len(entries),excluded=len(excluded),bytes=sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file()))))
if __name__=='__main__':main()
