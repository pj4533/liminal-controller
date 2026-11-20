# Contributor guide

Read README and docs/ARCHITECTURE.md, CONTROLS.md, INSTALL.md and VALIDATION.md
before editing. Runtime: Python3.10 stdlib only, one MIDI reader/display owner,
no audio production, no listener on Push. Pillow is offline asset tooling only.
Server snapshots are authoritative. Never invent ready controls, sound identity,
mode completion or transport success. Keep held onset identity independent of
selection; overflow disconnects rather than losing release. Do not replay a
previous session's commands. Preserve canonical complete scale-window bounds.

Run `python3 -m unittest discover -s tests -v` and `python3 scripts/demo.py`.
Verify Python3.10 compatibility, inspect native960x160 renders after UI changes,
run scripts/pack.py and inspect its whitelist. No private addresses, keys, samples,
footage, vendor init scripts, recordings, settings or operational logs in git.
Retain original art prompt and both upstream MIT notices. Do not touch hardware,
install a boot selector, start music or enable a Liminal capability without
explicit authorization. Preserve other contributors' changes.
