"""Full material scene, attached exact-value contacts and typography drawn last."""
from pathlib import Path
from canvas import Canvas, INK, BRASS, MIST
from controller import SLOTS
BASE=(Path(__file__).resolve().parents[1]/'assets/film-table.bin')

def render(ui):
    c=Canvas(BASE.read_bytes());remote=ui.client;state=remote.state or {};ch=ui.channel
    # Quiet full-width caption bands leave the continuous film mechanism visible.
    c.rect(0,0,960,43,(3,9,10));c.rect(0,119,960,41,(3,9,10))
    if ui.view=='settings':
        c.text(5,4,'LIMINAL / NETWORK ENDPOINT',INK,2)
        c.text(5,25,'ENCODERS 1-4 ADDRESS / 5 PORT / LOWER 8 APPLY / 7 CANCEL',BRASS)
        for i,s in enumerate(ui.draft_host.split('.')+[str(ui.draft_port)]):c.text(i*180+20,76,s,INK,3)
        c.text(5,124,ui.message or 'LOWER 1 STILLWATER / 2 STOCK / 8 APPLY / 7 CANCEL',MIST)
        return bytes(c.pixels)
    status='WAITING FOR LIMINAL'
    if remote.connected:
        transport=state.get('transport',{});status=transport.get('state','UNKNOWN').upper()
        if not transport.get('ready'):status+=' / PREPARING'
    c.text(5,3,'LIMINAL',INK,2);c.text(120,4,(ch or {}).get('label','NO CHANNEL')[:20],BRASS,2)
    c.text(400,4,status,INK,2)
    c.text(800,4,('RTT %.1F MS'%remote.rtt) if remote.rtt is not None else 'RTT UNKNOWN',MIST)
    bank=(ch or {}).get('pad_bank')
    identity=(('BANK '+str(bank.get('bank_id'))+' R'+str(bank['revision'])+' / WHOLE LINE PAD64') if bank else (ch or {}).get('instrument',''))
    if (ch or {}).get('kind')=='drums':identity=(state.get('drums') or {}).get('current_label',identity)
    c.text(5,22,('%s / %s / %s'%((ch or {}).get('mode',''),identity,(ch or {}).get('status',''))).upper()[:100],MIST)
    c.text(5,34,(remote.error or ui.message or ('DEVICE' if ui.view=='device' else 'MIXER'))[:95],BRASS)
    channels=ui.channels
    for i in range(8):
        x=i*120;index=ui.page*8+i
        if index<len(channels):
            cc=channels[index];c.text(x+3,111,('+' if index==ui.selected else '')+cc['label'][:14],MIST if cc.get('active') else (75,85,85))
        p=None
        if ui.view=='mix':
            cc=channels[index] if index<len(channels) else {};p=next((p for p in cc.get('parameters',[]) if p['id']=='gain'),None);label=cc.get('label','EMPTY')
        else:
            p=next((p for p in (ch or {}).get('parameters',[]) if p['id']==SLOTS[i]),None);label=(p or {}).get('label',SLOTS[i])
        enabled=p and p.get('enabled',True) and (ch or {}).get('active') and remote.connected
        if enabled:
            v=max(0,min(1,p['value']));y=103-round(v*54);rgb=BRASS if i%2==0 else MIST
            # Rail and contacts are registered directly to the authored film strips.
            for t in (0,.25,.5,.75,1):
                yy=103-round(t*54);c.line(x+55,yy,x+65,yy,(107,118,101))
            c.rect(x+52,y-3,17,7,(20,26,22));c.line(x+51,y-4,x+69,y-4,rgb);c.line(x+52,y+3,x+68,y+3,rgb)
            c.disc(x+60,y,3,2,rgb)
            value='%d%%'%round(v*100)
        else:value='UNAVAILABLE'
        c.text(x+4,122,label[:15],INK,2 if len(label)<10 else 1)
        c.text(x+4,141,value,BRASS if enabled else (90,100,100),2 if enabled else 1)
        if p and enabled:c.text(x+64,151,str(p.get('display',''))[:9],MIST)
    return bytes(c.pixels)

def write_ppm(path,frame):
    import struct
    out=bytearray()
    for y in range(160):
        for x in range(960):
            n=struct.unpack_from('<H',frame,(y*1024+x)*2)[0]
            out.extend(((n&31)*255//31,((n>>5)&63)*255//63,(n>>11)*255//31))
    Path(path).write_bytes(b'P6\n960 160\n255\n'+out)
