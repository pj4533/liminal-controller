# Standalone architecture

`standalone_app.py` owns one MIDI reader, USB display and native engine. It has
no remote-control peer or listener. `sampler.py` is a separate ABI1 and does not
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
Auto/Manual changes suppress auto notes without resetting this timeline. Mixer
changes do not retrigger drum takes. Missing next preparation repeats the
current take and says PREPARING/REPEATING CURRENT. A replacement drum choice is
prepared off-thread and replaces the queued next bank; it cannot splice an
already sounding full take. Manual drums play four deterministic cuts of the
current take. Manual chops are immediate unquantized one-shots from the exact
prepared PCM; pressure does not mutate/reverse/randomize them.

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
the full granular PadVoice, simplified guitar ornaments and simple per-channel
tone, stereo echo, diffuse-room proxy and pan. It omits the full Swift tape,
master-finisher, virtual-record and spectral-hold chains and bass kick-landmark
analysis. Soft limiting plus smoothed gains bound output. Taste, pad feel,
acoustic balance and physical latency require actual device/human acceptance.

`archive_worker.py` discovers public-domain Prelinger records through IA's
advancedsearch endpoint, validates metadata and fetches a bounded derivative
(prefer narration MP3; at most24MiB). One worker paces requests by2seconds,
limits read/decode time, and decodes a48second stereo44.1kHz float PCM window
with the existing licensed FFmpeg. Three immutable windows occupy at most51MiB
of decoded cache; one source/temporary decode adds at most41MiB. A one-result
mailbox and at most30 recent identifiers bound pending state. Failure preserves
the current bank; startup retains the bundled fallback and restores the latest
hash-validated live cache in the background. Ongoing requests run every180seconds
or on Repeat with Chops/Film selected. No network listener is opened.

The composition worker copies suggested energy/silence cuts into normal banks;
fresh footage and automatic edits publish only at64-beat boundaries. Manual
chops address the full immutable film PCM using Event.frame as source offset
for identified manual onsets (automatic Event.frame remains schedule time).
Start/length changes are small control metadata updates; no PCM slicing,
allocation or decoding occurs on the audio thread. Existing onset bank pins
retain both PCM and start/length through source changes. Film remains a separate
mixer path and its manual anchor plays up to8seconds. This is editable acoustic
chopping, without transcription or desktop semantic dialogue selection.
`dialogue_ledger.py` continues to track only committed offline fallback lines;
live source selection retains recent source identities in the archive worker.
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
