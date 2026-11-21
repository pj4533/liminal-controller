"""Serial keyless IA worker. Network/decode/cache never touch the render path."""
import array
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import random
import subprocess
import threading
import time
import urllib.parse
import urllib.request

SR=44100
SECONDS=48
MAX_SOURCE=24*1024*1024
PD=('/licenses/publicdomain','/publicdomain/zero/1.0','/publicdomain/mark/1.0')

def source_for(document):
    m=document['metadata'];collections=m.get('collection',[])
    if isinstance(collections,str):collections=[collections]
    license=str(m.get('licenseurl',''))
    rights=urllib.parse.urlsplit(license)
    if 'prelinger' not in collections or rights.scheme not in ('http','https') or rights.netloc!='creativecommons.org' or rights.path.rstrip('/') not in PD:raise ValueError('Public-domain Prelinger rights required')
    if str(m.get('sound','')).lower() in ('silent','si'):raise ValueError('Silent film')
    files=[f for f in document['files'] if f['name'].lower().endswith(('.mp3','.mp4','.ogv')) and 0<int(f.get('size',0))<=MAX_SOURCE]
    if not files:raise ValueError('No bounded audio source')
    f=min(files,key=lambda f:(not f['name'].lower().endswith('.mp3'),int(f['size'])))
    return f,m

def chops(pcm):
    """Energy/silence anchored starting suggestions; no speech recognition claim."""
    frames=len(pcm)//2;hop=SR//20
    energy=[sum(v*v for v in pcm[i*2:min(frames,i+hop)*2])/max(1,min(hop,frames-i)*2) for i in range(0,frames,hop)]
    if not energy or max(energy)<1e-7:raise ValueError('Silent archive window')
    threshold=max(1e-6,max(energy)*.025);onsets=[i*hop for i,e in enumerate(energy) if e>threshold and (i==0 or energy[i-1]<=threshold)]
    result=[]
    for i in range(8):
        target=round(i*frames/8);start=min(onsets,key=lambda p:abs(p-target)) if onsets else target
        # Keep suggestions spread out even when a film has continuous narration.
        if abs(start-target)>SR*2:start=target
        start=min(start,max(0,frames-SR//10))
        end=next((j*hop for j in range(start//hop+4,len(energy)) if energy[j]<=threshold),min(frames,start+SR*2))
        result.append((start,max(SR//10,min(SR*4,end-start,frames-start))))
    return result

class ArchiveWorker:
    def __init__(self,home,fetcher=None):
        self.home=Path(home);self.fetcher=fetcher;self.results=queue.Queue(maxsize=1)
        self.closed=threading.Event();self.thread=None;self.process=None;self.state='CACHED';self.error='';self.credit={};self.last_request=0;self.seen=[];self.serial=0;self.restored=False
    def fetch(self,url,limit):
        if not url.startswith('https://archive.org/'):raise ValueError('IA HTTPS required')
        if self.fetcher:return self.fetcher(url,limit)
        if self.closed.wait(max(0,2-(time.monotonic()-self.last_request))):raise RuntimeError('Closed')
        self.last_request=time.monotonic()
        request=urllib.request.Request(url,headers={'User-Agent':'Liminal/1.0'})
        with urllib.request.urlopen(request,timeout=15) as response:
            if not response.geturl().startswith('https://'):raise ValueError('HTTPS redirect required')
            data=bytearray();deadline=time.monotonic()+90
            while True:
                if self.closed.is_set() or time.monotonic()>deadline:raise TimeoutError('Archive download deadline')
                part=response.read(min(131072,limit+1-len(data)))
                if not part:break
                data.extend(part)
                if len(data)>limit:raise ValueError('Archive download limit')
        return data
    def request(self):
        if self.closed.is_set() or (self.thread and self.thread.is_alive()) or not self.results.empty():return False
        self.state='LOADING';self.error=''
        self.thread=threading.Thread(target=self._run,name='archive-source',daemon=True);self.thread.start();return True
    def decode(self,path,start,target):
        cmd=[str(self.home/'tools/ffmpeg')];loader=Path('/lib/ld-linux-x86-64.so.2')
        if platform.machine()=='x86_64' and loader.exists():cmd=[str(loader)]+cmd
        args=cmd+['-v','error','-nostdin','-y','-threads','1','-ss',str(start),'-i',str(path),'-t',str(SECONDS),'-vn','-ac','2','-ar',str(SR),'-af','highpass=f=180,lowpass=f=4600','-f','f32le',str(target)]
        self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:code=self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait();raise ValueError('Archive decode timeout')
        if code:raise ValueError('Archive decode failed')
        if not 2*SR*4<=target.stat().st_size<=SECONDS*SR*2*4:raise ValueError('Archive decoded size')
        pcm=array.array('f');pcm.frombytes(target.read_bytes())
        if not all(math.isfinite(v) and abs(v)<8 for v in pcm):raise ValueError('Invalid decoded PCM')
        return pcm
    def _run(self):
        cache=self.home/'archive-cache';cache.mkdir(parents=True,exist_ok=True);source=cache/'source.tmp';decoded=cache/'decode.tmp'
        try:
            if not self.restored:
                self.restored=True
                candidates=sorted(cache.glob('window-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
                for meta in candidates:
                    try:
                        credit=json.loads(meta.read_text());path=meta.with_suffix('.f32')
                        if not 2*SR*4<=path.stat().st_size<=SECONDS*SR*2*4:continue
                        data=path.read_bytes()
                        if hashlib.sha256(data).hexdigest()!=credit['sha256']:continue
                        pcm=array.array('f');pcm.frombytes(data);cuts=chops(pcm)
                        self.results.put_nowait(dict(pcm=pcm,credit=credit,cuts=cuts));self.credit=credit;self.seen=[credit['identifier']];self.state='CACHED READY';return
                    except (OSError,ValueError,KeyError):continue
            query='collection:prelinger AND mediatype:movies AND subject:Newsreels AND (licenseurl:*publicdomain* OR licenseurl:*zero*)'
            url='https://archive.org/advancedsearch.php?'+urllib.parse.urlencode({'q':query,'fl[]':'identifier','rows':25,'page':random.randint(1,3),'output':'json'})
            documents=json.loads(self.fetch(url,2000000))['response']['docs'];random.shuffle(documents)
            errors=[];deadline=time.monotonic()+150
            for record in documents[:5]:
                if self.closed.is_set() or time.monotonic()>deadline:break
                identifier=record['identifier']
                if identifier in self.seen:continue
                try:
                    metadata_url='https://archive.org/metadata/'+urllib.parse.quote(identifier,safe='')
                    f,m=source_for(json.loads(self.fetch(metadata_url,4000000)))
                    download='https://archive.org/download/'+urllib.parse.quote(identifier,safe='')+'/'+urllib.parse.quote(f['name'],safe='')
                    self.state='DOWNLOADING';data=self.fetch(download,MAX_SOURCE);source.write_bytes(data);digest=hashlib.sha256(data).hexdigest();del data
                    length=f.get('length','120')
                    try:
                        parts=str(length).split(':');duration=sum(float(p)*60**i for i,p in enumerate(reversed(parts)))
                    except ValueError:duration=120
                    start=round(random.uniform(5,max(5,duration-SECONDS-1)),2)
                    self.state='DECODING';pcm=self.decode(source,start,decoded);cuts=chops(pcm)
                    credit=dict(identifier=identifier,title=str(m.get('title',identifier)),license=m.get('licenseurl'),page='https://archive.org/details/'+identifier,metadata=metadata_url,download=download,original_sha256=digest,start_seconds=start,duration_seconds=len(pcm)/2/SR,sha256=hashlib.sha256(pcm.tobytes()).hexdigest(),cuts=cuts,policy='Public-domain Prelinger; energy/silence suggestions, editable; no transcription')
                    self.serial+=1;slot=self.serial%3;target=cache/('window-%d.f32'%slot);os.replace(decoded,target)
                    meta=target.with_suffix('.json');tmp=meta.with_suffix('.tmp');tmp.write_text(json.dumps(credit));os.replace(tmp,meta)
                    self.credit=credit;self.seen=(self.seen+[identifier])[-30:];self.results.put_nowait(dict(pcm=pcm,credit=credit,cuts=cuts));self.state='READY';self.error='';return
                except Exception as e:errors.append(str(e)[:65]);self.state='LOADING'
            raise ValueError('; '.join(errors[-2:]) or 'No fresh bounded source')
        except Exception as e:self.error=str(e)[:100];self.state='ERROR - KEEPING CACHE'
        finally:
            source.unlink(missing_ok=True);decoded.unlink(missing_ok=True)
    def poll(self):
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        self.closed.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        if self.thread:self.thread.join(timeout=1)
