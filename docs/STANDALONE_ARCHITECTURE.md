# Standalone architecture

`standalone_app.py` owns one MIDI reader, USB display and native engine. It has
no remote-control peer or listener. `sampler.py` is a separate ABI2 and does not
reuse Stillwater's role-bank synth. The only cross-compiled binary is x86_64;
the host ARM binary is memory-render testing only.

`composition.py` prepares deterministic score events, decoded stereo PCM,
programme metadata and current/next full drum takes on a serial worker.
`native.c` owns the44.1k sample clock and64-beat boundaries, 64voices, four bank
slots and1024 ordered commands. No allocation, decoding, file or network IO
runs on the render thread. Slot-local sample pointers cannot be replaced until
native retirement proves no current/next/held voice still references the bank.
Manual releases address onset-owned tokens even after selection/programme
changes. Rejecting newest voices bounds overload without stealing held tokens;
queue exhaustion fails the app safely instead of dropping a release.

One immutable bank holds every channel's schedule/programmes, drum take,
harmony and film chops. Publication applies together at a64-beat boundary.
Auto/Manual changes suppress only future automatic onsets without resetting this
timeline or releasing sounding voices. Pads play identically in either mode. Mixer
changes do not retrigger drum takes. Missing next preparation repeats the
current take and says PREPARING/REPEATING CURRENT. A replacement drum choice is
prepared off-thread and replaces the queued next bank; it cannot splice an
already sounding full take. Manual drums play four deterministic cuts of the
current take. Manual chops are immediate unquantized held cuts from the exact
prepared PCM. Each cut ends once at its slice boundary or earlier on its owning
pad release, through the existing256-frame click-free native release. Note-off
and velocity-zero note-on address the onset token across edits, mode/selection
and source changes; other pads retain their own voices. Film anchors remain
one-shots. Pressure does not mutate/reverse/randomize them.

The source-derived composition retains LofiScore motif onset tables/contours,
answer figures, section order and return emphasis; LofiPreset acoustic rows,
gains and envelopes; LofiSampleBank velocity selection and octave calibration;
LofiBassSamples kit/root parsing; the bass sub's fundamental and second–fourth
partial amplitudes and160Hz crossover weight from LofiBassVoice; and rootless
mid-register pad/inner revoice policy from LofiScore+Mids. PJ's override rotates
piano/pluck/guitar/piano over64-beat takes, preserving16-beat internal phrases.
The native pad is a crossfaded held sample loop. Bass retains an acoustic body
above a generated low sub. Every channel supports manual playback, with no
unavailable-placeholder mixer channels.

This MVP is **not** exact Swift DSP or seeded MusicRNG parity. It uses portable
Python deterministic RNG, a reduced bass cell, sampled looping pad rather than
the full granular PadVoice, simplified guitar ornaments and the portable per-channel
[Sound/Space/Motion bus effects](CHANNEL_FX.md). Room now uses independent
damped comb/allpass diffusion, separate from tempo echo. It omits the full Swift tape,
master-finisher, virtual-record and spectral-hold chains and bass kick-landmark
analysis. Soft limiting plus smoothed gains bound output. Taste, pad feel,
acoustic balance and physical latency require actual device/human acceptance.

`archive_worker.py` discovers public-domain Prelinger newsreel records through IA's
advancedsearch endpoint, validates metadata and fetches a bounded derivative
(prefer narration MP3; at most24MiB). One worker paces requests by2seconds,
limits read/decode time, and decodes a48second stereo44.1kHz float PCM window
with the existing licensed FFmpeg. Three immutable windows occupy at most51MiB
of decoded cache; one source/temporary decode adds at most41MiB. A one-result
mailbox and at most30 recent identifiers bound pending state. Failure preserves
the current bank; startup retains the bundled fallback and restores the latest
hash-validated live cache in the background. Ongoing requests run at each64-beat bank transition regardless of Auto/Manual,
with a180second background retry
or on Repeat with Chops/Film selected. No network listener is opened.

Archive acquisition still stores energy suggestions and immutable48-second PCM;
composition uses a separate serial text worker instead. dialogue_speech.py runs
one bounded hash-verified whisper.cpp process, first30seconds, actual DTW with
flash attention off, greedy English and35sdeadline. Local source/model/options
cache avoids repeated inference. dialogue_text.py refines lexical-center spans,
uses the packaged MIT perceptron model and upstream interest/grammar lexicons,
and prepares a unique eight-slot vocabulary. Failure preserves current playback.
See DIALOGUE_PORT.md for conservative name protection and alignment limits.

Manual offsets address the same immutable source PCM; Automatic owns eight
prepared slices. Drums uses16distinct offset/length ranges of its original PCM,
retaining the fixed15-bank-sample layout. All edited/automatic replacements
publish at64beats; native render does no inference/decode/allocation. Onset-owned
pins keep both PCM and range through source changes. Film is a separate mixer
and one manual8-second anchor. Played offline text line identities enter the
existing ledger only on committed playback; this is not the desktop motif crate.
Exact source URL, rights, window time, SHA256 and suggested cuts live in private
archive-cache JSON beside the decoded PCM.

`image_worker.py` fetches only keyless Cleveland records with CC0 status and
`images.print.url`, HTTPS, bounded downloads/timeouts and off-thread FFmpeg
one-frame decode. Images never block music. Three real offline images ship
privately, with source records/hashes. A six-slot disk cache and nine-image
in-memory rotation bound future pictures; failures keep current cached imagery.
The display worker alone opens, transfers to and closes the USB display.
Its one-frame pending queue replaces stale frames without blocking MIDI input;
transfer errors propagate to the supervisor, and shutdown refuses a new owner
while the old thread remains alive. The UI stays960x160 BGR565,1024stride, opaque controls/text drawn last,90seconds
between pictures with an8second crossfade. No audio-reactive flashing.

ALSA plumbing is adapted from Stillwater's MIT engine.c209–240: `hw:A3,0`,
44.1kHz/256frames,16channels S24_3LE, stereo duplicated into outputs1–4 and
others zero, nonblocking partial writes and xrun recovery, dlopen libasound.
Only device testing can qualify deadline/xrun/CPU claims.

Play toggle resolves on the native render owner in command queue order, so two
presses within one audio block still start then stop. Stop uses the existing
voice release, delay clear and take-position reset. Drums start with no echo or
room send. Melodic Manual uses Stillwater's centered default D Dorian grid
independently of the automatic arrangement key.

Chops and Film intentionally share immutable film PCM; they have separate
channel gain/mute/effects paths. Previously unnormalized .35 chop gain left
quiet archive material below the normalized drum take. Preparation now computes
per-cut foreground gain, bounded by16x and a .6 per-cut peak ceiling. The
same gains feed Auto sliced PCM and Manual full-source offsets. Edited Manual
ranges recalculate their gain on the control thread; the per-cut ceiling
protects louder edits. No
new audio-thread analysis, allocation or PCM rewrite is introduced.

The full selected-channel Device/Note UI and24parameter bus FX are documented
in CHANNEL_FX.md. ABI1 now adds command16 while preserving onset/bank ownership.

The D124–127 text-aware port is described in DIALOGUE_PORT.md. Native ABI2 appends
pad feedback identity to Event and provides lm_abi/lm_feedback. Python refuses
an older native engine; source, native binary and manifest must update together.
Successful native automatic onsets publish atomic channel/revision/pad feedback;
voice rejection and manual onsets cannot create a flash. Expiry uses the audio
sample clock, bounded to120ms or shorter gate/source duration. Stop/mute/Manual
clear it. No schedule scanning or wall-clock estimation drives the red pads.


Stopped publication correction: playing retains the64-beat bank boundary.
An explicitly requested preparation (initial text, source/drum request or edit)
may publish while stopped only after every native voice and admitted onset pin
is clear. A held pad defers it through release. Ordinary next-take prefetch stays
queued; stopping cannot spin through revisions. An initial unaligned bank is an
honest manual-only fallback. Read CHOP_REGRESSION_GATE.md (under docs/) for the
mandatory actual-source acceptance; one unique whole line is insufficient.
