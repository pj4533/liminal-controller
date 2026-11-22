# Chops release gate

The deployed c92fb2f reproduced one pad for ordinary aligned speech. Sentence
capitalization and noisy POS tags protected the entire sentence; the cutter
then suppressed every fragment. Auto also treated forbidden reordering as
forbidden chopping. Async analysis only queued banks at a64-beat boundary, so
a stopped manual player could keep the startup fallback indefinitely.

Protection now applies to local names, negation/predicate and number/noun groups.
The whole line remains pad1, with up to7 unique shorter aligned words/groups.
Restricted Auto plays complete fragments in source order, retaining whole-line
intro/outro. Sentence starts alone never protect a whole sentence. Candidate
selection prefers usable multiword lines; genuinely short material may report
LIMITED TEXT. Failed analysis retains the incumbent and bounded failure JSON
(max32 diagnostics, each bounded by the4MiB worker-document limit). Initial
fallback is manual-only. Active ranges/labels/source/revision and queued ranges
are explicit in ready.json; TEXT READY describes analysis, not current usability.

The old acceptance permitted any1–8 unique cuts and substituted synthetic halves
for manual qualification. This checked plumbing while bypassing the actual
selection failure. Test counts and silent hardware progress did not establish
usable chopping. Synthetic lifetime tests remain separate from this gate.

Required local gate (private paths supplied by the operator):

```
sh scripts/build-native.sh
python3 -m unittest discover -s tests -v
python3 scripts/qualify-text-bank.py --cases /PRIVATE/cases.json --assets /PRIVATE/assets --tagger .build/speech/averaged_perceptron_tagger_eng.zip --out /PRIVATE/results
```

The executable refuses a release set without the exact failing GuideDog PCM
SHA84777432b5f6c5d52d4599cc5c6e6c552f2eae1af6a70b1475ba2c19d3073671
at revisions0/4/8/10 plus an independent real archive. Case files name original
PCM, source credit, actual matching DTW JSON, SHA and revisions. They must be
reviewed as paired source/cache evidence. Never substitute fabricated PCM,
timestamps or cuts. The committed public-domain GuideDog/Chevrolet DTW fixtures
exercise the actual packaged POS model in unit tests; their constant unit-test
PCM checks selection policy only. They are not the private real-audio gate.

For each real source/revision, production prepare must become CURRENT native
bank before production MIDI/LED dispatch. Require whole phrase plus at least2
meaningful shorter unique audible ranges, distinct source/audio identities,
correct physical Ableton notes, all unused notes dark/inert, independent held
release, and at least2 non-line automatic pad identities. Auto slice PCM must
match Manual source ranges exactly. The JSON report records source/DTW/engine
hashes, labels/ranges/physical notes/audio identities/revision/current readiness.
No synthetic cut injection exists in this executable.

Also exercise cold cached startup and uncached worker completion, stopped Manual,
held defer/release, playing64-beat publication, source replacement, stale worker
results and failed alignment preserving good incumbent. Replaying actual DTW
through an uncached completion tests publication but is not fresh inference.
Silence/bracket markers must fail honestly; true one-word material may stay
limited and cannot serve as the multiword release acceptance source.

Device gate: pair source/native/model hashes; run the full suite and real-source
memory gate on actual x86, then actual ALSA/USB at master zero with fresh local
inference while progress continues and no new xruns/overflow. Require the actual
prepared text bank to become CURRENT; dispatch every real used pad via the same
MIDI path, write its actual LEDs, exercise overlap/release/Auto red onsets,
Echo/Reverb/Stop, then normal stopped healthy60seconds and preserved media.
Use fresh native snapshots after display/pump work. Never accept next_ready alone.
Human listening, visible pad colours and feel remain separate acceptance. These
checks target this regression; they cannot promise every future bug is impossible.
