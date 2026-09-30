from pydantic import BaseModel, ConfigDict, Field
from typing import List


class NoteSegment(BaseModel):
    """A detected note segment with timing and duration"""
    time: float = Field(..., description="Position en noires depuis le début de la partition (quantifiée)")
    note: str = Field(..., description="Nom de la note (ex: 'A4', 'C#3', 'Bb2')")
    duration: float = Field(..., description="Durée de la note en noires (quantifiée)")
    velocity: float = Field(..., description="Intensité normalisée (0-1)")


class RecognizeNotesResponse(BaseModel):
    """Response schema for recognize_notes endpoint"""
    bpm: int = Field(..., description="Tempo en battements par minute")
    offset: float = Field(..., description="Instant (en secondes) de la première note, qui correspond au temps 0 de la partition")
    notes: List[NoteSegment] = Field(..., description="Liste des segments de notes détectés avec leur durée")
    sample_rate: int = Field(..., description="Taux d'échantillonnage audio en Hz")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bpm": 120,
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
    )
