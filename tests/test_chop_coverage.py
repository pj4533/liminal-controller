"""Full phrase coverage and controls, exercised against the native bank clock."""
import array
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archive_worker import chops,SR
from composition import prepare
from sampler import Sampler
from channel_fx import defaults
from standalone import Instrument

class CoverageTests(unittest.TestCase):
    def test_entire_short_and_full_windows_partition_once(self):
        for seconds in (1,2,8,48):
            pcm=array.array('f',[.1,-.1])*(SR*seconds)
            cuts=chops(pcm)
            self.assertEqual(len(cuts),min(64,math.ceil(seconds/.75)))
            self.assertEqual(cuts[0][0],0);self.assertEqual(sum(n for _,n in cuts),len(pcm)//2)
            self.assertEqual(len(set(cuts)),len(cuts))
            for (start,n),(following,_) in zip(cuts,cuts[1:]):self.assertEqual(start+n,following)
    def test_sparse_speech_keeps_silences_and_tail_in_order(self):
        pcm=array.array('f',[0,0])*(SR*8)
        for second in (1,6):pcm[second*SR*2:(second*SR+500)*2]=array.array('f',[.2,-.2])*500
        cuts=chops(pcm);self.assertEqual(cuts[0][0],0);self.assertEqual(cuts[-1][0]+cuts[-1][1],SR*8)
        self.assertTrue(all(n>0 for _,n in cuts))
        self.assertEqual([s+n for s,n in cuts[:-1]],[s for s,_ in cuts[1:]])
    def test_preparation_keeps_all_live_cuts_and_complete_offline_line(self):
        class Instruments:
            entries=[dict(kind='LofiBass',group='test')]
            def event(self,*args):return dict(frame=0,channel=2,sample=0,gate=10,speed=1,gain=1,attack=1,release=1)
        pcm=array.array('f',[.1,-.1])*(SR*48)
        for live in (False,True):
            archive=dict(pcm=pcm,cuts=chops(pcm),credit=dict(sha256='live')) if live else None
            with patch('composition.read_pcm',return_value=(pcm,SR)),patch('composition.Path.exists',return_value=True):
                bank=prepare(Instruments(),ROOT,[dict(file='test.wav')],0,0,line_index=2,archive=archive)
            cuts=bank['cuts'];self.assertEqual(cuts[0][0],0 if live else SR*16)
            self.assertEqual(cuts[-1][0]+cuts[-1][1],SR*(48 if live else 24))
            self.assertEqual(len(bank['chop_gains']),len(cuts));self.assertEqual(len(bank['pcm']),15)
            for event in (e for e in bank['events'] if e['channel']==4):
                self.assertEqual(len(bank['pcm'][-event['sample']-1])//2,event['gate'])

    def ui(self,engine):
        ui=Instrument.__new__(Instrument);ui.fx_pages=[0,0,0,0,3,3];ui.effects=[defaults(ch) for ch in range(6)];ui.engine=engine;ui.last_bank=engine.status()['bank'];ui.settings=False;ui.shift=False;ui.held={};ui.identity=0;ui.selected=4;ui.manual=[True]*6;ui.chop=0;ui.edits={};ui.edit_gains={};ui.mix=False;ui.archive=None;ui.archive_dirty=False;ui.error='';ui.next_slot=None;ui.pending=None
        return ui
    def bank(self,revision=0,seconds=2,length=128):
        pcm=array.array('f',[.1,-.1])*(SR*seconds);cuts=chops(pcm)
        return dict(revision=revision,length=length,bpm=69,pcm=[pcm,pcm],events=[],cuts=cuts,chop_gains=[1]*len(cuts),archive_id=str(revision),line_index=0,drum=revision)
    def test_each_populated_pad_has_unique_offset_and_unused_pads_are_inert(self):
        for seconds in (2,48):
            engine=Sampler(ROOT/'.build/engine.so')
            try:
                bank=self.bank(seconds=seconds);engine.install(bank);engine.render(1);ui=self.ui(engine)
                onsets=[];ui.onset=lambda *args:onsets.append(args[-1]) or True
                for n in range(36,100):ui.event(dict(kind='note',number=n,value=100))
                self.assertEqual([(e.frame,e.gate) for e in onsets],bank['cuts'])
                self.assertEqual(len(set(e.frame for e in onsets)),len(bank['cuts']))
                self.assertEqual([n for n,v in ui.leds().items() if v],[36+i for i in range(len(bank['cuts']))])
                if seconds==2:
                    ui.shift=True;ui.chop=1;ui.event(dict(kind='note',number=99,value=100));self.assertEqual(ui.chop,1)
                    ui.event(dict(kind='cc',number=78,value=1));self.assertEqual(ui.chop,2)
                    ui.event(dict(kind='cc',number=78,value=1));self.assertEqual(ui.chop,0)
            finally:engine.close()
    def test_manual_mode_keeps_refreshing_across_three_native_take_transitions(self):
        engine=Sampler(ROOT/'.build/engine.so')
        try:
            engine.install(self.bank());engine.render(1);ui=self.ui(engine)
            ui.archive_worker=Mock();ui.archive_worker.poll.return_value=None
            ui.request_next=Mock();engine.command(3,4,1);engine.command(1)
            for revision in range(1,4):
                prepared=self.bank(revision,seconds=revision+1);engine.install(prepared);engine.render(129)
                ui.tick();self.assertEqual(ui.current['revision'],revision);self.assertTrue(ui.manual[4])
                self.assertEqual(ui.current['cuts'][-1][0]+ui.current['cuts'][-1][1],SR*(revision+1))
                ui.tick() # repeated control tick cannot cause another fetch
            self.assertEqual(ui.archive_worker.request.call_count,3);self.assertEqual(ui.request_next.call_count,3)
        finally:engine.close()
