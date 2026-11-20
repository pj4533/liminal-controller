#!/usr/bin/env python3
"""Offline geometric crop/packing only; original generated scene is unmodified."""
from pathlib import Path
import struct
from PIL import Image
root=Path(__file__).resolve().parents[1]
im=Image.open(root/'assets/film-table-original.png').convert('RGB')
im=im.crop((278,215,1770,464)).resize((960,160),Image.Resampling.LANCZOS)
im.save(root/'assets/film-table.png')
b=bytearray(1024*160*2)
for y in range(160):
    for x in range(960):
        r,g,blue=im.getpixel((x,y));struct.pack_into('<H',b,(y*1024+x)*2,((blue>>3)<<11)|((g>>2)<<5)|(r>>3))
(root/'assets/film-table.bin').write_bytes(b)
