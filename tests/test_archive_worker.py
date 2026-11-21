import array
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archive_worker import ArchiveWorker,source_for,chops,SR,MAX_SOURCE
from sampler import Sampler,Event
from standalone import Instrument

class ArchiveTests(unittest.TestCase):
    def document(self):
        return dict(metadata=dict(collection='prelinger',licenseurl='http://creativecommons.org/licenses/publicdomain/',title='Narration'),files=[dict(name='film.mp3',size=2000,length='1:30')])
    def test_rights_and_size(self):
        d=self.document();self.assertEqual(source_for(d)[0]['name'],'film.mp3')
        for field,value in [('collection','other'),('licenseurl','Copyright')]:
            bad=self.document();bad['metadata'][field]=value
            with self.assertRaises(ValueError):source_for(bad)
        d['files'][0]['size']=MAX_SOURCE+1
        with self.assertRaises(ValueError):source_for(d)
    def test_energy_chops_bounded_and_silence_rejected(self):
        pcm=array.array('f',[.1,-.1])*SR*2
        cuts=chops(pcm);self.assertEqual(len(cuts),8)
        self.assertTrue(all(0<=s<s+n<=len(pcm)//2 for s,n in cuts))
        with self.assertRaises(ValueError):chops(array.array('f',[0])*SR*4)
    def test_download_decode_cache_and_failure_retention(self):
        def fetch(url,limit):
            if 'advancedsearch' in url:return json.dumps({'response':{'docs':[{'identifier':'film'}]}}).encode()
            if '/metadata/' in url:return json.dumps(self.document()).encode()
            return b'compressed'
        with tempfile.TemporaryDirectory() as t:
            w=ArchiveWorker(t,fetcher=fetch)
            def decode(source,start,target):
                self.assertEqual(source.read_bytes(),b'compressed')
                pcm=array.array('f',[.1,-.1])*SR*2;target.write_bytes(pcm.tobytes());return pcm
            w.decode=decode;self.assertTrue(w.request());w.thread.join(3);result=w.poll()
            self.assertIsNotNone(result);self.assertEqual(w.state,'READY');self.assertFalse((Path(t)/'archive-cache/source.tmp').exists())
            self.assertTrue(list((Path(t)/'archive-cache').glob('window-*.f32')))
            w.fetcher=lambda *_:(_ for _ in ()).throw(OSError('offline'))
            w.request();w.thread.join(3);self.assertIn('ERROR',w.state);self.assertIsNone(w.poll());self.assertTrue(list((Path(t)/'archive-cache').glob('window-*.f32')));w.close()
            cached=ArchiveWorker(t,fetcher=lambda *_:self.fail('cache restore must work offline'));cached.request();cached.thread.join(3)
            self.assertEqual(cached.state,'CACHED READY');self.assertEqual(cached.poll()['credit']['sha256'],result['credit']['sha256']);cached.close()
    def test_close_prevents_late_decoder_spawn(self):
        with tempfile.TemporaryDirectory() as t:
            worker=ArchiveWorker(t);worker.close()
            with patch('archive_worker.subprocess.Popen') as spawn:
                with self.assertRaises(RuntimeError):worker.decode(Path(t)/'source',0,Path(t)/'target')
                spawn.assert_not_called()
    def test_single_worker_and_unconsumed_result_bound(self):
        w=ArchiveWorker('/tmp/unused');w.results.put({});self.assertFalse(w.request());w.close()
    def test_manual_source_offset_changes_pcm(self):
        def rendered(offset):
            s=Sampler(ROOT/'.build/engine.so')
            try:
                pcm=array.array('f',[0,0])*1000+array.array('f',[.2,-.2])*1000
                slot=s.install(dict(revision=0,length=640,pcm=[pcm],events=[]));s.render(1);s.command(3,4,1)
                self.assertTrue(s.command(7,slot,0,identity=1,event=Event(frame=offset,channel=4,sample=192+slot*16,gate=300,speed=1,gain=.5,attack=8,release=32)))
                return max(map(abs,s.render(200)))
            finally:s.close()
        self.assertEqual(rendered(0),0);self.assertGreater(rendered(1100),.0005)
    def test_manual_cut_never_reads_after_edited_end(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            pcm=array.array('f',[0,0])*500+array.array('f',[.8,-.8])*1000
            slot=s.install(dict(revision=0,length=640,pcm=[pcm],events=[]));s.render(1);s.command(3,4,1)
            s.command(7,slot,0,identity=1,event=Event(frame=250,channel=4,sample=192+slot*16,gate=250,speed=1,gain=.5,attack=8,release=256))
            self.assertEqual(max(map(abs,s.render(1000))),0)
        finally:s.close()
    def test_edit_controls_and_source_retention(self):
        ui=Instrument.__new__(Instrument);ui.settings=False;ui.selected=4;ui.shift=False;ui.mix=False;ui.chop=0;ui.edits={};ui.archive=None
        ui.engine=type('Engine',(),{'banks':{0:(None,dict(revision=1,archive_id='same',line_index=0,pcm=[[],array.array('f',[.1,.1])*SR*5],cuts=[(0,SR)]*8))}})();ui.last_bank=0
        ui.event(dict(kind='cc',number=76,value=1));self.assertEqual(ui.cut(ui.current,0),(round(SR*.05),SR))
        ui.shift=True;ui.event(dict(kind='cc',number=77,value=1));self.assertEqual(ui.cut(ui.current,0)[1],SR+round(SR*.005))
        ui.event(dict(kind='cc',number=78,value=1));self.assertEqual(ui.chop,1)
        bank=dict(ui.current,revision=9);self.assertEqual(ui.cut(bank,0),ui.cut(ui.current,0))
        ui.archive_worker=type('Worker',(),{'request':lambda _:setattr(ui,'requested',True)})();ui.event(dict(kind='cc',number=56,value=127));self.assertTrue(ui.requested)
