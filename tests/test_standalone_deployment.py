"""Recovery safety tests run against temporary files, never device init/data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
        base=dict(written=100,display_frames=10)
        current=dict(pid=42,ready=True,alive=True,written=200,display_frames=12,xruns=0,error='')
        self.assertTrue(module.healthy(base,current,42))
        for field,value in (('pid',43),('written',100),('display_frames',10),('xruns',1),('error','bad')):
            changed=dict(current);changed[field]=value;self.assertFalse(module.healthy(base,changed,42))
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
