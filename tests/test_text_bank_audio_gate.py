"""Fault injection tests for the release oracle, independent of text selection."""
import array,importlib.util,math,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('text_gate',ROOT/'scripts/qualify-text-bank.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class AudioGate(unittest.TestCase):
    def setUp(self):
        self.engine=gate.Sampler(ROOT/'.build/engine.so')
        pcm=array.array('f',(math.sin(i*.013+i*i*.000001)*.3 for i in range(12000)))
        self.bank=dict(pcm=[pcm,pcm],length=24000,revision=10,archive_id='test',events=[],cuts=[(0,6000),(1200,1800),(3300,2100)],chop_gains=[.8]*3,dialogue=dict(line='test',labels=['whole','first','second']))
    def tearDown(self):self.engine.close()
    def test_native_reference_and_natural_end(self):
        captures=gate.manual_audio(self.bank,self.engine)
        self.assertEqual(len({c['audio_sha256'] for c in captures}),3)
        self.assertTrue(all(c['reference_match'] and c['natural_end'] for c in captures))
    def mutate(self,kind):
        original=gate.Instrument.onset
        def onset(ui,slot,revision,identity,event):
            if kind=='whole':event.frame,event.gate=ui.current['cuts'][0]
            elif kind=='offset':event.frame+=100
            else:event.gate+=100
            return original(ui,slot,revision,identity,event)
        return patch.object(gate.Instrument,'onset',onset)
    def test_wrong_dispatch_rejected(self):
        for kind in ('whole','offset','duration'):
            with self.subTest(kind=kind),self.mutate(kind),self.assertRaisesRegex(AssertionError,'Dispatched source/range'):
                gate.manual_audio(self.bank,self.engine)
    def test_audio_oracle_independently_rejects_whole_phrase(self):
        with self.mutate('whole'),patch.object(gate,'assert_dispatch'),self.assertRaisesRegex(AssertionError,'naturally|Actual native audio'):
            gate.manual_audio(self.bank,self.engine)
    def test_audio_oracle_independently_rejects_wrong_offset(self):
        with self.mutate('offset'),patch.object(gate,'assert_dispatch'),self.assertRaisesRegex(AssertionError,'Actual native audio'):
            gate.manual_audio(self.bank,self.engine)
