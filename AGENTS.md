# Standalone contributor guide

This branch supersedes the old remote controller. Read README and
STANDALONE_SPEC/ARCHITECTURE/CONTROLS/INSTALL in docs before editing. Current
entry is src/standalone_app.py; legacy src/app.py is excluded from runtime packs.
Runtime Python3.10 stdlib plus packaged offline whisper.cpp/base.en and MIT POS model;
separate native sampler ABI2, single MIDI/display and
ALSA owner. No Mac peer, inbound listener or AI generation. Preserve other work.

Render stays bounded and allocation/file/network/decode free. Banks publish only
at64-beat boundaries; programme changes also use64 beats despite upstream16-beat
phrases. Held releases keep onset-owned bank/source identity. Reject newest
onsets on voice overflow; never discard a release to keep edits. Worker failure
keeps current playback/images. Stop must hush delayed effects as well as voices.

Run sh scripts/build-native.sh and python3 -m unittest discover -s tests -v.
Run private-asset scripts/rehearse-standalone.py for audio/media changes. Inspect
native960x160 display renders after UI changes. Crossbuild device with verified
Zig0.13.0, never deploy ARM. stage-standalone.py explicitly makes a PRIVATE
payload with100 commercial drum WAVs and licensed ffmpeg; never commit/publish it.
Keep original source/license/credits. No private addresses, keys, media catalog,
recordings, settings, vendor scripts or operational logs in git.

Hardware requires authorized deployment plus verified identity and saved
checkpoint. Preserve Stillwater songs/history/104recordings and existing recovery.
Gracefully stop/prove all owners dead; stage/hash review source and binary as a
pair; start stopped. Never bypass a changed SSH pin. Physical listening/display,
MIDI, ALSA/xruns, restart and default-boot acceptance are device gates, not
memory-render assertions. Commit/push completed implementation; no force push.
