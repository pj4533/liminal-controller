"""Bounded offline acoustic subset of Liminal D125–127 (10f5e1d, MIT PJ Gray).
No transcription: acoustic interest is not semantic word/line understanding.
All analysis happens on the preparation worker, never the render owner.
"""
import math
import random
from sampler import SR

TEMPLATES=(((0,0),(0,6),(1,12),(0,16),(2,22),(1,28)),
           ((0,2),(1,8),(0,18),(2,24),(1,28)),
           ((0,0),(1,4),(2,12),(0,16),(1,20),(0,24)),
           ((0,6),(1,10),(0,22),(2,26),(1,28)))
FEELS=((0,0,0),( .018,.008,.014),(.012,.004,-.016),(.024,.014,.006),(-.004,-.006,-.012))

def attack(pcm,start,length):
    """First strong syllable's half-peak; retain <=30ms soft lead +2ms roll.
    Portable 2ms RMS/0.5ms hop approximation of DialogueOnset.attack. PCM stays
    untouched and original chronological Manual cuts retain their full coverage.
    """
    hop=max(1,round(.0005*SR));window=round(.002*SR)
    end=min(start+length,start+round(.3*SR));values=[]
    for at in range(start,end,hop):
        lo=max(start,at-window//2);hi=min(start+length,at+window//2)
        values.append(math.sqrt(sum((pcm[i*2]**2+pcm[i*2+1]**2)*.5 for i in range(lo,hi,4))/max(1,len(range(lo,hi,4)))))
    if not values or max(values)<1e-6:return start,0,round(.005*SR)
    top=max(values);around=20;peak=max(range(len(values)),key=values.__getitem__)
    for k in range(1,len(values)):
        if values[k]>=top*.5 and values[k]>=max(values[max(0,k-around):k+around+1]):peak=k;break
    half=next((k for k in range(peak+1) if values[k]>=values[peak]*.5),0)
    noise=sorted(values)[len(values)//10];threshold=max(2*noise,values[peak]*.1)
    audible=0;quiet=0
    for k in range(half-1,-1,-1):
        quiet=quiet+1 if values[k]<threshold else 0
        if quiet>=30:audible=k+quiet;break
    beat=start+half*hop
    offset=max(start,start+audible*hop,beat-round(.030*SR))-round(.002*SR)
    offset=max(start,min(beat,offset))
    before=values[max(0,audible-1)];rise=max(values[audible:min(len(values),audible+11)],default=0)
    hard=rise>=max(before,noise,1e-9)*4
    return offset,beat-offset,round((.002 if hard else .005)*SR)

def vocabulary(pcm,cuts):
    """Prefer audible, dynamically articulated cuts to flat tone or silence.
    D124's lexical interest needs a transcript; this is its acoustic fallback.
    Retain source order as no semantic reorder permission can be established.
    """
    scores=[]
    for i,(start,n) in enumerate(cuts):
        hop=max(1,n//64);values=[abs(pcm[k*2])+abs(pcm[k*2+1]) for k in range(start,start+n,hop)]
        rms=math.sqrt(sum(v*v for v in values)/max(1,len(values)))
        motion=sum(abs(a-b) for a,b in zip(values,values[1:]))/max(1,len(values))
        scores.append((min(rms,.4)+min(motion,.4),i))
    count=min(8,len(cuts));selected=[]
    for group in range(count):
        lo=group*len(cuts)//count;hi=(group+1)*len(cuts)//count
        selected.append(max(scores[lo:hi],key=lambda pair:(pair[0],-pair[1]))[1])
    return selected

def drum_grid(pcm,bpm):
    """Measured energy attacks on each take's sixteenth grid, plus activity.
    No kick/snare classifier is claimed. Quarter anchors use measured timing;
    offbeat feel is added separately and stays consistent across this take.
    """
    hop=round(.005*SR);frames=len(pcm)//2
    energy=[sum((pcm[k*2]**2+pcm[k*2+1]**2)*.5 for k in range(a,min(frames,a+hop),16))/max(1,len(range(a,min(frames,a+hop),16))) for a in range(0,frames,hop)]
    if not energy:return [s*.25*60/bpm for s in range(256)],[0]*256
    novelty=[max(0,v-(energy[i-1] if i else 0)) for i,v in enumerate(energy)]
    peak=max(novelty,default=0);times=[];activity=[];step=.25*60/bpm
    source_beat=frames/SR/64;stretch=(60/bpm)/source_beat
    for s in range(256):
        expected=s*.25*source_beat;lo=max(0,round((expected-.04*source_beat)*SR/hop));hi=min(len(energy),round((expected+(.06 if s%2==0 else .19)*source_beat)*SR/hop)+1)
        best=max(range(lo,hi),key=novelty.__getitem__) if hi>lo else min(len(energy)-1,lo)
        active=novelty[best]>max(1e-8,peak*.12)
        at=best*hop/SR*stretch if active else s*step
        # Strict order and bounded assignment even for a busy/noisy take.
        times.append(max(times[-1]+.001 if times else 0,at));activity.append(novelty[best]/max(peak,1e-9) if active else 0)
    return times,activity

def plan(pcm,cuts,drums,bpm,revision,seed=1042):
    """(step, sample slot, gate steps, accent seconds), 16-bar seeded arc.
    Hook skeleton holds two takes; fills and feel evolve each take. At most
    six hits/bar, three consecutive sixteenths, one empty beat per groove bar.
    No consecutive repeated piece outside explicit build stutters.
    """
    if not cuts:return [],[],[]
    selected=vocabulary(pcm,cuts);rng=random.Random(seed+revision*617)
    times,activity=drum_grid(drums,bpm);feel=FEELS[(seed+revision)%len(FEELS)]
    template=TEMPLATES[(seed+revision//2)%len(TEMPLATES)];count=len(selected)
    signature=0;response=min(1,count-1);third=min(2,count-1)
    hits={0:(signature,None),24:(response,2)} # intro statement and tag
    # Repeating two-bar hook, filled against the real take's energy attacks.
    for base in (32,64,96):
        cell={base+s:((signature,response,third)[role],2 if role!=1 else 4) for role,s in template}
        for bar in (base,base+16):
            def fits(s):
                on=set(cell)|{s};run=0
                for k in range(bar,bar+16):
                    run=run+1 if k in on else 0
                    if run>3:return False
                return any(all(k not in on for k in range(a,a+4)) for a in range(bar,bar+13))
            candidates=list(range(bar,bar+16,2))+[bar+15];rng.shuffle(candidates)
            candidates.sort(key=lambda s:activity[s]+(.25 if s%2 else 0))
            for s in candidates:
                if sum(bar<=k<bar+16 for k in cell)>=6:break
                if s not in cell and fits(s):cell[s]=(rng.randrange(count),1 if s%2 else 2)
        hits.update(cell)
    # Build (bars7–8), then sparse breakdown (9–12), return/outro (13–16).
    for s in range(112,127,2):hits[s]=(rng.randrange(count),1)
    for s in (128,152,168,172,180):hits[s]=(rng.randrange(count),4)
    for s in (192,208,216,224,232,240,248,252):hits[s]=(rng.randrange(count),2)
    result=[];previous=None;bar=-1;heard=set();last_order=-1
    for s,(piece,gate) in sorted(hits.items()):
        if piece==previous and count>1:piece=(piece+1+rng.randrange(count-1))%count
        if s//16!=bar:bar=s//16;heard=set();last_order=-1
        # Without a transcript, new pieces run in source order into each
        # signature. Repeated pieces are stutters, not reordered new words.
        if piece!=signature and piece not in heard and piece<last_order:
            choices=[p for p in range(count) if p!=previous and (p in heard or p>=last_order)]
            if not choices:continue
            piece=rng.choice(choices)
        if piece not in heard:last_order=piece;heard.add(piece)
        if piece==signature:heard=set();last_order=-1
        previous=piece
        offset=0 if s%4==0 or not 32<=s<128 else feel[s%4-1]
        result.append((s,piece,gate,max(0,times[s]+offset)))
    return result,selected,times
