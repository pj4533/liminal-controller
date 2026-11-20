# Original artwork and material contacts

`assets/film-table-original.png` is original generated bitmap art, created with
the built-in `image_gen.imagegen` tool on2026-11-20. Generation output path:
`/codex-home/generated_images/01a1faec-65f4-7153-8212-7f6226995fd7/exec-1192ffd2-6a7a-45ac-aa29-91d08d6b1778.png`.
It was inspected, then copied into this repository. No Stillwater scene/image was
copied. The full original remains present. The MIT repository includes this
artwork; AI generation is disclosed rather than presented as a photograph of
real equipment or a physical Push acceptance capture.

Exact prompt:

> Use case: stylized-concept. Asset type: original full-screen cinematic material background for Liminal music controller 960x160 extreme panoramic display, later center-cropped from image. Primary request: a single tactile analog film editing table in a dark cinema, eight softly illuminated vertical translucent amber/teal glass film strips crossing a continuous horizontal aged-brass film transport rail, each strip has a physical sliding contact and tiny fixed witness marks, moody large-format film photograph, original imagery. Composition: all meaningful material in the central horizontal sixth of the image so a 6:1 panoramic center crop preserves eight evenly spaced glass strips and continuous rail. Upper and lower portions of central band dark quiet negative space for crisp live labels rendered separately. Rich charcoal, deep petrol, restrained amber practical light, subtle grain, precise material detail, no text, letters, numbers, logos, watermarks, card panels, UI, people. This is newly authored artwork, not a copy of any existing application.

`scripts/prepare-art.py` performs only the hardware-size crop `(278,215,1770,464)`,
resize to960×160 and deterministic BGR565 packing with1024pixel stride. Pillow
is offline tooling. `assets/film-table.png` is its exact RGB crop;
`assets/film-table.bin` is runtime packed data, not executable code.

The renderer retains Stillwater's full-scene architecture: source material spans
the complete display, fixed witnesses on each strip establish0/25/50/75/100,
and a brass/teal contact's vertical position follows the canonical remote value.
Exact percentage typography is drawn last, never baked into generated artwork.
The continuous rail connects all eight strips, without generic boxed cards.
`docs/media/simulator-device.png` is a synthetic, stopped production-renderer
capture at960×160; it is not physical hardware or native audio evidence.
