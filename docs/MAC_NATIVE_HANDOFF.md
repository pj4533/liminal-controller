# Host coding-session handoff: native acceptance and Push identity

Status on 2026-11-20: repairs are pushed, but the full playable-project objective
is open. PJ already authorized installation, boot takeover and appropriate device
checks. Remaining gates below require evidence, not another permission request.

Last verified installed controller: `c5917418ce4f0b785ab5077e395b09a72dc0f356`.
Paired Liminal source: branch `push3`,
`378174bd98ae74429f0b4b577f5e7dddbcb83e8c`. Latest controller `main` contains newer
documentation; its rebuilt bundle has not been deployed. Before reboot, the
controller ran with exclusive MIDI/USB ownership and advancing display transfers,
disconnected from Liminal. Session and 104 recordings were preserved and Stillwater
recovery was exercised. After controlled reboot, strict SSH rejected a changed
host key. No new key was accepted; post-reboot identity/operation are **unknown**.
Private identity and operational details are deliberately absent here.

## Native coding and qualification

Use the latest controller `main` and the exact Liminal `push3` commit above in
dedicated clean checkouts. Preserve unrelated edits, signing, private assets and
settings. **Keep Liminal main untouched; do not merge or deploy as part of this
handoff.** Read Liminal `AGENTS.md`, `docs/controller/README.md` and
`docs/mix-verification.md`. Resolve pinned packages with Xcode; use a placeholder
Secrets.swift from its template if absent. No real key is needed for acceptance.

After checkout, from the controller repository, run this in bash with the dedicated
Liminal path set. Direct commands fail on errors; no `|| true` or success trailer:

```bash
set -euo pipefail
: "${LIMINAL_CHECKOUT:?Set the dedicated Liminal checkout path}"
test "$(git branch --show-current)" = main
test "$(git -C "$LIMINAL_CHECKOUT" branch --show-current)" = push3
test "$(git -C "$LIMINAL_CHECKOUT" rev-parse HEAD)" = 378174bd98ae74429f0b4b577f5e7dddbcb83e8c
python3 scripts/native-acceptance.py "$LIMINAL_CHECKOUT"
```

The existing script builds macOS, runs all LiminalTests with parallel testing
disabled, then builds visionOS Simulator. Pass `--vision-destination` with an
installed destination if Apple Vision Pro differs. Expected: both BUILD SUCCEEDED,
all tests pass, no unexpectedly skipped controller tests. Preserve full logs and
xcresults outside git. Linux attempts lacked Xcode; **native builds/tests have
not run**. A failed native step must retain a nonzero status.

Fix any compile/API/isolation/test failures on `push3`, rerun this entry point and
record the new tested commit. Do not change signing to bypass build failures.
The critical new regressions are captured real Python wire validation
(`actualPythonControllerParameterFramesValidateNativeSchema`), actual-player drum
supersession (`supersedingQueuedSwapOnlyReusesInactivePlayer`), full-bank 44.1/48/96
kHz ownership/pressure retry
(`coordinatorReleasesObsoleteBanksBeforeThirdProductionWindowAndRetriesPressure`),
and chop trigger/stop fades between modulation ticks
(`betweenModulationTicksStopPreservesEntireChokeFade` plus the extended bank test).
The memory test's 45-second correctness allowance is not a preparation deadline.

Then qualify Debug **and** Release: default Auto PCM parity against baseline
`25592874bc614e1b481f68ff3651e2fac5c728ad` without changing Liminal main; serialized
mix captures/matrices per mix-verification.md; isolated-wet deadlines, source
exclusion/effect routing, peaks, CPU and complete/retired/manual PCM at supported
rates; at least ten minutes of transitions/rapid selections, held releases and
route/lifecycle stress. Keep captures and unique derived-data folders outside git.
Missing assets/footage and skipped captures are not passing evidence. Verify
quantized drum/chop timing under load and measure pad-to-audio latency separately
from network RTT. At 96 kHz next-bank prewarming can defer under 128 MiB; measure
whether visible not-ready replacement meets the musical requirement.

Keep `LofiBus.isolatedPreparationQualified=false` until those measurements pass.
Film/Space Manual remain unsupported. Build/test success alone does not establish
native audio qualification or connected playability.

## Restore trusted Push identity before further device checks

1. Consult the private deployment checkpoint in the existing trusted local records.
   Independently identify the physical Push through a trusted local console/host
   inventory or another authenticated path; verify its identity and actual host
   public key against that source. Diagnose address reassignment versus legitimate
   key rotation. Never accept `ssh-keyscan` output as proof of identity, disable
   strict checking, or blindly delete/replace the old pin.
2. Only after the presented key matches independently verified evidence, reconcile
   the specific stale pin while preserving the original checkpoint and audit
   trail. Reconnect with strict checking. Until then, do not deploy/reinstall,
   issue remote commands or claim post-reboot success.
3. Verify actual boot target, one supervisor/app, exclusive MIDI/USB ownership,
   stopped/disconnected startup, installed manifest hashes, session/recording
   preservation and Stillwater/stock recovery evidence. Complete physical
   display/pads/control/endpoint checks and, once native qualification permits,
   connected Play/video/readiness, Stop, releases and reconnect stress. Follow
   [INSTALL.md](INSTALL.md) and [VALIDATION.md](VALIDATION.md); preserve user data.

Return exact installed/tested/latest commits, build destinations/configurations,
test counts, logs/xcresults, qualification results and unresolved checks to PJ's
current coding session. This file is the handoff; it has not been sent elsewhere.
