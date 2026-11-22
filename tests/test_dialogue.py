"""Source-derived acoustic chop policy: fixture signals, no private media."""
import array
import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dialogue import attack,vocabulary,drum_grid,plan,FEELS
from sampler import SR

class DialogueTests(unittest.TestCase):
    def source(self):
        return array.array('f',(v for k in range(SR*2) for v in (math.sin(k*.07)*(.12 if k%(SR//4)>SR//20 else 0),)*2))
    def test_attack_skips_quiet_lead_retains_bounded_soft_lead_and_silence_fallback(self):
        pcm=array.array('f',[0,0])*(SR//10)+array.array('f',[.2,-.2])*(SR//5)
        start,lead,fade=attack(pcm,0,len(pcm)//2)
        self.assertGreater(start,SR*.09);self.assertLessEqual(lead,round(.033*SR))
        self.assertIn(fade,(round(.002*SR),round(.005*SR)))
        self.assertEqual(attack(array.array('f',[0,0])*SR,0,SR),(0,0,round(.005*SR)))
    def test_vocabulary_prefers_audible_cut_in_each_region_without_losing_source_spread(self):
        pcm=array.array('f');cuts=[]
        for i in range(64):
            cuts.append((i*256,256));pcm.extend(array.array('f',[.2,-.2] if i%8==3 else [0,0])*256)
        self.assertEqual(vocabulary(pcm,cuts),list(range(3,64,8)))
    def test_grid_measures_real_attack_offsets_strictly_and_handles_silence(self):
        pcm=array.array('f',[0,0])*(SR*32)
        onset=round(.020*SR);pcm[onset*2:(onset+256)*2]=array.array('f',[.5,-.5])*256
        grid,activity=drum_grid(pcm,120)
        self.assertAlmostEqual(grid[0],.020,delta=.006);self.assertGreater(activity[0],0)
        self.assertTrue(all(a<b for a,b in zip(grid,grid[1:])))
        self.assertEqual(drum_grid(array.array('f',[0,0])*SR,120)[0],[s*.125 for s in range(256)])
    def test_drum_grid_stretches_source_attacks_with_whole_take_playback(self):
        pcm=array.array('f',[0,0])*(SR*16)
        onset=SR//2+round(.01*SR)
        pcm[onset*2:(onset+100)*2]=array.array('f',[.5,-.5])*100
        grid,activity=drum_grid(pcm,120)
        self.assertGreater(activity[8],0)
        self.assertAlmostEqual(grid[8],1.02,delta=.012)
    def test_arc_is_seeded_varied_bounded_and_maps_every_hit_to_exact_source_cut(self):
        pcm=self.source();cuts=[(i*SR//4,SR//4) for i in range(8)]
        plans=[]
        for revision in range(6):
            result,selected,grid=plan(pcm,cuts,pcm,69,revision);plans.append(result)
            self.assertEqual((result,selected,grid),plan(pcm,cuts,pcm,69,revision))
            self.assertTrue(all(0<=piece<len(selected) and 0<=s<256 and accent>=0 for s,piece,g,accent in result))
            self.assertTrue(all(a[1]!=b[1] for a,b in zip(result,result[1:])))
            self.assertEqual(set(s//32 for s,p,g,a in result),set(range(8)))
            for s,p,g,accent in result:
                self.assertLessEqual(abs(accent-grid[s]),.0250001)
                if s%4==0 or not 32<=s<128:self.assertEqual(accent,grid[s])
            # Source-order runs end at signature0; no guessed semantic permission.
            heard=set();order=[];bar=-1
            for s,p,g,a in result:
                if s//16!=bar:bar=s//16;heard=set();order=[]
                if p==0:heard=set();order=[];continue
                if p not in heard:heard.add(p);order.append(p)
                self.assertEqual(order,sorted(order))
            self.assertLess(sum(128<=s<192 for s,p,g,a in result),sum(32<=s<96 for s,p,g,a in result))
        self.assertTrue(all(a!=b for a,b in zip(plans,plans[1:])))
    def test_short_single_and_empty_sources_are_bounded(self):
        pcm=array.array('f',[.1,-.1])*200
        self.assertEqual(plan(pcm,[],pcm,69,0),([],[],[]))
        for count in (1,2):
            result,selected,_=plan(pcm,[(i*50,50) for i in range(count)],pcm,69,0)
            self.assertEqual(len(selected),count);self.assertTrue(result)
