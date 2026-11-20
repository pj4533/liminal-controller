#!/usr/bin/env python3
"""One Mac build/test entry point. Never enables Lo-Fi's unqualified gate."""
import argparse
import platform
from pathlib import Path
import subprocess
import sys
p=argparse.ArgumentParser();p.add_argument('liminal',type=Path);p.add_argument('--vision-destination',default='platform=visionOS Simulator,name=Apple Vision Pro');a=p.parse_args()
if platform.system()!='Darwin':sys.exit('Native acceptance requires macOS/Xcode; Linux parsing is not acceptance.')
root=a.liminal.resolve();project=root/'Liminal.xcodeproj'
if not project.is_dir():sys.exit('Liminal.xcodeproj missing')
for tail in (['-destination','platform=macOS','build'],['-destination','platform=macOS','-parallel-testing-enabled','NO','-only-testing:LiminalTests','test'],['-destination',a.vision_destination,'build']):
    subprocess.run(['xcodebuild','-project',str(project),'-scheme','Liminal']+tail,cwd=root,check=True)
print('Native builds/tests passed. Audio capture, timing, cache budgets and physical Push acceptance remain manual gates.')
print('Do not enable LofiBus.isolatedPreparationQualified until serialized baseline/isolated-wet capture and deadline qualification pass.')
