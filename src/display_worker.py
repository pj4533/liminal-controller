"""One USB owner, one replaceable pending frame; MIDI never waits for USB."""
import queue
import threading
import time
from collections import deque

class DisplayWorker:
    INIT_TIMEOUT=5
    def __init__(self,factory=None):
        if factory is None:
            from hardware import Display
            factory=Display
        self.factory=factory;self.pending=queue.Queue(maxsize=1);self.stopping=threading.Event();self.ready=threading.Event();self.frames=0;self.error=None;self.transfer_seconds=deque(maxlen=256)
        self.thread=threading.Thread(target=self.run,name='liminal-display',daemon=True);self.thread.start()
        if not self.ready.wait(self.INIT_TIMEOUT):
            # A slow constructor may return later; its owning thread must close
            # that handle rather than start transfers after startup has failed.
            self.stopping.set()
            raise RuntimeError('USB display initialization timeout')
        self.check()
    def check(self):
        if self.error:raise RuntimeError('USB display worker failed') from self.error
    def send(self,frame):
        self.check()
        try:self.pending.put_nowait(frame)
        except queue.Full:
            try:self.pending.get_nowait()
            except queue.Empty:pass
            try:self.pending.put_nowait(frame)
            except queue.Full:pass
    def run(self):
        display=None
        try:
            display=self.factory();self.ready.set()
            while not self.stopping.is_set():
                try:frame=self.pending.get(timeout=.1)
                except queue.Empty:continue
                begin=time.monotonic();display.send(frame);self.transfer_seconds.append(time.monotonic()-begin);self.frames=display.frames
        except Exception as error:self.error=error
        finally:
            self.ready.set()
            if display:
                try:display.close()
                except Exception as error:self.error=error
    def close(self):
        self.stopping.set();self.thread.join(3)
        if self.thread.is_alive():raise RuntimeError('USB display owner did not stop; no takeover')
        self.check()
