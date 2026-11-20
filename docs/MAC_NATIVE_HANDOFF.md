# Native Mac build, test and qualification handoff

2026-11-20. This is a local handoff, not authorization to install, take over, boot,
or start music on Push. No device has been touched. Connected playability remains
unaccepted until the gates below pass. Python/Linux checks cannot replace them.

Paired sources: controller repository branch `main` (exact commit in the release
`.build/manifest.json` under `source_commits.liminal-controller`), and Liminal
branch `push3`, repair commit `378174bd98ae74429f0b4b577f5e7dddbcb83e8c`.
The final repair report also records both full commits. Never merge to or change
Liminal main for this validation. Work in dedicated clean clones/worktrees and
preserve existing local edits, private samples and settings.

## Fail-visible native entry point

On the Mac, fetch/check out those paired commits. Read Liminal `AGENTS.md`,
`docs/controller/README.md` and `docs/mix-verification.md` first. Xcode must support
macOS 26 and an installed visionOS Simulator destination; resolve its pinned
packages with Xcode. Preserve signing settings. If Secrets.swift is absent, copy
Secrets.swift.template with its placeholder; generation is unnecessary. Do not
copy private secrets into the controller repository or any report.

From the controller checkout, set LIMINAL_CHECKOUT to the dedicated native
checkout path, then run in bash (direct commands, no `|| true` or success trailer):

```bash
set -euo pipefail
: "${LIMINAL_CHECKOUT:?Set the dedicated Liminal checkout path}"
test "$(git -C "$LIMINAL_CHECKOUT" branch --show-current)" = push3
test "$(git -C "$LIMINAL_CHECKOUT" rev-parse HEAD)" = 378174bd98ae74429f0b4b577f5e7dddbcb83e8c
python3 scripts/native-acceptance.py "$LIMINAL_CHECKOUT"
```

This entry point stops with a nonzero status on the first failure and prints its
success sentence only after **all three** commands succeed:

```bash
xcodebuild -project Liminal.xcodeproj -scheme Liminal -destination 'platform=macOS' build
xcodebuild -project Liminal.xcodeproj -scheme Liminal -destination 'platform=macOS' -parallel-testing-enabled NO -only-testing:LiminalTests test
xcodebuild -project Liminal.xcodeproj -scheme Liminal -destination 'platform=visionOS Simulator,name=Apple Vision Pro' build
```

Use `--vision-destination` with an actually installed destination if different.
Expected: both builds report BUILD SUCCEEDED; all LiminalTests pass, no failed
or unexpectedly skipped controller tests. Preserve full logs and xcresult paths
outside git. A successful shell command after a failed build is never acceptance.
Linux attempts of these three xcodebuild operations exited 127 because Xcode is
absent; none of the native tests has run here.

The critical new regressions expected in the native results are:

- `ControllerProtocolTests.actualPythonControllerParameterFramesValidateNativeSchema`:
  four fixture frames captured from actual Python Controller.event/Client TCP
  output validate through ControllerWire.Command; the old array ID is rejected.
- `ControllerDrumTests.supersedingQueuedSwapOnlyReusesInactivePlayer`: a loop
  applies, two ready selections supersede queued swaps, and the actual audible
  player's sample clock keeps advancing on its unchanged lane before the bar.
- `ControllerInstrumentTests.coordinatorReleasesObsoleteBanksBeforeThirdProductionWindowAndRetriesPressure`:
  full current/next windows across three lead registers at 44.1/48 kHz, bounded
  single-bank admission at 96 kHz, independently pinned PCM, and retry after
  pressure is released. No 8 kHz-only memory substitute. Native preparation is
  intentionally given up to 45 seconds per ready state; this is a correctness
  test, not proof of a musical preparation deadline.
- `ControllerDialogueTests.betweenModulationTicksStopPreservesEntireChokeFade`
  and the extended `announcedBanksActivateAtomicallyAndCannotExposeOldPadsWhenNextIsUnready`:
  real manual player remains alive at 0/19 ms after stop/press between stale
  modulation ticks; stop completes only after the 20 ms fade.

## Audio and playability qualification still required

Keep `LofiBus.isolatedPreparationQualified=false`. Passing the native build and
regressions alone does not qualify isolated wet or make Film/Space Manual exist.
At 96 kHz current+next can exceed 128 MiB: next prewarming is deferred and an
actual replacement reports not-ready during preparation. Held notes can delay
readiness until their immutable PCM releases. Measure this policy explicitly;
do not advertise gap-free transitions or production-rate timing from static checks.

1. Compare untouched default Auto PCM/levels against baseline Liminal main
   `25592874bc614e1b481f68ff3651e2fac5c728ad`, using the same seeds, drum assets,
   footage cache, route and captures. Run captures sequentially in separate
   derived-data directories and output folders **outside** either repository.
   Read all mix-verification prerequisites and existing capture-lock rules.
2. Run serialized baseline and candidate mix matrices with private assets supplied
   locally and a cached film reel. For each checkout, use a unique output root:

   ```bash
   set -euo pipefail
   : "${QUALIFICATION_SCRATCH:?Set a writable path outside both repositories}"
   DD="$QUALIFICATION_SCRATCH/dd" scripts/mix-matrix.sh --out "$QUALIFICATION_SCRATCH/matrix" --strict
   ```

   Check per-case strict failures, skips, source fingerprints, finite PCM, peaks,
   routing, audible continuity and human listening. Do not count absent footage,
   sample/drum assets or skipped captures as success. The matrix is one part of
   qualification; it does not cover every manual controller interaction.
3. In Debug **and** Release, profile isolated-wet preparation, existing phrase
   deadlines, complete/retired/manual PCM ownership, peak RSS and CPU at 44.1,
   48 and 96 kHz. Run at least ten minutes of changes, quick drum supersession,
   chop choke timing, rapid windows/programs and held/stealing/releasing voices.
   Prove independent manual/Auto exclusion and dry/wet/effect routing. Capture
   drums on the source bar phase and chops on sixteenths under load. Any miss,
   leak, clipped fade or unrecovered not-ready result keeps qualification closed.
4. Exercise real protocol commands, normal Play/video gate, Stop, all-notes-off,
   lease loss/reconnect, mode switches and route recovery against the rebuilt Mac.
   Verify captured onset releases and current instrument/bank revision rejection.
   Network RTT is not pad-to-audio latency; measure the latter separately.
5. Only after native/audio gates and separate device authorization, use the
   controller INSTALL/VALIDATION checklist for exclusive hardware ownership,
   stopped/disconnected boot, controls/display/pads, private endpoint UI and
   verified Stillwater/stock recovery with saved bytes and user data preserved.
   Film/Space Manual remain unsupported. Do not enable Lo-Fi merely to obtain a
   green UI: qualification evidence must precede any gate change.

Return the exact tested commits, destinations/configurations, test counts,
xcresult/log locations, capture/profiling results and failed/skipped checks to
PJ's current session. Do not silently deploy or publish from this handoff.
