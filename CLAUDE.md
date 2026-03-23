# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music-to-partition: a full-stack app that converts piano audio files (.wav, .mp3, .aac, .m4a) into music sheet PDFs. React + Vite front-end, FastAPI back-end.

## Commands

### Front-end (run from `front-end/`)
```bash
npm run dev       # Start Vite dev server with HMR
npm run build     # Production build
npm run lint      # ESLint
npm run preview   # Preview production build
```

### Back-end (run from `back-end/`)
```bash
uv sync                                    # Install dependencies
uv run uvicorn api.main:app --reload       # Start FastAPI dev server (port 8000)
```

### External dependency
- **LilyPond** must be installed (used by music21 for PDF rendering). Expected at `/opt/homebrew/bin/lilypond` (macOS Homebrew).

## Architecture

### Data Flow
```
Audio upload → POST /api/recognize-notes/ → note extraction → POST /api/generate-sheet/ → PDF
```

The front-end makes two sequential API calls: first to extract notes from audio, then to generate a PDF sheet from those notes.

### Front-end (`front-end/src/`)
- **React 19 + Vite 7 + Tailwind CSS 4** (Tailwind via `@tailwindcss/vite` plugin, no separate config)
- `dashboard/Home.jsx` — main page, manages `uploadedFile` state
- `components/UploadButton.jsx` — drag-and-drop audio upload with format validation
- `components/GenerationSection.jsx` — orchestrates both API calls, holds generation state
- `components/PdfViewer.jsx` — displays generated PDF via iframe
- API base URL is hardcoded to `http://localhost:8000`

### Back-end (`back-end/`)
- **FastAPI** with CORS enabled for all origins
- `api/main.py` — app setup, CORS, route mounting at `/api`
- `api/routes.py` — two endpoints: `recognize-notes/` and `generate-sheet/`
- `core/processing.py` — audio analysis pipeline: librosa (beat tracking) → basic-pitch (pitch detection) → quantization to valid musical durations
- `core/sheet_generator.py` — builds music21 Score with treble (octave ≥ 4) and bass (octave < 4) parts, renders PDF via LilyPond
- `models/schemas.py` — Pydantic models: `NoteSegment` (time, note, duration, velocity) and `RecognizeNotesResponse` (bpm, offset, notes, sample_rate)

### Key processing details
- Notes below velocity 0.4 are filtered out
- Time is quantized to a 0.5s grid; durations snap to standard musical values (whole through sixty-fourth notes)
- Chords are detected by grouping notes at the same quantized time

## No Tests

There are currently no test files or test framework configured for either front-end or back-end.
