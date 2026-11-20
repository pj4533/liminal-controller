#!/usr/bin/env python3
"""Deterministic integration peer, never imported by the hardware entry point.
Golden envelopes are copied verbatim from Liminal docs/controller/fixtures.
Synthetic state follows ControllerCoordinator.snapshot; it is not native evidence.
"""
import argparse
import copy
import json
from pathlib import Path
import socket
import threading
from protocol import Framer, encode, address
from controller import SLOTS

ROOT=Path(__file__).resolve().parents[1]
GOLDEN=[json.loads(s) for s in (ROOT/'tests/fixtures/messages.ndjson').read_text().splitlines()]
IDS=('lofi.drums','lofi.bass','lofi.lead','lofi.mids','lofi.space','lofi.chops','film.bed','ambient.drone','ambient.pad','ambient.lead','ambient.keys','ambient.drips','ambient.air','ambient.grains','ambient.pluck','ambient.space')

def sample_state(session='test-session',ambient=False):
    channels=[]
    for i,id in enumerate(IDS):
        active=id.startswith('ambient.' if ambient else 'lofi.') or (id=='film.bed' and not ambient)
        kind='drums' if i==0 else 'chops' if i==5 else 'gate' if i==6 else 'return' if i in (4,15) else 'texture' if i==12 else 'melodic'
        ready=active and kind not in ('gate','return') and (ambient or i in (0,5))
        bank=None
        if i in (0,5):
            bank=dict(revision=1,bank_id='synthetic-bank',cue_token='synthetic-cue',plan_revision=1,transport_revision=1,effective_beat=0,pads=[dict(index=j,label='Whole line' if j==63 else 'Synthetic %d'%j,kind='loop' if i==0 else 'cut',ready=True,play_mode='latch' if i==0 else 'one_shot',beats=4) for j in ((0,1,2) if i==0 else (0,1,2,3,63))])
        params=[dict(id=s,label=s.replace('_',' ').title(),value=v,default=v,display='%d%%'%round(v*100),enabled=active and (ambient or i not in (1,2,3))) for s,v in zip(SLOTS,(.5,0,1,.5,0,0,0,.5))]
        channels.append(dict(id=id,label=id.split('.')[1].title(),kind=kind,active=active,mode='auto',pending_mode=None,ready=ready,mix_ready=all(p['enabled'] for p in params),mode_ready=ready,status='Ready' if ready else 'Awaiting native qualification',instrument='Synthetic demonstration',instrument_revision=5,base_midi=26 if i==1 else 38,root_midi=62,octave_offset=-1 if i==1 else 0,pending_window=None,parameters=params,pad_bank=bank))
    return dict(v=1,type='state',session=session,revision=1,transport=dict(state='stopped',ready=True,music_mode='ambient' if ambient else 'lofi',bpm=72,beat=0,take_index=0,transport_revision=1),harmony=dict(root_midi=62,tonic=2,scale_name='Dorian',pitch_classes=[0,2,3,5,7,9,10]),channels=channels,drums=dict(choices=[dict(id='synthetic-%d'%i,label='Generated loop %d'%i,ready=True,bpm=72) for i in range(3)],current_id='synthetic-0',current_label='Generated loop 0',pending=None),capabilities=dict(transport=True,manual_notes=ambient,manual_pads=True,drum_selection=not ambient,film_mix=True,isolated_lofi_wet=False))

class FakeServer:
    def __init__(self,host='127.0.0.1',port=0,ambient=False):
        self.socket=socket.socket();self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);self.socket.bind((address(host),port));self.socket.listen(4);self.socket.settimeout(.1)
        self.port=self.socket.getsockname()[1];self.stop=threading.Event();self.thread=None;self.peer=None;self.generation=0;self.commands=[];self.held={};self.state=sample_state(ambient=ambient);self.pause_reads=False
    def start(self):
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start();return self
    def drop(self):
        if self.peer:
            try:self.peer.shutdown(socket.SHUT_RDWR)
            except OSError:pass
    def close(self):
        self.stop.set();self.drop()
        if self.thread:self.thread.join(2)
        self.socket.close()
    def apply(self,f):
        seq=f['seq'];error=None;action=f['action'];c=next((c for c in self.state['channels'] if c['id']==f.get('channel')),None)
        if f['session']!=self.state['session']:error='stale_session'
        elif action in ('note_off','pad_off'):self.held.pop(f['note_id'],None)
        elif action=='all_notes_off':self.held.clear()
        elif action=='pressure':pass
        elif action=='transport':self.state['transport']['state']=f['state'];self.held.clear()
        elif action=='parameter':
            p=next((p for p in (c or {}).get('parameters',[]) if p['id']==f['parameter']),None)
            if not isinstance(f.get('parameter'),str):error='bad_message'
            elif not p or not p['enabled']:error='unavailable'
            elif not 0<=f['value']<=1:error='out_of_range'
            else:p['value']=f['value'];p['display']='%d%%'%round(f['value']*100)
        elif action=='mode':
            if not c or not c['mode_ready']:error='unavailable'
            else:c['mode']=f['mode']
        elif action in ('note_on','pad_on'):
            if not c or not c['ready']:error='not_ready'
            elif c['mode']!='manual':error='wrong_mode'
            elif self.state['transport']['state']!='playing':error='not_playing'
            elif action=='pad_on' and f['bank_revision']!=c['pad_bank']['revision']:error='stale_bank'
            elif action=='note_on' and f['instrument_revision']!=c['instrument_revision']:error='stale_instrument'
            else:self.held[f['note_id']]=copy.deepcopy(f)
        elif action=='pad_window':
            c['base_midi']=f['base_midi'];c['instrument_revision']+=1
        elif action in ('drum_select','drum_next'):pass
        elif action=='snapshot':pass
        else:error='unavailable'
        self.state['revision']+=1
        return dict(v=1,type='ack',seq=seq,ok=error is None,revision=self.state['revision'],**({'error':error} if error else {}))
    def run(self):
        while not self.stop.is_set():
            try:peer,_=self.socket.accept()
            except socket.timeout:continue
            except OSError:break
            self.peer=peer;peer.settimeout(.1);parser=Framer();self.generation+=1;session='test-session-%d'%self.generation;self.state['session']=session;self.state['revision']=1;welcomed=False
            try:
                while not self.stop.is_set():
                    if self.pause_reads:self.stop.wait(.02);continue
                    try:data=peer.recv(65536)
                    except socket.timeout:continue
                    if not data:break
                    for f in parser.feed(data):
                        if f['type']=='hello':
                            welcome=copy.deepcopy(GOLDEN[1]);welcome['session']=session;peer.sendall(encode(welcome)+encode(self.state));welcomed=True
                        elif not welcomed:raise ValueError('hello first')
                        elif f['type']=='ping':peer.sendall(encode(dict(v=1,type='pong',nonce=f['nonce'])))
                        elif f['type']=='command':
                            self.commands.append(copy.deepcopy(f));peer.sendall(encode(self.apply(f))+encode(self.state))
            except (OSError,ValueError):pass
            finally:self.held.clear();peer.close();self.peer=None

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=20808);p.add_argument('--ambient',action='store_true');a=p.parse_args();s=FakeServer(a.host,a.port,a.ambient).start()
    print('Synthetic Liminal integration server on %s:%s'%(a.host,s.port),flush=True)
    try:
        while True:s.stop.wait(1)
    except KeyboardInterrupt:s.close()
