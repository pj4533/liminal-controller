# Install and recover

The device has independent cryptographic identity verification for both OS
partitions. Preserve strict SSH checking and the original pin. A fresh scanned
key, matching IP or reboot timestamp alone must never authorize deployment.
The current secondary stock OS must remain an untouched recovery installation.
Use `deploy-staged.py --qualify-only` for current-session testing: preflight
before stopping, graceful SIGTERM, checkpoints and automatic fail-closed rollback.
It never installs over secondary stock init. Permanent installation belongs only
in the verified primary dispatcher after runtime qualification.

## Build and private staging

```sh
sh scripts/build-native.sh
python3 -m unittest discover -s tests -v
ZIG=/verified/zig-0.13.0/zig sh scripts/build-native.sh device
python3 scripts/stage-encoder.py
python3 scripts/stage-standalone.py --assets /PRIVATE/assets --out /PRIVATE/payload
```

The last command creates a PRIVATE archive with100 commercial drum takes,
143CC0 instrument WAVs, source-credit image/film cache, paired x86_64 engine,
stdlib runtime, supervision/recovery scripts, licenses and per-file hashes.
Never publish or commit that archive. FFmpeg is pinned to the documented
Stillwater release/hash and accompanied by its GPL license/provenance. Obtain
corresponding source/build configuration from the recorded upstream release.
No sessions, recordings, settings, keys, network endpoint or vendor init script
belong in the package. The original remote controller's pack.py is historical;
use stage-standalone.py for this branch.

Before transfer inspect ELF x86_64 architecture, all payload hashes, disk space
and the current MIDI/display/audio owners. Preserve a private complete checkpoint
of the active init/recovery scripts and Stillwater source/session/history state.
The existing104recordings remain in place with path/size/inode/mtime inventory;
never delete, reformat, wipe, or overwrite those recordings to make space.

Transfer into a new private staging location using independently pinned SSH.
Verify the archive hash before extraction and every manifest hash afterward.
The target home is isolated `/data/liminal`. Refuse an existing home until its
state has been inspected/backed up. Do not deploy an ARM host engine. The target
needs existing Python3.10, x86_64 libasound and amidi. Test the bundled FFmpeg
with the existing `/lib/ld-linux-x86-64.so.2` loader if necessary; do not modify
system loader links or libraries.

Save/stop the current player through `/etc/init.d/push3 stop`, then prove all
registered and discovered old owners dead. If stop/ownership fails, retain its
evidence and stop deployment. The installer refuses a competing owner. Only
then rename the fully verified stage to `/data/liminal` and run:

```sh
python3 /data/liminal/scripts/install-standalone.py
/etc/init.d/push3 start
/etc/init.d/push3 status
```

The installer preserves the active controller dispatcher **verbatim** under
`/data/liminal/recovery/previous-init` with its hash, writes a new wrapper and
selects Liminal. It does not itself start, stop or reboot. The old controller's
Stillwater/stock backups are retained untouched. The supervisor refuses competing
stock/Stillwater/controller owners, records PID/start identity before opening
its child gate, and uses three bounded quiet retries. Failure never starts
another hardware owner. `ready.json`/`liminal.log` describe current readiness;
shutdown removes readiness. New starts always have transport stopped.

## Device acceptance

Verify exactly one app/supervisor, expected payload source/native/asset hashes,
advancing actual ALSA written frames and USB display counters, no xruns/errors,
stopped transport and zero peak for at least60seconds. Check existing recordings
and Stillwater state match the stopped checkpoint. A controlled programmatic
play/manual test must use master zero or explicitly reduced supervised levels;
no unattended audible notes. Physical audio, pad feel, screen appearance and
latency remain human checks even after counters pass. Graceful stop/restart and
a saved-checkpoint reboot/default-boot test are separate device gates.

## Recovery

Settings gives an explicit Stillwater, stock or old controller return after
native shutdown. CLI recovery after proving shutdown:

```sh
/etc/init.d/push3 stop
python3 /data/liminal/scripts/standalone-boot.py select stillwater
/etc/init.d/push3 start
```

Use `select stock` or `select controller` deliberately. The wrapper calls the
preserved old dispatcher and leaves its recovery backups intact. To restore
the prior installation entirely, stop/prove all owners dead, verify
`recovery/previous-init` against `init-hashes.json`, then restore those exact
bytes and executable mode to `/etc/init.d/push3`. Keep all new/old data and
backups. No uninstall deletes music. Do not migrate/restore older sessions as
part of an application rollback.

## Primary boot success

GRUB sets the other root as next default before each boot. Stock normally calls
`com.ableton.update.registerSuccessfulStartup` at `/com/ableton/Update` to
acknowledge success. Bypassing that contract caused the prior controller boot to
fall back to the older secondary OS/key. `boot-success.py` acts only on primary,
requires60seconds of fresh, ready real ALSA/display progress without new xruns
or errors. Any xrun counter increase or decrease resets the window; the receipt
retains baseline/final totals and delta. It calls the existing stock API and,
if explicit service launch is needed, omits `--with-live-service`. Stock D-Bus
autoactivation can still launch UpdateDBusService with that flag: this was
observed on the accepted device, with no Live/Push3 launcher process and no
USB/ALSA descriptors in the service. That stock configuration stays unchanged.
Hardware exclusivity must be checked directly. It verifies primary default/secondary
fallback in grubenv and saves a boot-ID receipt. Failure leaves secondary
fallback selected; it never forces reboot, resets firmware or starts Live.
Before changing primary preserve its exact init, grubenv and recovery hashes.
Leave secondary init byte-for-byte stock. A successful controlled reboot and
then another boot are the persistence acceptance gates.
Both controlled post-fix boots passed for runtime1dfaa516; see
STANDALONE_VALIDATION.md. Later documentation commits are not deployed versions.


## Channel FX: source/native pairing

This change requires a NEW native engine plus the staged Python source as one
coherent manifest-reviewed pair. The earlier private `deploy-chop-gate.py`
refuses native-byte changes and assumes the old fixed file set. Its reviewed
replacement installed runtime87c8637 successfully on2026-11-22; see the device
evidence in STANDALONE_VALIDATION.md. Include `channel_fx.py`
in the runtime whitelist; `fx_specs.h`/`fx_dsp.h` are build inputs. Never combine
new Python with the previous native engine, which does not support command16.

Every subsequent authorized rollout must retain the documented pinned SSH wrapper,
save a fresh stopped checkpoint, gracefully stop/prove all owners dead, verify all
source/native/staged manifest hashes, run the complete device suite and a silent
master-zero actual ALSA/USB qualifier. Exercise all pages/effects, held releases,
boundary refresh, rapid changes and Stop; then require at least60seconds of
normal stopped service, zero new xruns/overflow, advancing ALSA/display and
exclusive ownership. Preserve recordings/session inventories and init hashes.
Rollback restores the checkpointed source/native/manifest and necessary private
mutable state as a pair, verifies hashes and repeats stopped health. Never
restore recordings/sessions/init/recovery/OS as part of application rollback.
This implementation does not authorize changing boot, rebooting or updating
the Drift gateway. Actual x86 timing and silent ALSA/USB checks passed for87c8637;
physical controls, listening and subjective quality remain human acceptance checks.

## Rhythmic chops / automatic pad feedback candidate

This is a paired ABI2 update. Include src/dialogue.py in the runtime whitelist;
its Event pad field changes the native/Python layout. The stage manifest records
abi2 and upstream10f5e1d. Never use the prior native engine or an earlier delta
helper's fixed added-files allowlist. Follow the existing checkpoint/owner/hash,
silent device suite/ALSA/USB qualification and60second normal-health gates above.
The previous accepted ABI1 source/native/manifest must remain together for rollback.
