import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from core.processing import recognize_notes_structured
from core.sheet_generator import generate_piano_sheet
from models.schemas import RecognizeNotesResponse

router = APIRouter()

# Dossier de stockage des uploads (à créer si non existant)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def right_extension(file: UploadFile):
    if not file.filename.endswith((".wav", ".mp3", ".aac", ".m4a")):
        raise HTTPException(status_code=400, detail="Format de fichier invalide. Seuls les fichiers WAV, MP3, AAC et M4A sont acceptés.")


@router.post("/recognize-notes/", response_model=RecognizeNotesResponse)
async def recognize_notes_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pour reconnaître les notes d'un fichier audio avec leur durée.

    Cette fonction analyse un fichier audio et retourne :
    - Le tempo (BPM)
    - L'offset du premier beat
    - Une liste de segments de notes avec :
      * frame : position dans l'analyse
      * time : timestamp en secondes
      * note : nom de la note (ex: "A4", "C#3")
      * duration : durée de la note en secondes

    La durée permet de différencier une note blanche (longue) d'une note noire
    suivie d'un silence.
    """
    right_extension(file)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = recognize_notes_structured(file_path)

    return result


@router.post("/generate-sheet/")
async def generate_sheet_endpoint(data: RecognizeNotesResponse):
    """Route temporaire : génère une partition PDF à partir des notes détectées"""
    notes_as_dicts = [n.model_dump() for n in data.notes]
    output_path = generate_piano_sheet(notes_as_dicts, data.bpm)

    return FileResponse(
        output_path,
        media_type='application/pdf',
        filename='partition.pdf'
    )
