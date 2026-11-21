"""Recovery safety tests run against temporary files, never device init/data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,MagicMock

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class DeploymentTests(unittest.TestCase):
    def test_stock_autostart_rejected_before_release(self):
        module=load('deploy','deploy-staged.py')
        with tempfile.TemporaryDirectory() as t:
            init=Path(t)/'init';init.write_bytes(b'other stock')
            with self.assertRaisesRegex(RuntimeError,'designated primary'):module.preflight(init,False)
            self.assertEqual(init.read_bytes(),b'other stock')
    def test_qualification_requires_known_init(self):
        module=load('deploy','deploy-staged.py')
        with tempfile.TemporaryDirectory() as t:
            init=Path(t)/'init';init.write_bytes(b'unknown')
            with self.assertRaisesRegex(RuntimeError,'Unknown active init'):module.preflight(init,True)
    def test_rollback_refuses_competing_owner(self):
        module=load('deploy','deploy-staged.py')
        class Owner:
            def competitors(self):return [123]
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);init=home/'init';init.write_bytes(b'unchanged')
            with self.assertRaisesRegex(RuntimeError,'competing owner'):module.recover(home,init,b'prior',Owner())
            self.assertEqual(init.read_bytes(),b'unchanged')
    def test_boot_success_requires_audio_and_display_progress(self):
        module=load('boot_success','boot-success.py')
        base=dict(written=100,display_frames=10,xruns=0)
        current=dict(pid=42,ready=True,alive=True,written=200,display_frames=12,xruns=0,error='')
        self.assertTrue(module.healthy(base,current,42))
        for field,value in (('pid',43),('written',100),('display_frames',10),('xruns',1),('error','bad')):
            changed=dict(current);changed[field]=value;self.assertFalse(module.healthy(base,changed,42))
    def boot_window(self,changes):
        module=load('boot_success_window','boot-success.py');clock=[100.0];home=MagicMock()
        def snapshot():
            elapsed=clock[0]-100
            current=dict(pid=42,ready=True,alive=True,written=int(elapsed*44100)+100,display_frames=int(elapsed*10)+10,xruns=1,error='',monotonic=clock[0])
            current.update(changes(elapsed));return json.dumps(current)
        home.__truediv__.return_value.read_text.side_effect=snapshot
        def sleep(seconds):clock[0]+=seconds
        with patch.object(module.time,'monotonic',side_effect=lambda:clock[0]),patch.object(module.time,'sleep',side_effect=sleep):
            result=module.wait_ready(home,42)
        return result,clock[0]-100
    def test_boot_accepts_clean_window_after_startup_xrun(self):
        (base,final,elapsed),wall=self.boot_window(lambda _: {})
        self.assertEqual((base['xruns'],final['xruns']),(1,1));self.assertEqual(elapsed,60);self.assertEqual(wall,60)
    def test_boot_xrun_increment_or_decrease_restarts_window(self):
        for count in (0,2):
            with self.subTest(count=count):
                (base,final,elapsed),wall=self.boot_window(lambda t:dict(xruns=count) if t>=10 else {})
                self.assertEqual((base['xruns'],final['xruns']),(count,count));self.assertEqual(elapsed,60);self.assertGreaterEqual(wall,70.5)
    def test_boot_rejects_unready_stale_errors_and_nonadvancing_counters(self):
        for change in (dict(ready=False),dict(alive=False),dict(pid=43),dict(error='bad'),dict(monotonic=1),dict(written=100),dict(display_frames=10)):
            with self.subTest(change=change),self.assertRaisesRegex(RuntimeError,'readiness timeout'):
                self.boot_window(lambda _,change=change:change)
    def test_boot_initial_unready_sample_does_not_start_window(self):
        (_,_,elapsed),wall=self.boot_window(lambda t:dict(ready=False) if t<5 else {})
        self.assertEqual(elapsed,60);self.assertEqual(wall,65)
    def test_boot_repeated_xruns_never_complete_window(self):
        with self.assertRaisesRegex(RuntimeError,'readiness timeout'):
            self.boot_window(lambda t:dict(xruns=1+int(t//10)))
    def test_install_refuses_existing_recovery(self):
        module=load('installer','install-standalone.py')
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);(home/'recovery').mkdir()
            with self.assertRaisesRegex(RuntimeError,'Existing recovery'):module.install(home,home/'absent-init')
    def test_install_refuses_unrecognized_init_without_writing(self):
        module=load('installer','install-standalone.py')
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);init=home/'init';init.write_bytes(b'unknown stock init')
            with self.assertRaisesRegex(RuntimeError,'Expected previously'):module.install(home,init)
            self.assertEqual(init.read_bytes(),b'unknown stock init');self.assertFalse((home/'recovery').exists())
    def test_recovery_rejects_changed_bytes(self):
        module=load('boot','standalone-boot.py')
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);recovery=home/'recovery';recovery.mkdir();(recovery/'previous-init').write_bytes(b'original')
            (recovery/'init-hashes.json').write_text(json.dumps({'previous-init':hashlib.sha256(b'original').hexdigest()}))
            self.assertEqual(module.original(home),recovery/'previous-init')
            (recovery/'previous-init').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError,'hash mismatch'):module.original(home)
    def test_return_to_liminal_stops_prior_selected_owner(self):
        module=load('boot','standalone-boot.py')
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);(home/'boot-target').write_text('stillwater\n');old=home/'old-init'
            with patch.object(sys,'argv',['boot','select','liminal','--home',str(home)]),patch.object(module,'stopped') as stopped,patch.object(module,'original',return_value=old),patch.object(module.subprocess,'run') as run:
                module.main()
            stopped.assert_called_once_with(home);run.assert_called_once_with([str(old),'stop'],check=True)
            self.assertEqual((home/'boot-target').read_text(),'liminal\n')
    def test_stop_refuses_live_app_after_supervisor_exit(self):
        module=load('boot','standalone-boot.py')
        with tempfile.TemporaryDirectory() as t:
            home=Path(t);(home/'owner.json').write_text(json.dumps({'pid':123,'start':'known'}))
            with patch.object(module.owner,'alive',return_value=True),self.assertRaisesRegex(RuntimeError,'App still alive'):module.stopped(home)

if __name__=='__main__':unittest.main()
