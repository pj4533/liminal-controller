# Install and recover

This branch has not been installed on hardware. The current blocker is a changed
SSH host key without independent device identity proof. Never accept a scanned
replacement key or disable strict checking. A trusted host's already established
connection/inventory or the physical device console must establish the public
key before deployment. A changed key at the same IP is not identity proof.

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
