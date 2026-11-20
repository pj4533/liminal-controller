#!/usr/bin/env python3
"""Synthetic production-renderer contact ranges; Pillow is offline only."""
from pathlib import Path
import struct
import sys
from PIL import Image
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from protocol import Client
from controller import Controller
from fake_server import sample_state
from render import render
import socket

def rgb(frame):
    data=bytearray()
    for y in range(160):
        for x in range(960):
            n=struct.unpack_from('<H',frame,(y*1024+x)*2)[0];data.extend(((n&31)*255//31,((n>>5)&63)*255//63,(n>>11)*255//31))
    return Image.frombytes('RGB',(960,160),bytes(data))
c=Client('127.0.0.1');c.sock=socket.socket();c.session='synthetic';c.error='SYNTHETIC CONTACT RANGE';c.state=sample_state('synthetic',ambient=True);ui=Controller(c)
frames=[]
for value in (0,.25,.5,.75,1):
    for p in ui.channel['parameters']:p['value']=value;p['display']=''
    frames.append(rgb(render(ui)))
sheet=Image.new('RGB',(960,800))
for i,im in enumerate(frames):sheet.paste(im,(0,i*160))
sheet.save(root/'docs/media/simulator-range.png')
frames[0].save(root/'docs/media/simulator-contacts.gif',save_all=True,append_images=frames[1:]+frames[-2:0:-1],duration=350,loop=0)
c.disconnect();rgb(render(ui)).save(root/'docs/media/simulator-disconnected.png')
