import array
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import threading
import time
import unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dialogue_speech import parse,Speech,OPTIONS,MODEL_SHA
from dialogue_text import Selector,weights,interest,protected
from dialogue import plan
from standalone import slice_note,slice_index
from sampler import SR

def document(tokens=None):
    return {'transcription':[dict(offsets=dict(**{'from':0,'to':3000}),tokens=tokens or [dict(text=' Strange',t_dtw=30),dict(text=' dream',t_dtw=100),dict(text="'s",t_dtw=120),dict(text=' machine',t_dtw=200),dict(text='!',t_dtw=-1)])]}
def spans(text):return [dict(text=w,start=i*.4,end=(i+1)*.4,confidence=None) for i,w in enumerate(text.split())]

class TimestampTests(unittest.TestCase):
    def test_dtw_subwords_contractions_punctuation_without_offsets(self):
        result=parse(document(),3)['lines'][0]['words']
        self.assertEqual([w['text'] for w in result],['Strange',"dream's",'machine!'])
        self.assertTrue(all(w['confidence'] is None for w in result))
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(result,result[1:])))
    def test_collapsed_missing_backward_outside_and_bracket_events_rejected(self):
        for tokens in ([dict(text=' word',t_dtw=0),dict(text=' next',t_dtw=0)],[dict(text=' word')],[dict(text=' word',t_dtw=100),dict(text=' next',t_dtw=50)],[dict(text=' word',t_dtw=400)],[dict(text='[Music]',t_dtw=50)]):
            with self.subTest(tokens=tokens),self.assertRaises(ValueError):parse(document(tokens),3)
    def test_duplicate_or_reversed_segments_not_added(self):
        doc=document();doc['transcription']*=3
        self.assertEqual(len(parse(doc,3)['lines']),1)
    def test_repeated_hallucination_grams_rejected(self):
        tokens=[dict(text=' '+w,t_dtw=10+i*20) for i,w in enumerate(('one','two','three')*3)]
        with self.assertRaises(ValueError):parse(document(tokens),3)

class MeaningTests(unittest.TestCase):
    def test_lexical_interest_prefers_vivid_content_to_connectives(self):
        words=spans('the strange dream machine');v=weights(words,['DT','JJ','NN','NN'])
        self.assertEqual(v[0],0);self.assertGreater(v[2],.8)
        plain=spans('it is just the thing');pv=weights(plain,['PRP','VBZ','RB','DT','NN'])
        self.assertGreater(interest(words,v,['DT','JJ','NN','NN']),interest(plain,pv,['PRP','VBZ','RB','DT','NN']))
    def test_names_negation_contractions_numbers_remain_protected(self):
        self.assertEqual(protected(spans('Sally do not open the door'),['RB','VB','RB','VB','DT','NN']),[(0,6)])
        for text,tags,expected in [('we do not open',['PRP','VB','RB','VB'],(1,4)),("we can't sleep",['PRP','MD','VB'],(1,3)),('three red machines',['CD','JJ','NNS'],(0,3))]:
            self.assertTrue(any(a<=expected[0] and b>=expected[1] for a,b in protected(spans(text),tags)))
    def selector(self):
        x=Selector.__new__(Selector);x.tagger=Mock();x.tagger.tag.side_effect=lambda words:[(w,'DT' if w.lower()=='the' else 'NN') for w in words];return x
    def test_full_line_and_unique_meaningful_fragments_with_anchor_continuity(self):
        pcm=array.array('f',[.1,-.1])*(SR*5);words=spans('the strange dream machine!');transcript=dict(lines=[dict(start=0,end=1.6,words=words)])
        selected=self.selector().select(pcm,transcript,0);again=self.selector().select(pcm,transcript,3)
        self.assertEqual(selected,again);self.assertEqual(selected['labels'][0],'the strange dream machine!')
        self.assertTrue(any('dream' in t for t in selected['labels'][1:]));self.assertNotIn('the',selected['labels'][1:]);self.assertEqual(len(set(selected['cuts'])),len(selected['cuts']))
        hits,indices,grid=plan(pcm,selected['cuts'],pcm,69,0,semantic=selected)
        self.assertEqual(hits[0][1:3],(0,None));self.assertEqual(hits[-1][1:3],(0,None));self.assertGreaterEqual(hits[1][3],selected['cuts'][0][1]/SR)
    def test_name_sentence_cannot_be_split_or_reordered(self):
        pcm=array.array('f',[.1,-.1])*(SR*5);words=spans('Sally do not open the door!');x=self.selector();x.tagger.tag.side_effect=lambda words:list(zip(words,['RB','VB','RB','VB','DT','NN']))
        selected=x.select(pcm,dict(lines=[dict(start=0,end=2.4,words=words)]),0)
        self.assertEqual(len(selected['cuts']),1);self.assertFalse(selected['reorder'])
    def test_protected_units_are_never_gated_or_interrupted_by_later_hits(self):
        pcm=array.array('f',[.1,-.1])*(SR*8)
        cuts=[(0,SR*2),(SR*2,SR),(SR*3,SR)]
        semantic=dict(signature=1,response=2,reorder=True,protected_cuts=[0,1])
        for revision in range(8):
            arc,_,_=plan(pcm,cuts,pcm,69,revision,semantic=semantic)
            self.assertEqual(arc[-1][1:3],(0,None))
        hits,selected,grid=plan(pcm,cuts,pcm,69,0,semantic=semantic)
        for i,(step,piece,gate,accent) in enumerate(hits):
            if piece not in semantic['protected_cuts']:continue
            self.assertIsNone(gate)
            if i+1<len(hits):self.assertGreaterEqual(hits[i+1][3],accent+cuts[piece][1]/SR)
    def test_silence_has_no_text_cuts(self):
        pcm=array.array('f',[0,0])*(SR*3)
        with self.assertRaises(ValueError):self.selector().select(pcm,dict(lines=[dict(words=spans('strange dream'))]),0)

class SpeechProcessTests(unittest.TestCase):
    def setup_speech(self,home):
        speech=Speech(home,timeout=.02);speech.verify=Mock();return speech
    def test_success_cache_avoids_repeated_inference(self):
        with tempfile.TemporaryDirectory() as home:
            speech=self.setup_speech(home);pcm=array.array('f',[.1,-.1])*(SR*3)
            def spawn(cmd,**kwargs):
                path=Path(cmd[cmd.index('-of')+1]).with_suffix('.json');path.write_text(json.dumps(document()));p=Mock();p.wait.return_value=0;return p
            with patch('dialogue_speech.subprocess.Popen',side_effect=spawn) as p:
                first=speech.transcript(pcm);self.assertEqual(first,speech.transcript(pcm));self.assertEqual(p.call_count,1)
                cmd=p.call_args.args[0];self.assertIn('-nfa',cmd);self.assertEqual(cmd[cmd.index('-t')+1],'1')
    def test_deadline_kills_reaps_and_failure_does_not_storm(self):
        with tempfile.TemporaryDirectory() as home:
            speech=self.setup_speech(home);p=Mock();p.wait.side_effect=[subprocess.TimeoutExpired('worker',.02),0]
            pcm=array.array('f',[.1,-.1])*SR
            with patch('dialogue_speech.subprocess.Popen',return_value=p) as spawn:
                with self.assertRaises(TimeoutError):speech.transcript(pcm)
                with self.assertRaises(ValueError):speech.transcript(pcm)
                self.assertEqual(spawn.call_count,1);p.kill.assert_called_once();self.assertEqual(p.wait.call_count,2)
    def test_close_reaps_active_and_rejects_new_work(self):
        with tempfile.TemporaryDirectory() as home:
            speech=self.setup_speech(home);p=Mock();p.poll.return_value=None;speech.process=p;speech.close();p.kill.assert_called_once();p.wait.assert_called_once()
            with self.assertRaises(RuntimeError):speech.transcript(array.array('f',[0,0]))
    def test_hash_failure_is_honest_unavailable(self):
        with tempfile.TemporaryDirectory() as home:
            speech=Speech(home,tools=home)
            with self.assertRaises((RuntimeError,FileNotFoundError)):speech.transcript(array.array('f',[0,0])*SR)
            self.assertEqual(speech.state,'UNAVAILABLE')

class PadLayoutTests(unittest.TestCase):
    def test_ableton_quadrants_inverse_unique(self):
        self.assertEqual([slice_note(i) for i in (0,3,4,15,16,31,32,47,48,63)],[36,39,44,63,68,95,40,67,72,99])
        self.assertEqual(len({slice_note(i) for i in range(64)}),64)
        for i in range(64):self.assertEqual(slice_index(slice_note(i)),i)
