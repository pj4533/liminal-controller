"""Wire-channel ownership of hardware controls, independent of pad expression."""
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from midi import MidiParser
from channel_fx import pages,page_parameters
import test_channel_fx as fx
import test_chop_gate as chops

class FxMidiRoutingTests(unittest.TestCase):
    def wire(self,ui,data,parser=None):
        parser=parser or MidiParser()
        # Exercise status/data fragmentation and interleaved realtime bytes.
        for byte in data:
            for event in parser.feed(bytes([byte])):ui.event(event)
    def test_member_expression_sweep_cannot_edit_any_page_or_mix(self):
        for ch in range(6):
            for page in range(len(pages(ch))+1):
                ui=fx.FxControlTests().ui();ui.selected=ch
                ui.mix=page==len(pages(ch));ui.fx_pages[ch]=min(page,len(pages(ch))-1)
                before=copy.deepcopy(ui.__dict__)
                for member in range(1,16):
                    parser=MidiParser()
                    self.wire(ui,[0xb0+member,74,0],parser)
                    for value in range(1,128):self.wire(ui,[74,248,value],parser)
                with self.subTest(channel=ch,page=page):
                    self.assertEqual(ui.__dict__,before)
                # The actual channel-zero knob remains operative on each page.
                if ui.mix:
                    self.wire(ui,[0xb0,74,1]);self.assertEqual(ui.level[3],.66)
                    self.assertEqual(ui.sent[-1][0],(4,3))
                elif page<4:
                    for knob,p in enumerate(page_parameters(ch,page)):
                        value=ui.effects[ch][p.id]
                        self.wire(ui,[0xb0,71+knob,1]);self.assertEqual(ui.effects[ch][p.id],p.edit(value,1))
                        self.assertEqual(ui.sent[-1][0],(16,ch,p.id))
    def test_entire_member_control_namespace_is_inert(self):
        ui=fx.FxControlTests().ui();ui.octave=0;ui.drum_page=0
        for settings in (False,True):
            ui.settings=settings;before=copy.deepcopy(ui.__dict__)
            for member in range(1,16):
                parser=MidiParser()
                # Every CC includes encoders, transport, selection, overlays,
                # recovery, cuts, modes, Shift, Repeat and master volume.
                self.wire(ui,[0xb0+member,0,127],parser)
                for cc in range(1,128):self.wire(ui,[cc,127,cc,0],parser)
            self.assertEqual(ui.__dict__,before)
        ui.settings=False
        self.wire(ui,[0xb0,107,127,112,127,79,1,85,127])
        self.assertEqual(ui.selected,5);self.assertTrue(ui.mix)
        self.assertEqual(ui.master,.46);self.assertEqual(ui.sent[-1][0],(15,))
    def test_member_notes_and_releases_survive_views_and_expression(self):
        fixture=chops.ChopGateTests();fixture.setUp()
        try:
            ui=fixture.ui;ui.mix=False;ui.level=[.65]*6;ui.master=.45;ui.muted=[False]*6
            for member in range(1,16):
                for release in (0x80+member,0x90+member):
                    ui.selected=4;ui.settings=False;ui.fx_pages[4]=0
                    before=copy.deepcopy(ui.effects)
                    self.wire(ui,[0xb0+member,74,64,0x90+member,36,100,0xb0+member,74,32,
                                  0xd0+member,100,0xa0+member,36,90,0xe0+member,0,64])
                    fixture.sounding();self.assertIn(36,ui.held)
                    # Physical selection, FX page and mode change must not
                    # hide a member-channel release of the original onset.
                    self.wire(ui,[0xb0,104,127,27,127,49,127,24,127,49,0])
                    ui.settings=True
                    self.wire(ui,[release,36,0,0xb0+member,74,127])
                    fixture.engine.render(512)
                    self.assertEqual(fixture.engine.status()['voices'],0)
                    self.assertFalse(ui.held);self.assertEqual(ui.effects,before)
        finally:fixture.tearDown()
    def test_rendered_echo_and_native_audio_survive_expression_and_bank_changes(self):
        import array
        from unittest.mock import patch
        import standalone_render as renderer
        from sampler import Event
        class Background:
            credits=[]
            def frame(self):return bytes(327680)
        captures=[]
        for expression in (False,True):
            fixture=chops.ChopGateTests();fixture.setUp()
            try:
                ui=fixture.ui;engine=fixture.engine;ui.fx_pages=[0]*6
                ui.level=[.65]*6;ui.master=.45;ui.muted=[False]*6;ui.help=False
                ui.error='';ui.next_slot=None;ui.pending=None;ui.archive_worker=None
                ui.archive_dirty=False;ui.request_next=lambda:None;ui.catalog=[dict(name='fixture')]
                for ch in range(6):
                    for p,value in enumerate(ui.effects[ch]):engine.command(16,ch,p,event=Event(gain=value))
                self.wire(ui,[0xb0,74,18]);engine.render(12000)
                before=copy.deepcopy(ui.effects);audio=array.array('f');text=[]
                original=renderer.Canvas.text
                def record(canvas,x,y,value,*args,**kw):
                    if x==368 and y==74:text.append(value)
                    return original(canvas,x,y,value,*args,**kw)
                for revision in (1,2):
                    bank=fixture.bank(revision);bank['programs']=[('changed',revision)];bank['drum']=0;bank['film_credit']={}
                    # Production stopped publication, then ordinary playing
                    # boundary publication: neither changes the channel FX.
                    slot=engine.install(bank)
                    if revision==1:engine.command(17,slot)
                    else:engine.command(1)
                    engine.render(129);ui.tick()
                    self.assertEqual(ui.last_bank,slot);self.assertEqual(ui.effects,before)
                    member=revision
                    self.wire(ui,[0xb0+member,74,64 if revision==1 else 32] if expression else [0xd0+member,64])
                    engine.render(1)
                    self.wire(ui,[0x90+member,35+revision,100]);audio.extend(engine.render(20000))
                    self.wire(ui,[0xb0+member,74,127] if expression else [0xd0+member,127])
                    audio.extend(engine.render(1000))
                    self.wire(ui,[0x80+member,35+revision,0]);audio.extend(engine.render(1000))
                    with patch.object(renderer.Canvas,'text',record):renderer.render(ui,engine.status(),Background())
                self.assertEqual(text,['30%','30%']);self.assertEqual(ui.effects,before)
                self.assertGreater(max(map(abs,audio)),.001);captures.append(audio.tobytes())
            finally:fixture.tearDown()
        self.assertEqual(captures[0],captures[1])
