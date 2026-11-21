#!/usr/bin/env python3
"""Liminal standalone: single MIDI/display owner and native ALSA audio engine."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import time
from sampler import Sampler
from standalone import Instrument
from image_worker import ImageWorker
from standalone_render import Background,render
from standalone_render import write_ppm

def main():
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,default=Path('/data/liminal'));p.add_argument('--assets',type=Path);p.add_argument('--engine',type=Path);p.add_argument('--start-fd',type=int);p.add_argument('--simulate',action='store_true');p.add_argument('--seconds',type=float);p.add_argument('--screenshot',type=Path);a=p.parse_args()
    if a.start_fd is not None:
        if os.read(a.start_fd,1)!=b'1':return 1
        os.close(a.start_fd)
    a.home.mkdir(parents=True,exist_ok=True);lock=(a.home/'app.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    alive=True
    def stop(*_):
        nonlocal alive
        alive=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    engine=Sampler(a.engine or a.home/'engine.so');ui=None;media=None;display=midi=None;ready=a.home/'ready.json';frame=None;last=0;leds={};controls={};started=time.monotonic()
    try:
        ui=Instrument(engine,a.assets or a.home/'private-assets',a.home);background=Background(a.assets or a.home/'private-assets',blender=engine.blend)
        started=time.monotonic();last_media=started
        if not a.simulate:
            media=ImageWorker(a.home)
            from hardware import Display,Midi
            midi=Midi();display=Display();engine.start()
        while alive and (a.seconds is None or time.monotonic()-started<a.seconds):
            if midi:
                for event in midi.read():ui.event(event)
            if ui.recovery_request:
                (a.home/'recovery-request').write_text(ui.recovery_request+'\n');break
            if a.simulate:engine.render(256)
            status=ui.tick()
            if not a.simulate and not status['alive']:raise RuntimeError('Audio thread stopped')
            now=time.monotonic()
            if media:
                result=media.poll()
                if result:background.update(*result)
                if now-last_media>=90:media.request();last_media=now
            if now-last>=.1:
                frame=render(ui,status,background)
                if display:display.send(frame)
                if midi:
                    for n,v in ui.leds().items():
                        if leds.get(n)!=v and midi.note(n,v):leds[n]=v
                    buttons={85:127 if status['playing'] else 20,29:20,49:127 if ui.shift else 20,110:20,112:40 if ui.mix else 20,56:20,118:20,62:20,63:20,30:20,81:20}
                    for ch in range(6):buttons[102+ch]=127 if ch==ui.selected else 30;buttons[20+ch]=0 if ui.muted[ch] else (90 if ui.manual[ch] else 20)
                    for n,v in buttons.items():
                        if controls.get(n)!=v and midi.cc(n,v):controls[n]=v
                status.update(pid=os.getpid(),ready=True,standalone=True,display_frames=display.frames if display else 0,next_ready=ui.next_slot is not None,preparing=ui.pending is not None,error=ui.error,image_worker_error=media.error if media else '',monotonic=now,revision=ui.current['revision'],drum=ui.current['drum'])
                tmp=ready.with_suffix('.tmp');tmp.write_text(json.dumps(status));os.replace(tmp,ready);last=now
            time.sleep(.002)
        if a.screenshot and frame:write_ppm(a.screenshot,frame)
    finally:
        engine.command(2)
        if media:media.close()
        if ui:ui.close()
        engine.close()
        if midi:
            for n in range(36,100):midi.note(n,0)
            midi.close()
        if display:display.close()
        ready.unlink(missing_ok=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
