# Installation and reversible boot selection

This independent application targets already-authorized Push3Standalone root
access; it supplies no key, enrollment, firmware modification or vendor software.
Local tests alone do not establish hardware acceptance; see VALIDATION.md for
the authorized pre-reboot installation and the unresolved post-reboot identity.
Keep trusted pinned SSH access and an off-device backup. Never run Stillwater,
stock or this controller as competing MIDI/USB owners. Preserve all existing
music, histories, recordings and settings; installation does not migrate them.

## Build and stage without touching hardware

```sh
python3 -m unittest discover -s tests -v
python3 scripts/demo.py
python3 scripts/pack.py
```

The archive `.build/liminal-controller.tar.gz` includes whitelisted stdlib runtime
source, scripts, original packed artwork and licenses. Its manifest records every
file SHA256. No Python runtime/native ELF binary is bundled. Use the existing
Push Python3.10.14, x86_64 libasound and amidi. Developer art regeneration alone
requires Pillow: `python3 scripts/prepare-art.py`. Check all runtime hashes after
transfer; stage into a new directory before any service change. Private network
settings are configured on-device and are excluded from every bundle.

## Back up and prove release

After the player saves/stops, privately back up the existing `/etc/init.d/push3`
**verbatim**, its original stock backup, current Stillwater source/scripts/assets,
enabled preference and all sessions/recordings. Record hashes and retain an
off-device copy. Do not publish those files or replace the stock backup with a
selector. Capture existing process PID/start identities. Gracefully stop through
the existing init and prove every MIDI/USB/stock/Stillwater owner is dead before
starting another app. A failed stop/registry check blocks takeover; do not remove
ownership evidence. Save unsaved stock work before any quit. This guide provides
no destructive kill sequence or automatic takeover.

Extract the reviewed payload into `/data/liminal-controller` after staging/hash
review. Start once directly, disconnected and stopped, only after release:

```sh
cd /data/liminal-controller
python3 src/app.py --home /data/liminal-controller
```

Terminate cleanly before supervised installation. Configure Liminal's opt-in
listener on its literal private LAN IPv4:20808 in Storage & Settings. No firewall
port forwarding, tunnel or public listener. The protocol is trusted-LAN only,
unauthed/unencrypted, one controller lease. Push has no new listener.

## Install the dispatcher explicitly

Supply the verified **stock** init backup path from your current installation.
The installer preserves both the current init and stock init bytes/modes under
`/data/liminal-controller/recovery`, saves hashes and refuses reinstall/overwrite.
No existing script is embedded in this public repo. The default selection stays
`stillwater`, invoking the preserved previous init exactly as before.

```sh
python3 /data/liminal-controller/scripts/install-boot.py \
  --stock-init /YOUR/VERIFIED/PRIVATE/STOCK/INIT
```

This only installs the selector: it never starts/stops a device or reboots it.
After separately stopping/proving existing owners released, select/start:

```sh
python3 /data/liminal-controller/scripts/dispatch.py select controller
/etc/init.d/push3 start
/etc/init.d/push3 status
```

The supervisor checks common stock/Stillwater owner names and its own registry;
these checks supplement the operator's complete release proof. Unknown renamed
hardware owners cannot be inferred reliably. A child starts only after its
PID/start identity is recorded. Logs are `controller.log`/`supervisor.log`;
`ready.json` reports process readiness separately from connection and transport.
No remote connection is needed to become hardware-ready. Shutdown removes ready.

Before auto-start/cold boot acceptance, verify one supervisor/app, no stock or
Stillwater competitor, manifest hashes, stopped transport, display/MIDI controls,
private endpoint editing, disconnect release and deliberate recovery. Physical
pad feel/hues and native audio need supervised human acceptance. A boot test needs a saved checkpoint and verified device identity. The current
installation/boot/check scope is already authorized; see VALIDATION.md. Never infer boot success
from a local simulator screenshot.

## Recovery / rollback / removal

Settings → lower1 Stillwater or lower2 Stock → lower8 Apply deliberately requests
recovery. The supervisor reaps the app before starting the chosen preserved init.
Crashes never automatically start another app. Repeated failures leave a marker
and logs; use trusted SSH if hardware cannot show settings.

For CLI recovery, stop first and prove all controller owners released, then:

```sh
/etc/init.d/push3 stop
python3 /data/liminal-controller/scripts/dispatch.py select stillwater
/etc/init.d/push3 start
# Or use select stock after verifying its preserved backup.
```

For full removal, gracefully stop the selected app, prove release, verify the
saved `recovery/previous-init` SHA256 against `init-hashes.json`, and restore it
verbatim with its executable mode to `/etc/init.d/push3`. Retain controller and
Stillwater private data/backups. No uninstall operation deletes music or files.
Do not restore older sessions merely to roll back application source.
