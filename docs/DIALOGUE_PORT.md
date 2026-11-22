# Text-aware chops and playable Auto

Adapted from pj4533/Liminal10f5e1d, particularly D124–127 DialogueHierarchy,
DialogueLineInterest, DialogueReorderGuard, DialogueMotif, DialogueOnset,
DialogueFeel and DialogueChopBeat. This remains an independent instrument.

## Offline speech and failure behavior

The default preparation worker runs whisper.cpp1.9.5 base.en locally on the
first30seconds of decoded dialogue. No cloud inference, Python packages or pip
are needed. Speech runs outside the audio owner, serially, with one inference
thread, nice15 and, when available, affinity to the highest allowed CPU. Its
35-second process deadline kills and reaps the worker. Shutdown also kills and
reaps before joining preparation. The explicit existing device loader handles
the research binary's interpreter path. Runtime verifies the worker, weights
and POS model hashes. Artifact provenance and licenses are in
[local-speech.md](local-speech.md).

Recognition uses greedy English decoding, no temperature fallback, actual DTW,
and **-nfa**: flash attention disables DTW. Full JSON lexical token t_dtw centers
are10ms units. Token offsets can collapse and are never substituted for DTW.
Subwords, contractions and punctuation join before neighboring lexical centers
produce word spans inside speech segments. Missing, collapsed, backwards,
out-of-range or implausible-rate spans are rejected; repeated three-grams are
hallucination guards. Whisper probabilities are not calibrated Apple confidence
and are not presented as such. Bracketed events do not become spoken words.

The cache key includes source PCM hash, model hash and decoding/parser options;
32successful sources are retained. Failed-source suppression prevents repeated
inference every section; a new source or restart permits another attempt.
A pending/unavailable status and bounded error are visible on the display and
in ready.json. Failure preserves the incumbent bank, music and images. Startup
has a clearly pending conservative whole8-second statement until a reliable
text bank is ready; it does not claim recognized word selection. No new word
cuts are published on recognition/alignment failure.

## Text and arrangement

The MIT English NLTK averaged-perceptron model provides local lexical classes.
The portable scorer includes the upstream function/discourse lists, seven
weighted evocative lexicon categories, prefix/inflection/false-friend rules,
name/vocative, number and long-content-word weighting, and line shape scoring.
Contiguous recognition segments join into complete sentences. Audio boundaries
snap within20ms to local quiet windows and inactive units are rejected.

The strongest three complete lines form the candidate pool. A selected line
and its strongest-word anchors stay stable for four64-beat takes; the next
candidate then rotates in. The unique vocabulary includes its complete line,
meaningful words, indivisible grammatical groups and contiguous mixed cuts,
with at most eight cuts to match the fixed native automatic PCM capacity.
Signature/response prefer the strongest text weights; source order breaks
manual layout ties. Intro and outro state the complete selected line.

Names and uncertain capitalization conservatively protect their full sentence.
Negation/predicate, determiner/noun, pronoun/verb and number/noun groups remain
indivisible; contractions are atoms. Protected pieces play intact and reserve
enough time before later onsets. A fully protected sentence uses conservative
whole-line statements. POS is **not NER**; this can protect too much and does not
promise complete semantic safety or perfect transcription.

Four two-bar hook skeletons and five loop feels drive the16-bar statement,
groove, build, breakdown and outro. Additional stabs prefer gaps in measured
drum energy attacks; response skeletons include backbeat steps. Regular stabs
use1/2/4sixteenth gates with6ms lead and60ms minimum where the source permits.
Validated text boundaries and explicit edits retain their complete source starts
in Auto and Manual; a short fade softens the onset without deleting quiet words.
Only the acoustic startup fallback uses up to30ms soft lead plus2ms preroll.
Edits to multiple pads accumulate for the same source/line through publication. Quarter steps stay
fixed; offbeats move consistently up to24ms. Native analysis stays allocation,
file and inference free; every replacement publishes at64-beat boundaries.

## Pads and ownership

Chops uses Ableton's Slicing layout: four pads left-to-right, ascending through
the entire left32, then from the bottom through right32. One unique vocabulary
cut occupies one pad; unused pads are dark and inert. Drums uses16distinct
source ranges in the bottom-left4x4; Shift+pad chooses a catalog take. Film has
one lit anchor pad. Manual and Auto share the same bank and physical mapping.
Chops is held-to-play, completing once if held and stopping on release.

Auto also accepts manual playing. Mode changes gate only future automated
onsets; held releases retain onset-owned bank/source identity across selection,
mode, editing and bank changes. Successful native automatic cut/pitch triggers
alone flash the exact pad red, bounded by120ms/source/gate. MIDI feedback runs
at50Hz independently of the10Hz display. Continuous Drum/Film playback does
not invent a pad trigger. Manual/rejected/stale events cannot create red flashes.

## Differences and validation

Linux replaces Apple Speech and NaturalLanguage; DTW is approximate alignment,
not forced phonetic alignment. Acoustic onset and drum novelty fields are
portable approximations, not the desktop classified kick/snare field. This
port does not transplant the desktop's cross-film motif crate, full DSP,
echo/reverse recipes or exact random sequence. Editable ranges share the source;
editing a live vocabulary pins its semantic line until new footage arrives.

Run build-native.sh, the full unittest suite, check-speech-artifacts.py and the
private-asset rehearsal; inspect960x160FX/Cuts/Help and LED mapping. Host rehearsal
on ARM validates honest unavailable-worker retention. Actual archival DTW/PCM
replay validates semantic cuts and native scoring separately. Neither replaces
concurrent device inference/audio/USB qualification, physical listening or human
acceptance. ABI2 source/native/model/tools/licenses must be staged coherently.


Stopped publication correction: playing retains the64-beat bank boundary.
An explicitly requested preparation (initial text, source/drum request or edit)
may publish while stopped only after every native voice and admitted onset pin
is clear. A held pad defers it through release. Ordinary next-take prefetch stays
queued; stopping cannot spin through revisions. An initial unaligned bank is an
honest manual-only fallback. Read CHOP_REGRESSION_GATE.md (under docs/) for the
mandatory actual-source acceptance; one unique whole line is insufficient.
