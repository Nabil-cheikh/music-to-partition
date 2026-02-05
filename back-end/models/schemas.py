from pydantic import BaseModel, Field
from typing import List


class NoteSegment(BaseModel):
    """A detected note segment with timing and duration"""
    time: float = Field(..., description="Timestamp en secondes (relatif au début du fichier)")
    note: str = Field(..., description="Nom de la note (ex: 'A4', 'C#3', 'Bb2')")
    duration: float = Field(..., description="Durée de la note en secondes")
    velocity: float = Field(..., description="Intensité du volume de la note")


class RecognizeNotesResponse(BaseModel):
    """Response schema for recognize_notes endpoint"""
    bpm: int = Field(..., description="Tempo en battements par minute")
    offset: float = Field(..., description="Décalage temporel du premier beat (en secondes)")
    notes: List[NoteSegment] = Field(..., description="Liste des segments de notes détectés avec leur durée")
    sample_rate: int = Field(..., description="Taux d'échantillonnage audio en Hz")

    class Config:
        json_schema_extra = {
            "example": {
                "bpm": 120.0,
                "offset": 0.23,
                "notes": [
                    {"time": 0.22, "note": "C5", "duration": 0.5, "velocity": 0.68},
                    {"time": 0.22, "note": "C4", "duration": 0.45, "velocity": 0.33},
                    {"time": 0.22, "note": "C3", "duration": 0.51, "velocity": 0.76},
                    {"time": 0.72, "note": "C5", "duration": 0.5, "velocity": 0.76}
                ],
                "sample_rate": 44100,
            }
        }
