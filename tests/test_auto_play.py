"""Actual native automatic onsets, pad feedback and independent manual ownership."""
import array
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,SR,Event
from standalone import Instrument
import test_chop_gate as gates

class AutoPlayTests(unittest.TestCase):
    bank=gates.ChopGateTests.bank
    event=gates.ChopGateTests.event
    sounding=gates.ChopGateTests.sounding
    silent=gates.ChopGateTests.silent
    tearDown=gates.ChopGateTests.tearDown
    def setUp(self):
        gates.ChopGateTests.setUp(self);self.ui.manual[4]=False;self.engine.command(3,4,0)
    def test_manual_chops_in_auto_release_while_automatic_activity_continues(self):
        bank=self.bank(1);bank['length']=SR*2
        bank['events']=[dict(frame=4096,channel=4,sample=-2,gate=SR,speed=1,gain=.1,attack=8,release=256,pad=2)]
        self.engine.install(bank);self.engine.command(1);self.engine.render(129);self.ui.last_bank=self.engine.status()['bank']
        self.event();self.sounding();self.assertIsNone(self.engine.feedback(4))
        self.event(kind='note_off',value=0);self.silent()
        self.engine.render(4096);self.assertEqual(self.engine.status()['voices'],1)
        self.assertEqual(self.engine.feedback(4),(1,2));self.assertEqual(self.ui.leds()[37],5)
        self.assertNotEqual(self.ui.leds()[36],5)
    def test_modes_only_gate_new_auto_onsets_and_never_cut_existing_notes(self):
        bank=self.bank(1);bank['length']=SR*2
        bank['events']=[dict(frame=0,channel=4,sample=-2,gate=SR,speed=1,gain=.1,attack=8,release=256,pad=2)]
        self.engine.install(bank);self.engine.command(1);self.engine.render(129)
        self.ui.toggle_mode(4);self.engine.render(512);self.assertEqual(self.engine.status()['voices'],1)
        self.assertIsNone(self.engine.feedback(4))
        self.event();self.engine.render(512);self.assertEqual(self.engine.status()['voices'],2)
        self.ui.toggle_mode(4);self.engine.render(512);self.assertEqual(self.engine.status()['voices'],2)
        self.event(kind='note_off',value=0);self.engine.render(512);self.assertEqual(self.engine.status()['voices'],1)
    def test_flash_is_actual_auto_only_bounded_revision_and_channel_scoped(self):
        bank=self.bank(1);bank['length']=SR*2
        bank['events']=[dict(frame=256,channel=4,sample=-2,gate=SR,speed=1,gain=.1,attack=8,release=256,pad=2)]
        self.engine.install(bank);self.engine.command(1);self.engine.render(129)
        self.assertIsNone(self.engine.feedback(4));self.engine.render(256)
        self.assertEqual(self.engine.feedback(4),(1,2));self.assertIsNone(self.engine.feedback(3))
        self.assertNotEqual(self.ui.leds()[37],5) # UI still owns revision0
        self.ui.last_bank=self.engine.status()['bank'];self.assertEqual(self.ui.leds()[37],5)
        self.engine.render(5292);self.assertIsNone(self.engine.feedback(4));self.assertNotEqual(self.ui.leds()[37],5)
    def test_all_channels_play_pads_in_auto_without_changing_modes(self):
        from unittest.mock import Mock
        bank=self.engine.banks[self.slot][1]
        bank.update(drumcuts=[1]*4,anchor=1,bass=(),pad=(),programs=[()])
        self.ui.octave=0;self.ui.catalog=[];self.ui.drum_page=0
        self.ui.instruments=Mock()
        self.ui.instruments.event.side_effect=lambda ch,*args:dict(channel=ch,sample=193,gate=SR,speed=1,gain=.1,attack=8,release=256)
        # Film's anchor guard retains its historical fixed eight-slice layout.
        bank['pcm'] += [array.array('f',[0,0])*2]*8
        bank['events']=[dict(gain=.2)]
        for ch in range(6):
            self.ui.selected=ch;self.event();self.engine.render(512)
            self.assertGreater(self.engine.status()['voices'],0)
            self.assertFalse(any(self.ui.manual));self.assertIsNone(self.engine.feedback(ch))
            self.ui.selected=(ch+1)%6;self.event(kind='note_off',value=0)
            if ch==5:self.engine.command(9) # Film intentionally remains a one-shot
            self.engine.render(SR) # allow channel filter/envelope tails to settle
            self.silent()
    def test_melodic_feedback_maps_actual_pitch_to_current_octave_only(self):
        from standalone import pad_pitch
        self.ui.selected=2;self.ui.octave=0
        bank=self.bank(1);bank['length']=SR*2
        bank['events']=[dict(frame=0,channel=2,sample=-2,gate=SR,speed=1,gain=.1,attack=8,release=256,pad=128+pad_pitch(39))]
        self.engine.install(bank);self.engine.command(1);self.engine.render(129)
        self.ui.last_bank=self.engine.status()['bank']
        self.assertEqual({n for n,c in self.ui.leds().items() if c==5},{39,44})
        self.ui.octave=3;self.assertFalse(any(c==5 for c in self.ui.leds().values()))
        self.ui.selected=4;self.assertFalse(any(c==5 for c in self.ui.leds().values()))
    def test_auto_manual_release_survives_mode_edit_selection_and_bank(self):
        gates.ChopGateTests.test_release_survives_selection_mode_edit_and_native_bank_change(self)
    def test_flash_expires_at_shorter_gate_or_source_not_only_timeout(self):
        for gate,frames in ((128,1024),(1024,128)):
            self.engine.close();self.engine=Sampler(ROOT/'.build/engine.so')
            pcm=array.array('f',[.2,-.2])*frames
            self.engine.install(dict(revision=0,length=SR,pcm=[pcm],events=[dict(frame=0,channel=4,sample=-1,gate=gate,speed=1,gain=.1,attack=8,release=32,pad=1)]))
            self.engine.render(1);self.engine.command(1);self.engine.render(1)
            self.assertEqual(self.engine.feedback(4),(0,1))
            self.engine.render(min(gate,frames));self.assertIsNone(self.engine.feedback(4))
    def test_stop_mute_and_rejected_onset_never_leave_a_flash(self):
        for action in ('stop','mute','overflow'):
            self.engine.close();self.engine=Sampler(ROOT/'.build/engine.so');self.ui.engine=self.engine
            bank=self.bank();bank['length']=SR*2;bank['events']=[dict(frame=0,channel=4,sample=-2,gate=SR,speed=1,gain=.1,attack=8,release=256,pad=2)]
            slot=self.engine.install(bank);self.engine.render(1)
            if action=='overflow':
                for identity in range(1,65):self.engine.command(7,slot,0,identity,Event(channel=4,sample=193,gate=SR,speed=1,gain=.1,attack=8,release=256))
            self.engine.command(1);self.engine.render(1)
            if action=='overflow':self.assertEqual(self.engine.status()['overflow'],1)
            else:
                self.assertEqual(self.engine.feedback(4),(0,2))
                self.engine.command(2 if action=='stop' else 5,4,1);self.engine.render(1)
            self.assertIsNone(self.engine.feedback(4))

if __name__=='__main__':unittest.main()
