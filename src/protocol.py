"""Bounded v1 framing and nonblocking, session-owned outbound transport."""
import ipaddress
import json
import math
import socket
import time
from collections import deque

LIMIT = 65536

def address(host):
    ip = ipaddress.IPv4Address(host)
    if not (ip in ipaddress.IPv4Network('10.0.0.0/8') or ip in ipaddress.IPv4Network('172.16.0.0/12') or ip in ipaddress.IPv4Network('192.168.0.0/16') or ip.is_loopback):
        raise ValueError('Use a literal private IPv4 or loopback address')
    return str(ip)

def validate(value, depth=0):
    if depth > 12: raise ValueError('frame nesting')
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('non-finite number')
    if isinstance(value, dict):
        for v in value.values(): validate(v, depth+1)
    elif isinstance(value, list):
        for v in value: validate(v, depth+1)

def encode(frame):
    b = json.dumps(frame, allow_nan=False, separators=(',', ':')).encode()+b'\n'
    if len(b)>LIMIT: raise ValueError('frame too large')
    return b

class Framer:
    def __init__(self): self.buffer = bytearray()
    def feed(self, data):
        self.buffer.extend(data); result=[]
        while b'\n' in self.buffer:
            i=self.buffer.index(10)
            if i+1>LIMIT: raise ValueError('frame too large')
            raw=bytes(self.buffer[:i]); del self.buffer[:i+1]
            def reject(s): raise ValueError('non-finite number')
            f=json.loads(raw.decode('utf-8'),parse_constant=reject)
            validate(f)
            if not isinstance(f,dict) or type(f.get('v')) is not int or f['v']!=1 or not isinstance(f.get('type'),str): raise ValueError('invalid envelope')
            result.append(f)
        if len(self.buffer)>=LIMIT: raise ValueError('unframed overflow')
        return result

class Client:
    def __init__(self, host, port=20808, clock=time.monotonic):
        self.host=address(host); self.port=int(port)
        if not 1<=self.port<=65535: raise ValueError('port')
        self.clock=clock; self.sock=None; self.session=None; self.server_id=None
        self.generation=0; self.seq=0; self.revision=-1; self.state=None
        self.queue=deque(); self.partial=b''; self.edits={}; self.error='Waiting for Liminal'
        self.last_rx=0; self.last_ping=0; self.last_edit=0; self.retry=0; self.rtt=None; self.pings={}
        self.connected_at=0
    @property
    def connected(self): return self.sock is not None and self.session is not None and self.state is not None
    def disconnect(self, reason='Disconnected'):
        if self.sock: self.sock.close()
        self.sock=None; self.session=None; self.state=None; self.revision=-1
        self.queue.clear(); self.edits.clear(); self.partial=b''; self.pings.clear(); self.rtt=None
        self.error=reason; self.retry=self.clock()+1
    def put(self, frame):
        data=encode(frame)
        if len(self.queue)>=256 or sum(map(len,self.queue))+len(self.partial)+len(data)>262144:
            self.disconnect('Backpressure: connection released'); return False
        self.queue.append(data); return True
    def command(self, action, **fields):
        if not self.connected: return False
        if action=='parameter':
            key=(fields.get('channel'),fields.get('parameter'))
            self.edits[key]=fields
            return True
        return self._command(action,fields)
    def _command(self,action,fields):
        self.seq+=1
        return self.put(dict(v=1,type='command',session=self.session,seq=self.seq,action=action,**fields))
    def receive(self, f):
        self.last_rx=self.clock(); typ=f['type']
        if typ=='welcome':
            if self.session is not None: raise ValueError('duplicate welcome')
            self.session=f['session']; self.server_id=f['server_id']; self.seq=0; self.generation+=1
        elif typ=='state':
            if not self.session or f.get('session')!=self.session: return
            if type(f.get('revision')) is not int: raise ValueError('revision')
            if f['revision']>self.revision:
                channels=f.get('channels',[])
                if len(channels)>16: raise ValueError('too many channels')
                if len((f.get('drums') or {}).get('choices',[]))>64:raise ValueError('too many drum choices')
                for channel in channels:
                    if len(channel.get('parameters',[]))>8 or len((channel.get('pad_bank') or {}).get('pads',[]))>64:raise ValueError('channel descriptor overflow')
                if self.state is None:self.error=''
                self.state=f; self.revision=f['revision']
        elif typ=='pong':
            sent=self.pings.pop(f.get('nonce'),None)
            if sent is not None: self.rtt=(self.clock()-sent)*1000
        elif typ in ('error','ack') and (typ=='error' or not f.get('ok')):
            self.error=str(f.get('error','Rejected'))[:80]
    def tick(self):
        now=self.clock()
        if not self.sock:
            if now<self.retry:return
            try:
                self.sock=socket.create_connection((self.host,self.port),timeout=.15)
                self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);self.sock.setblocking(False)
                self.framer=Framer();self.connected_at=now;self.last_rx=now
                self.put(dict(v=1,type='hello',client='liminal-controller',client_version='0.1.0'))
            except OSError as e:self.disconnect('Waiting for Liminal: '+str(e));return
        try:
            for _ in range(16):
                try: data=self.sock.recv(65536)
                except BlockingIOError:break
                if not data:raise OSError('peer closed')
                for f in self.framer.feed(data):self.receive(f)
            if now-self.last_rx>3 or (not self.session and now-self.connected_at>3):raise OSError('lease timeout')
            if self.session and now-self.last_ping>=1:
                nonce=time.monotonic_ns();self.pings={nonce:now};self.put(dict(v=1,type='ping',nonce=nonce));self.last_ping=now
            if self.connected and now-self.last_edit>=1/60:
                edits=self.edits;self.edits={};self.last_edit=now
                for fields in edits.values():
                    if not self._command('parameter',fields):return
            for _ in range(32):
                if not self.partial:
                    if not self.queue:break
                    self.partial=self.queue.popleft()
                try:n=self.sock.send(self.partial)
                except BlockingIOError:break
                if n==0:raise OSError('stalled socket')
                self.partial=self.partial[n:]
        except (OSError,ValueError,KeyError,TypeError) as e:self.disconnect(str(e))
