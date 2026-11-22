"""Bounded offline whisper.cpp worker; no render-thread inference or network.
DTW lexical centers (10ms) are not token offsets or calibrated confidence.
"""
import array
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time
import threading
import wave
from sampler import SR

MODEL_SHA='a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002'
TAGGER_SHA='6025f530624335c67d6547d44757b357b4e79bae030a0383e9887a92c1718f0b'
BINARY_SHA='bee176f0edafd2cc2c563cb8d73c611bcffb8dfe7af40465ea8c2c6e25fe51ab'
OPTIONS='base.en-v1.9.5-greedy-t1-nfa-dtw-v1'

def parse(document,seconds):
    """Join lexical subwords/contractions; infer edges between word centers.
    Reject malformed segments instead of inventing precision. Punctuation has
    no independent alignment and stays attached to the preceding word.
    """
    lines=[];last=0
    if len(document.get('transcription',[]))>256:raise ValueError('Speech segment limit')
    for seg in document.get('transcription',[]):
        lo=seg['offsets']['from']/1000;hi=seg['offsets']['to']/1000
        if not (math.isfinite(lo) and math.isfinite(hi) and last<=lo<hi<=seconds+.02):continue
        groups=[];valid=True;previous=-1
        if len(seg.get('tokens',[]))>4096:continue
        for token in seg.get('tokens',[]):
            text=token['text']
            if not text or '[' in text or '<|' in text:continue
            if not any(c.isalnum() for c in text):
                if groups:groups[-1]['text']+=text.strip()
                continue
            center=token.get('t_dtw',-1)*.01
            if not math.isfinite(center) or not lo<=center<=hi or center<previous:
                valid=False;break
            previous=center
            if text[0].isspace() or not groups:groups.append(dict(text=text.strip(),centers=[center]))
            else:groups[-1]['text']+=text;groups[-1]['centers'].append(center)
        if not valid or not groups:continue
        centers=[sum(g['centers'])/len(g['centers']) for g in groups]
        if any(b<=a for a,b in zip(centers,centers[1:])):continue
        bounds=[lo]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[hi]
        if any(not .04<=b-a<=2 for a,b in zip(bounds,bounds[1:])) or len(groups)/(hi-lo)>7:continue
        words=[dict(text=g['text'],start=a,end=b,confidence=None) for g,a,b in zip(groups,bounds,bounds[1:])]
        normalized=[w['text'].lower() for w in words]
        grams=[tuple(normalized[i:i+3]) for i in range(len(words)-2)]
        if any(grams.count(g)>=3 for g in grams):continue
        lines.append(dict(start=lo,end=hi,text=' '.join(g['text'] for g in groups),words=words));last=hi
    normalized=[w['text'].lower() for line in lines for w in line['words']]
    grams=[tuple(normalized[i:i+3]) for i in range(len(normalized)-2)]
    repeated={g for g in grams if grams.count(g)>=3}
    if repeated:
        lines=[line for line in lines if not any(tuple([w['text'].lower() for w in line['words']][i:i+3]) in repeated for i in range(len(line['words'])-2))]
    if not lines:raise ValueError('No reliable aligned speech; keeping current bank')
    return dict(locale='en-US',modelVersion=OPTIONS,lines=lines)

class Speech:
    def __init__(self,home,tools=None,timeout=35):
        self.home=Path(home);self.tools=Path(tools or Path(__file__).resolve().parents[1]/'tools')
        self.timeout=timeout;self.lock=threading.Lock();self.closed=threading.Event();self.process=None;self.state='PENDING';self.error='';self.checked=False;self.failed={};self.selector=None;self.metrics={}
    def verify(self):
        if self.checked:return
        if platform.machine()!='x86_64':raise RuntimeError('Speech requires packaged x86_64 worker')
        for name,expected in (('whisper-cli',BINARY_SHA),('ggml-base.en.bin',MODEL_SHA),('averaged_perceptron_tagger_eng.zip',TAGGER_SHA)):
            h=hashlib.sha256()
            with (self.tools/name).open('rb') as stream:
                for block in iter(lambda:stream.read(1048576),b''):h.update(block)
            if h.hexdigest()!=expected:raise ValueError('Speech artifact hash '+name)
        self.checked=True
    def transcript(self,pcm):
        data=pcm[:30*SR*2].tobytes();key=hashlib.sha256(data+OPTIONS.encode()+MODEL_SHA.encode()).hexdigest()
        cache=self.home/'speech-cache';cache.mkdir(parents=True,exist_ok=True);target=cache/(key+'.json')
        # One preparation owner; close interrupts the only subprocess.
        if self.closed.is_set():raise RuntimeError('Speech closed')
        if key in self.failed:raise ValueError(self.failed[key])
        self.state='ANALYZING';self.error='';self.metrics=dict(cache_hit=False,audio_seconds=len(data)/(SR*8),threads=1)
        try:
            self.verify()
            if target.exists():
                doc=json.loads(target.read_text());result=parse(doc,len(data)/(SR*8));self.metrics['cache_hit']=True;self.state='TEXT READY';return result
            with tempfile.TemporaryDirectory(prefix='speech-',dir=cache) as tmp:
                audio=Path(tmp)/'source.wav';out=Path(tmp)/'result'
                # Linear 44.1k stereo ->16k mono. No decoder/pip dependency.
                source=array.array('f');source.frombytes(data);frames=len(source)//2;mono=array.array('h')
                for k in range(int(frames*16000/SR)):
                    pos=k*SR/16000;a=int(pos);b=min(frames-1,a+1);f=pos-a
                    v=((source[a*2]+source[a*2+1])*(1-f)+(source[b*2]+source[b*2+1])*f)*.5
                    mono.append(round(max(-1,min(1,v))*32767))
                with wave.open(str(audio),'wb') as stream:stream.setparams((1,2,16000,0,'NONE','not compressed'));stream.writeframes(mono.tobytes())
                cmd=[str(self.tools/'whisper-cli')];loader=Path('/lib/ld-linux-x86-64.so.2')
                if loader.exists():cmd=[str(loader)]+cmd
                cmd+=['-ng','-t','1','-l','en','-bs','1','-bo','1','-nf','-nfa','-m',str(self.tools/'ggml-base.en.bin'),'-f',str(audio),'-dtw','base.en','-ojf','-of',str(out)]
                if shutil.which('taskset') and hasattr(os,'sched_getaffinity'):
                    cmd=['taskset','-c',str(max(os.sched_getaffinity(0)))]+cmd
                if shutil.which('nice'):cmd=['nice','-n','15']+cmd
                with self.lock:
                    if self.closed.is_set():raise RuntimeError('Speech closed')
                    started=time.monotonic()
                    self.process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    process=self.process
                try:
                    code=process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait();raise TimeoutError('Speech deadline; keeping current bank')
                finally:
                    with self.lock:self.process=None
                self.metrics.update(worker_seconds=time.monotonic()-started,exit_code=code)
                if code or self.closed.is_set():raise RuntimeError('Speech unavailable; keeping current bank')
                output=out.with_suffix('.json')
                if output.stat().st_size>4*1024*1024:raise ValueError('Speech output limit')
                document=json.loads(output.read_text());result=parse(document,frames/SR)
                temp=target.with_suffix('.tmp');temp.write_text(json.dumps(document));os.replace(temp,target)
                # Bounded cache retains latest32 sources; failures not retried every phrase.
                for old in sorted(cache.glob('*.json'),key=lambda p:p.stat().st_mtime)[:-32]:old.unlink()
                self.state='TEXT READY';return result
        except Exception as e:
            self.state='UNAVAILABLE';self.error=str(e)[:100];self.failed[key]=self.error
            if len(self.failed)>32:self.failed.pop(next(iter(self.failed)))
            raise
    def select(self,pcm,revision):
        from dialogue_text import Selector
        transcript=self.transcript(pcm)
        if self.selector is None:self.selector=Selector(self.tools/'averaged_perceptron_tagger_eng.zip')
        try:return self.selector.select(pcm,transcript,revision)
        except Exception as e:self.state='UNAVAILABLE';self.error=str(e)[:100];raise
    def close(self):
        self.closed.set()
        with self.lock:
            if self.process and self.process.poll() is None:self.process.kill();self.process.wait()
