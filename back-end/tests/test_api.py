"""API smoke tests with the heavy steps mocked (fast, no model, no LilyPond)."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import api.routes as routes
from api.main import app

client = TestClient(app)

RESULT = {
    "bpm": 120,
    "offset": 0.5,
    "notes": [{"time": 0.0, "note": "C4", "duration": 1.0, "velocity": 0.8}],
    "sample_rate": 44100,
}


@pytest.fixture
def seen_paths(monkeypatch):
    paths = []

    def fake_recognize(path):
        assert os.path.exists(path)
        paths.append(path)
        return RESULT

    monkeypatch.setattr(routes, "recognize_notes_structured", fake_recognize)
    return paths


def test_recognize_notes_returns_schema_and_deletes_upload(seen_paths):
    response = client.post("/api/recognize-notes/", files={"file": ("../../evil.MP3", b"fake", "audio/mpeg")})
    assert response.status_code == 200
    assert response.json() == RESULT
    assert seen_paths[0].startswith(tempfile.gettempdir()) and seen_paths[0].endswith(".mp3")
    assert not os.path.exists(seen_paths[0])


def test_recognize_notes_rejects_unknown_extension(seen_paths):
    response = client.post("/api/recognize-notes/", files={"file": ("song.txt", b"x", "text/plain")})
    assert response.status_code == 400
    assert seen_paths == []


def test_generate_sheet_returns_pdf_and_deletes_it(monkeypatch):
    fd, pdf = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(b"%PDF-1.4 fake")
    monkeypatch.setattr(routes, "generate_piano_sheet", lambda notes, bpm: pdf)

    response = client.post("/api/generate-sheet/", json=RESULT)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert not os.path.exists(pdf)
