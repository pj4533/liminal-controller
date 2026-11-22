# Rhythmic chops and playable Auto

Source: pj4533/Liminal main10f5e1d (2026-11-22 fetch), especially D124–127,
DialogueOnset.attack, DialogueMotifTuning.hookTemplates, DialogueFeel and
DialogueChopBeat.groove. This instrument remains independent of the Swift app.

The portable worker now selects eight articulated cuts spread across the complete
prepared source instead of eight evenly sampled indices played once every seven
beats. Each selected slice retains its original chronological pad identity.
A short RMS onset analysis skips quiet lead, retains at most30ms soft attack lead
plus2ms preroll, and aligns the half-peak attack to the musical accent. Prepared
PCM, bounded per-cut gain and held Manual source ranges remain immutable.

Automatic composition uses the upstream four two-bar signature/response/third
hook skeletons, held for two takes, within a64beat arc: statement/tag, recurring
chop beat, denser build, sparse breakdown and return/outro. Extra groove stabs
prefer gaps in the actual drum take's measured energy attacks. The groove is
bounded to six onsets per bar, at most three consecutive sixteenths and a beat
without an onset. Gates use one/two/four sixteenths, stop6ms before the grid end
and retain a60ms minimum when the source permits. Each loop chooses one of the
five upstream feels: grid, laid, rush, drunk or ahead; quarter steps stay put,
offbeats shift consistently by at most24ms. Seeded choices evolve each take.
New pieces remain in source order within runs into a signature because there is
no semantic evidence permitting arbitrary reordering. Immediate repeated pieces
are avoided when multiple cuts exist. Edits and new footage still publish only
at64beat boundaries; no render-thread analysis or allocation is added.

Both Auto and Manual now accept the same manual pad onsets. Mode changes only
gate future automated notes. Existing automatic and held notes retain their
own lifetime and release identity. Drums Shift+pad preserves catalog choice in
both modes; normal pads always audition the four drum cuts. Film retains its
one-shot anchor. Chops remains held-to-play, ending once or on release.
Native successful automatic triggers alone create red pad flashes, bounded by
120ms/source/gate. Exact cut identity and melodic pitch travel with the native
event; feedback is isolated by channel and bank revision. Continuous Drum/Film
playback has no invented pad trigger and does not flash a proxy pad. Manual playing, rejected voices and stale-bank feedback
cannot invent red triggers. Stop, mute and Manual clear the relevant feedback.

## Deliberate platform differences

There is no transcription/NaturalLanguage or semantic word-interest selection.
The acoustic fallback prefers audible envelope variation over silence/flat tone
within eight source regions. It cannot recognize cool words, negation, complete
spoken lines or syllables. The intro states a selected cut; it does not promise
the Swift complete-line introduction or complete spoken-line outro.

RMS onset/take-energy measurements approximate the upstream speech-band onset
and classified kick/snare/ghost timing field. They do not reproduce its filters,
semantic reorder permission, word hierarchy, valley gate snapping, full DSP,
echo-throw/reverse recipes, exact MusicRNG sequence or performance-memory reuse.
Manual pads retain complete chronological source coverage rather than being
replaced by the desktop semantic vocabulary. Physical listening, swing feel,
pad colour/latency and perceived line interest require human acceptance.

## Validation

Run build-native.sh, the complete unittest suite and private-asset
rehearse-standalone.py. Inspect native960x160FX/Cuts/Help renders. The ABI2 source,
x86 engine and manifest are a mandatory pair. Host memory/audio captures do not
establish device ALSA/xruns, physical input/display, restart or default-boot gates;
follow STANDALONE_INSTALL.md before calling a candidate installed.
