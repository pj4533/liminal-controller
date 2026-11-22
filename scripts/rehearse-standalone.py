#!/usr/bin/env python3
"""Actual private-library/native-PCM acceptance. Never opens hardware/network."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import wave
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from channel_fx import parameters,page_parameters
from sampler import Sampler,Event,SR
from standalone import Instrument
from composition import prepare
from standalone_render import Background,render,write_ppm
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
checks=[];metrics={}
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
catalog=json.loads((a.assets/'drums.json').read_text());check('100 eligible unique source hashes',len(catalog)==100 and len({e['sha256'] for e in catalog})==100)
for e in catalog:
    path=a.assets/'drums'/e['file'];check('drum hash '+e['sha256'],hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256'])
    with wave.open(str(path)) as w:check('64-beat source grid '+e['sha256'],abs(w.getnframes()-64*w.getframerate()*60/e['bpm'])<=2 and w.getnchannels()==2 and w.getsampwidth()==2)
check('all 143 instrument WAVs present',len(list((a.assets/'instruments').glob('*.wav')))==143)
with tempfile.TemporaryDirectory() as home:
    engine=Sampler(ROOT/'.build/engine.so');ui=Instrument(engine,a.assets,home)
    try:
        current=ui.current;check('boot stopped silent',not engine.status()['playing'] and max(map(abs,engine.render(512)))==0)
        check('64 beat working length',current['length']==round(64*44100*60/69))
        check('all six channels scheduled',set(e['channel'] for e in current['events'])==set(range(6)))
        check('programme stable over all four phrases',len({p[0] for p in current['programs']})==1)
        repeat=prepare(ui.instruments,a.assets,ui.catalog,0,current['drum'],line_index=current['line_index'])
        check('deterministic source-derived score',repeat['events']==current['events'])
        programmes=[]
        for revision in range(4):
            prepared=prepare(ui.instruments,a.assets,ui.catalog,revision,current['drum'],line_index=revision)
            programmes.append(prepared['programs'][0]);check('programme stable 64 beats revision '+str(revision),len(set(p[0] for p in prepared['programs']))==1)
        check('piano returns after pluck/guitar takes',programmes[0]==programmes[3] and programmes[0]!=programmes[1] and programmes[1]!=programmes[2])
        for ch in range(6):
            for other in range(6):ui.event(dict(kind='cc',number=102+other,value=127));ui.send(5,other,int(other!=ch))
            ui.send(2);engine.render(4096);ui.send(1)
            pcm=engine.render(SR*12)
            rms=math.sqrt(sum(x*x for x in pcm)/len(pcm));metrics['auto_rms_'+str(ch)]=rms;check('actual PCM auto channel '+str(ch),rms>1e-6)
        ui.send(2);engine.render(4096)
        for other in range(6):ui.send(5,other,0)
        for ch in range(6):
            ui.selected=ch
            if not ui.manual[ch]:ui.toggle_mode(ch)
            ui.event(dict(kind='note',number=36,value=96));pcm=engine.render(4096);check('manual PCM channel '+str(ch),max(map(abs,pcm))>1e-5)
            ui.event(dict(kind='note_off',number=36,value=0));ui.send(9);engine.render(SR)
        check('all mapped notes release after selection changes',not ui.held)
        ui.event(dict(kind='cc',number=49,value=127));ui.event(dict(kind='cc',number=20,value=127));check('shift lower toggles mode',not ui.manual[0]);ui.event(dict(kind='cc',number=49,value=0))
        ui.event(dict(kind='cc',number=79,value=1));check('master mapping',abs(ui.master-.46)<1e-6)
        ui.event(dict(kind='cc',number=112,value=127));ui.event(dict(kind='cc',number=72,value=1));check('mix channel mapping',abs(ui.level[1]-.66)<1e-6)
        ui.event(dict(kind='cc',number=110,value=127));ui.selected=2
        for page in range(3):
            ui.fx_pages[2]=page
            for knob,p in enumerate(page_parameters(2,page)):
                before=ui.effects[2][p.id];ui.event(dict(kind='cc',number=71+knob,value=127))
                check('FX physical encoder %d/%d'%(page,knob),abs(ui.effects[2][p.id]-p.edit(before,-1))<1e-5)
        ui.fx_pages[2]=0
        deadline=time.monotonic()+30
        while ui.pending and time.monotonic()<deadline:ui.tick();engine.render(1);time.sleep(.01)
        check('worker prepared next bank',ui.next_slot is not None)
        background=Background(a.assets);check('three real API image caches',len(background.images)==3)
        write_ppm(a.out/'stopped.ppm',render(ui,engine.status(),background))
        ui.send(1);pcm=array.array('f');remaining=current['length']+512
        started=time.monotonic()
        while remaining:
            n=min(4096,remaining);block=engine.render(n);pcm.extend(block);remaining-=n;ui.tick()
        metrics['render_wall_seconds']=time.monotonic()-started
        check('real 64 beat bank transition',engine.status()['bank']!=ui.last_bank or ui.current['revision']>=1)
        check('whole render finite limited',all(math.isfinite(x) and abs(x)<1 for x in pcm))
        write_ppm(a.out/'playing.ppm',render(ui,engine.status(),background))
        shorts=array.array('h',(round(max(-1,min(1,x))*32767) for x in pcm))
        with wave.open(str(a.out/'native-render.wav'),'wb') as w:w.setparams((2,2,SR,0,'NONE','not compressed'));w.writeframes(shorts.tobytes())
        ui.send(2);engine.render(SR);check('stop sustained hush',max(map(abs,engine.render(4096)))<1e-6)
        metrics['status']=engine.status()
    finally:ui.close();engine.close()
(a.out/'acceptance.json').write_text(json.dumps(dict(passed=len(checks),failed=0,checks=checks,metrics=metrics,architecture='host memory render only, no hardware/listening claim'),indent=2));print(json.dumps(dict(passed=len(checks),failed=0,metrics=metrics)))
