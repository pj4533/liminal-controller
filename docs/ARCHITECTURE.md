# Architecture

`src/app.py` owns one raw MIDI input and the usbfs display, rendering at10fps.
There is no onboard synth, PCM engine, file server or inbound network listener.
`hardware.py` and `midi.py` reuse the clean MIT Stillwater hardware/parser baseline;
`canvas.py` retains its bounded BGR565 canvas and pixel font. The runtime requires
Python3.10+ and existing `amidi`/`libasound.so.2` on Linux; display is USB2982:1969.
Target is Push x86_64 Python3.10.14. There are no native compiled payloads.

`protocol.py` owns persistent outbound private-IPv4 TCP20808, TCP_NODELAY,
UTF-8 NDJSON, 64KiB maximum frames, depth12, finite numbers, 3s lease timeout,
1s ping, fresh-session generations and monotonic snapshots. It bounds pending
output at256frames/256KiB. Parameter edits coalesce by channel/parameter at60Hz;
critical ordered commands never discard release to retain a knob edit. Overflow
closes the lease, so Liminal releases its captured voices. Reconnection clears
all queued messages/edits and waits for fresh state. Unknown/unsupported replies
remain visible. RTT is ping/pong elapsed time, not audio latency.

The single UI loop performs bounded nonblocking socket I/O; a connection attempt
has a150ms timeout and retries once a second. This can delay UI input while the
remote endpoint is unavailable; timing requires device measurement. Every read
is at most64KiB, with at most16 reads and32 writes per tick. No JSON/audio work
runs in a callback. Liminal is responsible for its own lease ownership, native
voices, score evolution, preparation/cache budgets, automatic gates and audio.

`controller.py` discovers up to16channels, active first, stable ordering within
banks. The server's exact parameter metadata maps eight fixed slots. Relative
knob targets accumulate locally for300ms while awaiting a canonical snapshot;
only canonical remote values are displayed. No setting is replayed after a new
session. Local settings persist only the private network endpoint, via atomic
replace. UI selection never sends a mode or sound change. Captured note IDs
survive selection/octave/program changes. Pressure and release address that ID.

The bottom-left melodic pitch is the **server's exact base_midi**, with
`degree=column+3*row`, row0 at the physical bottom. The default is root_midi-24
plus12*octave_offset, with bass offset-1. The complete window is checked before
requesting a new octave; old mapping remains until the server publishes a ready
window/revision. Onsets include instrument_revision or bank_revision. Ready
bank replacements are atomic snapshots; stale epochs reject on Liminal.

`render.py` copies the complete original packed scene and draws eight physical
contacts on its authored film strips, fixed witness marks and exact bounded
percentages last. All labels/values come from the selected remote channel.
The image is960×160 BGR565 with1024pixel stride,327680bytes per frame. Packing
and cropping use Pillow offline; runtime loads the packed asset directly.
There is no audio-reactive animation or fabricated playback activity.

The supervisor owns a permanent singleton flock, checks competing stock and
Stillwater process names, records PID plus `/proc` start identity, and gates each
child on a pipe until its registry exists. SIGTERM requests bounded graceful
shutdown. An unreleased owner blocks replacement; failed release never starts
stock. Three quiet retry attempts leave a recovery-required marker and logs.
The deliberate Settings recovery request is processed only after the child was
reaped and hardware closed. Recovery uses verbatim private init backups.
The dispatcher preserves the prior init instead of assuming Stillwater's internals.
See INSTALL for limits and operator release checks.
