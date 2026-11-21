import sys
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from display_worker import DisplayWorker

class DisplayWorkerTests(unittest.TestCase):
    def test_latest_frame_queue_does_not_block_dispatch(self):
        entered=threading.Event();release=threading.Event();seen=[];closed=[]
        class Fake:
            frames=0
            def send(self,frame):
                seen.append(frame)
                if frame==b'first':entered.set();release.wait(1)
                self.frames+=1
            def close(self):closed.append(True)
        worker=DisplayWorker(Fake);worker.send(b'first');self.assertTrue(entered.wait(1))
        start=time.monotonic();worker.send(b'second');worker.send(b'latest');self.assertLess(time.monotonic()-start,.02)
        release.set();end=time.monotonic()+1
        while worker.frames<2 and time.monotonic()<end:time.sleep(.001)
        worker.close();self.assertEqual(seen,[b'first',b'latest']);self.assertEqual(closed,[True])
    def test_open_error_propagates(self):
        def fail():raise OSError('USB unavailable')
        with self.assertRaisesRegex(RuntimeError,'worker failed'):DisplayWorker(fail)
    def test_late_open_after_timeout_closes_without_transfer(self):
        release=threading.Event();closed=threading.Event();sent=[]
        class Fake:
            def __init__(self):release.wait(1)
            def send(self,frame):sent.append(frame)
            def close(self):closed.set()
        with patch.object(DisplayWorker,'INIT_TIMEOUT',.01):
            with self.assertRaisesRegex(RuntimeError,'initialization timeout'):DisplayWorker(Fake)
        release.set();self.assertTrue(closed.wait(1));self.assertEqual(sent,[])
    def test_transfer_error_propagates_and_closes(self):
        closed=[]
        class Fake:
            def send(self,frame):raise OSError('transfer')
            def close(self):closed.append(True)
        worker=DisplayWorker(Fake);worker.send(b'frame');worker.thread.join(1)
        with self.assertRaisesRegex(RuntimeError,'worker failed'):worker.send(b'again')
        with self.assertRaises(RuntimeError):worker.close()
        self.assertEqual(closed,[True])

if __name__=='__main__':unittest.main()
