# Standalone controls

- Play85: start the prepared automatic arrangement immediately. Stop Clips29:
  hush all voices/effect tails and return the take position to zero. Boot starts
  stopped. Manual pads can audition while stopped.
- Top102–107 select Drums, Bass, Lead, Mids, Chops, Film. Wheel70 moves one channel
  per nonzero packet. Selection alone changes no notes or modes.
- Lower20–25 mute/unmute corresponding channels. **Shift49 + lower** toggles that
  channel's Auto/Manual. Auto/Manual suppresses automatic notes and leaves the
  common take clock evolving; manually held onsets keep their original source.
- Mix112: encoders71–76 change six corresponding channel levels. Device110 or
  Note50: encoders71–75 change selected Level, Tone, Echo, Room and Pan.
  Encoders76–78 have no action in Device view. Volume79 always changes master.
- Melodic Manual pads36–99: right+1scale degree, up+3. Bass begins at MIDI36+
  tonic, Lead/Mids at MIDI48+tonic. Arrows62/63 move octave, bounded to a complete
  MIDI0–127 window. Velocity changes onset loudness; release addresses the held
  token even after channel/octave/programme changes. Pressure is not mapped.
- Drums Auto pads select catalog entry1–64; arrows toggle to entries65–100.
  Dark/unassigned pads do nothing. Repeat56 requests a different tempo-compatible
  take. Selection queues preparation for the next64-beat boundary; it does not
  cut the current full take. Drums Manual pads repeat four fixed PCM cuts across
  all64pads (pad index modulo4), with release. These are source slices, not
  promised kick/snare labels or complete-loop latches.
- Chops Manual: eight exact prepared one-shots repeat across all64pads (modulo8).
  Film Manual: each pad triggers the current complete8second anchor line.
  They launch immediately, without forced sixteenth quantization. Pad release
  leaves these one-shots sounding; Delete118 releases all manual voices.
- Help81 opens controls/collection credit; press again to close. The asset JSON
  manifests retain full individual work, film, source URL and license credits.
- Settings30 opens recovery. Lower1 selects Stillwater,2 Stock,3 old Controller;
  lower8 confirms or lower7 cancels. Confirmation stops the native app before
  the preserved original dispatcher starts the deliberate selection. Existing
  sessions and recordings are never deleted or migrated.

All six sound channels remain playable; instrument, drum and chop metadata change
coherently at16-bar boundaries. NEXT READY means a native bank was accepted;
PREPARING/REPEATING CURRENT disclose unprepared work. Display frame counters
measure transfers; they do not claim visible hardware hues or audible output.
