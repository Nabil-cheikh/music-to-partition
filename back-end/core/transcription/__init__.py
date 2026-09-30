# Couche transcription : audio -> notes brutes en secondes (non quantifiées).
# Chaque backend expose transcribe(audio_path) -> list[RawNote] ; voir docs/architecture.md.
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

DEFAULT_BACKEND = "transkun"


@dataclass(frozen=True)
class RawNote:
    pitch: int        # numéro MIDI
    onset: float      # secondes
    offset: float     # secondes
    velocity: float   # 0-1


class TranscriptionBackend(Protocol):
    def transcribe(self, audio_path: str) -> list[RawNote]: ...


@lru_cache(maxsize=None)
def get_backend(name: str | None = None) -> TranscriptionBackend:
    """Charge (une seule fois) le backend demandé, ou celui de TRANSCRIPTION_BACKEND."""
    name = name or os.environ.get("TRANSCRIPTION_BACKEND", DEFAULT_BACKEND)
    if name == "transkun":
        from core.transcription.transkun_backend import TranskunBackend
        return TranskunBackend()
    if name == "pop2piano":
        from core.transcription.pop2piano_backend import Pop2PianoBackend
        return Pop2PianoBackend()
    raise ValueError(f"Backend de transcription inconnu : {name!r}")
