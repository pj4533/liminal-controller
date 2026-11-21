"""Standalone control state. One MIDI producer; no remote Liminal connection."""
import concurrent.futures
import json
from pathlib import Path
import random
from composition import Instruments,prepare,choose_drum,SR
from sampler import Event
from dialogue_ledger import DialogueLedger
NAMES=('DRUMS','BASS','LEAD','MIDS','CHOPS','FILM')
class Instrument:
    def __init__(self,engine,assets,home=None,archive_worker=None):
        self.engine=engine;self.assets=Path(assets);self.catalog=json.loads((self.assets/'drums.json').read_text())
        film=json.loads((self.assets/'film.json').read_text()) if (self.assets/'film.json').exists() else {}
        self.ledger=DialogueLedger(Path(home or assets)/'dialogue-lines.json',film.get('sha256','no-film'))
        self.instruments=Instruments(self.assets/'instruments',engine)
        self.settings=False;self.recovery_target=None;self.recovery_request=None;self.help=False;self.selected=0;self.shift=False;self.mix=False;self.manual=[False]*6;self.muted=[False]*6
        self.level=[.65]*6;self.effects=[[.55,.12,.10,0] for _ in range(6)];self.master=.45;self.octave=0
        self.held={};self.identity=0;self.next_revision=1;self.error='';self.pending=None;self.last_bank=-1;self.next_slot=None;self.queued_drum=None;self.drum_page=0
        self.archive_worker=archive_worker;self.archive=None;self.archive_dirty=False;self.chop=0;self.edits={};self.archive_started=0
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix='prepare')
        first=min(range(len(self.catalog)),key=lambda i:abs(self.catalog[i]['bpm']-69))
        bank=prepare(self.instruments,self.assets,self.catalog,0,first,line_index=self.ledger.choose())
        self.engine.install(bank);self.engine.render(1);self.last_bank=self.engine.status()['bank']
        for ch in range(6):
            for i,op in enumerate((11,12,13,14)):self.engine.command(op,ch,event=Event(gain=self.effects[ch][i]))
        self.request_next()
    def request_next(self,index=None,refresh=False):
        if index is not None:self.queued_drum=index
        if self.pending is not None or (self.next_slot is not None and index is None and not refresh):return
        current=self.engine.banks[self.last_bank][1]
        if self.queued_drum is None:index=choose_drum(self.catalog,current['bpm'],self.catalog[current['drum']]['sha256'],random.Random(1042+self.next_revision))
        else:index=self.queued_drum;self.queued_drum=None
        self.pending=self.pool.submit(prepare,self.instruments,self.assets,self.catalog,self.next_revision,index,current['bpm'],1042,self.ledger.choose(current['line_index']),self.archive);self.next_revision+=1;self.archive_dirty=False
    def tick(self):
        status=self.engine.status();bank=status['bank']
        if self.archive_worker:
            fresh=self.archive_worker.poll()
            if fresh:self.archive=fresh;self.archive_dirty=True
        if self.archive_dirty and self.pending is None:self.request_next(refresh=True)
        if status['playing'] and bank in self.engine.banks:
            prepared=self.engine.banks[bank][1];text='' if prepared['archive_id'] else self.ledger.commit(prepared['line_index'],prepared['revision'])
            if text:self.pool.submit(self.ledger.save,text)
        if bank>=0 and bank!=self.last_bank:
            self.last_bank=bank;self.edits={k:v for k,v in self.edits.items() if k[0]==self.cut_source(self.current)};self.next_slot=None;self.request_next()
        if self.pending is not None and self.pending.done():
            try:
                prepared=self.pending.result()
                if self.queued_drum is not None:
                    self.pending=None;self.request_next(self.queued_drum);return status
                if self.archive_dirty:
                    self.pending=None;self.request_next(refresh=True);return status
                slot=self.engine.install(prepared)
                if slot is not None:self.next_slot=slot;self.pending=None;self.error=''
            except Exception as e:self.pending=None;self.error='PREP ERROR '+str(e)[:55]
        return status
    @property
    def current(self):return self.engine.banks[self.last_bank][1]
    def send(self,*args,**kw):
        if not self.engine.command(*args,**kw):raise BufferError('Audio queue full; stop safely')
    def onset(self,slot,revision,identity,event):
        if self.engine.command(7,slot,revision,identity,event):return True
        if self.engine.last_admission==-1:self.error='SOURCE CHANGED - RETRY PAD';return False
        raise BufferError('Audio queue full; stop safely')
    def toggle_mode(self,ch):
        self.send(3,ch,int(not self.manual[ch]));self.manual[ch]=not self.manual[ch]
    def event(self,e):
        kind=e['kind'];number=e['number'];value=e['value']
        if kind=='note_off':
            identity=self.held.pop(number,None)
            if identity:self.send(8,identity=identity)
            return
        if kind=='note' and 36<=number<=99:
            # Snapshot the native current source, not the UI's last tick (which
            # can straddle a boundary while a replacement is being prepared).
            slot=self.engine.status()['bank']
            if slot not in self.engine.banks:return
            ch=self.selected;pad=number-36;bank=self.engine.banks[slot][1]
            if ch==4:
                self.chop=pad%8
                if self.shift:return
            if not self.manual[ch]:
                if ch==0:
                    index=self.drum_page*64+pad
                    if index<len(self.catalog):self.request_next(index)
                return
            if number in self.held:self.send(8,identity=self.held.pop(number))
            self.identity+=1;identity=self.identity
            if ch in (0,4,5):
                if ch==0:local=bank['drumcuts'][pad%4];gain=bank['events'][0]['gain']*.9
                elif ch==4:
                    if len(bank['pcm'])<10:return
                    local=2+pad%8;gain=.35
                else:
                    if len(bank['pcm'])<10:return
                    local=bank['anchor'];gain=.25
                # Film/chops are immediate one-shots. Release does not truncate them.
                frames=len(bank['pcm'][local])//2;offset=0
                if ch==4:
                    offset,frames=self.cut(bank,pad%8);local=1
                event=Event(frame=offset,channel=ch,sample=192+slot*16+local,gate=frames,speed=1,gain=gain*value/127,attack=128,release=256)
                if not self.onset(slot,bank['revision'],identity,event):return
                if ch==0:self.held[number]=identity
            else:
                degree=pad%8+3*(pad//8);scale=bank['scale'];base=(36 if ch==1 else 48)+bank['tonic']+self.octave*12
                midi=base+12*(degree//len(scale))+scale[degree%len(scale)]
                program=bank['bass'] if ch==1 else (bank['pad'] if ch==3 else bank['programs'][0])
                values=self.instruments.event(ch,midi,0,120,value/127,program,bank['bpm']);values['gate']=SR*120
                if self.onset(slot,bank['revision'],identity,Event(**values)):self.held[number]=identity
            return
        if kind!='cc':return
        if number==49:self.shift=bool(value);return
        if 71<=number<=79:
            delta=value if value<64 else value-128
            if not delta:return
            if number==79:
                self.master=min(1,max(0,self.master+delta*.01));self.send(10,event=Event(gain=self.master));return
            knob=number-71;ch=self.selected
            if not self.mix and ch in (4,5) and knob in (5,6,7):
                if knob==7:self.chop=(self.chop+(1 if delta>0 else -1))%8
                else:
                    start,length=self.cut(self.current,self.chop);total=len(self.current['pcm'][1])//2
                    step=round(SR*(.005 if self.shift else .05))*delta
                    if knob==5:start=max(0,min(total-length,start+step))
                    else:length=max(SR//20,min(total-start,length+step))
                    self.edits[(self.cut_source(self.current),self.chop)]=(start,length)
                    if self.archive and self.current['archive_id']==self.archive['credit']['sha256']:
                        self.archive=dict(self.archive,cuts=list(self.archive['cuts']));self.archive['cuts'][self.chop]=(start,length);self.archive_dirty=True
                return
            if self.mix:
                if knob<6:self.level[knob]=min(1,max(0,self.level[knob]+delta*.01));self.send(4,knob,event=Event(gain=self.level[knob]))
            elif knob==0:self.level[ch]=min(1,max(0,self.level[ch]+delta*.01));self.send(4,ch,event=Event(gain=self.level[ch]))
            elif knob in (1,2,3,4):
                i=knob-1;lo=-1 if i==3 else 0;hi=(1,.6,.5,1)[i];self.effects[ch][i]=min(hi,max(lo,self.effects[ch][i]+delta*.01));self.send((11,12,13,14)[i],ch,event=Event(gain=self.effects[ch][i]))
            return
        if not value:return
        if number==30:self.settings=not self.settings;self.recovery_target=None;return
        if number==81:self.help=not self.help;return
        if self.settings:
            if number in (20,21,22):self.recovery_target={20:'stillwater',21:'stock',22:'controller'}[number]
            elif number==26:self.settings=False;self.recovery_target=None
            elif number==27 and self.recovery_target:self.send(2);self.recovery_request=self.recovery_target
            return
        if 102<=number<=107:self.selected=number-102
        elif 20<=number<=25:
            ch=number-20
            if self.shift:self.toggle_mode(ch)
            else:self.muted[ch]=not self.muted[ch];self.send(5,ch,int(self.muted[ch]))
        elif number==85:self.send(1)
        elif number==29:self.send(2);self.held.clear()
        elif number==118:self.send(9);self.held.clear()
        elif number==112:self.mix=True
        elif number in (50,110):self.mix=False
        elif number==56 and self.selected in (4,5) and self.archive_worker:self.archive_worker.request()
        elif number==56:self.request_next(choose_drum(self.catalog,self.current['bpm'],self.catalog[self.current['drum']]['sha256'],random.Random(self.identity+1042)))
        elif number in (62,63):
            if self.selected==0:self.drum_page=1-self.drum_page
            else:
                candidate=max(-2,min(2,self.octave+(-1 if number==62 else 1)))
                base=(36 if self.selected==1 else 48)+self.current['tonic']+candidate*12
                scale=self.current['scale'];top=base+12*(28//len(scale))+scale[28%len(scale)]
                if 0<=base and top<=127:self.octave=candidate
        elif number==70:self.selected=(self.selected+(1 if value<64 else -1))%6
    def cut_source(self,bank):return bank['archive_id'] or ('offline',bank['line_index'])
    def cut(self,bank,index):
        return self.edits.get((self.cut_source(bank),index),bank['cuts'][index])
    def leds(self):
        ch=self.selected
        return {n:(100 if n in self.held else (35 if self.manual[ch] else (12 if ch==0 and self.drum_page*64+n-36<len(self.catalog) else 0))) for n in range(36,100)}
    def close(self):self.pool.shutdown(wait=True,cancel_futures=True)
