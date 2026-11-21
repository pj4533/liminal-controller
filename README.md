# Liminal for Push 3 Standalone

A self-contained Lo-Fi instrument: six Auto/Manual mixer channels, real AJ Hall
full drum takes, acoustic Liminal multisamples, playable exact film chops, and
slowly crossfading collection images behind readable controls. No Mac instance,
controller connection, AI music/image service or network listener is needed.
Boot starts stopped; Play starts the local arrangement.

**Status:** host implementation and private x86_64 staging are verified. Device
identity has been independently verified across the two OS partitions. Runtime
and persistent-primary boot qualification are in progress; physical listening
acceptance remains separate. Existing controller/Stillwater music is preserved.

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
