# Standalone channel effects

Device110 / Note50 uses the whole960x160 display for the selected channel.
Eight120pixel columns align with encoders71–78. Top102–107 / wheel70 select
Drums, Bass, Lead, Mids, Chops, Film; lower7/8 (CC26/27) move to the previous/next
FX page. Each channel remembers its page; the initial page is Sound, including
Chops and Film. Mix112 retains six level strips. Selection/page changes send no
audio commands. Pads remain playable on every page and in overlays; releases
are routed before all view logic. Settings takes priority over page buttons:
lower7 cancels, lower8 confirms its deliberate recovery target.

| Page | Encoders1–8 |
|---|---|
| Sound | Level, Low Cut, High Cut, Drive, character, Compress/Glue, Width, Pan |
| Space | Echo Mix, Division, Feedback, Echo Tone, Room Mix, Decay, Damping, Predelay |
| Motion | Chorus, Rate, Depth, Wow, Flutter, Tremolo, Trem Div, Crush |
| Cuts (Chops/Film) | first5 explanatory/inert;6 Start,7 Length,8 Pad |

Cuts keeps50ms/tick and Shift5ms/tick editing. Shift+pad selects silently;
Manual Chops holds its unique chronological cut until release/end once, Film
anchors remain one-shots. Unused pads stay inert/unlit. Arrows keep octave/drum
catalog navigation. Lower1–6 mute, Shift+lower Auto/Manual; Play, Stop, Repeat,
Delete, Volume, source refresh and64beat publication retain their behavior.

`channel_fx.py` is the parameter contract: IDs, bounds, defaults, units, choices,
steps, channel variants and pages. `scripts/generate-fx.py` produces the checked-in
`fx_specs.h` native admission table. ABI1 layout is unchanged; command16 uses
`a=channel,b=parameter,event.gain=value`. Python rejects nonfinite values/invalid
addresses and clamps finite values; native independently rejects/clamps those
same fields. Legacy commands11–14 still route tone/echo/room/pan for existing
qualifiers; legacy tone retains its original normalized0–1 range. Production
encoders use command16 only. The native constructor remains dry for low-level
ABI callers; the app explicitly installs the per-channel defaults.

All Auto and Manual voices sum into their channel bus before these processors:

- Original tone one-pole (`.025+.6*.55=.355`) preserves the dry source voicing.
  Low Cut subtracts a one-pole lowpass, off then20–1200Hz (Bass off then20–160Hz).
  High Cut is a separate one-pole800–18kHz lowpass;18k bypasses it, transitioning
  over the upper1kHz. These are gentle filters, without resonance claims.
- Drive0–18dB uses compensated rational soft saturation. Character is a genuine
  envelope transient shaper on Drums (±50%); Bass Body and Mids Warmth are low
  shelves at180/500Hz, Lead Presence/Chops Bite/Film Clarity are high shelves at
 3k/2.4k/1.8kHz (±6dB). These are frequency variants of the same shelf topology,
  not claimed to be different algorithms. Glue/Compress is a stereo-linked
  envelope compressor, amount0–100%, ratio1–6:1, threshold.16→.04, no auto makeup.
- Width scales stereo side0–150%; Bass is bounded0–100% and removes side below
  a gentle160Hz crossover, retaining the mono low band. Pan retains the original
  linear one-side attenuation. Level/master defaults stay65%/45% and keep their
  original smoothing and master soft limiter.
- Echo is an independent stereo feedback delay, mix0–40%, feedback0–65%,
  tone800–12kHz. Divisions are1/16,1/8,dotted1/8,1/4,dotted1/4,1/2 from the current
 64beat bank duration; right time is1.125x left. Times clamp below the allocated
 3second buffer limit. Division changes crossfade between old/new taps over30ms;
  rapid changes finish that transition before admitting the latest requested time.
- Room is a separate send: four parallel damped feedback combs, then two
  allpasses per stereo side, mix0–35%, decay.2–4s (feedback-derived nominal RT60),
  damping1.5–12kHz, predelay0–60ms. It does not read or feed the echo buffer.
- Chorus uses a stereo phase-offset triangle LFO with an interpolated10ms delay,
  mix0–35%, rate.05–2Hz, depth0–6ms (peak-to-peak excursion). Wow is a.33Hz
  triangle delay modulation up to±60samples; Flutter6.1Hz up to±4samples. They
  share a separate interpolated tape delay with a128sample base when active.
  Modulation does not alter source read speed, gate or onset ownership.
  Tremolo is tempo-division amplitude modulation up to80%, phase-continuous
  across division changes. Crush blends quantization16→6bits and sample hold
 1→12frames. No ring-mod replacement was made.

All new destructive/shaping/motion amounts start zero; Width1, Pan0, HP off,
LP18k bypass. Drums stay dry. Other channels retain12%echo/10%room amounts;
Room now has its own diffusion and Echo is tempo-synced, so their late/default
sound intentionally differs from the old duplicate fixed delay. Bass additionally
monos its low side. Dry source gains, programmes and normalization are preserved.

Fixed buffers allocate at engine creation (roughly7MiB for six FX paths).
No allocation, decoding, files or network run in rendering. Continuous controls
smooth with a20ms time constant; filter/gain/feedback coefficients update every
32samples. Division selectors are discrete. Disabled wet processors stop writing
and clear their history once their smoothed mix falls below1e-5; re-enabling cannot
resurrect a stale tail. Muting attenuates the channel after effects and keeps its
musical state evolving. Stop clears every delay/filter/envelope/LFO/hold state
immediately and again at the existing bounded30ms hush, so released voices cannot
leave new tails behind. Play/new Manual onset retains existing early-restart
behavior. PCM-bank retirement, voice admission and onset tokens are unchanged.

Build both engines and run tests/rehearsal as described in STANDALONE_VALIDATION.
`scripts/benchmark-fx.py` measures host block distributions under64voices/all FX
and rapid edits. `scripts/rehearse-fx.py` exports every page at min/max values,
overlays, six short private real-source comparisons and PCM measurements, with
an optional previous engine baseline. Neither tool opens hardware/network.
These measurements do not substitute for device timing or human listening.
