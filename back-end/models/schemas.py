from pydantic import BaseModel, Field
from typing import List


class NoteSegment(BaseModel):
    """A detected note segment with timing and duration"""
    frame: int = Field(..., description="Index de la frame d'analyse où commence la note")
    time: float = Field(..., description="Timestamp en secondes (relatif au début du fichier)")
    note: str = Field(..., description="Nom de la note (ex: 'A4', 'C#3', 'Bb2')")
    duration: float = Field(..., description="Durée de la note en secondes")


class RecognizeNotesResponse(BaseModel):
    """Response schema for recognize_notes endpoint"""
    bpm: float = Field(..., description="Tempo en battements par minute")
    offset: float = Field(..., description="Décalage temporel du premier beat (en secondes)")
    notes: List[NoteSegment] = Field(..., description="Liste des segments de notes détectés avec leur durée")
    frame_duration: float = Field(..., description="Durée d'une frame d'analyse en secondes")
    sample_rate: int = Field(..., description="Taux d'échantillonnage audio en Hz")
    hop_length: int = Field(..., description="Nombre d'échantillons entre chaque frame d'analyse")

    class Config:
        json_schema_extra = {
            "example": {
                "bpm": 120.0,
                "offset": 0.23,
                "notes": [
                    {"frame": 0, "time": 0.23, "note": "A4", "duration": 0.5},
                    {"frame": 45, "time": 0.75, "note": "F3", "duration": 0.25},
                    {"frame": 68, "time": 1.02, "note": "G#4", "duration": 1.0},
                    {"frame": 156, "time": 2.1, "note": "B3", "duration": 0.5}
                ],
                "frame_duration": 0.0116,
                "sample_rate": 44100,
                "hop_length": 512
            }
        }
