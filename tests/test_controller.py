import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from controller import Controller,Settings,pitches
from protocol import Client,Framer,encode,address
from fake_server import FakeServer,sample_state,GOLDEN
from midi import MidiParser
from render import render

class MemoryClient(Client):
    def __init__(self,ambient=True):
        super().__init__('127.0.0.1');self.sock=socket.socket();self.session='test-session';self.state=sample_state(ambient=ambient);self.generation=1;self.actions=[]
    def command(self,action,**fields):self.actions.append(dict(action=action,**fields));return super().command(action,**fields)

def event(kind,n,v=127):return dict(kind=kind,number=n,value=v,channel=0)

class FramingTests(unittest.TestCase):
    def test_golden_split_every_byte(self):
        parser=Framer();got=[];wire=b''.join(encode(f) for f in GOLDEN)
        for b in wire:got+=parser.feed(bytes([b]))
        self.assertEqual(got,GOLDEN)
    def test_split_unicode(self):
        frame=dict(v=1,type='state',label='é');p=Framer();out=[]
        for b in (json.dumps(frame,ensure_ascii=False)+'\n').encode():out+=p.feed(bytes([b]))
        self.assertEqual(out,[frame])
    def test_invalid_frames(self):
        for b in (b'[]\n',b'{"v":true,"type":"hi"}\n',b'{"v":2,"type":"hi"}\n',b'\xff\n',b'{"v":1,"type":"x","x":NaN}\n',b'{"v":1,"type":"x","x":1e999}\n'):
            with self.subTest(b=b),self.assertRaises((ValueError,UnicodeError)):Framer().feed(b)
    def test_depth(self):
        with self.assertRaises(ValueError):Framer().feed(b'{"v":1,"type":"x","a":'+b'['*14+b'0'+b']'*14+b'}\n')
    def test_unframed_limit(self):
        with self.assertRaises(ValueError):Framer().feed(b'x'*65536)
    def test_oversized_frame(self):
        with self.assertRaises(ValueError):encode(dict(v=1,type='x',data='x'*65536))
    def test_network_limits(self):
        for host in ('0.0.0.0','8.8.8.8','169.254.0.1','::1','example.com'):
            with self.subTest(host=host),self.assertRaises(ValueError):address(host)
        for host in ('10.1.2.3','172.16.1.1','192.168.1.2','127.0.0.1'):self.assertEqual(address(host),host)
        with self.assertRaises(ValueError):Client('127.0.0.1',0)

class ControlsTests(unittest.TestCase):
    def setUp(self):self.c=MemoryClient();self.ui=Controller(self.c)
    def tearDown(self):self.c.disconnect()
    def test_scale_mapping(self):
        notes=pitches(38,[0,2,3,5,7,9,10]);self.assertEqual(notes[:8],[38,40,41,43,45,47,48,50]);self.assertEqual(notes[8],43);self.assertEqual(notes[-1],86)
        self.assertEqual(pitches(26,[0,2,3,5,7,9,10])[0],26)
    def test_nonseven_scale(self):self.assertEqual(pitches(36,[0,3,5,7,10])[-1],103)
    def test_window_bounds(self):
        for base in (-1,100):
            with self.assertRaises(ValueError):pitches(base,[0,2,4,5,7,9,11])
    def test_onset_owned_across_selection(self):
        self.ui.channel['mode']='manual';self.ui.event(event('note',36,90));self.ui.select(1);self.ui.event(event('note_off',36,0))
        self.assertEqual(self.c.actions[0]['channel'],'ambient.drone');self.assertEqual(self.c.actions[0]['midi'],38)
        self.assertEqual(self.c.actions[0]['note_id'],self.c.actions[1]['note_id']);self.assertNotIn('channel',self.c.actions[1])
    def test_pressure_owned(self):
        self.ui.channel['mode']='manual';self.ui.event(event('note',36));self.ui.select(1);self.ui.event(event('poly_pressure',36,64))
        self.assertEqual(self.c.actions[-1]['action'],'pressure');self.assertEqual(self.c.actions[-1]['value'],64/127)
    def test_auto_rejects_manual(self):self.ui.event(event('note',36));self.assertEqual(self.c.actions,[])
    def test_disabled_parameter(self):
        self.ui.channel['parameters'][0]['enabled']=False;self.ui.event(event('cc',71,1));self.assertEqual(self.c.actions,[])
    def test_remote_authority_and_clamp(self):
        self.ui.event(event('cc',71,63));self.ui.event(event('cc',71,63));self.assertEqual(self.c.state['channels'][7]['parameters'][0]['value'],.5);self.assertEqual(self.c.actions[-1]['value'],1)
    def test_channels_page(self):
        self.ui.event(event('cc',49));self.ui.event(event('cc',63));self.assertEqual(self.ui.selected,8);self.assertEqual(self.ui.page,1)
    def test_mode_button(self):
        self.ui.event(event('cc',49));self.ui.event(event('cc',20));self.assertEqual(self.c.actions[-1]['mode'],'manual')
    def test_mute_button(self):self.ui.event(event('cc',20));self.assertEqual(self.c.actions[-1]['value'],0)
    def test_transport(self):
        self.ui.event(event('cc',85));self.assertEqual(self.c.actions[-1],dict(action='transport',state='playing'));self.assertEqual(self.c.state['transport']['state'],'stopped')
    def test_unknown_master(self):self.ui.event(event('cc',79,1));self.assertEqual(self.c.actions,[]);self.assertIn('unavailable',self.ui.message)
    def test_octave_waits_for_server(self):
        base=self.ui.channel['base_midi'];self.ui.event(event('cc',63));self.assertEqual(self.ui.channel['base_midi'],base);self.assertEqual(self.c.actions[-1]['base_midi'],base+12)
    def test_disconnect_clears_held(self):
        self.ui.channel['mode']='manual';self.ui.event(event('note',36));self.c.disconnect();self.ui.sync();self.assertFalse(self.ui.held);self.assertEqual(set(self.ui.leds().values()),{0})
    def test_drum_auto_selection(self):
        self.c.state=sample_state();self.ui.select(0);self.ui.event(event('note',37));self.assertEqual(self.c.actions[-1],dict(action='drum_select',choice_id='synthetic-1'))
    def test_chop_whole_line_epoch(self):
        self.c.state=sample_state();self.ui.select(5);self.ui.channel['mode']='manual';self.ui.event(event('note',99));f=self.c.actions[-1];self.assertEqual(f['pad'],63);self.assertEqual(f['bank_revision'],1)
    def test_unready_pad_dark(self):
        self.c.state=sample_state();self.ui.select(5);self.ui.channel['pad_bank']['pads'][0]['ready']=False;self.assertEqual(self.ui.leds()[36],0)
    def test_midi_running_status_and_pressure(self):
        events=MidiParser().feed(bytes([144,36,99,37,90,160,37,64,128,36,0]));self.assertEqual([e['kind'] for e in events],['note','note','poly_pressure','note_off'])
    def test_render_size_and_stopped(self):
        frame=render(self.ui);self.assertEqual(len(frame),1024*160*2);self.c.disconnect();self.assertEqual(len(render(self.ui)),len(frame))

class TransportTests(unittest.TestCase):
    def pump(self,c,predicate,seconds=2):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            c.tick()
            if predicate():return
            time.sleep(.003)
        self.fail('Timed out: '+c.error)
    def setUp(self):self.server=FakeServer(ambient=True).start();self.client=Client('127.0.0.1',self.server.port)
    def tearDown(self):self.client.disconnect();self.server.close()
    def test_connect_heartbeat_and_reconnect(self):
        c=self.client;self.pump(c,lambda:c.connected and c.rtt is not None);old=c.session;generation=c.generation
        c.command('parameter',channel='ambient.drone',parameter='gain',value=.7);self.pump(c,lambda:c.state['channels'][7]['parameters'][0]['value']==.7)
        self.server.drop();self.pump(c,lambda:not c.connected);self.pump(c,lambda:c.connected,3);self.assertNotEqual(c.session,old);self.assertGreater(c.generation,generation);self.assertFalse(c.edits)
    def test_note_release_original(self):
        c=self.client;self.pump(c,lambda:c.connected);ui=Controller(c);ui.event(event('cc',49));ui.event(event('cc',20));self.pump(c,lambda:ui.channel['mode']=='manual');ui.event(event('cc',85));self.pump(c,lambda:c.state['transport']['state']=='playing');ui.event(event('note',36));self.pump(c,lambda:bool(self.server.held));ui.select(1);ui.event(event('note_off',36,0));self.pump(c,lambda:not self.server.held)
    def test_stale_bank_rejected(self):
        c=self.client;self.pump(c,lambda:c.connected);self.server.state=sample_state(session=c.session);c.command('pad_on',channel='lofi.chops',note_id='old',pad=0,velocity=100,bank_revision=0);self.server.state['transport']['state']='playing';self.server.state['channels'][5]['mode']='manual';self.pump(c,lambda:c.error=='stale_bank');self.assertFalse(self.server.held)
    def test_coalesced_bounded_edits(self):
        c=self.client;self.pump(c,lambda:c.connected)
        for i in range(10000):c.command('parameter',channel='ambient.drone',parameter='gain',value=i/10000)
        self.assertEqual(len(c.edits),1);self.pump(c,lambda:len(self.server.commands)>0);self.assertEqual(len([f for f in self.server.commands if f['action']=='parameter']),1)
    def test_overflow_releases_connection(self):
        c=self.client;self.pump(c,lambda:c.connected)
        for _ in range(257):c.command('note_off',note_id='safe')
        self.assertFalse(c.connected);self.assertFalse(c.queue);self.assertIn('Backpressure',c.error)
    def test_stale_session_state_ignored(self):
        c=self.client;self.pump(c,lambda:c.connected);old=c.state;c.receive(sample_state('wrong'));self.assertIs(c.state,old)
    def test_old_revision_ignored(self):
        c=self.client;self.pump(c,lambda:c.connected);old=c.state;state=copy.deepcopy(old);state['revision']=0;state['channels']=[];c.receive(state);self.assertIs(c.state,old)

class SettingsAndBootTests(unittest.TestCase):
    def test_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            s=Settings(Path(d)/'settings.json');s.host='10.3.2.1';s.port=21000;s.save();s2=Settings(s.path);self.assertEqual((s2.host,s2.port),(s.host,s.port))
    def test_settings_physical_edit(self):
        with tempfile.TemporaryDirectory() as d:
            c=MemoryClient();ui=Controller(c,Settings(Path(d)/'settings.json'));ui.event(event('cc',30));ui.event(event('cc',74,1));ui.event(event('cc',27));self.assertEqual(c.host,'127.0.0.2');self.assertFalse(c.connected)
    def test_recovery_deliberate_confirmation(self):
        c=MemoryClient();ui=Controller(c);ui.event(event('cc',30));ui.event(event('cc',20));self.assertIsNone(ui.recovery_request);ui.event(event('cc',27));self.assertEqual(ui.recovery_request,'stillwater');c.disconnect()
    def test_init_preserved_and_reinstall_refused(self):
        spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install-boot.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);home=d/'home';init=d/'push3';stock=d/'stock';init.write_bytes(b'#!/bin/sh\n# synthetic previous selector\n');init.chmod(0o755);stock.write_bytes(b'#!/bin/sh\n# synthetic vendor\n');before=init.read_bytes();module.install(home,init,stock);self.assertEqual((home/'recovery/previous-init').read_bytes(),before);self.assertEqual((home/'recovery/stock-init').read_bytes(),stock.read_bytes());self.assertEqual((home/'boot-target').read_text(),'stillwater\n')
            with self.assertRaises(RuntimeError):module.install(home,init,stock)
    def test_supervisor_lock_ready_and_clean_shutdown(self):
        with tempfile.TemporaryDirectory() as d:
            cmd=[sys.executable,str(ROOT/'scripts/supervisor.py'),'--simulate','--home',d]
            first=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                end=time.monotonic()+3
                while not (Path(d)/'ready.json').exists() and time.monotonic()<end:time.sleep(.02)
                self.assertTrue((Path(d)/'ready.json').exists())
                second=subprocess.run(cmd,capture_output=True,text=True)
                self.assertNotEqual(second.returncode,0)
                first.terminate();first.communicate(timeout=7)
                self.assertEqual(first.returncode,0)
                self.assertFalse((Path(d)/'ready.json').exists())
                self.assertFalse((Path(d)/'owner.json').exists())
            finally:
                if first.poll() is None:first.terminate();first.communicate(timeout=7)
    def test_descriptor_bounds(self):
        c=MemoryClient();state=sample_state();state['revision']=2;state['channels']*=2
        with self.assertRaises(ValueError):c.receive(state)
        c.disconnect()
    def test_runtime_simulate_shutdown(self):
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(ROOT/'src/app.py'),'--simulate','--home',d,'--seconds','.2'],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);self.assertFalse((Path(d)/'ready.json').exists())

if __name__=='__main__':unittest.main()
