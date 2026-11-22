# Liminal for Push 3 Standalone

A self-contained Lo-Fi instrument: six Auto/Manual mixer channels, real AJ Hall
full drum takes, acoustic Liminal multisamples, playable exact film chops, and
slowly crossfading collection images behind readable controls. No Mac instance,
controller connection, AI music/image service or network listener is needed.
Boot starts stopped; Play toggles the local arrangement.

**Status:** live Push runtime **a89cc365cb669e12793dfe8c6d20de7d007079dc**.
Live Internet Archive newsreel sourcing, background decoding, boundary publication
and editable manual chops pass actual silent device qualification. Play toggles
play/stop, melodic pads use Stillwater defaults, drums start dry, and chops have
bounded foreground gain. All118device tests and234private-library rehearsal
checks pass. Existing recordings/sessions
are preserved. Physical listening and pad feel remain human checks; see
[validation](docs/STANDALONE_VALIDATION.md).

Press Play to start or stop. Select a channel with the six top buttons; hold Shift and
press its lower button for Manual, then play the pads. Mix exposes six channel
levels on the first six encoders; the Volume encoder adjusts master. In Drums
Auto, pads choose a take, arrows switch catalog pages, and Repeat requests
another compatible take. Changes arrive at the next 16-bar boundary.

With Chops selected, Repeat fetches fresh archive material directly on Push.
Shift+lower5 enables Manual; lit pads trigger unique consecutive editable cuts across the full phrase. In Device view,
encoder6 sets start,7 length,8 selected cut; Shift gives finer editing. Fresh footage is requested at every take transition in Auto and Manual. New
sources arrive at the next16-bar boundary. No computer is required; internet
is needed for fresh sources, and failures retain local material.

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
