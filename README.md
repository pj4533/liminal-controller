# Liminal Controller

A standalone Push 3 surface for a running [Liminal](https://github.com/pj4533/Liminal)
instance. Full-screen original cinematic material, eight live remote controls,
channel mixer, manual scale pads, prepared drum choices and live chop banks.
Python 3.10+, standard library at runtime. No audio is generated on Push.

![Synthetic 960×160 simulator screen](docs/media/simulator-device.png)

The controller opens one persistent outbound TCP connection to Liminal on your
trusted LAN, normally port 20808. It boots safely disconnected and displays
WAITING FOR LIMINAL. Play requests the normal Liminal video/readiness gate.
All values, modes, instrument identities and pad readiness come from Liminal;
reconnect never restores an old mix or replays a note.

## Try without hardware

```sh
python3 -m unittest discover -s tests -v
python3 scripts/demo.py --screenshot .build/demo.ppm
```

The demo runs the actual `src/app.py --simulate` entry point and a deterministic
local synthetic peer. It produces a native-size PPM without USB, MIDI or audio.
For interactive protocol experiments, run `python3 src/fake_server.py --ambient`
and `python3 src/app.py --simulate --seconds 10 --screenshot .build/frame.ppm`
in separate terminals. The simulator is intentionally headless; automated tests
exercise the real MIDI parser and Controller.event handler.

**Status:** application, tests and release tooling are implemented; native macOS
audio qualification and actual Push acceptance remain required. Liminal's `push3`
branch advertises partial capabilities: Lo-Fi bass/lead/mids remain disabled until
isolated-wet native qualification; Film and Space manual pads are unavailable.
The UI reports unsupported controls and keeps unprepared pads dark. Network RTT
is measured round trip, never represented as pad-to-audio latency.

Read [installation/recovery](docs/INSTALL.md), [controls](docs/CONTROLS.md),
[architecture](docs/ARCHITECTURE.md), [protocol](docs/protocol-v1.md),
[validation](docs/VALIDATION.md), and [artwork provenance](docs/ARTWORK.md).
MIT; retained upstream notices in NOTICE and LICENSE.push-hack.
