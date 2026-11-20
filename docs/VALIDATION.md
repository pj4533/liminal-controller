# Validation and explicit remaining gates

Local validation on2026-11-20:

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -v` | 41 passed,0 failed (Python3.11 Linux host) |
| `/tmp/Python-3.10.14/python -m unittest discover -s tests -v` | 41 passed,0 failed (locally built CPython3.10.14, matching device version) |
| `/tmp/Python-3.10.14/python scripts/demo.py --screenshot .build/python310-demo.ppm` | pass, real simulator entry point+TCP fake peer, no hardware/audio |
| `python3 scripts/pack.py` | pass, manifest plus whitelisted release archive |

CPython3.10.14 was built from the official Python source archive
`https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tar.xz`, outside this
repository, for host compatibility testing. That interpreter is not bundled.
The device already supplies x86_64 Python3.10.14. This proves language/runtime
compatibility locally, not hardware or x86_64 device execution.

Tests cover golden frames split byte-by-byte, UTF-8 splitting, malformed/nonfinite
and deeply nested JSON, frame bounds, private network address restriction, scale
layout and complete window bounds, sixteen-channel navigation, remote authority,
unsupported parameters/modes/master, mute, octave publication, velocity/pressure,
onset-owned release across navigation, bank epochs and whole-line slot63,
disconnect clearing, real TCP reconnect/session generations, RTT heartbeat,
coalesced10000knob edits, bounded queue overflow closing the lease, stale-session
and old-revision rejection, endpoint editing/persistence, confirmed recovery,
verbatim init preservation/reinstall refusal, simulator shutdown, descriptor bounds
and singleton supervised readiness/clean child release.

The deterministic fake server uses the real Liminal golden envelopes verbatim
and a synthetic snapshot shaped from ControllerCoordinator.snapshot. It is not
an implementation of Liminal audio. It intentionally does not emulate video
analysis, async preparation, DSP, bank memory budgets, bar/sixteenth audio timing,
automatic score evolution, native queue replays or every server rejection.
Liminal's native tests own those contracts. No successful fake command certifies
native tone, musical continuity, effect quality or latency.

`docs/media/simulator-device.png` is the real stopped production renderer at
960×160, inspected visually. Range/contact sheet and disconnected view are
synthetic previews, not actual Push screenshots. There are no copied private
screenshots or recordings. Physical pad hue/feel and actual display transmission
need a separately authorized hardware acceptance run.

## One Mac native entry point

```sh
python3 scripts/native-acceptance.py /PATH/TO/Liminal
```

This runs macOS build, all LiminalTests and a visionOS Simulator build. Choose an
installed destination with `--vision-destination` if needed. It never changes
signing, generates private keys or enables capabilities. Follow the Liminal
`docs/controller/README.md` and `docs/mix-verification.md` for serialized native
baseline/candidate PCM captures and profiling.

**Lo-Fi gate remains unqualified.** Keep
`LofiBus.isolatedPreparationQualified=false` until native Debug/Release isolated-wet
preparation deadlines, actual default PCM parity, current/next/retired cache
budgets, manual source isolation, effect routing, sustained playback and captures
pass. Film/Space Manual remain unsupported. Ambient/drum/chop ready flags are
asset/routing facts and do not substitute for native acceptance. No pad-to-audio
latency, gap-free playback or human listening claim is made.

No device, boot dispatcher, existing Stillwater installation, Liminal main
branch or public service was changed by these tests. Actual-device acceptance
must separately prove stopped/disconnected boot, exclusive hardware ownership,
all64pads/control mapping, display hashes/counters, endpoint UI, disconnect voice
release, practical Stillwater/stock return and preserved user data. A controlled
boot test requires its own saved checkpoint and authorization.
