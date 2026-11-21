# Liminal for Push 3 Standalone

A self-contained Lo-Fi instrument: six Auto/Manual mixer channels, real AJ Hall
full drum takes, acoustic Liminal multisamples, playable exact film chops, and
slowly crossfading collection images behind readable controls. No Mac instance,
controller connection, AI music/image service or network listener is needed.
Boot starts stopped; Play starts the local arrangement.

**Status:** live on Push 3, runtime **1dfaa5164933c8e6d00dafe18bec0d27ce074d27**.
All 93 device tests and the silent full-take/six-channel manual rehearsal passed.
Two controlled reboots returned automatically to primary with successful stock
boot acknowledgement. It is ready and stopped, master at 45%, with all 100 AJ
drum takes and 143 instrument samples installed. All 104 existing recordings
and seven sessions are preserved. Physical button presses and listening remain
unverified; [validation](docs/STANDALONE_VALIDATION.md) records the evidence.
Later documentation commits do not change that installed runtime version.

Press Play to start. Select a channel with the six top buttons; hold Shift and
press its lower button for Manual, then play the pads. Mix exposes six channel
levels on the first six encoders; the Volume encoder adjusts master. In Drums
Auto, pads choose a take, arrows switch catalog pages, and Repeat requests
another compatible take. Changes arrive at the next 16-bar boundary.

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
and bundled separately licensed FFmpeg for off-thread image decoding. Pillow is
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
