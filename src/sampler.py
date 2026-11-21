"""ctypes ABI1; immutable PCM owners outlive native bank/voice references."""
import ctypes as C
from pathlib import Path
import array
import sys
import wave
SR=44100
class Event(C.Structure):
    _fields_=[('frame',C.c_int),('channel',C.c_int),('sample',C.c_int),('gate',C.c_int),('speed',C.c_float),('gain',C.c_float),('attack',C.c_float),('release',C.c_float),('frequency',C.c_float)]
class Bank(C.Structure):
    _fields_=[('length',C.c_int),('count',C.c_int),('revision',C.c_int),('events',Event*512)]
class Command(C.Structure):
    _fields_=[('op',C.c_int),('a',C.c_int),('b',C.c_int),('id',C.c_int),('event',Event)]
def read_pcm(path):
    with wave.open(str(path),'rb') as w:
        if w.getsampwidth()!=2 or w.getnchannels() not in (1,2):raise ValueError('16-bit mono/stereo PCM required')
        channels=w.getnchannels();rate=w.getframerate();data=array.array('h',w.readframes(w.getnframes()))
    if sys.byteorder!='little':data.byteswap()
    # Native playback resamples; duplicate mono on this non-realtime preparation path.
    pcm=array.array('f')
    for i in range(0,len(data),channels):pcm.extend((data[i]/32768,data[i+channels-1]/32768))
    return pcm,rate
class Sampler:
    def __init__(self,path):
        self.lib=C.CDLL(str(path));L=self.lib
        L.lm_create.restype=C.c_void_p
        for name,args in [('lm_sample',[C.c_void_p,C.c_int,C.POINTER(C.c_float),C.c_int]),('lm_bank_sample',[C.c_void_p,C.c_int,C.c_int,C.POINTER(C.c_float),C.c_int]),('lm_reserve',[C.c_void_p]),('lm_bank',[C.c_void_p,C.c_int,C.POINTER(Bank)]),('lm_command',[C.c_void_p,C.POINTER(Command)]),('lm_render',[C.c_void_p,C.POINTER(C.c_float),C.c_int]),('lm_status',[C.c_void_p,C.c_int]),('lm_state',[C.c_void_p,C.c_int]),('lm_start',[C.c_void_p,C.c_char_p]),('lm_stop',[C.c_void_p]),('lm_destroy',[C.c_void_p])]:getattr(L,name).argtypes=args
        for name in ('frames','written','xruns'):
            f=getattr(L,'lm_'+name);f.argtypes=[C.c_void_p];f.restype=C.c_ulong
        L.lm_peak.argtypes=[C.c_void_p];L.lm_peak.restype=C.c_float
        self.ptr=L.lm_create()
        if not self.ptr:raise MemoryError('native engine')
        self.owners={};self.bank_owners={};self.banks={}
    def sample(self,index,pcm):
        owner=(C.c_float*len(pcm)).from_buffer(pcm)
        if not self.lib.lm_sample(self.ptr,index,owner,len(pcm)//2):raise ValueError('sample admission')
        self.owners[index]=(pcm,owner)
    def install(self,prepared):
        slot=self.lib.lm_reserve(self.ptr)
        if slot<0:return None
        owners=[]
        for i,pcm in enumerate(prepared['pcm']):
            owner=(C.c_float*len(pcm)).from_buffer(pcm);owners.append((pcm,owner))
            if not self.lib.lm_bank_sample(self.ptr,slot,i,owner,len(pcm)//2):raise ValueError('bank PCM admission')
        bank=Bank(length=prepared['length'],revision=prepared['revision'],count=len(prepared['events']))
        for i,values in enumerate(prepared['events']):
            event=Event(**values)
            if event.sample<0:event.sample=192+slot*16+(-event.sample-1)
            bank.events[i]=event
        if not self.lib.lm_bank(self.ptr,slot,C.byref(bank)):raise ValueError('bank admission')
        if not self.command(6,slot):raise BufferError('bank queue full')
        self.bank_owners[slot]=owners;self.banks[slot]=(bank,prepared)
        return slot
    def command(self,op,a=0,b=0,identity=0,event=None):
        c=Command(op=op,a=a,b=b,id=identity,event=event or Event())
        self.last_admission=self.lib.lm_command(self.ptr,C.byref(c));return self.last_admission==1
    def render(self,frames):
        out=(C.c_float*(frames*2))();self.lib.lm_render(self.ptr,out,frames);return out
    def status(self):
        return dict(bank=self.lib.lm_status(self.ptr,0),position=self.lib.lm_status(self.ptr,1),playing=bool(self.lib.lm_status(self.ptr,2)),overflow=self.lib.lm_status(self.ptr,3),voices=self.lib.lm_status(self.ptr,4),alive=bool(self.lib.lm_status(self.ptr,5)),frames=self.lib.lm_frames(self.ptr),written=self.lib.lm_written(self.ptr),xruns=self.lib.lm_xruns(self.ptr),peak=self.lib.lm_peak(self.ptr))
    def start(self):
        result=self.lib.lm_start(self.ptr,b'hw:A3,0')
        if result:raise RuntimeError('ALSA start: %d'%result)
    def close(self):
        if self.ptr:
            if self.lib.lm_stop(self.ptr):raise RuntimeError('audio thread failed to stop; memory retained')
            self.lib.lm_destroy(self.ptr);self.ptr=None
