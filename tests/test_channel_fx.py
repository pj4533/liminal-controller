"""Audible FX, admission, tail lifetime and physical page ownership regressions."""
import array
import ctypes as C
import math
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from channel_fx import defaults,parameters,pages,page_parameters
from sampler import Sampler,Event,Command,SR
from standalone import Instrument
from standalone_render import fit

class FxTests(unittest.TestCase):
    def capture(self,changes=(),ch=2,seconds=1,impulse=False,other=()):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            for channel,p,v in list(other)+[(ch,p,v) for p,v in changes]:s.command(16,channel,p,event=Event(gain=v))
            # Settle parameter smoothing before a fresh source starts.
            s.render(6000)
            pcm=array.array('f',([.7,.25]*16+[0,0]*(SR*3-16)) if impulse else (v for i in range(SR*3) for v in ((.4 if i%4000<2000 else .08)*math.sin(i*.137)+.10*math.sin(i*.013),.2*math.sin(i*.151))))
            slot=s.install(dict(revision=0,length=round(SR*64*60/69),pcm=[pcm],events=[]));s.render(1);s.command(3,ch,1)
            s.command(7,slot,0,identity=1,event=Event(channel=ch,sample=192+slot*16,gate=SR*3,speed=1,gain=1,attack=1,release=64))
            return list(s.render(round(SR*seconds)))
        finally:s.close()
    def difference(self,a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a))
    def test_each_sound_processor_changes_actual_pcm(self):
        dry=self.capture()
        for p,value in ((0,.2),(1,900),(2,900),(3,18),(4,6),(5,1),(6,0),(7,1)):
            with self.subTest(parameter=p):self.assertGreater(self.difference(dry,self.capture([(p,value)])),.0001)
    def test_channel_character_algorithms_are_audible(self):
        for ch in range(6):
            with self.subTest(channel=ch):self.assertGreater(self.difference(self.capture(ch=ch),self.capture([(4,parameters(ch)[4].high)],ch=ch)),.00001)
    def test_each_motion_control_changes_actual_pcm(self):
        dry=self.capture()
        for p,v in ((16,.35),(19,1),(20,1),(21,.8),(23,1)):
            with self.subTest(parameter=p):self.assertGreater(self.difference(dry,self.capture([(p,v)])),.00001)
        for p,v in ((17,2),(18,6)):
            with self.subTest(parameter=p):self.assertGreater(self.difference(self.capture([(16,.35)]),self.capture([(16,.35),(p,v)])),.00001)
        self.assertGreater(self.difference(self.capture([(21,.8)]),self.capture([(21,.8),(22,0)])),.00001)
    def test_each_space_control_changes_actual_pcm(self):
        dry=self.capture(seconds=2)
        for p,v,base in ((8,.4,[]),(9,0,[(8,.4)]),(10,.65,[(8,.4)]),(11,800,[(8,.4)]),(12,.35,[]),(13,4,[(12,.35)]),(14,1500,[(12,.35)]),(15,60,[(12,.35)])):
            with self.subTest(parameter=p):
                before=self.capture(base,seconds=2) if base else dry
                self.assertGreater(self.difference(before,self.capture(base+[(p,v)],seconds=2)),.000001)
    def test_echo_and_room_have_independent_impulse_responses(self):
        dry=self.capture(impulse=True)
        echo=self.capture([(8,.4)],impulse=True)
        room=self.capture([(12,.35)],impulse=True)
        # Comb room begins in tens of ms; tempo echo arrives much later.
        self.assertLess(self.difference(dry[4000:12000],echo[4000:12000]),1e-12)
        self.assertGreater(max(map(abs,room[4000:12000])),1e-6)
        self.assertGreater(self.difference(echo,room),1e-5)
    def test_zero_width_monos_all_stereo_wet_paths(self):
        out=self.capture([(6,0),(8,.4),(12,.35),(16,.35)],seconds=2)
        # Width is smoothed; allow its20ms settling from the default unity.
        side=max(abs(out[i]-out[i+1]) for i in range(SR,len(out),2))
        self.assertLess(side,1e-7)
    def test_inactive_processors_have_no_delayed_tail(self):
        out=self.capture(impulse=True)
        self.assertLess(max(map(abs,out[4000:])),1e-12)
    def test_other_channel_edits_cannot_change_source_bus(self):
        changes=[(ch,p.id,p.high) for ch in (0,1,3,4,5) for p in parameters(ch)]
        self.assertEqual(self.capture(),self.capture(other=changes))
    def test_generated_bounds_are_current(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/generate-fx.py'),'--check'],check=True)
    def test_python_rejects_nonfinite_and_bad_addresses(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            for ch,p,v in ((-1,0,1),(6,0,1),(0,-1,1),(0,24,1),(0,1,float('nan')),(0,3,float('inf'))):
                with self.subTest(address=(ch,p,v)),self.assertRaises(ValueError):s.command(16,ch,p,event=Event(gain=v))
        finally:s.close()
    def test_native_rejects_nonfinite_and_bad_addresses(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            for ch,p,v in ((-1,0,1),(6,0,1),(0,-1,1),(0,24,1),(0,1,float('nan')),(0,3,float('inf'))):
                command=Command(op=16,a=ch,b=p,event=Event(gain=v))
                self.assertEqual(s.lib.lm_command(s.ptr,C.byref(command)),-1)
            self.assertEqual(s.status()['overflow'],0)
        finally:s.close()
    def test_native_clamps_same_as_python_including_bass_safe_ranges(self):
        # Bypass the Python admission layer to test both native range boundaries.
        for ch,p,v in ((1,1,99999),(1,6,99),(2,10,999),(0,4,-99),(5,12,-99),(2,9,99),(2,9,2.5)):
            def capture(raw):
                s=Sampler(ROOT/'.build/engine.so')
                try:
                    c=Command(op=16,a=ch,b=p,event=Event(gain=v if raw else parameters(ch)[p].clamp(v)))
                    self.assertEqual(s.lib.lm_command(s.ptr,C.byref(c)),1)
                    s.sample(0,array.array('f',[.2,-.1])*10000);s.install(dict(revision=0,length=10000,pcm=[],events=[dict(frame=0,channel=ch,sample=0,gate=9000,speed=1,gain=1,attack=1,release=32)]));s.command(1)
                    return bytes(s.render(9000))
                finally:s.close()
            with self.subTest(channel=ch,parameter=p):self.assertEqual(capture(True),capture(False))
    def test_all_effects_maximum_remain_bounded_and_stop_clears_restart_tails(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            pcm=array.array('f',(v for i in range(SR*2) for v in (math.sin(i*.21)*.7,math.sin(i*.17)*.7)))
            s.sample(0,pcm);slot=s.install(dict(revision=0,length=SR*8,pcm=[],events=[]));s.render(1)
            for ch in range(6):
                s.command(3,ch,1)
                for p in parameters(ch):s.command(16,ch,p.id,event=Event(gain=p.high))
                for i in range(10):s.command(7,slot,identity=1+ch*10+i,event=Event(channel=ch,sample=0,gate=SR*2,speed=1,gain=1,attack=1,release=256))
            out=s.render(SR*2);self.assertTrue(all(math.isfinite(x) and abs(x)<1 for x in out));self.assertEqual(s.status()['overflow'],0)
            s.command(2);s.render(1323);self.assertEqual(max(map(abs,s.render(SR))),0)
            s.command(1);self.assertEqual(max(map(abs,s.render(SR))),0)
        finally:s.close()
    def test_disabling_and_reenabling_wet_effects_cannot_resurrect_history(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            s.sample(0,array.array('f',[.4,.4])*400)
            slot=s.install(dict(revision=0,length=round(SR*64*60/69),pcm=[],events=[]));s.render(1);s.command(3,2,1)
            for p,v in ((8,.4),(12,.35),(13,4),(16,.35)):s.command(16,2,p,event=Event(gain=v))
            s.render(6000);s.command(7,slot,identity=1,event=Event(channel=2,sample=0,gate=300,speed=1,gain=1,attack=1,release=64));s.render(2000)
            for p in (8,12,16):s.command(16,2,p,event=Event(gain=0))
            s.render(SR)
            for p,v in ((8,.4),(12,.35),(16,.35)):s.command(16,2,p,event=Event(gain=v))
            self.assertEqual(max(map(abs,s.render(SR*2))),0)
        finally:s.close()
    def test_maximum_feedback_room_decay_have_finite_decaying_tail(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            s.sample(0,array.array('f',[.8,.8])*32)
            slot=s.install(dict(revision=0,length=round(SR*64*60/69),pcm=[],events=[]));s.render(1);s.command(3,2,1)
            for p,v in ((8,.4),(10,.65),(12,.35),(13,4),(14,12000)):s.command(16,2,p,event=Event(gain=v))
            s.render(6000);s.command(7,slot,identity=1,event=Event(channel=2,sample=0,gate=32,speed=1,gain=1,attack=1,release=8))
            early=list(s.render(SR*3));late=list(s.render(SR*12))
            self.assertTrue(all(math.isfinite(x) and abs(x)<1 for x in early+late))
            self.assertLess(max(map(abs,late[-SR*2:])),max(map(abs,early))*.02)
        finally:s.close()
    def test_continuous_gain_and_pan_smooth_instead_of_step(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            s.sample(0,array.array('f',[.2,.2])*SR);s.install(dict(revision=0,length=SR*8,pcm=[],events=[dict(frame=0,channel=2,sample=0,gate=SR,speed=1,gain=1,attack=1,release=32)]));s.command(1);s.render(6000)
            before=list(s.render(1));s.command(16,2,7,event=Event(gain=1));after=list(s.render(1))
            self.assertLess(abs(before[0]-after[0]),.0002)
            s.render(6000);self.assertLess(abs(s.render(1)[0]),abs(before[0])*.01)
        finally:s.close()
    def test_division_change_crossfades_without_resetting_transport(self):
        s=Sampler(ROOT/'.build/engine.so')
        try:
            s.sample(0,array.array('f',[.2,.2])*(SR*2));s.install(dict(revision=0,length=SR*64,pcm=[],events=[dict(frame=0,channel=2,sample=0,gate=SR*2,speed=1,gain=1,attack=1,release=32)]));s.command(16,2,8,event=Event(gain=.4));s.command(1);s.render(SR)
            position=s.status()['position'];s.command(16,2,9,event=Event(gain=0));out=list(s.render(4096))
            self.assertEqual(s.status()['position'],position+4096)
            self.assertLess(max(abs(out[i+2]-out[i]) for i in range(len(out)-2)),.002)
        finally:s.close()

class FxControlTests(unittest.TestCase):
    def ui(self):
        ui=Instrument.__new__(Instrument);ui.settings=False;ui.help=False;ui.shift=False;ui.mix=False;ui.selected=0;ui.fx_pages=[0]*6;ui.effects=[defaults(ch) for ch in range(6)];ui.level=[.65]*6;ui.master=.45;ui.held={36:19};ui.manual=[True]*6;ui.muted=[False]*6;ui.recovery_target=None;ui.recovery_request=None
        ui.sent=[];ui.send=lambda *args,**kw:ui.sent.append((args,kw));return ui
    def event(self,ui,n,v=127,kind='cc'):ui.event(dict(kind=kind,number=n,value=v))
    def test_all_channel_page_encoders_use_metadata(self):
        ui=self.ui()
        for ch in range(6):
            self.event(ui,102+ch)
            for page in range(3):
                self.assertEqual(ui.fx_pages[ch],page)
                for knob,p in enumerate(page_parameters(ch,page)):
                    before=ui.effects[ch][p.id];self.event(ui,71+knob,1)
                    self.assertAlmostEqual(ui.effects[ch][p.id],p.edit(before,1))
                    self.assertEqual(ui.sent[-1][0],(16,ch,p.id))
                self.event(ui,27)
    def test_first_entry_sound_and_per_channel_page_memory(self):
        ui=self.ui();self.event(ui,106);self.assertEqual(ui.fx_pages[4],0)
        self.event(ui,27);self.event(ui,27);self.event(ui,107);self.assertEqual(ui.fx_pages[5],0)
        self.event(ui,106);self.assertEqual(ui.fx_pages[4],2);self.event(ui,27);self.assertEqual(pages(4)[ui.fx_pages[4]],'CUTS')
        self.event(ui,26);self.assertEqual(ui.fx_pages[4],2)
        self.assertFalse(ui.sent);self.assertEqual(ui.held,{36:19})
    def test_held_release_routes_before_settings_or_fx_view(self):
        ui=self.ui()
        for ch in range(6):
            self.event(ui,102+ch)
            for page in range(len(pages(ch))):
                ui.fx_pages[ch]=page;ui.settings=bool(page%2);ui.held={36:19}
                self.event(ui,36,0,'note');self.assertEqual(ui.sent[-1][0],(8,));self.assertEqual(ui.sent[-1][1]['identity'],19)
            ui.settings=False
    def test_settings_owns_lower_seven_eight_before_fx(self):
        ui=self.ui();self.event(ui,30);self.event(ui,20);self.event(ui,27)
        self.assertEqual(ui.recovery_request,'stillwater');self.assertEqual(ui.fx_pages,[0]*6);self.assertEqual(ui.sent[-1][0],(2,))
        self.event(ui,26);self.assertFalse(ui.settings);self.assertEqual(ui.fx_pages,[0]*6)
    def test_mix_encoders_keep_level_in_sound_page(self):
        ui=self.ui();self.event(ui,112);self.event(ui,72,1)
        self.assertEqual(ui.level[1],.66);self.assertEqual(ui.effects[1][0],.66);self.assertEqual(ui.sent[-1][0],(4,1))
        self.event(ui,27);self.assertEqual(ui.fx_pages,[0]*6)
    def test_long_values_fit_inside_each_physical_column(self):
        for ch in range(6):
            for p in parameters(ch):
                self.assertEqual(fit(p.label,104,2),p.label)
                for value in (p.low,p.default,p.high):self.assertEqual(fit(p.display(value),104,2),p.display(value))
