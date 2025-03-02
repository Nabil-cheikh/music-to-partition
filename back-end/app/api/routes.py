import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.core.processing import process_audio_file

router = APIRouter()

# Dossier de stockage des uploads (à créer si non existant)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    # Vérifier l'extension du fichier (ici, on accepte uniquement les .wav)
    if not file.filename.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Format de fichier invalide. Seuls les fichiers WAV sont acceptés.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Appel à la fonction de traitement (séparation d'instruments, identification des notes, etc.)
    results = process_audio_file(file_path)

    return {"filename": file.filename, "results": results}
