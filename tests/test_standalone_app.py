"""Readiness must disappear even when resource teardown reports failure."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import standalone_app as app
from display_worker import DisplayWorker

class AppCleanupTests(unittest.TestCase):
    def test_readiness_removed_after_engine_or_transfer_cleanup_failure(self):
        class FailedUSB:
            def send(self,frame):raise OSError('injected transfer failure')
            def close(self):pass
        for failure in ('engine','display'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
                home=Path(t);ready=home/'ready.json';ready.write_text('{"ready":true}')
                engine=MagicMock();display=None
                if failure=='engine':engine.close.side_effect=RuntimeError('injected engine close failure')
                else:
                    display=DisplayWorker(FailedUSB);display.send(b'frame');display.thread.join(1)
                    self.assertIsNotNone(display.error)
                args=['app','--home',str(home),'--seconds','0']
                if failure=='engine':args.append('--simulate')
                with patch.object(sys,'argv',args),patch.object(app.signal,'signal'),patch.object(app,'Sampler',return_value=engine),patch.object(app,'Instrument'),patch.object(app,'Background'),patch.object(app,'ImageWorker'),patch.object(app,'DisplayWorker',return_value=display),patch('hardware.Midi'):
                    with self.assertRaises(RuntimeError):app.main()
                self.assertFalse(ready.exists())

class AppFeedbackTests(unittest.TestCase):
    def test_short_auto_flash_reaches_midi_between_display_frames(self):
        # This60ms trigger sits wholly between the10Hz display updates.
        clock=[0.0];writes=[];display=MagicMock();display.frames=0
        def sleep(seconds):clock[0]+=.005
        def send(frame):display.frames+=1
        display.send.side_effect=send
        midi=MagicMock();midi.read.return_value=[]
        midi.note.side_effect=lambda n,v:writes.append((clock[0],n,v)) or True
        ui=MagicMock();ui.recovery_request=None;ui.selected=4;ui.shift=False;ui.mix=False;ui.settings=False
        ui.manual=[False]*6;ui.muted=[False]*6;ui.next_slot=None;ui.pending=None;ui.error='';ui.archive=None
        ui.current=dict(film_credit='',revision=0,drum=0)
        ui.tick.side_effect=lambda:dict(alive=True,playing=False,voices=0,peak=0,xruns=0,overflow=0)
        ui.leds.side_effect=lambda:{36:5 if .025<=clock[0]<.085 else 35}
        media=MagicMock();media.error='';media.poll.return_value=None
        archive=MagicMock();archive.state='OFFLINE';archive.error=''
        with tempfile.TemporaryDirectory() as t:
            args=['app','--home',t,'--seconds','.16']
            with patch.object(sys,'argv',args),patch.object(app.signal,'signal'),patch.object(app,'Sampler'),patch.object(app,'Instrument',return_value=ui),patch.object(app,'Background'),patch.object(app,'ImageWorker',return_value=media),patch.object(app,'ArchiveWorker',return_value=archive),patch.object(app,'DisplayWorker',return_value=display),patch('hardware.Midi',return_value=midi),patch.object(app,'render',return_value=b'frame'),patch.object(app.time,'monotonic',side_effect=lambda:clock[0]),patch.object(app.time,'sleep',side_effect=sleep):
                self.assertEqual(app.main(),0)
        reds=[at for at,n,v in writes if n==36 and v==5]
        self.assertTrue(reds);self.assertLess(reds[0],.1)
        self.assertTrue(any(.085<=at<=.12 and n==36 and v==35 for at,n,v in writes))
        self.assertEqual(display.frames,1)

if __name__=='__main__':unittest.main()
