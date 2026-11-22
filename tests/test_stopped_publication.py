"""Safe stopped publication uses the same native ownership and worker path."""
import array,concurrent.futures,sys,unittest
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sampler import Sampler,SR
from standalone import Instrument

class StoppedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.engine=Sampler(ROOT/'.build/engine.so')
        self.first=self.engine.install(self.bank(0));self.engine.render(1)
    def tearDown(self):self.engine.close()
    def bank(self,revision):
        pcm=array.array('f',[.2,-.2])*SR
        return dict(pcm=[pcm,pcm],revision=revision,length=640,events=[],cuts=[(0,SR)],chop_gains=[1],archive_id=str(revision),line_index=0)
    def ui(self):
        ui=Instrument.__new__(Instrument);ui.engine=self.engine;ui.last_bank=self.first;ui.archive_worker=None;ui.archive_dirty=False;ui.queued_drum=None;ui.next_slot=None
        ui.error='';ui.chop=0;ui.edits={};ui.edit_gains={};ui.held={};ui.selected=4;ui.manual=[True]*6;ui.shift=False;ui.identity=0;ui.stopped_refresh=True
        ui.pending=concurrent.futures.Future();ui.pending.set_result(self.bank(1));ui.request_next=Mock();return ui
    def test_completed_worker_becomes_current_while_stopped(self):
        ui=self.ui();ui.tick();self.engine.render(1);ui.tick()
        self.assertEqual(ui.current['revision'],1);self.assertFalse(self.engine.status()['playing'])
        ui.request_next.assert_called_once()
    def test_held_voice_defers_publication_until_owning_release_finishes(self):
        ui=self.ui();ui.event(dict(kind='note',number=36,value=100));self.engine.render(1)
        ui.tick();self.engine.render(32);ui.tick();self.assertEqual(ui.current['revision'],0)
        ui.event(dict(kind='note_off',number=36,value=0));self.engine.render(300)
        self.assertEqual(self.engine.status()['bank'],self.first)
        self.engine.render(1);ui.tick();self.assertEqual(ui.current['revision'],1)
    def test_admitted_onset_pin_prevents_swap_before_rendered_voice(self):
        ui=self.ui();ui.tick();ui.event(dict(kind='note',number=36,value=100));self.engine.render(32)
        self.assertEqual(self.engine.status()['bank'],self.first)
    def test_playing_still_waits_for_complete64beat_bank(self):
        ui=self.ui();self.engine.command(1);self.engine.render(1);ui.tick()
        self.engine.render(638);self.assertEqual(self.engine.status()['bank'],self.first)
        self.engine.render(2);ui.tick();self.assertEqual(ui.current['revision'],1)
    def test_failed_worker_keeps_current_source_and_reports_error(self):
        ui=self.ui();ui.pending=concurrent.futures.Future();ui.pending.set_exception(ValueError('No reliable aligned speech'))
        ui.tick();self.engine.render(32);self.assertEqual(ui.current['revision'],0);self.assertIn('No reliable',ui.error)
