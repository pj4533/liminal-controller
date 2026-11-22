"""Held Manual Chops through MIDI dispatch and the real native renderer."""
import array
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,SR
from channel_fx import defaults
from standalone import Instrument
from midi import MidiParser

class ChopGateTests(unittest.TestCase):
    def setUp(self):
        self.engine=Sampler(ROOT/'.build/engine.so')
        self.slot=self.engine.install(self.bank());self.engine.render(1)
        ui=Instrument.__new__(Instrument);ui.fx_pages=[0,0,0,0,3,3];ui.effects=[defaults(ch) for ch in range(6)];ui.engine=self.engine;ui.last_bank=self.slot
        ui.settings=False;ui.shift=False;ui.held={};ui.identity=0;ui.selected=4
        ui.archive=None;ui.manual=[False]*6;ui.manual[4]=True;ui.chop=0;ui.edits={};ui.edit_gains={};ui.mix=False
        self.ui=ui;self.engine.command(3,4,1)
    def tearDown(self):self.engine.close()
    def bank(self,revision=0):
        pcm=array.array('f',[.2,-.2])*(SR*2)
        return dict(revision=revision,length=128,bpm=69,pcm=[pcm,pcm],events=[],
                    cuts=[(0,SR//2),(SR//2,SR//2)],chop_gains=[1,1],archive_id=str(revision),line_index=0)
    def event(self,number=36,kind='note',value=96):
        self.ui.event(dict(kind=kind,number=number,value=value))
    def sounding(self):
        self.assertGreater(max(map(abs,self.engine.render(1024))),.001)
        self.assertGreater(self.engine.status()['voices'],0)
    def silent(self):
        self.engine.render(512) # existing 256-frame click-free native release
        self.assertEqual(self.engine.status()['voices'],0)
        self.assertLess(max(map(abs,self.engine.render(512))),1e-8)
    def test_early_release_truncates_instead_of_finishing_slice(self):
        self.event();self.sounding();self.assertIn(36,self.ui.held)
        self.event(kind='note_off',value=0);self.silent();self.assertFalse(self.ui.held)
    def test_zero_velocity_dispatch_and_both_wire_release_forms(self):
        for release in (None,bytes([0x80,36,64]),bytes([0x90,36,0])):
            with self.subTest(release=release):
                self.event();self.sounding()
                if release is None:self.event(value=0)
                else:
                    for event in MidiParser().feed(release):self.ui.event(event)
                self.silent();self.assertFalse(self.ui.held)
    def test_hold_reaches_slice_end_once_then_requires_new_press(self):
        self.event();self.sounding()
        self.engine.render(SR//2-1025);self.assertEqual(self.engine.status()['voices'],1)
        self.engine.render(1);self.assertEqual(self.engine.status()['voices'],0)
        self.engine.render(512);self.assertLess(max(map(abs,self.engine.render(SR))),1e-8)
        self.event(kind='note_off',value=0);self.event();self.sounding()
    def test_old_pad_release_does_not_stop_new_pad_or_retrigger(self):
        self.event();self.sounding();old=self.ui.held[36]
        self.event(37);self.engine.render(512);new=self.ui.held[37];self.assertNotEqual(old,new)
        self.event(kind='note_off',value=0);self.engine.render(512)
        self.assertEqual(self.engine.status()['voices'],1);self.sounding()
        self.event(37);self.engine.render(512);self.assertNotEqual(new,self.ui.held[37])
        self.assertEqual(self.engine.status()['voices'],1)
        self.event(kind='note_off',value=0);self.sounding() # repeated stale old-pad release
        self.event(37,'note_off',0);self.silent()
    def test_release_survives_selection_mode_edit_and_native_bank_change(self):
        self.event();self.sounding()
        # Editing the cut or changing selection never reassigns the onset token.
        self.event(77,'cc',1);self.ui.toggle_mode(4);self.ui.selected=2
        self.engine.install(self.bank(1));self.engine.command(1);self.engine.render(129)
        self.assertNotEqual(self.engine.status()['bank'],self.slot)
        self.assertEqual(self.engine.status()['voices'],1)
        self.event(kind='note_off',value=0);self.silent()
    def test_release_in_same_queue_as_onset_and_stop_delete_are_safe(self):
        for stop in ('release',29,118):
            self.event()
            if stop=='release':self.event(kind='note_off',value=0)
            else:self.event(stop,'cc',127)
            self.engine.render(2048);self.silent();self.assertFalse(self.ui.held)
    def test_full_film_anchor_retains_existing_one_shot_behavior(self):
        bank=self.engine.banks[self.slot][1];bank['pcm'] += [array.array('f',[.2,-.2])*SR]*8;bank['anchor']=2
        # Install a new native bank so its anchor PCM is registered.
        self.engine.install(dict(bank,revision=1));self.engine.command(1);self.engine.render(129)
        self.ui.selected=5;self.ui.manual[5]=True;self.engine.command(3,5,1)
        self.event();self.sounding();self.assertNotIn(36,self.ui.held)
        self.event(kind='note_off',value=0);self.sounding()
