import array
import ctypes as C
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event,Bank
from composition import Instruments,choose_drum
from dialogue_ledger import DialogueLedger
from standalone_render import Background
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.s=Sampler(ROOT/'.build/engine.so');self.s.sample(0,array.array('f',[.2,-.2])*10000)
    def tearDown(self):self.s.close()
    def bank(self,revision=0,length=640,channel=2):
        return dict(revision=revision,length=length,pcm=[],events=[dict(frame=0,channel=channel,sample=0,gate=length*4,speed=1,gain=.5,attack=8,release=32)])
    def test_boot_silent(self):self.assertEqual(max(map(abs,self.s.render(1024))),0)
    def test_auto_audible(self):
        self.s.install(self.bank());self.s.command(1);self.assertGreater(max(map(abs,self.s.render(512))),.001)
    def test_manual_suppresses_auto_but_keeps_time(self):
        self.s.install(self.bank());self.s.command(3,2,1);self.s.command(1)
        self.assertEqual(max(map(abs,self.s.render(512))),0);self.assertEqual(self.s.status()['position'],512)
    def test_manual_audible_stopped(self):
        slot=self.s.install(self.bank());self.s.render(1);self.s.command(3,2,1);self.s.command(7,slot,identity=42,event=Event(channel=2,sample=0,gate=1000,speed=1,gain=.5,attack=8,release=32));self.assertGreater(max(map(abs,self.s.render(512))),.001)
    def test_manual_cannot_launch_in_auto(self):
        slot=self.s.install(self.bank());self.s.command(7,slot,identity=42,event=Event(channel=2,sample=0,gate=1000,speed=1,gain=.5,attack=8,release=32));self.assertEqual(max(map(abs,self.s.render(512))),0)
    def test_mute_and_master(self):
        self.s.install(self.bank(length=10000));self.s.command(1);self.s.render(1024);self.s.command(5,2,1);self.s.render(12000);self.assertLess(max(map(abs,self.s.render(512))),1e-6)
    def test_stop_hush_and_reset(self):
        self.s.install(self.bank());self.s.command(1);self.s.render(512);self.s.command(2);self.s.render(4096)
        self.assertLess(max(map(abs,self.s.render(512))),1e-6);self.assertFalse(self.s.status()['playing']);self.assertEqual(self.s.status()['position'],0)
    def test_boundary_atomic_exact(self):
        a=self.s.install(self.bank());b=self.s.install(self.bank(1));self.s.command(1);self.s.render(640)
        self.assertEqual(self.s.status()['bank'],a);self.s.render(1);self.assertEqual(self.s.status()['bank'],b);self.assertEqual(self.s.status()['position'],1)
    def test_mode_does_not_reset_bank_or_time(self):
        slot=self.s.install(self.bank());self.s.command(1);self.s.render(200);self.s.command(3,2,1);self.s.render(1)
        self.assertEqual(self.s.status()['position'],201);self.assertEqual(self.s.status()['bank'],slot)
    def test_held_identity_retains_old_bank(self):
        a=self.s.install(self.bank(length=64));self.s.render(1);self.s.command(3,2,1);self.s.command(7,a,identity=77,event=Event(channel=2,sample=0,gate=9000,speed=1,gain=.5,attack=8,release=32));b=self.s.install(self.bank(1,length=64));self.s.command(1);self.s.render(65)
        self.assertEqual(self.s.status()['bank'],b);self.assertEqual(self.s.lib.lm_state(self.s.ptr,a),2)
        self.s.command(8,identity=77);self.s.render(40);self.assertEqual(self.s.lib.lm_state(self.s.ptr,a),0)
    def test_exact_pcm_retrigger(self):
        def render_once():
            s=Sampler(ROOT/'.build/engine.so');s.sample(0,array.array('f',[.2,-.1])*1024);s.install(self.bank(channel=4));s.render(1);s.command(3,4,1);s.command(7,0,identity=9,event=Event(channel=4,sample=0,gate=900,speed=1,gain=.5,attack=8,release=32));out=bytes(s.render(1000));s.close();return out
        self.assertEqual(render_once(),render_once())
    def test_queue_bounded_rejects_new(self):
        self.assertTrue(all(self.s.command(4,2,event=Event(gain=.5)) for _ in range(1024)));self.assertFalse(self.s.command(1));self.assertEqual(self.s.status()['overflow'],1)
    def test_voice_bound_and_release(self):
        self.s.install(self.bank());self.s.render(1);self.s.command(3,2,1)
        for i in range(80):self.s.command(7,0,identity=i+1,event=Event(channel=2,sample=0,gate=9000,speed=1,gain=.1,attack=8,release=32))
        self.s.render(10);self.assertEqual(self.s.status()['voices'],64);self.assertEqual(self.s.status()['overflow'],16)
        self.s.command(9);self.s.render(40);self.assertEqual(self.s.status()['voices'],0)
    def test_invalid_bank_rejected(self):
        slot=self.s.lib.lm_reserve(self.s.ptr);b=Bank(length=640,count=1);b.events[0]=Event(frame=700,channel=2,sample=0,gate=20,speed=1,gain=.3,attack=8,release=32)
        self.assertFalse(self.s.lib.lm_bank(self.s.ptr,slot,C.byref(b)))
    def test_pending_replacement(self):
        self.s.install(self.bank());b=self.s.install(self.bank(1));self.s.render(1);c=self.s.install(self.bank(2));self.s.command(1);self.s.render(641)
        self.assertEqual(self.s.status()['bank'],c);self.assertNotEqual(b,c);self.assertEqual(self.s.lib.lm_state(self.s.ptr,b),0)
    def test_queued_onset_pins_bank_and_stale_revision_rejects(self):
        slot=self.s.install(self.bank());self.s.render(1);self.s.command(3,2,1)
        event=Event(channel=2,sample=0,gate=9000,speed=1,gain=.2,attack=8,release=32)
        self.assertFalse(self.s.command(7,slot,99,identity=1,event=event));self.assertEqual(self.s.last_admission,-1)
        self.assertTrue(self.s.command(7,slot,0,identity=2,event=event));self.assertEqual(self.s.lib.lm_state(self.s.ptr,slot),2)
        self.s.render(1);self.assertEqual(self.s.status()['voices'],1)
    def test_limiter_finite(self):
        self.s.install(self.bank());self.s.command(1);self.s.command(10,event=Event(gain=1));out=self.s.render(1024);self.assertTrue(all(math.isfinite(x) and abs(x)<1 for x in out))
    def test_future_and_retired_manual_sources_rejected(self):
        a=self.s.install(self.bank(length=64));self.s.render(1);b=self.s.install(self.bank(1,length=64));self.s.render(1)
        self.s.command(3,2,1);e=Event(channel=2,sample=0,gate=9000,speed=1,gain=.2,attack=8,release=32)
        self.assertFalse(self.s.command(7,b,1,identity=1,event=e))
        self.assertTrue(self.s.command(7,a,0,identity=2,event=e));self.s.command(1);self.s.render(65)
        self.assertFalse(self.s.command(7,a,0,identity=3,event=e))
        c=self.s.install(self.bank(2,length=64));self.s.render(1);d=self.s.install(self.bank(3,length=64));self.s.render(1)
        self.assertEqual(self.s.status()['voices'],1);self.assertEqual(self.s.lib.lm_state(self.s.ptr,a),2)
        self.assertEqual(self.s.lib.lm_state(self.s.ptr,c),0)
        self.s.command(8,identity=2);self.s.render(40);self.assertEqual(self.s.lib.lm_state(self.s.ptr,a),0)
    def test_stop_then_immediate_play_does_not_kill_restarted_take(self):
        self.s.install(self.bank(length=10000,channel=0));self.s.command(1);self.s.render(100)
        self.s.command(2);self.s.render(200);self.s.command(1);self.s.render(1500)
        self.assertTrue(self.s.status()['playing']);self.assertGreater(self.s.status()['voices'],0)
        self.assertGreater(max(map(abs,self.s.render(256))),.001)
    def test_native_background_crossfade(self):
        a=array.array('H',[0])*163840;b=array.array('H',[65535])*163840
        self.assertEqual(self.s.blend(a,b,0),a.tobytes());self.assertEqual(self.s.blend(a,b,1),b.tobytes())
        out=array.array('H',self.s.blend(a,b,.5));self.assertEqual(out[0],16|(32<<5)|(16<<11));self.assertEqual(len(out),163840)
class PolicyTests(unittest.TestCase):
    def test_choose_avoids_repeat_with_tempo_pool(self):
        import random
        c=[dict(bpm=x,sha256=str(x)) for x in (60,68,69,72,90)]
        for i in range(50):self.assertIn(choose_drum(c,69,'69',random.Random(i)),(1,3))
    def test_octave_compensation_and_bass_filename(self):
        import wave
        class Engine:
            def sample(self,*a):pass
        with tempfile.TemporaryDirectory() as t:
            for name in ('LofiLead-upright-55.wav','LofiLead-grand-58-3.wav','LofiBass-flatwound-long-36-1.wav'):
                with wave.open(str(Path(t)/name),'wb') as w:w.setparams((1,2,32000,0,'NONE','not compressed'));w.writeframes(bytes(64))
            i=Instruments(t,Engine());u=next(e for e in i.entries if e['group']=='upright');self.assertEqual(u['recorded'],67)
            e=i.event(2,55,0,1,.5,('Upright','upright',.006,.3,.5,0),69);self.assertAlmostEqual(e['speed'],32000/44100*.5)
    def test_ledger_survives_reload_exhausts(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'ledger.json';l=DialogueLedger(p,'film');seen=[]
            for r in range(6):
                line=l.choose();seen.append(line);l.save(l.commit(line,r));l=DialogueLedger(p,'film')
            self.assertEqual(len(set(seen)),6);self.assertEqual(l.choose(),0)
    def test_ledger_not_consumed_by_preparation(self):
        with tempfile.TemporaryDirectory() as t:
            l=DialogueLedger(Path(t)/'ledger','film');l.choose();self.assertEqual(l.data,{})
    def test_background_failure_keeps_available_cache(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'one.bin').write_bytes(bytes(327680));(p/'images.json').write_text(json.dumps([dict(file='one.bin'),dict(file='missing.bin')]))
            b=Background(p);self.assertEqual(len(b.images),1);self.assertEqual(len(b.frame()),327680)
    def test_image_rights_validation(self):
        spec=importlib.util.spec_from_file_location('media',ROOT/'scripts/prepare-media.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with self.assertRaises(ValueError):m.image_record(dict(share_license_status='Copyright'))
if __name__=='__main__':unittest.main()

class ImageWorkerTests(unittest.TestCase):
    def test_worker_error_keeps_cache(self):
        from image_worker import ImageWorker
        def fail(*_):raise OSError('offline')
        with tempfile.TemporaryDirectory() as t:
            worker=ImageWorker(t,fetcher=fail);worker.request();worker.thread.join(2)
            self.assertEqual(worker.error,'offline');self.assertIsNone(worker.poll());worker.close()
    def test_worker_rights_and_decode_cache(self):
        from image_worker import ImageWorker
        record=dict(share_license_status='CC0',title='Landscape',url='https://example.test/work',images={'print':{'url':'https://example.test/image'}},id=1)
        def fetch(url,limit):return json.dumps({'data':[record]}).encode() if 'api/artworks' in url else b'fake JPEG'
        with tempfile.TemporaryDirectory() as t:
            worker=ImageWorker(t,fetcher=fetch,decoder=lambda _:bytes([80,100,120])*(960*160));worker.request();worker.thread.join(2)
            result=worker.poll();self.assertIsNotNone(result);self.assertEqual(len(result[0]),327680);self.assertEqual(result[1]['rights'],'CC0');self.assertTrue((Path(t)/'image-cache/image-1.json').exists());worker.close()
    def test_worker_rejects_non_cc0(self):
        from image_worker import credit_for
        with self.assertRaises(ValueError):credit_for({'share_license_status':'Copyright'})
    def test_background_transition_dimensions_and_text_panel(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'one.bin').write_bytes(bytes(327680));(p/'images.json').write_text(json.dumps([dict(file='one.bin')]))
            b=Background(p,clock=lambda:85);b.started=0
            self.assertEqual(len(b.frame()),327680)
