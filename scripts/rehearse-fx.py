#!/usr/bin/env python3
"""Private real-material FX evidence and all native-size channel/page renders.

No network, hardware, source publication or asset mutation. Optional --baseline
accepts a separately built previous ABI1 engine for measured default differences.
"""
import argparse
import array
import json
import math
from pathlib import Path
import sys
import tempfile
import wave
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event,SR
from composition import Instruments
from standalone import Instrument,NAMES
from standalone_render import Background,render,write_ppm
from channel_fx import parameters,pages,defaults
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
def stats(pcm):return dict(rms=math.sqrt(sum(x*x for x in pcm)/len(pcm)),peak=max(map(abs,pcm)),finite=all(math.isfinite(x) and abs(x)<1 for x in pcm))
metrics={}
with tempfile.TemporaryDirectory() as home:
    s=Sampler(ROOT/'.build/engine.so');ui=Instrument(s,a.assets,home)
    try:
        bank=ui.current;background=Background(a.assets)
        # Source title/status intentionally long: renderer must bound all text.
        ui.error='IA ERROR / RETAINING CURRENT SOURCE / '+('LONG STATUS '*20)
        for ch,name in enumerate(NAMES):
            ui.selected=ch;ui.manual[ch]=True;ui.muted[ch]=ch%2==1
            for page in range(len(pages(ch))):
                ui.fx_pages[ch]=page
                for high in (False,True):
                    ui.effects[ch]=[descriptor.high if high else descriptor.low for descriptor in parameters(ch)];ui.level[ch]=ui.effects[ch][0]
                    write_ppm(a.out/('%s-%s-%s.ppm'%(name.lower(),pages(ch)[page].lower(),'max' if high else 'min')),render(ui,s.status(),background))
        ui.effects=[defaults(ch) for ch in range(6)];ui.level=[.65]*6;ui.error='';ui.muted=[False]*6;ui.manual=[False]*6
        for overlay in ('help','settings','mix'):
            setattr(ui,overlay,True);write_ppm(a.out/(overlay+'.ppm'),render(ui,s.status(),background));setattr(ui,overlay,False)
        # Render native auto sources at unchanged balances, isolating buses.
        for ch,name in enumerate(NAMES):
            captures=[]
            for label,enginepath in ((('old-default',a.baseline),) if a.baseline else ())+(('new-default',ROOT/'.build/engine.so'),('expressive',ROOT/'.build/engine.so')):
                engine=Sampler(enginepath)
                try:
                    instruments=Instruments(a.assets/'instruments',engine);engine.install(bank)
                    for other in range(6):engine.command(5,other,int(other!=ch))
                    if label=='old-default':
                        for i,value in enumerate((.55,0 if ch==0 else .12,0 if ch==0 else .1,0)):engine.command(11+i,ch,event=Event(gain=value))
                    else:
                        values=defaults(ch)
                        if label=='expressive':
                            edits={3:7,4:.25 if ch==0 else 3,5:.3,8:.23,10:.42,12:.20,13:1.8,16:0 if ch==1 else .22,19:.28,20:.18,23:.25}
                            for param,value in edits.items():values[param]=value
                        for descriptor in parameters(ch):engine.command(16,ch,descriptor.id,event=Event(gain=values[descriptor.id]))
                    engine.render(6000);engine.command(1);pcm=list(engine.render(SR*12));metrics[name+' '+label]=stats(pcm)
                    if metrics[name+' '+label]['rms']<=1e-6:raise AssertionError('inaudible comparison '+name+' '+label)
                    captures.append((label,pcm))
                finally:engine.close()
            if a.baseline:
                old,new=captures[0][1],captures[1][1]
                metrics[name+' default delta']=dict(rms_db=20*math.log10((stats(new)['rms']+1e-20)/(stats(old)['rms']+1e-20)),difference_rms=math.sqrt(sum((x-y)**2 for x,y in zip(old,new))/len(old)))
            # Three two-second excerpts in documented order; no normalization.
            excerpt=array.array('h')
            start=max(SR, min(e['frame'] for e in bank['events'] if e['channel']==ch)+SR//5)
            for label,pcm in captures:excerpt.extend(round(max(-1,min(1,x))*32767) for x in pcm[start*2:(start+SR*2)*2])
            with wave.open(str(a.out/(name.lower()+'-comparison.wav')),'wb') as w:w.setparams((2,2,SR,0,'NONE','uncompressed'));w.writeframes(excerpt.tobytes())
        metrics['excerpt_order']='old default (if supplied), new default, expressive; 2 seconds each from first channel onset +200ms (minimum1s), unchanged master/levels'
    finally:ui.close();s.close()
(a.out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n');print(json.dumps(metrics))
