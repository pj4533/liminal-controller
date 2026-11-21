# Standalone validation

SSH identity has been independently verified for primary and secondary OS.
Device qualification is separate from the host memory-render tests below.

On the ARM host with Python3.11.2:

```sh
sh scripts/build-native.sh
python3 -m unittest discover -s tests -v
python3 scripts/rehearse-standalone.py --assets /PRIVATE/assets --out /PRIVATE/evidence
ZIG=/verified/zig-0.13.0/zig sh scripts/build-native.sh device
```

The unit suite passes82tests, including43 inherited controller tests, native
PCM/mode/stop/boundary/held-release/queue/voice limits, queued-onset bank pins,
source programme/sample policies, durable dialogue ledger, image cache failure,
rights validation and five isolated install/recovery safety regressions.

The private-library rehearsal passes234checks: all100 unique original drum
hashes and64-beat durations,143 melodic instruments, deterministic events,
stable64-beat programmes with piano return, six isolated audible auto paths,
six manual mappings, next preparation, whole-take native transition, controls,
finite bounded PCM and silent Stop. Native preview is960x160 with opaque labels
over three actual credited CC0 image caches. Private evidence contains the
acceptance JSON, framebuffer previews and memory-rendered WAV, never git assets.

The cross-build is ELF64 x86_64 with maximum GLIBC requirement2.34, within the
specified2.35 target. All33 Python source/script files parse with Python3.10
grammar. The prior controller's Python3.10 interpreter was no longer present;
the new branch has not yet been executed under that interpreter or device ALSA.

Before use, verify the private staged manifest and archive checksum independently.
After authenticated device access, complete the acceptance in
STANDALONE_INSTALL.md. The prepared deployment helper refuses existing homes,
unsafe archives, wrong architecture, failed hashes, insufficient disk or live
competitors; it checkpoints old recovery/state and observes stopped ALSA/display
counters for60seconds. Its device-only integration path remains unexecuted.
