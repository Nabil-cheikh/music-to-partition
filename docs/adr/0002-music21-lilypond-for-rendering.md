# ADR-0002: music21 + LilyPond for score building and PDF rendering

- **Status**: accepted
- **Date**: written 2026-09-27, retroactively
- **Deciders**: project owner

## Context
Detected notes must become a readable two-staff piano score in PDF.

## Decision
Build a `music21.stream.Score` (treble and bass parts) in `core/sheet_generator.py` and render it with `score.write('lily.pdf', ...)`, which calls the LilyPond binary.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| music21 → MusicXML → MuseScore CLI | MusicXML is editable by users | MuseScore is heavy, headless rendering needs a display on Linux |
| music21 → MusicXML → Verovio (pip) | pure pip, SVG/PDF, no system binary | would require rewriting the rendering step |
| Custom LilyPond text generation | full control | reimplements what music21 already does |

## Consequences
- LilyPond is a required system dependency on every platform. It is resolved via `LILYPOND_PATH`, then `PATH`.
- music21 invokes LilyPond through `os.system` with unquoted paths and leaves the `.ly` source in the temp dir.
- Score structure (measures, rests, ties) comes from `makeMeasures()` / `makeRests()`. Notation tests should assert on that music21 structure, not on the PDF.
- Exporting MusicXML as well (`score.write('musicxml')`) is cheap and would let users fix scores in MuseScore. That is worth considering as a feature.
