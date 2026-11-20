#!/usr/bin/env python3
"""One MIDI reader/display owner. No audio and no network listener."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import time
from controller import Controller, Settings
from protocol import Client
from render import render, write_ppm

def main():
    p=argparse.ArgumentParser();p.add_argument('--start-fd',type=int);p.add_argument('--home',default=str(Path.home()/'.liminal-controller'));p.add_argument('--simulate',action='store_true');p.add_argument('--host');p.add_argument('--port',type=int);p.add_argument('--seconds',type=float);p.add_argument('--screenshot');args=p.parse_args()
    if args.start_fd is not None:
        if os.read(args.start_fd,1)!=b'1':return 1
        os.close(args.start_fd)
    home=Path(args.home);home.mkdir(parents=True,exist_ok=True)
    lock=(home/'app.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    settings=Settings(home/'settings.json');client=Client(args.host or settings.host,args.port or settings.port);ui=Controller(client,settings)
    alive=True
    def stop(*_):
        nonlocal alive
        alive=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    display=midi=None;ready=home/'ready.json';started=time.monotonic();last_frame=0;leds={};buttons={};frame=None
    try:
        if not args.simulate:
            from hardware import Display,Midi
            midi=Midi();display=Display()
        (home/'app.pid').write_text(str(os.getpid()))
        while alive and (args.seconds is None or time.monotonic()-started<args.seconds):
            client.tick();ui.sync()
            if ui.recovery_request:
                (home/'recovery-request').write_text(ui.recovery_request+'\n');break
            if midi:
                for event in midi.read():ui.event(event)
            now=time.monotonic()
            if now-last_frame>=.1:
                frame=render(ui)
                if display:display.send(frame)
                if midi:
                    for n,v in ui.leds().items():
                        if leds.get(n)!=v and midi.note(n,v):leds[n]=v
                    controls={85:127 if client.connected and (client.state or {}).get('transport',{}).get('state')=='playing' else 20,29:20,49:127 if ui.shift else 20,110:20,112:20,30:20,56:20,118:20,62:20,63:20}
                    for i in range(8):
                        index=ui.page*8+i;ch=ui.channels[index] if index<len(ui.channels) else {}
                        controls[102+i]=127 if index==ui.selected and ch else (30 if ch.get('active') else 0)
                        controls[20+i]=90 if ch.get('mode')=='manual' else (20 if ch.get('active') else 0)
                    for n,v in controls.items():
                        if buttons.get(n)!=v and midi.cc(n,v):buttons[n]=v
                status=dict(pid=os.getpid(),ready=True,connected=client.connected,generation=client.generation,transport=(client.state or {}).get('transport',{}),display_frames=display.frames if display else 0,error=client.error,monotonic=now)
                tmp=ready.with_suffix('.tmp');tmp.write_text(json.dumps(status));os.replace(tmp,ready);last_frame=now
            time.sleep(.002)
        if args.screenshot and frame:write_ppm(args.screenshot,frame)
    finally:
        if client.connected:
            client.command('all_notes_off')
            for _ in range(3):client.tick();time.sleep(.005)
        client.disconnect('Shutdown')
        if midi:
            for n in range(36,100):midi.note(n,0)
            midi.close()
        if display:display.close()
        ready.unlink(missing_ok=True);(home/'app.pid').unlink(missing_ok=True)
    return 0
if __name__=='__main__':sys.exit(main())
