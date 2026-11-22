#!/usr/bin/env python3
"""Real-source offline release gate. No hardware/network and no synthetic cuts.

Case JSON: list of {pcm, credit, dtw, sha256, revisions}. Paths are operator
supplied private files. PCM must be stereo44.1k float32, matching its credited
hash; DTW must be captured from the paired real source, not fabricated timing.
"""
import argparse,array,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,SR
from composition import Instruments,prepare
from dialogue_speech import parse
from dialogue_text import Selector
from standalone import Instrument,slice_note
from standalone_render import Background,render,write_ppm
from channel_fx import defaults

def qualify(bank,engine,out=None):
    """Require the production-prepared bank to become CURRENT before dispatch."""
    slot=engine.install(bank);assert slot is not None
    engine.command(17,slot);engine.render(2048)
    assert engine.status()['bank']==slot,'Actual text bank must be CURRENT'
    ui=Instrument.__new__(Instrument);ui.engine=engine;ui.last_bank=slot;ui.selected=4
    ui.held={};ui.manual=[False]*6;ui.shift=False;ui.chop=0;ui.identity=0
    ui.edits={};ui.edit_gains={};ui.error=''
    cuts=bank['cuts'];whole=cuts[0]
    assert bank.get('dialogue') and bank['dialogue']['quality']=='TEXT'
    assert 3<=len(cuts)<=8 and len(set(cuts))==len(cuts),'Multiword release sources need >=3 unique cuts'
    assert sum(n<whole[1]*.85 for _,n in cuts[1:])>=2,'Need meaningful shorter fragments'
    assert all(whole[0]<=s<s+n<=whole[0]+whole[1] for s,n in cuts)
    used=[slice_note(i) for i in range(len(cuts))]
    assert [n for n,v in ui.leds().items() if v]==sorted(used)
    captures=[]
    for i,(start,length) in enumerate(cuts):
        engine.command(2);engine.render(2048)
        ui.event(dict(kind='note',number=used[i],value=100))
        audio=engine.render(length+512)
        rms=math.sqrt(sum(v*v for v in audio)/len(audio));assert rms>1e-5,(i,rms)
        assert all(math.isfinite(v) and abs(v)<1 for v in audio)
        ui.event(dict(kind='note_off',number=used[i],value=0));engine.render(2048)
        assert engine.status()['voices']==0
        source=bank['pcm'][1][start*2:(start+length)*2]
        captures.append(dict(pad=used[i],label=bank['dialogue']['labels'][i],start=start,length=length,rms=rms,
                             pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),audio_sha256=hashlib.sha256(bytes(audio)).hexdigest()))
    assert len({c['pcm_sha256'] for c in captures})==len(cuts)
    for note in range(36,100):
        if note in used:continue
        ui.event(dict(kind='note',number=note,value=100));engine.render(32)
        assert engine.status()['voices']==0 and not ui.leds()[note]
    # Actual simultaneous onsets and onset-owned release, no injected ranges.
    ui.event(dict(kind='note',number=used[0],value=100));ui.event(dict(kind='note',number=used[1],value=100));engine.render(32)
    assert engine.status()['voices']==2
    ui.selected=0;ui.event(dict(kind='note_off',number=used[0],value=0));engine.render(300)
    # The other shorter cut may naturally end; its ownership is still retained.
    assert used[1] in ui.held
    ui.event(dict(kind='note_off',number=used[1],value=0));engine.command(2);engine.render(2048);ui.selected=4
    for ch in range(6):engine.command(3,ch,int(ch!=4))
    events=[e for e in bank['events'] if e['channel']==4]
    assert len({e['pad'] for e in events if e['pad']>1})>=2,'Auto must actually use short fragments'
    for event in events:
        index=event['pad']-1;start,length=cuts[index]
        assert bank['pcm'][-event['sample']-1]==bank['pcm'][1][start*2:(start+length)*2], 'Auto/Manual PCM mismatch'
    engine.command(1);position=0;flashed=set()
    for event in events:
        target=event['frame']+1
        while position<target:
            frames=min(4096,target-position);engine.render(frames);position+=frames
        feedback=engine.feedback(4)
        assert feedback==(bank['revision'],event['pad']),(feedback,event)
        assert ui.leds()[slice_note(event['pad']-1)]==5
        flashed.add(event['pad'])
    engine.command(2);engine.render(2048)
    return dict(revision=bank['revision'],current_bank=slot,ready=True,cut_count=len(cuts),cuts=captures,
                line=bank['dialogue']['line'],auto_pads=sorted(flashed),unused_pads_dark_silent=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--tagger',type=Path,required=True);p.add_argument('--engine',type=Path,default=ROOT/'.build/engine.so');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();cases=json.loads(a.cases.read_text());assert any(c['sha256']=='84777432b5f6c5d52d4599cc5c6e6c552f2eae1af6a70b1475ba2c19d3073671' and set((0,4,8,10))<=set(c['revisions']) for c in cases),'Release gate must include exact failing GuideDog source/all rotations';assert len(cases)>=2,'Need failing source and independent archive source'
    a.out.mkdir(parents=True,exist_ok=True);selector=Selector(a.tagger);reports=[]
    catalog=json.loads((a.assets/'drums.json').read_text());engine=Sampler(a.engine)
    try:
        instruments=Instruments(a.assets/'instruments',engine)
        for case in cases:
            pcm=array.array('f');pcm.frombytes(Path(case['pcm']).read_bytes());sha=hashlib.sha256(pcm.tobytes()).hexdigest()
            credit=json.loads(Path(case['credit']).read_text());assert sha==case['sha256']==credit['sha256']
            transcript=parse(json.loads(Path(case['dtw']).read_text()),min(30,len(pcm)/2/SR))
            class Replay:
                def select(self,film,revision):
                    assert film is pcm
                    return selector.select(film,transcript,revision)
            for revision in case['revisions']:
                bank=prepare(instruments,a.assets,catalog,revision,94,archive=dict(pcm=pcm,credit=credit,cuts=credit.get('cuts',[])),speech=Replay())
                report=qualify(bank,engine);report.update(source_sha256=sha,dtw_sha256=hashlib.sha256(Path(case['dtw']).read_bytes()).hexdigest(),identifier=credit['identifier'])
                reports.append(report)
        (a.out/'acceptance.json').write_text(json.dumps(dict(passed=True,cases=reports,engine_sha256=hashlib.sha256(a.engine.read_bytes()).hexdigest(),inference='real cached DTW replay; not fresh inference or physical listening'),indent=2)+'\n')
        print(json.dumps(dict(passed=len(reports),cuts=[r['cut_count'] for r in reports])))
    finally:engine.close()
if __name__=='__main__':main()
