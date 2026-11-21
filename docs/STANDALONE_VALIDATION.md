# Standalone validation

SSH identity has been independently verified for primary and secondary OS.
Live runtime on 2026-11-21 is **1dfaa5164933c8e6d00dafe18bec0d27ce074d27**.
This documentation update does not deploy a new runtime. All 277 installed file
hashes were verified, and all 93 tests passed on device Python3.10.14 in 2.169s.
The x86 native engine remained unchanged by the final boot-helper correction.

Actual ALSA/display qualification, with master zero and synthetic MIDI controls,
passed all six manual channel onsets, rapid Stop/Play, a full 64-beat bank change
and silent Stop, with no xruns or queue overflow. Fade/control maximum was
1.490ms; MIDI polling p95 was 2.319ms and maximum 33.203ms. These observations
do not measure physical pad-to-audio latency or establish acoustic balance.

Two controlled post-fix reboots automatically selected primary and produced
same-boot stock startup acknowledgements, primary default and secondary fallback:

- `e6d7ecce-3bc5-4662-8be7-04c287dbac36`: 60.101s sustained progress, xruns 1→1,
  delta 0.
- `2395f1dd-c667-4831-a2d8-6379f5c15b87`: 60.087s sustained progress, xruns 0→0,
  delta 0.

The final sample was alive, ready, stopped, next bank ready and not preparing,
with no app/image errors. ALSA and display counters advanced; xruns were zero.
CPU was 21.2% of one core and RSS 229,884KiB at that sample. The app exclusively
owned USB display, ALSA MIDI and PCM output. Normal master is 45%; channel
defaults are 65%. All 100 AJ drum entries and 143 instrument WAVs are installed.
Preservation audit found all 104 recordings unchanged (16,887,273,274 bytes) and
all seven session hashes matching. Secondary stock was unchanged.

The observed stock D-Bus activation launched UpdateDBusService with
`--with-live-service`; it had no USB/ALSA descriptors, and no Live or Push3
launcher process was present. The activation configuration was left unchanged.
The final UI image is an offline render of live state and shipped defaults,
not a photograph or capture of the physical screen. No physical-button press
or audible listening test is claimed.

On the ARM host with Python3.11.2:

```sh
sh scripts/build-native.sh
python3 -m unittest discover -s tests -v
python3 scripts/rehearse-standalone.py --assets /PRIVATE/assets --out /PRIVATE/evidence
ZIG=/verified/zig-0.13.0/zig sh scripts/build-native.sh device
```

The unit suite passes93tests, including43 inherited controller tests, native
PCM/mode/stop/boundary/held-release/queue/voice limits, queued-onset bank pins,
source programme/sample policies, durable dialogue ledger, image cache failure,
rights validation, five isolated install/recovery safety regressions and four
display-worker lifetime/queue regressions. An accepted manual onset retains its
pinned source across a boundary before command consumption; teardown failures
still remove readiness. Both cases have deterministic regressions.

Primary boot acknowledgement requires60seconds of fresh, ready audio/display
progress with an unchanged xrun counter. A startup xrun may precede this settled
window; any increase or unexpected decrease resets it. The receipt preserves
baseline/final totals, their delta and the sustained interval. Five simulated
clock tests cover settling, counter changes, readiness/freshness/errors and
failure to advance; counters are never erased to satisfy acknowledgement.

The private-library rehearsal passes234checks: all100 unique original drum
hashes and64-beat durations,143 melodic instruments, deterministic events,
stable64-beat programmes with piano return, six isolated rendered auto paths,
six manual mappings, next preparation, whole-take native transition, controls,
finite bounded PCM and silent Stop. Native preview is960x160 with opaque labels
over three actual credited CC0 image caches. Private evidence contains the
acceptance JSON, framebuffer previews and memory-rendered WAV, never git assets.

The cross-build is ELF64 x86_64 with maximum GLIBC requirement2.34, within the
specified2.35 target. Runtime source uses Python3.10 grammar. Host memory-render
tests and the private-library rehearsal complement the live acceptance above;
they do not constitute physical listening or button-press evidence.

The display has one worker thread owning its USB handle and a single pending
frame replaced by newer frames. MIDI dispatch never waits for USB transfer.
The device rehearsal retains blend, control, USB-transfer and MIDI-poll timing
distributions, even when the strict10ms fade/control assertion fails. Its
synthetic onset timings are engine voice observations, not physical pad-to-audio
latency measurements.

For future installations, verify the private staged manifest/archive checksum
and repeat the acceptance in STANDALONE_INSTALL.md. The deployment helper refuses existing homes,
unsafe archives, wrong architecture, failed hashes, insufficient disk or live
competitors; it checkpoints old recovery/state and observes stopped ALSA/display
counters for60seconds. The live installation used checkpointed current-session
qualification followed by primary-only dispatcher installation and stock API
acknowledgement, preserving the secondary recovery system.
