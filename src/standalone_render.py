"""Stable opaque controls over slow crossfading API collection images."""
from pathlib import Path
import array
import json
import time
from canvas import Canvas,INK,BRASS,MIST,DARK,FONT
from channel_fx import pages,page_parameters
from standalone import NAMES
class Background:
    def __init__(self,assets,clock=time.monotonic,blender=None):
        self.blender=blender
        self.clock=clock;self.started=clock();self.images=[];self.credits=[];self.error=''
        try:
            records=json.loads((Path(assets)/'images.json').read_text())
            for record in records:
                data=(Path(assets)/record['file']).read_bytes()
                if len(data)!=327680:raise ValueError('image size')
                self.images.append(array.array('H',data));self.credits.append(record)
        except (OSError,ValueError,KeyError) as e:self.error=str(e)
    def update(self,packed,credit):
        if len(packed)!=327680:return
        if any(c.get('sha256')==credit.get('sha256') for c in self.credits):return
        # Append safely; transitions and current image persist through worker failure.
        if len(self.images)<9:self.images.append(array.array('H',packed));self.credits.append(credit)
        else:
            elapsed=self.clock()-self.started;slot=(int(elapsed//90)+(2 if elapsed%90>=82 else 1))%len(self.images)
            self.images[slot]=array.array('H',packed);self.credits[slot]=credit
    def frame(self):
        if not self.images:return bytes(327680)
        elapsed=self.clock()-self.started;index=int(elapsed//90)%len(self.images);phase=elapsed%90
        if phase<82:return self.images[index].tobytes()
        a=self.images[index];b=self.images[(index+1)%len(self.images)];weight=(phase-82)/8
        # Bounded native loop releases the GIL; no Python pixel loop delays MIDI.
        return self.blender(a,b,weight) if self.blender else a.tobytes()
def fit(text,width,scale=1):
    result='';used=0
    for ch in str(text).upper():
        size=(len(FONT[ch][0])+1 if ch in FONT else 4)*scale
        if used+size>width:break
        result+=ch;used+=size
    return result

def render(ui,status,background):
    c=Canvas(background.frame());bank=ui.current;ch=ui.selected
    drum=ui.catalog[bank['drum']]['name'].replace('AJ_HALL_DRUM_BREAK_','')
    worker=ui.archive_worker
    archive=('IA '+worker.state+(' NEXT16' if worker.credit and worker.credit.get('sha256')!=bank['archive_id'] else '')+' '+(worker.error if worker.error else (str(bank['film_credit'].get('title','')) if isinstance(bank['film_credit'],dict) else 'OFFLINE FALLBACK'))) if worker else ''
    c.rect(0,0,960,27,DARK)
    if ui.mix:
        c.text(8,7,'LIMINAL / MIX',INK,2)
        c.text(300,9,'TOP: SELECT  DEVICE/NOTE: CHANNEL EFFECTS',MIST)
        for i,name in enumerate(NAMES):
            x=i*120;c.rect(x+3,33,114,86,DARK)
            c.text(x+8,40,('+' if ch==i else '')+name,MIST if ch==i else INK)
            c.text(x+8,59,'MANUAL' if ui.manual[i] else 'AUTO',BRASS)
            c.text(x+8,78,'MUTE' if ui.muted[i] else '%d%%'%round(ui.level[i]*100),INK,2)
            c.rect(x+8,105,100,3,(34,56,58));c.rect(x+8,105,round(100*ui.level[i]),3,MIST)
        c.rect(725,33,230,86,DARK)
        c.text(733,42,'KNOBS 1-6: CHANNEL LEVELS',MIST)
        c.text(733,62,'LOWER 1-6: MUTE')
        c.text(733,82,'SHIFT+LOWER: AUTO/MANUAL')
        c.text(733,103,'VOLUME: MASTER %d%%'%round(ui.master*100))
    else:
        page=ui.fx_pages[ch];names=pages(ch)
        c.text(8,6,NAMES[ch],MIST,2)
        c.text(156,9,('MANUAL' if ui.manual[ch] else 'AUTO')+(' / MUTE' if ui.muted[ch] else ''),BRASS)
        c.text(310,9,names[page]+'  %d/%d'%(page+1,len(names)),INK,2)
        c.text(600,9,'7 PREV / 8 NEXT',MIST)
        c.text(804,9,'MASTER %d%%'%round(ui.master*100))
        source=drum if ch==0 else (bank['bass'][0] if ch==1 else bank['programs'][0][0] if ch==2 else bank['pad'][0] if ch==3 else (str(bank['film_credit'].get('title','OFFLINE FILM')) if isinstance(bank['film_credit'],dict) else 'OFFLINE FILM'))
        if ch==4 and bank.get('dialogue'):
            labels=bank['dialogue']['labels'];source=labels[min(ui.chop,len(labels)-1)]
        c.rect(0,30,960,14,DARK);c.text(8,33,fit('SOURCE: '+source,610),BRASS)
        c.text(640,33,'TOP/WHEEL: CHANNEL  LOWER 7/8: FX PAGE',MIST)
        values=[]
        if page<3:
            for p in page_parameters(ch,page):
                value=ui.level[ch] if p.id==0 else ui.effects[ch][p.id]
                values.append((p.label,p.display(value),(value-p.low)/(p.high-p.low)))
        else:
            values=[('CUTS','',0),('SHIFT','FINE',0),('COARSE','50 MS',0),('FINE','5 MS',0),('PAD PLAY','HOLD' if ch==4 else 'ONE SHOT',0)]
            if bank['cuts']:
                index=min(ui.chop,len(bank['cuts'])-1);start,length=ui.cut(bank,index);total=len(bank['pcm'][1])//2
                values.extend((('START','%.2f S'%(start/44100),start/max(1,total)),('LENGTH','%.2f S'%(length/44100),length/max(1,total)),('PAD','%d/%d'%(index+1,len(bank['cuts'])),(index+1)/len(bank['cuts']))))
        for i,(label,value,fraction) in enumerate(values):
            x=i*120;c.rect(x+3,48,114,71,DARK)
            c.text(x+8,53,fit(label,104,2),BRASS,2)
            c.text(x+8,74,fit(value,104,2),INK,2)
            c.rect(x+8,105,100,4,(34,56,58));c.rect(x+8,105,round(100*max(0,min(1,fraction))),4,MIST)
        c.text(8,122,'KNOBS 1-8: '+names[page]+' / PADS PLAY  SHIFT+LOWER 1-6: AUTO/MANUAL',MIST)
        c.text(726,122,'LOWER 7 PREV / 8 NEXT',BRASS)
    c.rect(0,134,960,26,DARK)
    bar=min(16,1+int(status['position']/max(1,bank['length'])*16))
    ready='NEXT READY' if ui.next_slot is not None else ('PREPARING' if ui.pending else 'REPEATING CURRENT')
    c.text(8,137,('PLAYING' if status['playing'] else 'STOPPED')+'  %d BPM  BAR %02d/16  '%(bank['bpm'],bar)+ready,MIST)
    c.text(600,137,'REPEAT: NEW TAKE/IA  STOP: HUSH',BRASS)
    speech=getattr(ui,'speech',None)
    speech_status=('SPEECH '+speech.state+' '+speech.error) if speech else ''
    c.text(8,150,fit(ui.error or speech_status or archive or 'ARROWS: OCTAVE/DRUM PAGE  DELETE: RELEASE  MIX: OVERVIEW  HELP: CONTROLS',944))
    if ui.settings:
        c.rect(0,28,960,132,DARK);c.text(12,40,'RECOVERY - SAVE AND STOP FIRST',INK,2)
        c.text(12,65,'LOWER 1 STILLWATER / 2 STOCK / 3 OLD CONTROLLER',MIST)
        c.text(12,90,'TARGET: '+(ui.recovery_target or 'CHOOSE DELIBERATELY').upper(),BRASS,2)
        c.text(12,130,'LOWER 8 CONFIRM / LOWER 7 CANCEL - PRESERVES EXISTING MUSIC')
    elif ui.help:
        c.rect(0,28,960,132,DARK);c.text(12,35,'LIMINAL / CHANNEL EFFECTS',INK,2)
        c.text(12,57,'DEVICE/NOTE: SELECTED CHANNEL. KNOBS 1-8: SOUND / SPACE / MOTION. LOWER 7/8: PREV/NEXT.',MIST)
        c.text(12,72,'TOP 1-6 OR WHEEL: CHANNEL. MIX: LEVELS. SHIFT+LOWER 1-6: AUTO/MANUAL. PADS ALWAYS PLAY.')
        c.text(12,87,'CHOPS/FILM CUTS PAGE: KNOB 6 START / 7 LENGTH / 8 PAD. 50MS STEPS; SHIFT: 5MS.')
        c.text(12,102,'CHOPS: HOLD LIT PADS IN SOURCE ORDER. SHIFT+PAD: SELECT. FILM: ANCHOR ONE-SHOT.')
        c.text(12,117,'CHOPS: 4-WIDE UP LEFT32 THEN RIGHT32. DRUMS: LEFT16. UNUSED PADS DARK. SHIFT+DRUM: TAKE.')
        credit=background.credits[0] if background.credits else {}
        c.text(12,132,fit('IMAGES: CLEVELAND / CC0 / '+str(credit.get('title','CACHE UNAVAILABLE')),936),BRASS)
        c.text(12,147,'SOURCE CREDITS: LOCAL PRIVATE-ASSETS/*.JSON. SPEECH RUNS LOCALLY; PENDING/FAILURE KEEPS MUSIC.')
    return bytes(c.pixels)


def write_ppm(path,frame):
    import struct
    rgb=bytearray()
    for y in range(160):
        for x in range(960):
            v=struct.unpack_from('<H',frame,(y*1024+x)*2)[0]
            rgb.extend(((v&31)*255//31,((v>>5)&63)*255//63,(v>>11)*255//31))
    Path(path).write_bytes(b'P6\n960 160\n255\n'+rgb)
