import librosa as lr
from transformers import Pop2PianoForConditionalGeneration, Pop2PianoProcessor

from core.transcription import RawNote


class Pop2PianoBackend:
    """Pop2Piano : génère une reprise piano (arrangement), pas une transcription fidèle."""

    def __init__(self):
        self._model = Pop2PianoForConditionalGeneration.from_pretrained("sweetcocoa/pop2piano")
        self._processor = Pop2PianoProcessor.from_pretrained("sweetcocoa/pop2piano")

    def transcribe(self, audio_path: str) -> list[RawNote]:
        audio, _ = lr.load(audio_path, sr=44100)
        inputs = self._processor(audio=audio, sampling_rate=44100, return_tensors="pt")
        output = self._model.generate(input_features=inputs["input_features"], composer="composer1")
        midi = self._processor.batch_decode(token_ids=output, feature_extractor_output=inputs)["pretty_midi_objects"][0]
        return [
            RawNote(n.pitch, n.start, n.end, n.velocity / 127.0)
            for instr in midi.instruments
            for n in instr.notes
        ]
