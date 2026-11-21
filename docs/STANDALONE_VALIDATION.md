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

The unit suite passes88tests, including43 inherited controller tests, native
PCM/mode/stop/boundary/held-release/queue/voice limits, queued-onset bank pins,
source programme/sample policies, durable dialogue ledger, image cache failure,
rights validation, five isolated install/recovery safety regressions and four
display-worker lifetime/queue regressions. An accepted manual onset retains its
pinned source across a boundary before command consumption; teardown failures
still remove readiness. Both cases have deterministic regressions.

The private-library rehearsal passes234checks: all100 unique original drum
hashes and64-beat durations,143 melodic instruments, deterministic events,
stable64-beat programmes with piano return, six isolated audible auto paths,
six manual mappings, next preparation, whole-take native transition, controls,
finite bounded PCM and silent Stop. Native preview is960x160 with opaque labels
over three actual credited CC0 image caches. Private evidence contains the
acceptance JSON, framebuffer previews and memory-rendered WAV, never git assets.

The cross-build is ELF64 x86_64 with maximum GLIBC requirement2.34, within the
specified2.35 target. Runtime source uses Python3.10 grammar. The preceding
82-test suite passed on the device's Python3.10.14. A stopped device rehearsal
observed60seconds of advancing ALSA frames and display transfers with zero
xruns; a silent playback rehearsal reached a full64-beat bank transition.
Its strict10ms fade/control maximum failed, so that result does not qualify
the updated runtime. Repeat device qualification after installing this change.

The display has one worker thread owning its USB handle and a single pending
frame replaced by newer frames. MIDI dispatch never waits for USB transfer.
The device rehearsal retains blend, control, USB-transfer and MIDI-poll timing
distributions, even when the strict10ms fade/control assertion fails. Its
synthetic onset timings are engine voice observations, not physical pad-to-audio
latency measurements.

Before use, verify the private staged manifest and archive checksum independently.
After authenticated device access, complete the acceptance in
STANDALONE_INSTALL.md. The prepared deployment helper refuses existing homes,
unsafe archives, wrong architecture, failed hashes, insufficient disk or live
competitors; it checkpoints old recovery/state and observes stopped ALSA/display
counters for60seconds. Its device-only integration path remains unexecuted.
