#!/usr/bin/env python3
"""Exclusive device rehearsal, always master zero; synthetic control events.
Run only after gracefully stopping the app. Never claims physical listening.
"""
import argparse
import fcntl
import json
from pathlib import Path
import resource
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event
from standalone import Instrument
from standalone_render import Background,render,write_ppm
from hardware import Midi
from display_worker import DisplayWorker

def main():
    sys.setswitchinterval(.001)
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,default=Path('/data/liminal'));a=p.parse_args()
    lock=(a.home/'app.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    engine=Sampler(a.home/'engine.so');ui=None;display=midi=None;report={};cpu0=resource.getrusage(resource.RUSAGE_SELF)
    try:
        ui=Instrument(engine,a.home/'private-assets',a.home);background=Background(a.home/'private-assets',blender=engine.blend)
        engine.command(10,event=Event(gain=0));engine.render(4096);ui.master=0
        midi=Midi();display=DisplayWorker();engine.start();poll_gaps=[];last_poll=time.monotonic()
        def pump(seconds):
            nonlocal last_poll
            end=time.monotonic()+seconds;last=0;last_poll=time.monotonic()
            while time.monotonic()<end:
                # Consume real input, but do not change unattended qualification.
                now=time.monotonic();poll_gaps.append(now-last_poll);last_poll=now
                midi.read();status=ui.tick();now=time.monotonic()
                if not status['alive'] or status['xruns'] or status['overflow'] or status['peak']>1e-8:raise RuntimeError('ALSA/silent qualification failed '+str(status))
                if now-last>.1:display.send(render(ui,status,background));last=now
                time.sleep(.002)
            return engine.status()
        baseline=pump(1);manual=[]
        for ch in range(6):
            ui.selected=ch;ui.toggle_mode(ch);begin=time.monotonic();ui.event(dict(kind='note',number=36,value=96))
            while not engine.status()['voices'] and time.monotonic()-begin<.03:time.sleep(.0005)
            onset_ms=(time.monotonic()-begin)*1000;s=pump(.05)
            if s['voices']<1:raise RuntimeError('Manual onset missing '+str(ch))
            manual.append(dict(channel=ch,voices=s['voices'],onset_to_voice_ms=onset_ms))
            ui.event(dict(kind='note_off',number=36,value=0));ui.send(9);pump(.1);ui.toggle_mode(ch)
        ui.event(dict(kind='cc',number=85,value=127));pump(.05)
        ui.event(dict(kind='cc',number=29,value=127));pump(.005)
        ui.event(dict(kind='cc',number=85,value=127));pump(.1)
        bank=engine.status()['bank'];duration=ui.current['length']/44100+1
        started=time.monotonic();pump(duration);final=engine.status()
        if final['bank']==bank:raise RuntimeError('No real64beat bank transition')
        blend=[];native=[];control=[]
        for i in range(50):
            background.started=background.clock()-85
            begin=time.monotonic();background.frame();middle=time.monotonic();ui.event(dict(kind='cc',number=71,value=1));end=time.monotonic()
            blend.append(end-begin);native.append(middle-begin);control.append(end-middle)
        ui.event(dict(kind='cc',number=29,value=127));stopped=pump(.2)
        if stopped['voices'] or stopped['playing']:raise RuntimeError('Stop did not hush')
        write_ppm(a.home/'qualified-display.ppm',render(ui,stopped,background))
        cpu=resource.getrusage(resource.RUSAGE_SELF)
        def timings(values):
            values=sorted(values);return dict(p50=values[len(values)//2]*1000,p95=values[min(len(values)-1,int(len(values)*.95))]*1000,max=values[-1]*1000)
        report=dict(baseline=baseline,final=final,stopped=stopped,manual=manual,display_frames=display.frames,
                    boundary_seconds=time.monotonic()-started,fade_dispatch_max_ms=max(blend)*1000,
                    fade_native_max_ms=max(native)*1000,control_dispatch_max_ms=max(control)*1000,
                    midi_poll_gap_p95_ms=sorted(poll_gaps)[int(len(poll_gaps)*.95)]*1000,midi_poll_gap_max_ms=max(poll_gaps)*1000,
                    fade_native_ms=timings(native),control_dispatch_ms=timings(control),midi_poll_gap_ms=timings(poll_gaps),
                    usb_transfer_ms=timings(list(display.transfer_seconds)),
                    rss_kib=cpu.ru_maxrss,user_cpu_seconds=cpu.ru_utime-cpu0.ru_utime,system_cpu_seconds=cpu.ru_stime-cpu0.ru_stime,
                    physical_audio_heard=False,synthetic_midi_controls=True,master_zero=True)
        (a.home/'qualification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
        if max(blend)>.01:raise RuntimeError('Fade/control dispatch exceeded10ms; measurements retained')
    finally:
        engine.command(2)
        if ui:ui.close()
        engine.close()
        if midi:midi.close()
        if display:display.close()
if __name__=='__main__':main()
