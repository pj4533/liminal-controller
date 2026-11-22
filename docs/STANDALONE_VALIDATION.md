# Standalone validation

Latest accepted live runtime: **87c8637add926fb52551e0b5f0d0b752e5e101c7**,
selected-channel FX,2026-11-22. Its device acceptance appears at the end; earlier
sections retain the historical evidence for each preceding rollout.

Playability correction (2026-11-21), implemented and deployed:
strict native host and Zig0.13 x86_64 builds pass; host113tests pass, including
12 focused regressions for Play toggle/queue order/hush, Stillwater default
pitches/colors/chord triangle/octave limits, manual native events, drum impulse
tail silence, bounded foreground gain, exact Auto/Manual chop PCM equality and
Chops/Film channel/source isolation. Review regressions force native Start
consumption before control dispatch returns and move initially silent cuts onto
speech, then louder PCM, for both offline and live source identities. Private-library rehearsal passes234checks.
The same offline-source Auto Chops render rises from RMS.00045764 to.00504492
(20.8dB); Film stays.00108610. Dry drums are.02713861. These are isolated
native memory-render measurements, not listening or physical pad evidence.
Live device was inspected read-only before rollout: expectedbc800b5 source,
stopped, ready, no error/overflow, one historical xrun and no log text.
Cached live sources had RMS.01181/.01263/.04439 before the fixed.35 chop
multiplier, confirming level mismatch against drums normalized to.11.
Source inspection and PCM isolation tests found separate Chops/Film channel
routes sharing film PCM intentionally. Normalization cannot remove music or
background sound already in that source. Manual remains fixed Stillwater D
Dorian independently of automatic harmony. Actual deployment evidence follows;
physical listening remains a human acceptance check.


Actual playability deployment (2026-11-21): live source
**fad948f102b2f1981e2dabffba20ac340de10beb**, all279manifest files verified.
Manifest SHA256 is
`b989b0ca4c21e13269e3e4f135d56ea667bad79b7fa89a7d65b7260e5c0adabd`;
paired x86_64 engine SHA256 is
`4b11b37343625d1cbe681564b400b5ab1c553c3a506a8e2cdb14ad361cec473d`.
Device113tests passed in2.324seconds. The isolated master-zero qualifier passed
synthetic MIDI Play/Stop/Play and manual chop editing against real ALSA, direct
IA download/decode/prepared PCM, cache retention under forced fetch failure,
and Stop with zero voices/peak. It observed zero xrun delta and567displayframes.
Qualification used its own writable ledger/cache; original music was preserved.

After normal service restart,60.305seconds of fresh stopped readiness had no
errors, next_ready=true, ALSA frames20225→2679809, written frames20128→2679790,
display frames3→600 and xruns0→0. The application was the sole USB/MIDI/PCM
owner. Recording inventory and session hashes passed preservation checks.
A private checkpoint retains rollback source/native/state; its exact path and
operational evidence are recorded in the existing private deployment handoff.
No OS/init/recovery deployment or additional reboot was required for this change.
These are synthetic controls and measured hardware progress; physical listening,
button presses, pad feel and acoustic balance await PJ. Documentation commits
afterfad948f do not change the live runtime.

Historical live archive update on2026-11-21: deployed runtime
**bc800b5ebc6a9ce5021be0f011fa7b317ce8e3fc**,279manifest hashes verified.
Host101/101tests passed in2.161s; device101/101tests passed in2.136s. Strict native host/x86 builds pass. The final private
library rehearsal again passed234checks with unchanged six-channel audio paths.

Actual Push downloaded NewsMaga00_3.mp3 directly from IA and decoded48seconds
starting at204.00seconds while the native ALSA engine played master-zero.
Fetch/decode took31.096seconds; the fresh immutable bank published at55.722seconds
on the next64-beat boundary. The entire rehearsal had0xruns/overflow and566USB
frames. Synthetic MIDI selected Chops Manual, selected pad3 silently, changed
start12.00→12.15seconds and length2.00→2.10seconds, and triggered a native voice.
A separate on-device native memory render of that exact downloaded/edited PCM
was finite, peak.0234085/RMS.00425167 over93122frames. It did not open ALSA.
Forced offline fetch failure retained the active source and advancing playback.
Stop returned peak0,voices0,playing=false. Poll p95 was2.294ms,max56.752ms;
RSS320644KiB. These are synthetic dispatch/counter measurements, not physical
pad latency or audible output acceptance. Master stayed zero throughout device
qualification; normal service starts stopped at45%.

All104recordings (16,887,273,274bytes; path/size/inode/mtime) and7session hashes
match the original checkpoint. Only Liminal's runtime files were updated;
existing primary dispatcher/recovery remained byte-for-byte unchanged.
Private evidence: live-archive-shutdown-device.log, archive-qualified.png,
live-archive-preboot-audit.json in the existing standalone work directory.
The screenshot is a rendered native framebuffer, not a physical screen capture.

A controlled reboot automatically returned to primary, boot
`e506b885-3c7b-4d31-a1f9-7f4406dbe879`. The unchanged boot helper recorded
60.084seconds of advancing ALSA/display progress with xruns1→1,delta0;
one startup xrun preceded the settled window. Stock startup acknowledgement
set primary default/secondary fallback. Service PID747 was alive, ready and
stopped with peak0, next bank ready, no preparation/app/image/archive errors,
and CACHED READY with the previous live source queued. The post-reboot audit
again verified all279runtime hashes, exclusive device ownership, all104recordings
and7sessions, and an unchanged primary dispatcher. Final sample CPU30.3% of
one core (lifetime average),RSS201636KiB. Normal master remains45% by the
unchanged shipped defaults. Documentation commits afterbc800b5 are not runtime
updates. Private reboot evidence: live-archive-reboot.json and
live-archive-postboot-audit.json.

Earlier acceptance history follows; version numbers below describe those
historical builds.


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


## Complete phrase pads and Manual source refresh — 2026-11-22 UTC

Deployed runtime `a89cc365cb669e12793dfe8c6d20de7d007079dc`. Each populated
Chops pad now addresses one unique consecutive region, covering the entire
available phrase. Quiet boundaries near750ms subdivisions give64cuts for a
48second live window and11for an8second offline line; unused pads are unlit
and inert. Automatic sample slots remain bounded at eight; Manual addresses
all cuts in the immutable source. Fresh archive requests run at every take
transition in Auto or Manual, retaining the180second background retry and
existing cache on failed/slow fetches. New material still publishes at64beats.

Host and actual Push `python3 -m unittest discover -s tests -v`:118passed,
zero failures (device3.784s). New regressions verify complete contiguous source
coverage, unique native pad offsets for short/full windows, inactive pads,
offline/live preparation, and refresh requests across three native Manual take
transitions. Existing transport, melodic layout, chop gain and dry-drum tests pass.
Host and verified Zig0.13x86 builds pass;37source/scriptfiles parse asPython3.10.
Private-library rehearsal:234checks passed, zero failures. Native960x160Chops
and Help renders were viewed, including the actual device qualifier framebuffer.

Actual master-zero ALSA/USB qualifier passed in230.809s. Fresh IA download and
decode took6.658s; first source publication55.608s. Its64unique cuts covered all
2,116,800frames. Chops stayed Manual through three subsequent take transitions:
revisions5,7,9 each published a different freshly downloaded archive source,
and all three observed transition requests were accepted. Edited chop PCM was
finite, peak.092710/RMS.024543; Stop ended with zero voices and peak. No audio
was heard. Xrun delta0, overflow0,2198displayframes; MIDI-pollp952.327ms,
max106.244ms. These timings do not establish physical pad latency or feel.
A forced network failure retained the active source and continuing ALSA.

All279runtime hashes verified after normal-service restart; manifest SHA256
`4c95985547c7ed4680cfcc967fb44e321c22b9e7e45f7a14bf22da603f8f37a8`.
Native engine is byte-identical to the previous accepted build. Fresh normal
service passed60.284s stopped readiness, zero voices/peak/errors/overflow,
xruns0→0, ALSAframes19,969→2,680,577, written19,995→2,680,363 and display3→600.
The app was sole USB/MIDI/PCM owner; NEXT READY was true at completion.
Recording inventory and session hashes matched the stopped checkpoint. Existing
init, stock/recovery paths and OS were preserved; no reboot was needed for this
Python control/preparation change. Private deployment log/checkpoint details
remain outside git. Physical listening, button presses and pad feel remain PJ's
acceptance; silent controls/counters/PCM checks establish only technical behavior.


## Held Manual Chops — 2026-11-22 UTC

Live runtime `9ea6e6152ac242f3c85e6dc2adac31b544ac4cc5`. Manual Chops now
retains each pad's onset token: note-off or velocity-zero note-on stops that
voice through the existing256-frame (5.8ms) native release. Holding plays the
slice once to its end, without looping. Separate Film anchors remain one-shots.
Unique chronological full-phrase cuts, inactive pads, gain, automatic refresh,
Auto playback and onset-owned PCM/ranges remain unchanged.

`sh scripts/build-native.sh` and verified Zig0.13x86 build pass. Host
`python3 -m unittest discover -s tests -v`:125passed,0failed (2.970s).
Seven new native-backed tests cover early/wire/zero-velocity releases, slice-end
termination without looping, overlap/retrigger/stale old-pad release, release
after edit/selection/mode/source changes, Stop/Delete and unchanged Film.
Private-library rehearsal:234passed,0failed;37source/scriptfiles parse asPython3.10.
Actual Push suite:125passed,0failed (3.847s).

Exclusive master-zero device qualification passed synthetic wire note-off and
velocity-zero releases, overlap, retrigger, stale prior-pad release, mode change,
hold-to-end/no-loop, repress and Stop. ALSA written frames9,721→123,932,
xruns0→0,overflow0;20USBframes. Stop ended at0voices/peak. Observation waits
include control pumping/display work and do not measure physical pad latency.

All279runtime hashes passed. Manifest SHA256
`ce0bf07b97442d99569f23abdb00822d5e6162030d4dc81f16be2304bfcb20ba`;
paired x86 engine remains byte-identical to the previous accepted build.
Normal service then passed60.277s fresh stopped readiness: no errors, voices,
peak or overflow; xruns0→0; ALSAframes21,505→2,678,273, written21,319→2,678,214,
display3→600; NEXT READY=true. One app exclusively owned USB/MIDI/PCM.
Recording inventory and session hashes matched the stopped checkpoint; primary
init was unchanged. No OS/recovery/GRUB change, reboot or Drift runtime update.
Physical listening, button presses and pad feel remain human acceptance checks.

Two private rollout checks first triggered successful automatic rollback: the
new qualifier initially used exact-zero instead of the existing1e-8 silent-peak
tolerance; a retry then refused an already retained source-test directory. Both
were harness issues corrected before the final successful rollout. Checkpoints,
logs and operational continuation remain private, outside source control.

## Selected channel FX candidate — host review, 2026-11-22

At this host-review stage the candidate was implemented but not deployed;
the live runtime was9ea6e615. The later device acceptance below supersedes this
status. See CHANNEL_FX.md for all24controls, algorithms, defaults and ranges.

- `sh scripts/build-native.sh`: pass, strict warnings; host AArch64 memory engine.
- `ZIG=/verified/zig-0.13.0/zig sh scripts/build-native.sh device`: pass, ELF64
  x86_64 with maximum GLIBC requirement2.34 (target2.35).
- `python3 -m unittest discover -s tests -v`:148passed,0failed,7.289s.
 23new tests cover every processor/control's actual PCM contribution, channel
  isolation, native/Python nonfinite/address/bounds admission, generated contract,
  maximum settings, finite decaying feedback tails, stale-tail bypass/re-enable,
  Stop/restart silence, smoothing, echo-time crossfade and transport continuity,
  per-channel/page mappings, Sound-first entry, held releases, Mix and Settings,
  and Width0 mono routing including all stereo wet paths.
  Existing chop fixtures explicitly select Cuts; ownership checks stay intact.
- `scripts/rehearse-standalone.py --assets PRIVATE --out PRIVATE`:257passed,
 0failed (previous234 plus23additional actual encoder assertions). It retains
  all100drum source hashes/durations,143instrument assets, coherent programme
  banks, six Auto/Manual PCM routes, preparation, boundary ownership and Stop.
- All41source/script Python files parse with Python3.10 grammar.
- `scripts/benchmark-fx.py --out PRIVATE`:64voices confirmed at warmup, six
  channels/all FX,2,000blocks each static and rapid full-parameter traffic.
  Static p99.552ms/max3.602ms; rapid p99.542ms/max.630ms. Zero blocks exceed
 5.805ms (44.1kHz/256). Stop clear.539ms; stopped peak0, voices0, overflow0.
  This is an ARM host memory benchmark, excluding ALSA/USB and device scheduling.

Viewed40native960x160screenshots: every channel/page at min/max settings,
including Chops/Film Cuts, plus Mix, Help and Settings. All eight large labels
and values fit within120pixel encoder columns; longest TRANSIENT/COMPRESS labels,
18.0kHz/60.0ms/negative pan, page counts, source and long error text remain
bounded. Device shows only the selected channel, Mix shows six strips. Native
frames are not physical Push photographs or proof of pad/button feel.

Private `scripts/rehearse-fx.py` captures12seconds per isolated real channel
(old default/new default/expressive). Six6second WAV comparisons contain2seconds
of each case at unchanged gains, without export normalization. All captures are
finite and bounded. Default RMS changes against the previous native engine:
Drums0.000dB (difference RMS1.30e-9), Bass+.309dB, Lead-.128dB, Mids+.085dB,
Chops-.055dB, Film-.020dB. Bass now monos its low side; other differences arise
from genuine independent Room and tempo Echo replacing the shared fixed tap.
These measurements characterize a deterministic offline source, not arbitrary
archive speech, human listening or exact original-DSP parity.

Private evidence remains outside git: fx-tests-final.log, fx-benchmark-final.json,
rehearsal-fx-final/acceptance.json, fx-evidence/metrics.json,40min/max frames,
three overlays and six short comparison WAVs. No private media or asset catalog
is committed. Independent review precedes a later paired source/native rollout.
The existing private delta helper assumes an unchanged binary/file set and needs
adaptation, followed by the full device acceptance in STANDALONE_INSTALL.md.


Review corrections (before deployment): control smoothing now snaps to its
exact target below1e-6 parameter units or when float rounding stalls. A read-only
native-storage regression verifies all continuous controls settle exactly after
four seconds, all zero targets are zero, and Stop leaves no subnormal controls.
Film Cuts explicitly says ONE SHOT; Chops says HOLD. The benchmark also measures
64 voices after effects return to zero, reporting p99 headroom without imposing
a generic host scheduling threshold. Actual x86 ALSA/USB qualification remains
required on the device before acceptance.

`python3 -m unittest discover -s tests -v`:149passed,0failed,6.762s.
Host and Zig x86 builds pass strict warnings. ARM memory benchmark (2000blocks
per phase): static p99.452ms, rapid-controls p99.513ms, returned-to-zero p99.368ms,
max3.247ms, zero deadline overruns; deadline5.805ms. Stop clear.461ms, stopped
peak0, voices0, overflow0. Evidence: private fx-reviewfix-tests.log and
fx-reviewfix-benchmark-host.json. These are host results, not x86/ALSA claims.


## Selected channel FX — accepted on device, 2026-11-22

Live source **87c8637add926fb52551e0b5f0d0b752e5e101c7** was installed as a
coherent Python/native pair after independent implementation and workflow review.
All280installed manifest hashes verified. Manifest SHA256:
`5d1a3195234500ab7bc3ec8348b9b26ac376e0464f92075e80399bcdb6b52a3b`.
The paired x86 engine SHA256 is
`8ca0d9e402ab613507c7d4ddfb88ab224c5fb70c12d47b5eb004cd5ece74aa63`.
Actual Push suite:149passed,0failed in11.889s, including the exact-endpoint
smoothing regression and all prior pad/source/ownership checks.

Actual x86 memory-render qualification ran4000blocks per phase,64voices across
all six channels. Against the256frame/44.1kHz deadline5.804989ms:

| Phase | p99 render time | p99 headroom | Blocks over deadline |
|---|---:|---:|---:|
| All effects | .715548ms | 87.67% | 0 |
| Rapid controls | .737053ms | 87.30% | 0 |
| Effects returned to zero | .528746ms | 90.89% | 0 |

Stop clear took.638249ms; stopped peak0, voices0, overflow0. The separate
exclusive master-zero qualifier exercised actual ALSA/USB with synthetic MIDI,
held releases across pages, all effects/six channels/64voices, rapid controls,
returned-zero controls and Stop tails. It passed with0xruns/overflow,
353display frames, stopped frames1,762,817/written1,758,561, peak0 and voices0.
These are actual hardware IO and deterministic/synthetic checks; no physical
listening or button/pad manipulation was tested, and subjective sound quality
or acoustic balance is not established by these results.

Normal service then passed60.2916s fresh, ready and stopped with the same app
PID5222 as sole USB/PCM/MIDI owner. Errors, image-worker errors and archive
errors stayed empty; xruns0→0, overflow0, voices0, peak0. Audio frames advanced
20,737→2,676,737, written20,480→2,676,736 and display3→600. NEXT READY=true;
archive state CACHED READY. The exact inventory of104recordings totaling
16,887,273,274bytes (path/size/mtime/inode), seven session hashes and primary init
matched. Recovery and boot-selection preservation assertions passed. No reboot,
OS/init/boot change or Drift runtime update was part of this application rollout.

The fresh checkpoint, coherent package, original-runtime backup, benchmark,
qualifier, normal-health and preservation receipts remain private. Automatic
rollback retains the established graceful-stop/zero-owner requirement, paired
native/source/manifest and mutable ledger/cache restoration, removal only of
introduced files, old-hash verification and60seconds stopped health. It never
restores recordings/sessions/init/recovery/OS as application state. Prior held
Manual Chops, one-shot Film, chronological phrase mapping and take/archive
refresh agreements remain in force. Subsequent documentation commits do not
change the installed runtime identifier or require another deployment.


## Rhythmic chops / playable Auto — host candidate, 2026-11-22

Candidate source extraction: Liminal main10f5e1d2758b5f05007221673cc476ce6c9048e2.
See DIALOGUE_PORT.md for exact portable scope and deliberately omitted semantic
and Swift-only processing. This is host evidence; installed runtime remains
87c8637 until a separately executed paired rollout and device acceptance.

Host strict native build and verified Zig0.13x86 build passed. The official
Zig aarch64-linux0.13archive SHA256 was checked against ziglang.org's release
index:041ac42323837eb5624068acd8b00cd5777dac4cf91179e8dad7a7e90dd0c556.
Device engine is ELF64x86_64 with maximum GLIBC2.34 (target2.35).
`python3 -m unittest discover -s tests -v`:164passed,0failed,7.144s.
Fifteen added tests cover all-channel Auto/manual coexistence, mode-only onset
gating, source-owned releases across mode/edit/selection/bank, actual successful
native automatic feedback, rejected/muted/manual/stale/channel isolation, short
source/gate/120ms expiry, melodic octave mapping, acoustic vocabulary spread,
onset trimming, measured/stretched take timing, deterministic arc/feel/gates,
chronological reorder guard and tiny/empty sources. A production-loop regression
verifies a60ms red flash entirely between display frames reaches MIDI and clears;
pad LEDs poll at50Hz independently of the10Hz display. The former native test that
accidentally exercised unpublished-bank admission now explicitly tests manual
onsets accepted in Auto. Continuous Drum/Film playback carries no proxy pad ID.

Private-asset rehearsal:257passed,0failed, including real six-channel PCM,
100drum hashes/durations,143instrument assets, coherent64beat programme/source
publication, held releases and Stop. All42source/script files parse asPython3.10.
Native960x160Chops Auto Sound/Cuts and Help were viewed; all eight FX columns,
held-cut controls and the new Drums Shift+pad help fit their bounds.

Host memory benchmark,64voices/2000blocks per phase: all-FX p99.477166ms,
rapid controls.538875ms, returned-zero.348625ms; zero5.804989ms deadline
misses. Stop clear.427458ms, stopped peak0/voices0/overflow0. These are ARM
memory-render results, excluding actual ALSA/USB/device scheduling. Device unit
suite, silent qualifier, ownership, preservation and60second stopped-health
checks remain mandatory. No listening, physical pad/display or device latency
acceptance is claimed here. Source/native/manifest must upgrade together toABI2;
the prior accepted ABI1 source/native pair remains the rollback target.

## Text-aware candidate (not device deployment evidence)

Host unit suite:181passed,0failed, including actual native red slice5 on physical
second-row pad, inactive right-half pad, post-selection release, DTW subword/
contraction assembly, invalid/collapsed/missing timestamps, repeated-gram guard,
semantic interest, conservative names/negations/numbers, protected intact gates,
reserved complete outro across8revisions, subprocess deadline/kill/reap/cache,
failed-source storm suppression and incumbent retention on preparation failure.
Host private-library rehearsal:257checks passed; ARM correctly reports speech
unavailable and keeps the incumbent. Separate actual device base.en DTW JSON plus
matching public-domain AmateurS1950 PCM replay:52checks passed across8revisions,
including complete intro/outro, unique bounded cuts,16distinct drum ranges,
anchor continuity/line evolution and actual native finite full-score rendering.
Native960x160Sound/Cuts/Help renders were inspected. Strict host and x86 native
builds passed; check-speech-artifacts.py verified all three exact hashes.

These do not establish newly integrated concurrent device speech/audio/USB
performance, physical colors/input latency, hearing or human interest/feel.
The private deployment qualifier must measure fresh (uncached) local base.en DTW
while real ALSA and display/MIDI continue at master zero, show an actual prepared
semantic bank and no new xruns. Retain stopped boot and saved rollback gates.
