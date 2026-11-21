# Standalone Liminal specification

PJ's 2026-11-21 request supersedes the remote-controller target on this branch.
The entire Lo-Fi sound engine runs on Push 3; no running Mac Liminal instance,
TCP controller peer, AI image generation or model service is required.

Each of six mixer channels has Auto/Manual, mute, level, tone, echo, room and
pan. Play starts the local AJ Hall-backed arrangement; manual channels suppress
only their automatic notes and remain playable while the common timeline runs.
Drums, harmony, prepared film chops and instrument programmes change together
at a 16-bar/64-beat boundary. Held notes retain their original sample identity.
Manual chops launch immediately and reuse exactly the prepared PCM.

The authoritative source is pj4533/Liminal main at
67fde8da0c18bb8ace86d0a03a866f5670f141d6. The portable policy subset follows
LofiScore's motif onsets/contours, theme/variation/breakdown/return, answer
figures, sample calibration and LofiPreset's acoustic programmes. Source
16-beat phrases remain internal composition units. PJ's explicit override moves
piano/pluck/guitar/piano programme rotation to successive **64-beat takes**;
the instrument remains stable during each whole take, including Manual mode.

AJ Hall imports preserve all 100 verified eligible full takes privately, with
source SHA256 and provenance, without modifying the archive. Eligibility is
labelled45–120 BPM and64beats within2frames. Playback resamples whole takes to
69BPM and normalizes using min(2.6,.11/max(.025,RMS)). New automatic selections
use the closest tempo plus4BPM pool and avoid immediate repetition.

Approved API images change the interface background through a slow crossfade;
opaque controls and text stay readable. Keyless Cleveland CC0 images and a
provenance-checked curated Prelinger film excerpt are staged for offline use.
No full-screen reactive visualizer is added. Network failures retain the cache.

Preserve all Stillwater sessions/history/recordings and the existing controller,
stock and Stillwater recovery routes. Boot must start stopped. Never install a
host ARM engine on x86_64 Push or bypass changed SSH identity verification.

The original user wording is retained in the private task artifact
user-specification.md. This project specification is the durable implementation
contract; older controller documentation describes the superseded branch only.
