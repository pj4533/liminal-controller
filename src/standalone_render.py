"""Stable opaque controls over slow crossfading API collection images."""
from pathlib import Path
import array
import json
import time
from canvas import Canvas,INK,BRASS,MIST,DARK
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
def render(ui,status,background):
    c=Canvas(background.frame());bank=ui.current
    c.rect(0,0,960,26,DARK);c.text(8,7,'LIMINAL',INK,2)
    c.text(115,9,('PLAYING' if status['playing'] else 'STOPPED')+'  LO-FI  %d BPM'%bank['bpm'],MIST)
    bar=min(16,1+int(status['position']/max(1,bank['length'])*16));c.text(370,9,'BAR %02d/16'%bar)
    c.text(480,9,'NEXT READY' if ui.next_slot is not None else ('PREPARING' if ui.pending else 'REPEATING CURRENT'),BRASS)
    c.text(730,9,'MASTER %d'%round(ui.master*100))
    for ch,name in enumerate(NAMES):
        x=ch*120;c.rect(x+3,31,114,51,DARK)
        c.text(x+8,36,('+' if ui.selected==ch else '')+name,MIST if ui.selected==ch else INK)
        c.text(x+8,50,'MANUAL' if ui.manual[ch] else 'AUTO',BRASS)
        c.text(x+8,65,'MUTE' if ui.muted[ch] else '%d%%'%round(ui.level[ch]*100))
    c.rect(725,31,230,51,DARK);c.text(733,36,'SHIFT + LOWER : AUTO/MANUAL',MIST);c.text(733,50,'LOWER : MUTE  TOP : SELECT');c.text(733,65,'MIX : SIX CHANNEL LEVELS')
    c.rect(0,89,960,30,DARK)
    if ui.mix:
        labels=[name+' '+str(round(ui.level[i]*100)) for i,name in enumerate(NAMES)]+['','']
    else:
        ch=ui.selected;fx=ui.effects[ch];labels=['LEVEL '+str(round(ui.level[ch]*100)),'TONE '+str(round(fx[0]*100)),'ECHO '+str(round(fx[1]*100)),'ROOM '+str(round(fx[2]*100)),'PAN '+str(round(fx[3]*100)),'','','']
    if not ui.mix and ui.selected in (4,5) and bank['cuts']:
        start,length=ui.cut(bank,ui.chop);labels[5:] = ['START %.2fS'%(start/44100),'LENGTH %.2fS'%(length/44100),'PAD %d'%(ui.chop+1)]
    for i,label in enumerate(labels):c.text(i*120+7,99,label,INK)
    c.rect(0,126,960,34,DARK)
    drum=ui.catalog[bank['drum']]['name'].replace('AJ_HALL_DRUM_BREAK_','')
    c.text(8,130,'TAKE '+drum[:45],BRASS)
    c.text(370,130,'LEAD '+bank['programs'][0][0][:27],MIST)
    worker=ui.archive_worker
    archive=('IA '+worker.state+(' NEXT16' if worker.credit and worker.credit.get('sha256')!=bank['archive_id'] else '')+' '+(worker.error if worker.error else (str(bank['film_credit'].get('title','')) if isinstance(bank['film_credit'],dict) else 'OFFLINE FALLBACK'))) if worker else ''
    c.text(8,146,(ui.error or archive or 'REPEAT: NEXT DRUM  ARROWS: OCTAVE/DRUM PAGE  DELETE: RELEASE  STOP: HUSH')[:96])
    c.text(733,130,'API IMAGE / OFFLINE CACHE')
    c.text(733,146,'CHOPS/FILM REPEAT: FETCH')
    if ui.settings:
        c.rect(0,28,960,132,DARK);c.text(12,40,'RECOVERY - SAVE AND STOP FIRST',INK,2)
        c.text(12,65,'LOWER 1 STILLWATER / 2 STOCK / 3 OLD CONTROLLER',MIST)
        c.text(12,90,'TARGET: '+(ui.recovery_target or 'CHOOSE DELIBERATELY').upper(),BRASS,2)
        c.text(12,130,'LOWER 8 CONFIRM / LOWER 7 CANCEL - PRESERVES EXISTING MUSIC')
    elif ui.help:
        c.rect(0,28,960,132,DARK);c.text(12,38,'LIMINAL / LOCAL LO-FI / NO MAC REQUIRED',INK,2)
        c.text(12,62,'SHIFT+LOWER AUTO/MANUAL. MELODIC PADS: RIGHT 1 / UP 3 SCALE DEGREES.')
        c.text(12,79,'CHOPS: PADS 1-8. SHIFT+PAD SELECT. KNOBS 6 START / 7 LENGTH / 8 PAD. SHIFT: FINE.')
        c.text(12,96,'CHOPS/FILM REPEAT FETCHES FRESH IA. NEW SOURCE AT 16 BARS. STOP HUSHES. NO TRANSCRIPTION.')
        credit=background.credits[0] if background.credits else {}
        c.text(12,116,'IMAGES: CLEVELAND MUSEUM / CC0 / '+str(credit.get('title','CACHE UNAVAILABLE'))[:60],BRASS)
        c.text(12,140,'SOURCE CREDITS AND FILE HASHES: LOCAL PRIVATE-ASSETS/*.JSON')
    return bytes(c.pixels)


def write_ppm(path,frame):
    import struct
    rgb=bytearray()
    for y in range(160):
        for x in range(960):
            v=struct.unpack_from('<H',frame,(y*1024+x)*2)[0]
            rgb.extend(((v&31)*255//31,((v>>5)&63)*255//63,(v>>11)*255//31))
    Path(path).write_bytes(b'P6\n960 160\n255\n'+rgb)
