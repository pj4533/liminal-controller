# Liminal for Push 3 Standalone

A self-contained Lo-Fi instrument: six Auto/Manual mixer channels, real AJ Hall
full drum takes, acoustic Liminal multisamples, playable exact film chops, and
slowly crossfading collection images behind readable controls. No Mac instance,
controller connection, AI music/image service or network listener is needed.
Boot starts stopped; Play toggles the local arrangement.

**Status:** live runtime **011e676110d888ca08f9716426a16b79d37aeb67** fixes
pad-expression messages changing Echo and other physical controls. Knob edits
remain stable across notes and bank/program changes; startup applies defaults.
All202device tests, the seven-case real-source audio gate and silent ALSA/USB
qualification passed, followed by60seconds of healthy stopped service.
The previous real multi-cut Chops correction remains intact, including the
exact GuideDog eight-cut acceptance. See [release gate](docs/CHOP_REGRESSION_GATE.md)
and [device acceptance](docs/STANDALONE_VALIDATION.md). Physical listening and
feel remain human checks.

On a channel's initial Device/Note **Effects** page, encoder4 is **Echo** and
encoder7 is **Reverb**; encoder5 sets Echo Time,6 Feedback and8 Decay.
Knob edits persist across pad playing and bank/program changes. Startup applies
channel defaults. Member-channel pad expression cannot edit physical CC controls.

Press Play to start or stop. Select a channel with the six top buttons; play pads in either mode; hold Shift and
press its lower button to disable automatic triggers for that channel. Mix exposes six channel
levels on the first six encoders; the Volume encoder adjusts master. For Drums,
Shift+pads choose a take, arrows switch catalog pages, and Repeat requests
another compatible take. Changes arrive at the next 16-bar boundary.

The runtime includes source-derived rhythmic chops and automatic red pad feedback;
see [portable dialogue policy](docs/DIALOGUE_PORT.md) for scope and validation.

With Chops selected, Repeat fetches fresh archive material directly on Push.
Shift+lower5 enables Manual; lit pads play unique consecutive editable cuts across the full phrase while held.
Release stops the cut; holding plays it to the end once, without looping. On the Device/Note Cuts page (lower7/8),
encoder6 sets start,7 length,8 selected cut; Shift gives finer editing. Fresh footage is requested at every take transition in Auto and Manual. While playing, new
sources arrive at the next16-bar boundary. While stopped, prepared requests
publish after all voices finish; a held pad defers publication. No computer is required; internet
is needed for fresh sources, and failures retain local material.

Device/Note fills the screen with eight effects for the selected channel.
Lower7/8 changes Effects/Sound/Space/Motion pages; Chops/Film also have Cuts.
See [all channel effects and controls](docs/CHANNEL_FX.md).

Read [specification](docs/STANDALONE_SPEC.md),
[architecture and limitations](docs/STANDALONE_ARCHITECTURE.md),
[controls](docs/STANDALONE_CONTROLS.md) and
[installation/recovery](docs/STANDALONE_INSTALL.md).

```sh
sh scripts/build-native.sh
python3 -m unittest discover -s tests -v
ZIG=/your/verified/zig sh scripts/build-native.sh device
python3 scripts/rehearse-standalone.py --assets /your/private-assets --out .build/rehearsal
python3 src/standalone_app.py --simulate --home /tmp/liminal-demo \
  --engine "$PWD/.build/engine.so" --assets /your/private-assets --seconds 3 \
  --screenshot .build/demo.ppm
```

Runtime is Python3.10 standard library plus the native C11 engine, existing ALSA
and bundled separately licensed FFmpeg for off-thread image and archive audio decoding. Pillow is
only needed by explicit host-side media preparation. Commercial AJ Hall WAVs
are supplied privately by their owner; they are never committed or distributed
in this source repository. Bundled acoustic sample credits are retained in
[lofi-samples.md](docs/lofi-samples.md).

This branch supersedes the older remote-controller implementation. Legacy
controller files/tests remain for provenance and regression coverage and are
excluded from the standalone runtime payload. The current runtime entry is
`src/standalone_app.py`; `src/app.py` is the historical controller entry.

MIT PJ Gray; Stillwater/Push Hack notices retained. FFmpeg has its own GPL
license/provenance in the private runtime tools directory.

Text-aware chops now run offline on Push via whisper.cpp base.en and the MIT
NLTK POS model. Whole-line intros/outros, meaningful words and protected phrases
share unique Ableton Slicing pads; Drums has16distinct bottom-left4x4cuts.
Only assigned pads light or play. Pending/failed analysis retains the current
bank. See [dialogue port](docs/DIALOGUE_PORT.md) and [speech artifacts](docs/local-speech.md).
