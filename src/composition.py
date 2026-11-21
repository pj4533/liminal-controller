"""Portable Liminal Lo-Fi policy subset, upstream 67fde8da (MIT PJ Gray).
Motif/answer contours and articulation come from LofiScore; program rows from
LofiPreset; octave calibration from LofiSampleBank. This is not Swift DSP parity.
"""
import array
import math
from pathlib import Path
import random
import re
from sampler import SR,read_pcm

SCALES=((0,2,3,5,7,8,10),(0,2,3,5,7,9,10),(0,3,5,7,10))
PATTERNS=((.5,1.25,2.75,5.5,7,10.25),(.75,2,2.75,6.5,7.25,10.5),(.5,1,3.5,6.75,8.5,11),(1.25,2.75,4,7.5,8.25,10.5),(.75,2.5,5.25,7.75,10.5))
CONTOURS=((0,3,7,3,-2,0),(7,7,3,-2,3,0),(-5,-2,0,5,3,0),(3,0,3,7,3,0))
# name, sample group, attack seconds, release seconds, gain, loudness trim dB
PIANOS=(('Steinway Grand','grand',.003,.27,.49,0),('Felt Steinway','grand',.013,.34,.49,0),('Kawai Grand','kawai',.004,.30,.49,-.8),('Close Kawai','kawai',.004,.24,.49,0),('Felt Osiris','osiris',.012,.36,.49,-.4),('Quiet Osiris','osiris',.006,.28,.49,-1.4),('Living Room Upright','uprightkw',.006,.30,.50,.3),('Knight Upright','upright',.006,.31,.50,-.5),('Tape Upright','upright',.010,.33,.50,-.9),('Yamaha Upright','yamaha',.006,.30,.52,.5))
PLUCKS=(('Pizzicato Viola','pizz',.004,.22,.54,1.9),('Pizzicato Cello','cellopluck',.006,.29,.55,-.2),('Concert Harp','harp',.004,.29,.51,.7),('Folk Harp','folkharp',.004,.30,.51,-1.2))
GUITARS=(('Nylon Fingerstyle','nylon',.004,.30,.50,1.5),('Nylon Strum','nylon',.005,.32,.50,.9),('Steel Acoustic','steel',.008,.30,.50,1),('Archtop Acoustic','archtop',.004,.28,.50,-.7),('Archtop Jazz','jazzbox',.006,.30,.48,.3),('Flatwound Tape','flatwound',.008,.32,.48,.7))
def nearest(target,choices):return min(choices,key=lambda p:abs(p-target))
def choose_drum(catalog,bpm,previous,rng):
    choices=[i for i,e in enumerate(catalog) if e['sha256']!=previous]
    distance=min(abs(catalog[i]['bpm']-bpm) for i in choices)
    pool=[i for i in choices if abs(catalog[i]['bpm']-bpm)<=distance+4]
    return rng.choice(pool)
class Instruments:
    def __init__(self,root,engine):
        self.entries=[]
        for path in sorted(Path(root).glob('*.wav')):
            fields=path.stem.split('-')
            if fields[0] not in ('LofiLead','LofiBass'):continue
            group=fields[1];root=int(fields[3] if fields[0]=='LofiBass' else fields[2]);layer=int(fields[3]) if fields[0]=='LofiLead' and len(fields)>3 else 2
            recorded=root+(12 if fields[0]=='LofiLead' and group in ('upright','yamaha','pizz','cellopluck') else 0)
            pcm,rate=read_pcm(path);index=len(self.entries)
            if index>=192:raise ValueError('instrument capacity')
            engine.sample(index,pcm);self.entries.append(dict(index=index,kind=fields[0],group=group,root=root,recorded=recorded,layer=layer,rate=rate,name=path.name,stroke=fields[2] if fields[0]=='LofiBass' else ''))
        if not self.entries:raise ValueError('no instruments')
    def event(self,ch,midi,beat,length,velocity,program,bpm):
        kind='LofiBass' if ch==1 else 'LofiLead';group=program[1]
        choices=[e for e in self.entries if e['kind']==kind and e['group']==group and (kind!='LofiBass' or e['stroke']=='long')]
        if not choices:raise ValueError('missing '+kind+' '+group)
        layer=3 if velocity>=.60 else 2
        sample=min(choices,key=lambda e:(abs(e['root']-midi),abs(e['layer']-layer)))
        return dict(frame=round(beat*SR*60/bpm),channel=ch,sample=sample['index'],gate=max(1,round(length*SR*60/bpm)),speed=sample['rate']/SR*2**((midi-sample['recorded'])/12),gain=velocity*program[4]*10**(program[5]/20),attack=max(1,program[2]*SR),release=max(1,program[3]*SR),frequency=440*2**((midi-69)/12))

def prepare(instruments,assets,catalog,revision,drum_index,bpm=69,seed=1042,line_index=0):
    rng=random.Random(seed+revision*617);harmony=random.Random(seed+145)
    tonic=harmony.choice((0,2,3,5,7,9));scale=harmony.choice(SCALES)
    pitches=[p for p in range(53,73) if (p-tonic)%12 in scale]
    anchor=nearest(61,[p for p in range(57,69) if p%12==tonic])
    base=random.Random(seed+revision//2+206);pattern=base.choice(PATTERNS);lilt=base.uniform(.010,.045)
    contour=base.choice(((-5,0,7,4,0),(7,4,0,4,0))) if len(pattern)==5 else base.choice(CONTOURS)
    melody=[nearest(anchor+d,pitches) for d in contour];melody[-1]=anchor
    program_rng=random.Random(seed+(revision//4)*617)
    piano=program_rng.choice(PIANOS);strings=program_rng.choice(PLUCKS);guitar=program_rng.choice(GUITARS)
    rotation=[piano,strings,guitar,piano] if program_rng.random()<.60 else [piano,guitar,strings,piano]
    programs=[rotation[revision%4]]*4
    entry=catalog[drum_index];pcm,rate=read_pcm(Path(assets)/'drums'/entry['file'])
    rms=math.sqrt(sum(v*v for v in pcm)/len(pcm));gain=min(2.6,.11/max(.025,rms))
    length=round(SR*60/bpm*64)
    events=[dict(frame=0,channel=0,sample=-1,gate=length,speed=(len(pcm)//2-1)/length,gain=gain,attack=64,release=128)]
    bassgroups=sorted({e['group'] for e in instruments.entries if e['kind']=='LofiBass'})
    bassgroup=bassgroups[revision%len(bassgroups)]
    bassprogram=('Bass '+bassgroup,bassgroup,.010,.16,.65,0)
    for phrase,program in enumerate(programs):
        section=('theme','variation','breakdown','return')[phrase] if revision%2==0 else ('theme','answer','breakdown','return')[phrase]
        beats=[b+lilt for b in pattern];notes=list(melody);vel=[.78 if i%3==0 else .55 for i in range(len(beats))];vel[-1]=.81
        if section in ('answer','breakdown'):
            beats=[b+.035 for b in ((1.5,2.5,6.75,10.75) if section=='breakdown' else (1,2.75,4,7.5))]
            notes=[nearest(p,pitches) for p in (melody[0],anchor-4,anchor-7,anchor)];vel=[.77,.63,.63,.77]
        elif section=='variation':
            for i in range(3,len(notes)-1):notes[i]=nearest(anchor+(6 if i==3 else 3),pitches)
        offset=phrase*16
        for i,(beat,midi,v) in enumerate(zip(beats,notes,vel)):
            held=1.15 if i==len(beats)-1 else (.71 if i%3==0 else .38)
            held*=.61 if program in PLUCKS else (.92 if program in GUITARS else 1)
            e=instruments.event(2,midi,offset+beat,held,v,program,bpm)
            if section=='return' and i<2:e['gain']*=1.4125375
            events.append(e)
            if program in GUITARS and i in (0,3):
                # D114 guitar double-stop, in its own lead stem.
                events.append(instruments.event(2,nearest(midi-5,pitches),offset+beat+.17,.55,v*.45,program,bpm))
        chord=5 if section in ('variation','answer') else 0
        root=nearest(34,[p for p in range(28,42) if p%12==(tonic+nearest(chord,scale))%12])
        for b,step,held in ((0,0,1.6),(4,0,.7),(7,7,.8),(10,0,1.6),(13,3,.55)):
            midi=nearest(root+step,[p for p in range(28,42) if (p-tonic)%12 in scale])
            events.append(instruments.event(1,midi,offset+b,held,.68,bassprogram,bpm))
        # D117 rootless pad: thirds/sevenths/ninths, C3-D4, moving inner voice at beat8.
        classes=[(tonic+chord+nearest(i,scale))%12 for i in (3,10,2)]
        padpitches=sorted(set(nearest(t,[p for p in range(51,63) if p%12==pc]) for t,pc in zip((52,57,60),classes)))
        if section=='breakdown':padpitches=padpitches[:2]
        start=max(2,beats[1]+1.5) if section=='return' else 0
        end=16-.85/(60/bpm)-.02
        for i,midi in enumerate(padpitches):
            padprogram=('Held '+piano[0],piano[1],.35,.85,.30,0)
            if i==1:
                events.append(instruments.event(3,midi,offset+start,8.25-start,.52,padprogram,bpm))
                other=nearest(midi+2,[p for p in range(51,63) if (p-tonic)%12 in scale])
                events.append(instruments.event(3,other,offset+8,end-8,.52,padprogram,bpm))
            else:events.append(instruments.event(3,midi,offset+start,end-start,.52,padprogram,bpm))
    # Offline film bed and exact acoustic chops; decoded/prepared outside audio thread.
    film_path=Path(assets)/'film.wav';banks=[pcm];film_credit=''
    if film_path.exists():
        film,filmrate=read_pcm(film_path);banks.append(film)
        events.append(dict(frame=0,channel=5,sample=-2,gate=length,speed=filmrate/SR,gain=.16,attack=SR*.4,release=SR*.4))
        chop_frames=min(round(SR*.55),len(film)//2//8)
        for i in range(8):
            line_start=round(line_index*8*SR)
            start=min(len(film)//2-chop_frames,line_start+round(i*.8*SR));cut=array.array('f',film[start*2:(start+chop_frames)*2]);banks.append(cut)
            events.append(dict(frame=round((8+i*7)*SR*60/bpm),channel=4,sample=-(i+3),gate=chop_frames,speed=1,gain=.35,attack=128,release=256))
        banks.append(array.array('f',film[round(line_index*8*SR)*2:round((line_index+1)*8*SR)*2]));film_credit='film.json'
    # Four deterministic manual drum cuts, same PCM every trigger.
    drumcuts=[]
    for beat in (0,1,2,3):
        start=round(beat*len(pcm)/2/64);end=min(len(pcm)//2,start+round(SR*.45))
        drumcuts.append(len(banks));banks.append(array.array('f',pcm[start*2:end*2]))
    events.sort(key=lambda e:(e['frame'],e['channel'],e['sample']))
    return dict(length=length,revision=revision,events=events,pcm=banks,drum=drum_index,bpm=bpm,programs=programs,pad=('Held '+piano[0],piano[1],.35,.85,.30,0),bass=bassprogram,tonic=tonic,scale=scale,film_credit=film_credit,drumcuts=drumcuts,line_index=line_index,anchor=10)
