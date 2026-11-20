"""Remote-authoritative hardware interaction; onset identity survives navigation."""
import json
import os
from pathlib import Path
from protocol import address

SLOTS=('gain','low_cut','high_cut','tone','drive','echo','room','pan')

def pitches(base, intervals):
    notes=[base+12*((x+3*y)//len(intervals))+intervals[(x+3*y)%len(intervals)] for y in range(8) for x in range(8)]
    if min(notes)<0 or max(notes)>127:raise ValueError('Complete window outside MIDI range')
    return notes

class Settings:
    def __init__(self,path):
        self.path=Path(path); self.host='127.0.0.1';self.port=20808
        if self.path.exists():
            d=json.loads(self.path.read_text());self.host=address(d['host']);self.port=int(d['port'])
            if not 1<=self.port<=65535:raise ValueError('port')
    def save(self):
        address(self.host)
        if not 1<=self.port<=65535:raise ValueError('port')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(dict(host=self.host,port=self.port))+'\n');os.replace(temp,self.path)

class Controller:
    def __init__(self,client,settings=None):
        self.client=client;self.settings=settings;self.selected=0;self.page=0;self.view='device';self.shift=False
        self.held={};self.serial=0;self.generation=client.generation;self.message='';self.ip_cursor=0
        self.recovery_request=None;self.recovery_choice=None;self.targets={}
        self.draft_host=settings.host if settings else '127.0.0.1';self.draft_port=settings.port if settings else 20808
    @property
    def channels(self):
        ch=(self.client.state or {}).get('channels',[])
        return sorted(ch,key=lambda c:not c.get('active',False))
    @property
    def channel(self):
        ch=self.channels
        return ch[min(self.selected,len(ch)-1)] if ch else None
    def sync(self):
        if self.generation!=self.client.generation or not self.client.connected:
            self.held.clear();self.targets.clear();self.generation=self.client.generation
    def send(self,action,**fields):return self.client.command(action,**fields)
    def select(self,i):
        if 0<=i<len(self.channels):self.selected=i;self.page=i//8
    def parameter(self,c,key,delta=None,value=None):
        p=next((p for p in c.get('parameters',[]) if p['id']==key),None)
        if not c.get('active') or not p or not p.get('enabled',True):self.message='Control unavailable';return
        target_key=(c['id'],key)
        import time
        target,when=self.targets.get(target_key,(p['value'],0))
        if time.monotonic()-when>.3:target=p['value']
        v=max(0,min(1,target+delta if delta is not None else value))
        self.targets[target_key]=(v,time.monotonic())
        self.send('parameter',channel=c['id'],parameter=key,value=v)
    def event(self,e):
        self.sync();kind,n,v=e['kind'],e['number'],e['value'];c=self.channel
        if kind=='note_off' and n in self.held:
            note,action=self.held.pop(n);self.send(action,note_id=note);return
        if kind in ('poly_pressure','pressure'):
            for pad,(note,_) in list(self.held.items()):
                if kind=='pressure' or pad==n:self.send('pressure',note_id=note,value=v/127)
            return
        if kind=='note' and 36<=n<=99 and c:
            if c.get('kind')=='drums' and c.get('mode')=='auto' and self.client.connected:
                choices=(self.client.state.get('drums') or {}).get('choices',[])
                if n-36<len(choices):self.send('drum_select',choice_id=choices[n-36]['id'])
                return
            if not self.client.connected or c.get('mode')!='manual' or not c.get('ready') or not c.get('active'):self.message='Manual assets not ready';return
            if n in self.held:return
            self.serial+=1;note='%d-%d'%(self.client.generation,self.serial);bank=c.get('pad_bank')
            if bank:
                p=next((p for p in bank['pads'] if p['index']==n-36 and p.get('ready')),None)
                if not p:return
                ok=self.send('pad_on',channel=c['id'],note_id=note,pad=n-36,velocity=max(1,v),bank_revision=bank['revision']);off='pad_off'
            elif c.get('kind') in ('melodic','texture'):
                try:midi=pitches(c['base_midi'],self.client.state['harmony']['pitch_classes'])[n-36]
                except (KeyError,ValueError):return
                ok=self.send('note_on',channel=c['id'],note_id=note,midi=midi,velocity=max(1,v),instrument_revision=c['instrument_revision']);off='note_off'
            else:return
            if ok:self.held[n]=(note,off)
            return
        if kind!='cc':return
        if n==49:self.shift=bool(v);return
        if self.view=='settings':
            if n in (20,21) and v:
                self.recovery_choice='stillwater' if n==20 else 'stock';self.message='APPLY TO RETURN TO '+self.recovery_choice.upper()
            elif n in (71,72,73,74,75) and v:
                delta=v if v<64 else v-128
                if n==75:self.draft_port=max(1,min(65535,self.draft_port+delta))
                else:
                    parts=list(map(int,self.draft_host.split('.')));parts[n-71]=max(0,min(255,parts[n-71]+delta));self.draft_host='.'.join(map(str,parts))
            elif n==27 and v and self.recovery_choice:
                self.recovery_request=self.recovery_choice
            elif n==27 and v and self.settings:
                try:
                    address(self.draft_host);self.settings.host=self.draft_host;self.settings.port=self.draft_port;self.settings.save()
                    self.client.disconnect('Endpoint changed');self.client.host=self.draft_host;self.client.port=self.draft_port;self.view='device'
                except ValueError:self.message='Private IPv4 required'
            elif n==26 and v:self.view='device';self.recovery_choice=None
            return
        if 71<=n<=78 and v and c:
            delta=(v if v<64 else v-128)*.005
            if self.view=='mix':
                i=self.page*8+n-71
                if i<len(self.channels):self.parameter(self.channels[i],'gain',delta)
            else:self.parameter(c,SLOTS[n-71],delta)
            return
        if n==79 and v:
            master=(self.client.state or {}).get('master')
            if master and master.get('enabled'):self.send('master',value=max(0,min(1,master['value']+(v if v<64 else v-128)*.005)))
            else:self.message='Master unavailable'
            return
        if not v:return
        if 102<=n<=109:self.select(self.page*8+n-102)
        elif 20<=n<=27:
            i=self.page*8+n-20
            if i<len(self.channels):
                ch=self.channels[i]
                if self.shift:
                    if ch.get('mode_ready',False):self.send('mode',channel=ch['id'],mode='manual' if ch['mode']=='auto' else 'auto')
                    else:self.message='Manual mode unavailable'
                else:
                    p=next((p for p in ch.get('parameters',[]) if p['id']=='gain'),None)
                    if p:self.parameter(ch,'gain',value=0 if p['value']>0 else p.get('default',.5))
        elif n==85:self.send('transport',state='playing')
        elif n==29:self.send('transport',state='stopped')
        elif n==112:self.view='mix'
        elif n in (110,50):self.view='device'
        elif n==30:self.view='settings'
        elif n in (62,63):
            direction=1 if n==63 else -1
            if self.shift:self.select(max(0,min(len(self.channels)-1,self.selected+8*direction)))
            elif c and c.get('kind') in ('melodic','texture'):
                base=c['base_midi']+12*direction
                try:pitches(base,self.client.state['harmony']['pitch_classes']);self.send('pad_window',channel=c['id'],base_midi=base)
                except ValueError:self.message='Octave limit'
        elif n==70:self.select(max(0,min(len(self.channels)-1,self.selected+(1 if v<64 else -1))))
        elif n==56:self.send('drum_next')
        elif n==118:self.send('all_notes_off')
    def leds(self):
        c=self.channel;out={}
        for i in range(64):
            value=0
            if self.client.connected and c and c.get('active'):
                bank=c.get('pad_bank')
                if bank:
                    pad=next((p for p in bank['pads'] if p['index']==i and p.get('ready')),None)
                    value=(9 if i==63 else {'loop':45,'cut':37,'gate':11,'return':14}.get(pad.get('kind'),45)) if pad else 0
                elif c.get('ready') and c.get('kind') in ('melodic','texture'):
                    intervals=(self.client.state or {}).get('harmony',{}).get('pitch_classes',[0,2,4,5,7,9,11]);value=9 if (i%8+3*(i//8))%len(intervals)==0 else 37
            out[36+i]=127 if 36+i in self.held else value
        return out
