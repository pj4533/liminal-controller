#!/usr/bin/env python3
"""Explicit bounded offline cache preparation from approved source providers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

def fetch(url,limit=16000000):
    if not url.startswith('https://'):raise ValueError('HTTPS required')
    request=urllib.request.Request(url,headers={'User-Agent':'Liminal/1.0'})
    with urllib.request.urlopen(request,timeout=30) as r:
        data=r.read(limit+1)
        if len(data)>limit:raise ValueError('bounded preparation download exceeded')
    return data

def image_record(record):
    if record.get('share_license_status')!='CC0':raise ValueError('Cleveland CC0 record required')
    image=record['images']['print']['url']
    if not image.startswith('https://'):raise ValueError('HTTPS image required')
    return dict(provider='Cleveland Museum of Art',title=record['title'],rights='CC0',page=record['url'],image=image,creators=record.get('creators',[]),id=record['id'])
def pack_image(data):
    from PIL import Image,ImageOps
    import io
    image=ImageOps.fit(Image.open(io.BytesIO(data)).convert('RGB'),(960,160));packed=bytearray(327680)
    for y in range(160):
        for x in range(960):
            r,g,b=image.getpixel((x,y));v=((b>>3)<<11)|((g>>2)<<5)|(r>>3);off=(y*1024+x)*2;packed[off]=v&255;packed[off+1]=v>>8
    return packed

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--seeds',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    query='https://openaccess-api.clevelandart.org/api/artworks/?'+urllib.parse.urlencode(dict(has_image=1,cc0=1,limit=3,q='landscape'))
    records=json.loads(fetch(query))['data'];credits=[]
    for index,record in enumerate(records):
        credit=image_record(record);data=fetch(credit['image']);packed=pack_image(data);name='image-%d.bin'%index
        (a.out/name).write_bytes(packed);credit.update(file=name,sha256=hashlib.sha256(packed).hexdigest(),api=query);credits.append(credit)
    (a.out/'images.json').write_text(json.dumps(credits,indent=2))
    # Source seed, validated by current IA metadata; retain source and clip boundaries.
    seeds=json.loads(a.seeds.read_text())['seeds'];errors=[]
    for seed in seeds[:8]:
        try:
            time.sleep(2);url='https://archive.org/metadata/'+urllib.parse.quote(seed['id']);metadata=json.loads(fetch(url,4000000));m=metadata['metadata']
            collections=m.get('collection',[]);collections=[collections] if isinstance(collections,str) else collections
            if 'prelinger' not in collections:raise ValueError('not Prelinger')
            files=[f for f in metadata['files'] if f['name'].lower().endswith(('.mp4','.ogv')) and f.get('size') and int(f['size'])<16000000]
            files.sort(key=lambda f:int(f['size']))
            if not files:raise ValueError('no bounded source file')
            f=files[0];download='https://archive.org/download/'+urllib.parse.quote(seed['id'])+'/'+urllib.parse.quote(f['name'])
            time.sleep(2);movie=fetch(download);cache=a.out/'film-source.tmp';cache.write_bytes(movie)
            subprocess.run(['ffmpeg','-v','error','-y','-ss','5','-i',str(cache),'-t','48','-vn','-ac','2','-ar','44100','-af','highpass=f=180,lowpass=f=4600,afade=t=in:d=0.1,afade=t=out:st=47.7:d=0.3','-c:a','pcm_s16le',str(a.out/'film.wav')],check=True,timeout=90)
            cache.unlink();credit=dict(identifier=seed['id'],title=m.get('title'),collection=collections,license=m.get('licenseurl'),page='https://archive.org/details/'+seed['id'],metadata=url,download=download,original_file=f['name'],original_sha256=hashlib.sha256(movie).hexdigest(),start_seconds=5,duration_seconds=48,policy='Liminal curated Prelinger seed; acoustic fallback chops, no transcription',sha256=hashlib.sha256((a.out/'film.wav').read_bytes()).hexdigest())
            (a.out/'film.json').write_text(json.dumps(credit,indent=2));print(json.dumps(dict(images=len(credits),film=seed['id'])));break
        except Exception as e:errors.append(seed['id']+': '+str(e))
    else:raise RuntimeError('No film cached: '+'; '.join(errors))
if __name__=='__main__':main()
