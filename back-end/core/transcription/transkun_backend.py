import librosa as lr
import moduleconf
import torch
from importlib.resources import files

from core.transcription import RawNote


class TranskunBackend:
    """Transkun V2 (ISMIR 2024) : transcription piano, checkpoint embarqué dans le paquet."""

    def __init__(self, device: str = "cpu"):
        pretrained = files("transkun") / "pretrained"
        conf_manager = moduleconf.parseFromFile(str(pretrained / "2.0.conf"))
        model_class = conf_manager["Model"].module.TransKun
        checkpoint = torch.load(str(pretrained / "2.0.pt"), map_location=device)

        self._device = device
        self._model = model_class(conf=conf_manager["Model"].config).to(device)
        state_key = "best_state_dict" if "best_state_dict" in checkpoint else "state_dict"
        self._model.load_state_dict(checkpoint[state_key], strict=False)
        self._model.eval()

    def transcribe(self, audio_path: str) -> list[RawNote]:
        audio, _ = lr.load(audio_path, sr=self._model.fs, mono=True)
        x = torch.from_numpy(audio).reshape(-1, 1).to(self._device)
        with torch.no_grad():
            notes = self._model.transcribe(x, discardSecondHalf=False)

        # pitch <= 0 : événements de pédale, ignorés pour la partition
        return [
            RawNote(int(n.pitch), float(n.start), float(n.end), float(n.velocity) / 127.0)
            for n in notes
            if n.pitch > 0
        ]
