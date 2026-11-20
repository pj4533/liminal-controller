# Controls

- Play85 requests playing; Stop Clips29 requests stopped. Display follows remote
  transport and readiness; disconnect always shows WAITING, never stale PLAYING.
- Top102–109 select channels on the current page. Right navigation wheel70 moves
  one channel per nonzero packet; Shift+Left/Right62/63 changes an eight-channel
  page. Up to16remote channels are available, active channels first.
- Device110 or Note50: eight channel controls: Level, Low cut, High cut, Tone,
  Drive, Echo, Room, Pan. Encoders71–78; exact remote metadata/disabled flags win.
- Mix112: the same eight encoders change corresponding channel levels on this
  page. Lower20–27 mute/unmute their matching channel through its remote gain;
  unmute restores that parameter's published default. Shift+lower toggles
  Auto/Manual only where mode_ready is true. Returning Auto uses Liminal's ramp.
- Volume79 shows Master unavailable with the current v1 server, which has no
  master descriptor/action. It does not silently change a selected channel.
- Melodic pads36–99: right+1scale degree, up+3. Root pads highlighted. Manual
  ready instruments only; velocity1–127 and poly/channel pressure0–1. Left/Right
  request a whole octave window; old ready mapping stays until new state arrives.
- Drums: pads address catalog choices. In Auto a press requests drum_select,
  including preparation if needed; in Manual only a ready pad launches/latches
  the selected loop. Repeat56 requests drum_next. Server state describes the
  actual boundary/pending selection. Releasing a drum pad does not stop its latch.
- Chops: illuminated pads follow the actual active bank, with pad64 (MIDI99)
  the full anchor line when ready. Dark/unprepared pads cannot trigger. Pad
  launches carry the exact bank revision; Liminal rejects retired banks. One-shot
  release semantics remain on the server. Whole line uses a distinct pad color.
- Delete118 sends all_notes_off, cancelling manual launches/latches. It does not
  reset the generative transport. Film/Space manual pads remain unavailable
  until Liminal advertises their actual adapters; their mixer can still work.
- Settings30: encoders1–4 edit each IPv4 octet, encoder5 edits port. Lower8 applies,
  lower7 cancels. Only literal RFC1918 or loopback IPv4 endpoints are accepted.
  Endpoint changes disconnect safely and persist locally; no shell/SSH is needed.
- In Settings, lower1 selects return to Stillwater; lower2 selects stock. Lower8
  confirms; lower7 cancels. This requires an installed supervisor and verified
  private recovery init backups. It closes the app's hardware before returning.

Top/button LEDs show selection/mode, pads show readiness and physical held notes.
These are controller state, not a claim of audible output. Unknown pressure IDs
and release after a server-side voice retirement are harmless. Liminal keeps
mix/modes across disconnect and Stop/Play; only app restart/reset restores its
defaults. The controller never restores stale local mix values on startup.
