"""Bounded keyless Cleveland worker; decode/network never run on audio/UI thread."""
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import random
import subprocess
import threading
import urllib.parse
import urllib.request
API='https://openaccess-api.clevelandart.org/api/artworks/'
def fetch(url,limit):
    if not url.startswith('https://'):raise ValueError('HTTPS required')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Liminal/1.0'}),timeout=5) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('image download limit')
    return data

def credit_for(record):
    if record.get('share_license_status')!='CC0':raise ValueError('Cleveland CC0 required')
    image=record['images']['print']['url']
    if not image.startswith('https://'):raise ValueError('HTTPS image required')
    return dict(provider='Cleveland Museum of Art',rights='CC0',title=record['title'],page=record['url'],image=image,id=record['id'])
def pack_rgb(data):
    if len(data)!=960*160*3:raise ValueError('decoded image dimensions')
    packed=bytearray(327680)
    for y in range(160):
        for x in range(960):
            at=(y*960+x)*3;r,g,b=data[at:at+3];v=((b>>3)<<11)|((g>>2)<<5)|(r>>3);off=(y*1024+x)*2;packed[off]=v&255;packed[off+1]=v>>8
    return bytes(packed)
class ImageWorker:
    def __init__(self,home,fetcher=fetch,decoder=None):
        self.home=Path(home);self.fetcher=fetcher;self.decoder=decoder;self.results=queue.Queue(maxsize=1);self.error='';self.closed=threading.Event();self.thread=None;self.process=None
    def request(self):
        if self.closed.is_set() or (self.thread and self.thread.is_alive()):return
        self.thread=threading.Thread(target=self._run,name='image-api',daemon=True);self.thread.start()
    def _run(self):
        try:
            query=API+'?'+urllib.parse.urlencode(dict(has_image=1,cc0=1,limit=1,q=random.choice(('landscape','river','night','garden')),skip=random.randint(0,20)))
            records=json.loads(self.fetcher(query,2000000))['data']
            if not records:raise ValueError('No CC0 image result')
            credit=credit_for(records[0]);source=self.fetcher(credit['image'],12000000)
            if self.closed.is_set():return
            if self.decoder:data=self.decoder(source)
            else:
                tool=self.home/'tools/ffmpeg';cmd=[str(tool)]
                loader=Path('/lib/ld-linux-x86-64.so.2')
                if platform.machine()=='x86_64' and loader.exists():cmd=[str(loader),str(tool)]
                self.process=subprocess.Popen(cmd+['-v','error','-threads','1','-i','pipe:0','-vf','scale=960:160:force_original_aspect_ratio=increase,crop=960:160','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:data,_=self.process.communicate(source,timeout=5)
                except subprocess.TimeoutExpired:self.process.kill();self.process.communicate();raise ValueError('Image decode timeout')
                if self.process.returncode:raise ValueError('Image decode failed')
            packed=pack_rgb(data);credit.update(sha256=hashlib.sha256(packed).hexdigest(),api=query)
            if self.closed.is_set():return
            cache=self.home/'image-cache';cache.mkdir(parents=True,exist_ok=True)
            # A bounded six-slot rotating cache, independent from bundled offline originals.
            slot=int(records[0]['id'])%6;target=cache/('image-%d.bin'%slot);tmp=target.with_suffix('.tmp');tmp.write_bytes(packed);os.replace(tmp,target)
            credit['file']=target.name;meta=target.with_suffix('.json');temp=meta.with_suffix('.tmp');temp.write_text(json.dumps(credit));os.replace(temp,meta)
            try:self.results.put_nowait((packed,credit))
            except queue.Full:pass
            self.error=''
        except Exception as e:self.error=str(e)[:100]
    def poll(self):
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        self.closed.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill()
