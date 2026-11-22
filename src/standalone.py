"""Standalone control state. One MIDI producer; no remote Liminal connection."""
import concurrent.futures
import json
from pathlib import Path
import random
from composition import Instruments,prepare,choose_drum,chop_gain,SR
from sampler import Event
from channel_fx import defaults,parameters,pages,page_parameters
from dialogue_ledger import DialogueLedger
from dialogue_speech import Speech
def slice_note(index):
    return 36+((index%32)//4)*8+(index//32)*4+index%4
def slice_index(note):
    pad=note-36;return (pad%8//4)*32+(pad//8)*4+pad%4

NAMES=('DRUMS','BASS','LEAD','MIDS','CHOPS','FILM')
# Stillwater's default centered D Dorian grid and Silt hardware palette.
MANUAL_SCALE=(0,2,3,5,7,9,10)
def pad_pitch(number,octave=0):
    degree=(number-36)%8+3*((number-36)//8)-14+7*octave
    return 62+12*(degree//7)+MANUAL_SCALE[degree%7]

class Instrument:
    def __init__(self,engine,assets,home=None,archive_worker=None):
        self.engine=engine;self.assets=Path(assets);self.catalog=json.loads((self.assets/'drums.json').read_text())
        film=json.loads((self.assets/'film.json').read_text()) if (self.assets/'film.json').exists() else {}
        self.ledger=DialogueLedger(Path(home or assets)/'dialogue-lines.json',film.get('sha256','no-film'))
        self.instruments=Instruments(self.assets/'instruments',engine)
        self.settings=False;self.recovery_target=None;self.recovery_request=None;self.help=False;self.selected=0;self.shift=False;self.mix=False;self.manual=[False]*6;self.muted=[False]*6
        self.level=[.65]*6;self.effects=[defaults(ch) for ch in range(6)];self.fx_pages=[0]*6;self.master=.45;self.octave=0
        self.held={};self.identity=0;self.next_revision=1;self.error='';self.pending=None;self.last_bank=-1;self.next_slot=None;self.queued_drum=None;self.drum_page=0
        self.archive_worker=archive_worker;self.archive=None;self.archive_dirty=False;self.chop=0;self.edits={};self.edit_gains={};self.archive_started=0
        self.speech=Speech(home or assets,tools=Path(home or assets)/'tools')
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix='prepare')
        first=min(range(len(self.catalog)),key=lambda i:abs(self.catalog[i]['bpm']-69))
        bank=prepare(self.instruments,self.assets,self.catalog,0,first,line_index=self.ledger.choose())
        self.engine.install(bank);self.engine.render(1);self.last_bank=self.engine.status()['bank']
        for ch in range(6):
            for p in parameters(ch):self.engine.command(16,ch,p.id,event=Event(gain=self.effects[ch][p.id]))
        self.request_next()
    def request_next(self,index=None,refresh=False):
        if index is not None:self.queued_drum=index
        if self.pending is not None or (self.next_slot is not None and index is None and not refresh):return
        current=self.engine.banks[self.last_bank][1]
        if self.queued_drum is None:index=choose_drum(self.catalog,current['bpm'],self.catalog[current['drum']]['sha256'],random.Random(1042+self.next_revision))
        else:index=self.queued_drum;self.queued_drum=None
        self.pending=self.pool.submit(prepare,self.instruments,self.assets,self.catalog,self.next_revision,index,current['bpm'],1042,self.ledger.choose(current['line_index']),self.archive,self.speech);self.next_revision+=1;self.archive_dirty=False
    def tick(self):
        status=self.engine.status();bank=status['bank']
        if self.archive_worker:
            fresh=self.archive_worker.poll()
            if fresh:self.archive=fresh;self.archive_dirty=True
        if self.archive_dirty and self.pending is None:self.request_next(refresh=True)
        if status['playing'] and bank in self.engine.banks:
            prepared=self.engine.banks[bank][1];text='' if prepared['archive_id'] else self.ledger.commit(('text:'+prepared['dialogue']['line']) if prepared.get('dialogue') else prepared['line_index'],prepared['revision'])
            if text:self.pool.submit(self.ledger.save,text)
        if bank>=0 and bank!=self.last_bank:
            self.last_bank=bank;self.chop=min(self.chop,max(0,len(self.current['cuts'])-1));self.edits={k:v for k,v in self.edits.items() if k[0]==self.cut_source(self.current)};self.edit_gains={k:v for k,v in self.edit_gains.items() if k[0]==self.cut_source(self.current)};self.next_slot=None;self.request_next()
            if self.archive_worker:self.archive_worker.request()
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
        if kind=='note_off' or (kind=='note' and value==0):
            identity=self.held.pop(number,None)
            if identity:self.send(8,identity=identity)
            return
        if kind=='note' and 36<=number<=99:
            # Snapshot the native current source, not the UI's last tick (which
            # can straddle a boundary while a replacement is being prepared).
            slot=self.engine.status()['bank']
            if slot not in self.engine.banks:return
            ch=self.selected;pad=number-36;bank=self.engine.banks[slot][1]
            if ch==4:pad=slice_index(number)
            elif ch==0 and not self.shift:
                pad=slice_index(number)
                if pad>=len(bank['drumcuts']):return
            elif ch==5 and pad!=0:return
            if ch==4:
                if pad>=len(bank['cuts']):return
                self.chop=pad
                if self.shift:return
            if ch==0 and self.shift:
                index=self.drum_page*64+pad
                if index<len(self.catalog):self.request_next(index)
                return
            if number in self.held:self.send(8,identity=self.held.pop(number))
            self.identity+=1;identity=self.identity
            if ch in (0,4,5):
                if ch==0:local=bank['drumcuts'][pad];gain=bank['events'][0]['gain']*.9
                elif ch==4:
                    local=1;gain=self.edit_gains.get((self.cut_source(bank),pad),bank['chop_gains'][pad])
                else:
                    if len(bank['pcm'])<10:return
                    local=bank['anchor'];gain=.25
                # Chops end at their slice boundary or owning pad release;
                # Film remains a full-anchor one-shot.
                frames=len(bank['pcm'][local])//2;offset=0
                if ch==4:
                    offset,frames=self.cut(bank,pad);local=1
                elif ch==0 and 'drum_ranges' in bank:offset,frames=bank['drum_ranges'][pad]
                event=Event(frame=offset,channel=ch,sample=192+slot*16+local,gate=frames,speed=1,gain=gain*value/127,attack=128,release=256)
                if not self.onset(slot,bank['revision'],identity,event):return
                if ch in (0,4):self.held[number]=identity
            else:
                midi=pad_pitch(number,self.octave)
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
            if not self.mix and self.fx_pages[ch]==3 and ch in (4,5) and knob in (5,6,7):
                count=len(self.current['cuts'])
                if not count:return
                self.chop=min(self.chop,count-1)
                if knob==7:self.chop=(self.chop+(1 if delta>0 else -1))%count
                else:
                    start,length=self.cut(self.current,self.chop);total=len(self.current['pcm'][1])//2
                    step=round(SR*(.005 if self.shift else .05))*delta
                    if knob==5:start=max(0,min(total-length,start+step))
                    else:length=max(SR//20,min(total-start,length+step))
                    key=(self.cut_source(self.current),self.chop)
                    self.edits[key]=(start,length)
                    # Control-thread analysis: the next pad uses the edited range,
                    # including a formerly silent suggestion moved onto speech.
                    pcm=self.current['pcm'][1]
                    self.edit_gains[key]=chop_gain(pcm[start*2:(start+length)*2])
                    if self.archive and self.current['archive_id']==self.archive['credit']['sha256']:
                        self.archive=dict(self.archive,cuts=list(self.current['cuts']),edited=True,semantic=self.current.get('dialogue'));self.archive['cuts'][self.chop]=(start,length);self.archive_dirty=True
                return
            if self.mix:
                if knob<6:self.level[knob]=min(1,max(0,self.level[knob]+delta*.01));self.effects[knob][0]=self.level[knob];self.send(4,knob,event=Event(gain=self.level[knob]))
            elif self.fx_pages[ch]<3:
                p=page_parameters(ch,self.fx_pages[ch])[knob]
                self.effects[ch][p.id]=p.edit(self.effects[ch][p.id],delta)
                if p.id==0:self.level[ch]=self.effects[ch][0]
                self.send(16,ch,p.id,event=Event(gain=self.effects[ch][p.id]))
            return
        if not value:return
        if number==30:self.settings=not self.settings;self.recovery_target=None;return
        if number==81:self.help=not self.help;return
        if self.settings:
            if number in (20,21,22):self.recovery_target={20:'stillwater',21:'stock',22:'controller'}[number]
            elif number==26:self.settings=False;self.recovery_target=None
            elif number==27 and self.recovery_target:self.send(2);self.recovery_request=self.recovery_target
            return
        if number in (26,27) and not self.mix:
            self.fx_pages[self.selected]=(self.fx_pages[self.selected]+(-1 if number==26 else 1))%len(pages(self.selected));return
        if 102<=number<=107:self.selected=number-102
        elif 20<=number<=25:
            ch=number-20
            if self.shift:self.toggle_mode(ch)
            else:self.muted[ch]=not self.muted[ch];self.send(5,ch,int(self.muted[ch]))
        elif number==85:self.send(15)
        elif number==29:self.send(2);self.held.clear()
        elif number==118:self.send(9);self.held.clear()
        elif number==112:self.mix=True
        elif number in (50,110):self.mix=False
        elif number==56 and self.selected in (4,5) and self.archive_worker:self.archive_worker.request()
        elif number==56:self.request_next(choose_drum(self.catalog,self.current['bpm'],self.catalog[self.current['drum']]['sha256'],random.Random(self.identity+1042)))
        elif number in (62,63):
            if self.selected==0:self.drum_page=1-self.drum_page
            else:
                candidate=max(-4,min(4,self.octave+(-1 if number==62 else 1)))
                if 0<=pad_pitch(36,candidate) and pad_pitch(99,candidate)<=127:self.octave=candidate
        elif number==70:self.selected=(self.selected+(1 if value<64 else -1))%6
    def cut_source(self,bank):
        source=bank['archive_id'] or ('offline',bank['line_index'])
        return (source,bank['dialogue']['line']) if bank.get('dialogue') else source
    def cut(self,bank,index):
        return self.edits.get((self.cut_source(bank),index),bank['cuts'][index])
    def leds(self):
        ch=self.selected
        if ch==4:
            leds={n:(100 if n in self.held else 35 if slice_index(n)<len(self.current['cuts']) else 0) for n in range(36,100)}
        elif ch in (1,2,3):
            active={pad_pitch(n,self.octave) for n in self.held}
            leds={n:(37 if pad_pitch(n,self.octave) in active else 65 if pad_pitch(n,self.octave)%12==2 else 123 if pad_pitch(n,self.octave)%12 in (0,2,4,5,7,9,11) else 66) for n in range(36,100)}
        elif ch==0 and self.shift:leds={n:(35 if self.drum_page*64+n-36<len(self.catalog) else 0) for n in range(36,100)}
        else:
            count=len(self.current['drumcuts']) if ch==0 else 1
            leds={n:(100 if n in self.held else 35 if (slice_index(n) if ch==0 else n-36)<count else 0) for n in range(36,100)}
        feedback=self.engine.feedback(ch)
        if not self.manual[ch] and feedback and feedback[0]==self.current['revision']:
            code=feedback[1]
            if code>=128:
                for n in leds:
                    if pad_pitch(n,self.octave)==code-128:leds[n]=5
            elif 1<=code<=64:
                note=slice_note(code-1) if ch in (0,4) else 35+code
                if leds.get(note):leds[note]=5
        return leds
    def close(self):
        if hasattr(self,'speech'):self.speech.close()
        self.pool.shutdown(wait=True,cancel_futures=True)
