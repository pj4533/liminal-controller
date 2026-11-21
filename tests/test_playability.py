"""User-facing controls through the real native engine and distinct PCM sources."""
import array
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,Event,SR
from standalone import Instrument,pad_pitch
from composition import chop_gain

class PlayabilityTests(unittest.TestCase):
    def setUp(self):
        self.engine=Sampler(ROOT/'.build/engine.so')
    def tearDown(self):self.engine.close()
    def ui(self):
        ui=Instrument.__new__(Instrument);ui.engine=self.engine;ui.settings=False;ui.shift=False;ui.held={};ui.identity=0;ui.selected=4;ui.manual=[True]*6;ui.octave=0;ui.chop=0;ui.edits={};ui.catalog=[];ui.drum_page=0
        return ui
    def event(self,ui,number,kind='cc',value=127):ui.event(dict(kind=kind,number=number,value=value))
    def bank(self,pcm,events=None,**kwargs):
        bank=dict(revision=0,length=SR*3,bpm=69,pcm=pcm,events=events or [],archive_id='fixture',line_index=0,cuts=[(SR//2,SR//4)]*8,chop_gains=[1]*8)
        bank.update(kwargs);slot=self.engine.install(bank);self.engine.render(1);return slot
    def test_physical_play_toggles_and_hushes_tails(self):
        self.bank([array.array('f',[.2,.2])*SR],[dict(frame=0,channel=0,sample=-1,gate=SR,speed=1,gain=1,attack=8,release=32)])
        ui=self.ui();self.event(ui,85);self.assertGreater(max(map(abs,self.engine.render(4096))),.001)
        self.assertTrue(self.engine.status()['playing']);self.event(ui,85);self.engine.render(SR)
        self.assertFalse(self.engine.status()['playing']);self.assertEqual(self.engine.status()['position'],0);self.assertEqual(max(map(abs,self.engine.render(1024))),0)
        self.event(ui,85);self.engine.render(1);self.assertTrue(self.engine.status()['playing'])
    def test_rapid_play_presses_toggle_in_queue_order(self):
        self.bank([array.array('f',[.2,.2])*SR]);ui=self.ui()
        self.event(ui,85);self.event(ui,85);self.engine.render(1);self.assertFalse(self.engine.status()['playing'])
        self.event(ui,85);self.event(ui,85);self.event(ui,85);self.engine.render(1);self.assertTrue(self.engine.status()['playing'])
    def test_start_keeps_stopped_manual_note_release(self):
        self.bank([array.array('f',[.2,.2])*SR]);ui=self.ui();ui.held={36:99}
        self.event(ui,85);self.assertEqual(ui.held,{36:99})
        self.event(ui,36,'note_off',0);self.assertFalse(ui.held)
    def test_stillwater_exact_default_all_pitches_and_colors(self):
        ui=self.ui()
        for ch in (1,2,3):
            ui.selected=ch
            for octave in (-2,-1,0,1,2):
                ui.octave=octave;leds=ui.leds()
                for n in range(36,100):
                    degree=(n-36)%8+3*((n-36)//8)-14+7*octave
                    expected=62+12*(degree//7)+(0,2,3,5,7,9,10)[degree%7]
                    self.assertEqual(pad_pitch(n,octave),expected)
                    self.assertEqual(leds[n],65 if expected%12==2 else 123 if expected%12 in (0,2,4,5,7,9,11) else 66)
        self.assertEqual((pad_pitch(36),pad_pitch(99)),(38,86))
        self.assertEqual([pad_pitch(n) for n in (36,38,45)],[38,41,45])
        ui.octave=0;ui.held={39:1};self.assertEqual(ui.leds()[44],37) # duplicate absolute pitch
    def test_octave_moves_keep_complete_stillwater_window_valid(self):
        ui=self.ui();ui.selected=2
        for _ in range(8):self.event(ui,62)
        self.assertEqual(ui.octave,-3);self.assertEqual(pad_pitch(36,ui.octave),2)
        for _ in range(12):self.event(ui,63)
        self.assertEqual(ui.octave,3);self.assertEqual(pad_pitch(99,ui.octave),122)

    def test_manual_melodic_events_use_same_grid_for_all_channels(self):
        ui=self.ui();self.bank([array.array('f',[.1,.1])*SR],bass=(),pad=(),programs=[()])
        class Instruments:
            def event(self,ch,midi,*args):
                played.append((ch,midi));return dict(channel=ch,sample=192,gate=1000,speed=1,gain=.1,attack=8,release=32)
        played=[];ui.instruments=Instruments()
        for ch in (1,2,3):
            ui.selected=ch
            for n in (36,38,45):self.event(ui,n,'note',96)
        self.assertEqual(played,[(ch,p) for ch in (1,2,3) for p in (38,41,45)])
    def test_default_drums_have_no_delayed_echo_or_room(self):
        class Instruments:pass
        bank=dict(revision=0,length=SR*2,pcm=[array.array('f',[.2,.2])*128],events=[dict(frame=0,channel=0,sample=-1,gate=128,speed=1,gain=1,attack=8,release=32)])
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'drums.json').write_text('[{"bpm":69}]')
            with patch('standalone.Instruments',return_value=Instruments()),patch('standalone.prepare',return_value=bank),patch.object(Instrument,'request_next'):
                ui=Instrument(self.engine,t,t)
            try:
                self.assertEqual(ui.effects[0][1:3],[0,0]);ui.send(1);pcm=self.engine.render(SR)
                self.assertGreater(max(map(abs,pcm[:2048])),1e-4)
                self.assertLess(max(map(abs,pcm[SR//2:])),1e-12)
            finally:ui.close()
    def test_quiet_chop_gain_bounded_and_not_silence_boosted(self):
        quiet=array.array('f',[.01,-.01])*SR
        self.assertAlmostEqual(chop_gain(quiet)*.01,.11,places=6)
        self.assertEqual(chop_gain(array.array('f',[0,0])*100),0)
        self.assertLessEqual(chop_gain(array.array('f',[1,-1])*100),.6)
        self.assertLessEqual(chop_gain(array.array('f',[.00001,-.00001])*100),16)
    def test_auto_and_manual_chops_match_and_exceed_bed_level(self):
        source=array.array('f',(v for i in range(SR) for v in (math.sin(i*2*math.pi*441/SR)*.012,)*2))
        gain=chop_gain(source)
        def capture(channel,gain,manual):
            engine=Sampler(ROOT/'.build/engine.so')
            try:
                event=dict(frame=0,channel=channel,sample=-1,gate=SR,speed=1,gain=gain,attack=128,release=256)
                slot=engine.install(dict(revision=0,length=SR*2,pcm=[source],events=[] if manual else [event]));engine.render(1)
                if manual:
                    engine.command(3,channel,1);event['sample']=192+slot*16
                    engine.command(7,slot,0,identity=1,event=Event(**event))
                else:engine.command(1)
                return list(engine.render(4096))
            finally:engine.close()
        auto=capture(4,gain,False);manual=capture(4,gain,True);bed=capture(5,.16,False)
        self.assertEqual(auto,manual)
        rms=lambda pcm:math.sqrt(sum(v*v for v in pcm)/len(pcm))
        self.assertGreater(rms(auto),rms(bed)*16) # at least24dB foreground over the same quiet bed

    def test_chops_use_cut_source_are_audible_and_separate_from_film(self):
        # Silence at the bed start and a distinct 441Hz cut at the edited offset.
        source=array.array('f',[0,0])*(SR//2)
        source.extend(v for i in range(SR) for v in (math.sin(i*2*math.pi*441/SR)*.012,)*2)
        gain=chop_gain(source[SR:SR+SR//2]);slot=self.bank([array.array('f',[.9,.9])*SR,source]+[array.array('f',[.9,.9])*100]*8,chop_gains=[gain]*8)
        ui=self.ui();self.engine.command(3,4,1)
        self.event(ui,36,'note',96);self.engine.command(5,5,1);out=self.engine.render(SR)
        rms=math.sqrt(sum(v*v for v in out[:SR//2])/ (SR//2));self.assertGreater(rms,.01)
        self.assertLess(max(map(abs,out[SR:])),1e-6)
        self.engine.command(2);self.engine.render(4096);self.engine.command(5,4,1);self.engine.render(SR);self.event(ui,36,'note',96)
        self.assertLess(max(map(abs,self.engine.render(SR))),1e-12)
