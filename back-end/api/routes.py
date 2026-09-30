import os
import shutil
import tempfile
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from core.processing import recognize_notes_structured
from core.sheet_generator import generate_piano_sheet
from models.schemas import RecognizeNotesResponse

router = APIRouter()

ALLOWED_EXTENSIONS = (".wav", ".mp3", ".aac", ".m4a")


def right_extension(file: UploadFile) -> str:
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format de fichier invalide. Seuls les fichiers WAV, MP3, AAC et M4A sont acceptés.")
    return extension


@router.post("/recognize-notes/", response_model=RecognizeNotesResponse)
def recognize_notes_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pour reconnaître les notes d'un fichier audio avec leur durée.

    Cette fonction analyse un fichier audio et retourne :
    - Le tempo (BPM)
    - L'offset du premier beat
    - Une liste de segments de notes avec :
      * time : position en noires (quantifiée)
      * note : nom de la note (ex: "A4", "C#3")
      * duration : durée de la note en noires
      * velocity : intensité normalisée (0-1)

    La durée permet de différencier une note blanche (longue) d'une note noire
    suivie d'un silence.
    """
    extension = right_extension(file)

    # Fichier temporaire : nom non contrôlé par le client, supprimé après analyse
    fd, file_path = tempfile.mkstemp(suffix=extension)
    try:
        with os.fdopen(fd, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return recognize_notes_structured(file_path)
    finally:
        os.remove(file_path)


@router.post("/generate-sheet/")
def generate_sheet_endpoint(data: RecognizeNotesResponse):
    """Génère une partition PDF à partir des notes détectées"""
    notes_as_dicts = [n.model_dump() for n in data.notes]
    output_path = generate_piano_sheet(notes_as_dicts, data.bpm)

    return FileResponse(
        output_path,
        media_type='application/pdf',
        filename='partition.pdf',
        background=BackgroundTask(os.remove, output_path),
    )
