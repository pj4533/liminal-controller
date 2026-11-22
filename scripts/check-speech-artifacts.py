#!/usr/bin/env python3
"""Check prebuilt offline speech bundle before private staging; never downloads."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dialogue_speech import BINARY_SHA,MODEL_SHA,TAGGER_SHA
root=ROOT/'.build/speech';records={}
for name,expected in (('whisper-cli',BINARY_SHA),('ggml-base.en.bin',MODEL_SHA),('averaged_perceptron_tagger_eng.zip',TAGGER_SHA)):
    h=hashlib.sha256()
    with (root/name).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    assert h.hexdigest()==expected,name;records[name]=expected
blob=(root/'whisper-cli').read_bytes();assert blob[:4]==b'\x7fELF' and blob[18:20]==b'\x3e\x00'
print(json.dumps(dict(architecture='x86_64 AVX2, GLIBC2.35 target; explicit device loader',sha256=records)))
