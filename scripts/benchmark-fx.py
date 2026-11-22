#!/usr/bin/env python3
"""Host memory-render stress; device ALSA deadlines must be qualified separately."""
import argparse
import array
import ctypes as C
import json
import math
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event,SR
from channel_fx import parameters
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--blocks',type=int,default=2000);a=p.parse_args()
s=Sampler(ROOT/'.build/engine.so');out=(C.c_float*512)();results={}
try:
    pcm=array.array('f',(v for i in range(SR*8) for v in (math.sin(i*.13)*.3,math.sin(i*.17)*.3)))
    s.sample(0,pcm);slot=s.install(dict(revision=0,length=SR*64,pcm=[],events=[]));s.render(1)
    for ch in range(6):
        s.command(3,ch,1)
        for descriptor in parameters(ch):s.command(16,ch,descriptor.id,event=Event(gain=descriptor.high))
    for i in range(64):
        ch=i%6;s.command(7,slot,identity=i+1,event=Event(channel=ch,sample=0,gate=SR*120,speed=.01,gain=.2,attack=32,release=256,frequency=110 if ch==1 else 0))
    for _ in range(100):s.lib.lm_render(s.ptr,out,256)
    results['warmup_voices']=s.status()['voices']
    if results['warmup_voices']!=64:raise AssertionError('64-voice load required')
    for name,rapid in (('all_fx_64_voices',False),('all_fx_64_voices_rapid_parameters',True)):
        timings=[]
        for block in range(a.blocks):
            if rapid:
                for ch in range(6):
                    # Full knob surface traffic, including delay-time changes.
                    for descriptor in parameters(ch):
                        value=descriptor.high if block%2 else descriptor.low
                        s.command(16,ch,descriptor.id,event=Event(gain=value))
            start=time.perf_counter_ns();s.lib.lm_render(s.ptr,out,256);timings.append((time.perf_counter_ns()-start)/1e6)
        timings.sort();results[name]=dict(blocks=len(timings),p50_ms=statistics.median(timings),p95_ms=timings[int(len(timings)*.95)],p99_ms=timings[int(len(timings)*.99)],maximum_ms=max(timings),over_deadline=sum(t>256/SR*1000 for t in timings))
    s.command(2);start=time.perf_counter_ns();s.lib.lm_render(s.ptr,out,256);results['stop_clear_ms']=(time.perf_counter_ns()-start)/1e6
    s.render(1323);results['stopped_peak']=max(map(abs,s.render(4096)));results['status']=s.status();results['deadline_ms']=256/SR*1000;results['machine']='host memory-render; no ALSA/USB/device scheduling claim'
finally:s.close()
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
