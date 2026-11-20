# Validation and explicit remaining gates

Local validation on2026-11-20:

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests -v` | 41 passed,0 failed (Python3.11 Linux host) |
| `/tmp/Python-3.10.14/python -m unittest discover -s tests -v` | 43 passed,0 failed (locally built CPython3.10.14, matching device version) |
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
screenshots or recordings. Physical pad hue/feel and an independent physical-screen view remain unverified.
Pre-reboot successful USB display transfers were observed as described below.

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

## Hardware evidence and current boundary (2026-11-20)

The authorized device installation and controlled boot sequence proceeded after
the local tests. Last verified installed controller commit:
`c5917418ce4f0b785ab5077e395b09a72dc0f356`, paired with Liminal `push3` source
`378174bd98ae74429f0b4b577f5e7dddbcb83e8c`. Before reboot, exactly one controller
supervisor/app owned MIDI/USB, readiness was true, and successful USB display
transfers advanced. The controller was disconnected because the Liminal listener
was unavailable; no remote audio or connected playability was verified.

The existing session remained unchanged and 104 recordings were preserved in
place and inventoried. Verbatim recovery init backups were checked, and the
Stillwater recovery route was exercised successfully before controller selection
was restored. Selecting stock was exercised; stock app startup was not claimed.
A checkpoint was saved before the controlled reboot.

Strict SSH reconnect then rejected a changed ED25519 host key. No replacement
key was accepted, no pin was edited, and no remote command ran after that mismatch.
Post-reboot device identity, app state, ownership and boot success are **unknown**.
The latest public docs/bundle are newer than the last verified installed payload;
repacking does not deploy them. Operational identity details remain private.

PJ already authorized installation, boot takeover and appropriate device checks;
this is not a request for repeated approval. Independent trusted device identity
verification must precede reconnect or deployment. Native builds/tests and audio
qualification remain evidence prerequisites. After trust is restored, complete
boot/ownership, all64pads/control mapping, physical display, endpoint UI,
disconnect release and recovery checks, preserving the existing data/checkpoints.
Liminal main remains untouched. The full playable project is not yet accepted.

## Integration review repairs (2026-11-20)

Real Controller.event device FX, mixer and mute packets now retain string parameter
IDs separately from the local target dictionary key. The 43-test Python 3.10.14
suite includes TCP-applied events and byte-for-byte checks of
`tests/fixtures/controller-parameters.ndjson`; the same captured bytes feed the
native `ControllerProtocolTests.actualPythonControllerParameterFramesValidateNativeSchema`
test. The fake peer rejects array parameter IDs with `bad_message` like the native
schema. Native tests remain unexecuted on Linux.

`python3 scripts/pack.py --liminal-commit FULL_PUSH3_COMMIT` records both source
commits in the manifest. Run after committing the controller, then verify manifest
hashes and the paired Liminal branch. Omitted Liminal metadata is explicitly null.
See [Mac handoff](MAC_NATIVE_HANDOFF.md) for the concrete build/test and qualification
sequence. A failed native command is a blocking result, regardless of Linux checks.
