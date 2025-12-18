import os
import shutil
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException
from core.processing import recognize_notes as recognize_notes_core, recognize_notes_structured
from models.schemas import RecognizeNotesResponse

router = APIRouter()

# Dossier de stockage des uploads (à créer si non existant)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def right_extension(file: UploadFile):
    if not file.filename.endswith((".wav", ".mp3", ".aac", ".m4a")):
        raise HTTPException(status_code=400, detail="Format de fichier invalide. Seuls les fichiers WAV, MP3, AAC et M4A sont acceptés.")


# @router.post("/upload/")
# async def upload_file(file: UploadFile = File(...)):
#     # Vérifier l'extension du fichier (ici, on accepte uniquement les .wav)
#     right_extension(file)

#     file_path = os.path.join(UPLOAD_DIR, file.filename)
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     # Appel à la fonction de traitement (séparation d'instruments, identification des notes, etc.)
#     results = process_audio_file(file_path)

#     return {"filename": file.filename, "partitions": results}


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

    # Utiliser la nouvelle fonction structurée
    result = recognize_notes_structured(file_path)

    return result


@router.post("/recognize-notes-detailed/")
async def recognize_notes_detailed_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pour obtenir des détails de bas niveau sur les fréquences détectées.
    Conserve l'ancien comportement pour le debug ou l'analyse approfondie.
    """
    right_extension(file)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    times_s, f0_hz, voiced_flag, voiced_probs, sr = recognize_notes_core(file_path)

    # Keep response compact by sampling every N frames for preview
    preview_stride = max(1, len(f0_hz) // 1000)
    idx = slice(0, None, preview_stride)

    # Convert NaN F0 to null for JSON
    f0_sample = [None if np.isnan(val) else float(val) for val in f0_hz[idx]]

    return {
        "sampling_rate": int(sr),
        "frames": int(len(f0_hz)),
        "times_s": [float(t) for t in times_s[idx]],
        "f0_hz": f0_sample,
        "voiced_flag": [bool(v) for v in voiced_flag[idx]],
        "voiced_probs": [float(p) for p in voiced_probs[idx]],
    }
