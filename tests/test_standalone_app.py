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

if __name__=='__main__':unittest.main()
