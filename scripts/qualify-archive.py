#!/usr/bin/env python3
"""Exclusive device IA rehearsal; actual ALSA/display, silent synthetic controls."""
import argparse
import array
import fcntl
import json
import math
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event,SR
from archive_worker import ArchiveWorker
from standalone import Instrument
from standalone_render import Background,render,write_ppm
from display_worker import DisplayWorker
from hardware import Midi

def main():
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,default=Path('/data/liminal'));a=p.parse_args();home=a.home
    lock=(home/'app.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    engine=Sampler(home/'engine.so');worker=ArchiveWorker(home);worker.restored=True
    ui=display=midi=None;report={'physical_audio_heard':False,'synthetic_midi_controls':True,'master_zero':True};started=time.monotonic();gaps=[]
    try:
        ui=Instrument(engine,home/'private-assets',home,worker);bg=Background(home/'private-assets',blender=engine.blend)
        engine.command(10,event=Event(gain=0));engine.render(4096);ui.master=0
        midi=Midi();display=DisplayWorker();engine.start();last=time.monotonic();frame_at=0
        def pump(seconds):
            nonlocal last,frame_at
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                now=time.monotonic();gaps.append(now-last);last=now;midi.read();s=ui.tick()
                if not s['alive'] or s['overflow'] or s['peak']>1e-8:raise RuntimeError('Audio/silence failure '+str(s))
                if now-frame_at>.1:display.send(render(ui,s,bg));frame_at=now
                time.sleep(.002)
            return engine.status()
        baseline=pump(1);report['baseline']=baseline
        ui.event(dict(kind='cc',number=85,value=127));ui.event(dict(kind='cc',number=106,value=127));ui.event(dict(kind='cc',number=56,value=127))
        fetch_start=time.monotonic();deadline=fetch_start+240
        while not ui.archive and time.monotonic()<deadline:
            pump(.1)
            if worker.error:raise RuntimeError(worker.error)
        if not ui.archive:raise TimeoutError('No fresh IA window')
        report['download_decode_seconds']=time.monotonic()-fetch_start;report['credit']=ui.archive['credit'];report['after_decode']=engine.status()
        while ui.current['archive_id']!=ui.archive['credit']['sha256'] and time.monotonic()<deadline:pump(.1)
        if ui.current['archive_id']!=ui.archive['credit']['sha256']:raise RuntimeError('Fresh bank did not publish')
        report['publish_seconds']=time.monotonic()-fetch_start;report['published']=engine.status()
        ui.event(dict(kind='cc',number=49,value=127));ui.event(dict(kind='cc',number=24,value=127));ui.event(dict(kind='note',number=38,value=100));ui.event(dict(kind='cc',number=49,value=0))
        assert ui.manual[4] and ui.chop==2
        before=ui.cut(ui.current,2);ui.event(dict(kind='cc',number=76,value=3));ui.event(dict(kind='cc',number=77,value=2));after=ui.cut(ui.current,2)
        assert before!=after
        ui.event(dict(kind='note',number=38,value=100));manual=pump(.05);assert manual['voices']>0
        report['manual']={'before':before,'after':after,'status':manual}
        # Render the exact downloaded PCM through a separate native memory engine.
        # This instance never opens ALSA; actual playback above remains master-zero.
        memory=Sampler(home/'engine.so')
        try:
            slot=memory.install(dict(revision=0,length=640,pcm=[ui.archive['pcm']],events=[]));memory.render(1);memory.command(3,4,1)
            memory.command(7,slot,0,identity=1,event=Event(frame=after[0],channel=4,sample=192+slot*16,gate=after[1],speed=1,gain=.35,attack=128,release=256))
            data=memory.render(min(SR*4,after[1]+512));peak=max(map(abs,data));rms=math.sqrt(sum(v*v for v in data)/len(data));assert peak>1e-5 and rms>1e-6
            report['downloaded_chop_memory_audio']={'peak':peak,'rms':rms,'frames':len(data)//2,'finite':all(math.isfinite(v) for v in data)}
        finally:memory.close()
        # Memory-render/signal measurement deliberately pauses this harness.
        # Exclude that harness-only gap from the MIDI polling distribution.
        last=time.monotonic()
        # A failed subsequent fetch must not replace the active PCM or stop ALSA.
        identity=ui.current['archive_id'];oldfetch=worker.fetcher;worker.fetcher=lambda *_:(_ for _ in ()).throw(OSError('qualification offline'))
        while worker.thread and worker.thread.is_alive():pump(.05)
        worker.request()
        while worker.thread.is_alive():pump(.05)
        assert worker.error and ui.current['archive_id']==identity;report['failure_retention']={'error':worker.error,'archive_id':identity,'status':engine.status()};worker.fetcher=oldfetch
        ui.event(dict(kind='cc',number=29,value=127));stopped=pump(1);assert not stopped['playing'] and stopped['voices']==0 and stopped['peak']==0
        report['stopped']=stopped;report['xruns_delta']=stopped['xruns']-baseline['xruns'];assert report['xruns_delta']==0
        write_ppm(home/'archive-qualified.ppm',render(ui,stopped,bg))
        values=sorted(gaps);report['midi_poll_ms']={'p95':values[int(len(values)*.95)]*1000,'max':max(values)*1000};report['display_frames']=display.frames
        report['rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;report['elapsed']=time.monotonic()-started;report['passed']=True
    finally:
        report['worker_state']=worker.state;report['worker_error']=worker.error;(home/'archive-qualification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
        engine.command(2);worker.close()
        if ui:ui.close()
        engine.close()
        if midi:midi.close()
        if display:display.close()
if __name__=='__main__':main()
