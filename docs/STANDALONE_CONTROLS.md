# Standalone controls

- Play85: toggle the prepared arrangement between playing and stopped. Stop Clips29:
  hush all voices/effect tails and return the take position to zero. Boot starts
  stopped. Manual pads can audition while stopped.
- Top102–107 select Drums, Bass, Lead, Mids, Chops, Film. Wheel70 moves one channel
  per nonzero packet. Selection alone changes no notes or modes.
- Lower20–25 mute/unmute corresponding channels. **Shift49 + lower** toggles that
  channel's Auto/Manual. Auto/Manual suppresses automatic notes and leaves the
  common take clock evolving; manually held onsets keep their original source.
- Mix112: encoders71–76 change six corresponding channel levels. Device110 or
  Note50: the full display shows eight selected-channel effects on Sound, Space
  or Motion. Lower7/8 (CC26/27) move previous/next; each channel remembers its
  page, initially Sound. Encoders71–78 edit that page. Chops/Film additionally
  have Cuts: encoders76–78 retain Start/Length/Pad. Volume79 changes master.
  See [channel effects](CHANNEL_FX.md) for all24parameters, ranges and DSP.
- Melodic Manual pads36–99: exact Stillwater default centered D Dorian grid,
  right+1scale degree, up+3. All three note channels span MIDI38–86 at octave0;
  the movable triangle plays D/F/A. Root pads use Silt65, natural notes123,
  accidentals66 and held exact-pitch duplicates37. Arrows62/63 move octave, bounded to a complete
  MIDI0–127 window. Velocity changes onset loudness; release addresses the held
  token even after channel/octave/programme changes. Pressure is not mapped.
- Drums Auto pads select catalog entry1–64; arrows toggle to entries65–100.
  Dark/unassigned pads do nothing. Repeat56 requests a different tempo-compatible
  take. Selection queues preparation for the next64-beat boundary; it does not
  cut the current full take. Drums Manual pads repeat four fixed PCM cuts across
  all64pads (pad index modulo4), with release. These are source slices, not
  promised kick/snare labels or complete-loop latches.
- Chops Manual: up to64 consecutive held cuts walk through the complete available
  phrase in source order, left to right then up the grid. Each cut appears once;
  only populated pads light and unused pads do nothing.
  Hold a pad to play its cut once to the end; releasing it stops that cut with
  the native256-frame (5.8ms) click-free release. It never loops while held.
  Film Manual: each pad triggers the current complete8second anchor line.
  They launch immediately, without forced sixteenth quantization. Pad release
  leaves the Film anchor sounding; Delete118 releases all manual voices.
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

Live archive audio (standalone-native live sourcing update):

- With Chops or Film selected, Repeat56 requests a fresh public-domain Prelinger newsreel
  source from Internet Archive. A serial background worker also requests material
  at each full64-beat take transition, including Manual, and every180seconds
  as a background retry. Network and decoding continue while the instrument plays.
  IA LOADING/DOWNLOADING/DECODING/READY or ERROR appears along the bottom;
  NEXT16 means a source is waiting for the next64-beat boundary.
- Select Chops (top5 / CC106), Shift+lower5 to Manual. Populated pads expose consecutive
  cuts covering the complete prepared window; each onset plays the current prepared film PCM immediately.
  Shift+pad selects a cut silently. On the Device/Note Cuts page (lower7/8), encoder6 changes Start,
  encoder7 Length, encoder8 selects among populated cuts. Start/length steps are50ms per tick;
  hold Shift for5ms. Editing is audible on the next pad trigger immediately.
  Edits also enter the next automatic bank; previously sounding voices retain
  their onset start/length. Edits persist while the source stays the same; each take transition requests
  fresh footage. Slow/failed requests retain the current source.
- Film pads still audition the prepared anchor (up to8seconds). Film view exposes
  the same chop editors; use Chops pads to audition those edits. Delete releases
  manual voices; Stop hushes everything. Source changes still happen at16bars,
  so press Play to advance a newly queued source when transport is stopped.

These are energy/silence suggestions and hands-on PCM start/length editing.
There is no transcription, semantic dialogue search, moving-video display or
claim that every suggested cut contains speech. Only explicitly public-domain
Prelinger metadata with a bounded audio/media derivative is eligible. Requests
can fail or take minutes; the active source continues playing. Three decoded
windows are cached on disk; the latest valid window is restored after reboot.
The original bundled film remains the immediate offline boot fallback.

Drums start dry (Echo0, Room0); their original take remains intact. Echo and
Room can still be added deliberately. Each chop has bounded foreground gain
(target .11 source RMS, peak ceiling .6, maximum16x gain), shared by Auto and
Manual. Film remains the quiet full source at .16 gain. Both use the same film
recording; chopping does not isolate speech from its original soundtrack.
Editing a manual cut recalculates its gain on the control thread for the new
range, with the same .6 peak ceiling.
