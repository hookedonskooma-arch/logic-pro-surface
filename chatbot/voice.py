"""Local, offline voice adapters.

Nothing here reaches the network. Each adapter probes for a binary or module at
construction time and reports UNAVAILABLE rather than raising, so the text path
keeps working on a machine with no speech stack installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass


@dataclass(frozen=True)
class Probe:
    available: bool
    name: str
    detail: str


class Recognizer:
    """Speech to text. Subclasses implement `transcribe`."""

    name = "none"

    def probe(self) -> Probe:
        return Probe(False, self.name, "no recognizer configured")

    def transcribe(self, wav_path: str) -> str:
        raise NotImplementedError


class WhisperCppRecognizer(Recognizer):
    """whisper.cpp via its `whisper-cli` (or legacy `main`) binary."""

    name = "whisper.cpp"

    def __init__(self, binary: str | None = None, model: str | None = None):
        self.binary = binary or os.environ.get("WHISPER_CPP_BIN") or shutil.which(
            "whisper-cli"
        ) or shutil.which("whisper")
        self.model = model or os.environ.get("WHISPER_CPP_MODEL")

    def probe(self) -> Probe:
        if not self.binary:
            return Probe(False, self.name, "whisper-cli not on PATH; set WHISPER_CPP_BIN")
        if not self.model or not os.path.exists(self.model):
            return Probe(False, self.name, "set WHISPER_CPP_MODEL to a ggml model file")
        return Probe(True, self.name, f"{self.binary} + {os.path.basename(self.model)}")

    def transcribe(self, wav_path: str) -> str:
        out = subprocess.run(
            [self.binary, "-m", self.model, "-f", wav_path, "-nt", "-np", "-l", "en"],
            capture_output=True, text=True, timeout=300,
        )
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip() or "whisper.cpp failed")
        return " ".join(out.stdout.split())


class FasterWhisperRecognizer(Recognizer):
    """faster-whisper, in-process, CPU by default."""

    name = "faster-whisper"

    def __init__(self, model_size: str | None = None):
        self.model_size = model_size or os.environ.get("FASTER_WHISPER_MODEL", "base.en")
        self._model = None

    def probe(self) -> Probe:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return Probe(False, self.name, "pip install faster-whisper")
        return Probe(True, self.name, f"model {self.model_size}")

    def transcribe(self, wav_path: str) -> str:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        segments, _ = self._model.transcribe(wav_path, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()


class Speaker:
    """Text to speech."""

    name = "none"

    def probe(self) -> Probe:
        return Probe(False, self.name, "no speaker configured")

    def say(self, text: str) -> None:
        raise NotImplementedError


class MacSaySpeaker(Speaker):
    """macOS `say`. Present on every machine that can run Logic."""

    name = "macOS say"

    def __init__(self, voice: str | None = None):
        self.binary = shutil.which("say")
        self.voice = voice or os.environ.get("SAY_VOICE")

    def probe(self) -> Probe:
        if not self.binary:
            return Probe(False, self.name, "`say` is macOS-only")
        return Probe(True, self.name, self.voice or "system voice")

    def say(self, text: str) -> None:
        cmd = [self.binary]
        if self.voice:
            cmd += ["-v", self.voice]
        subprocess.run(cmd + [text], check=False, timeout=120)


class PiperSpeaker(Speaker):
    """Piper, offline neural TTS, piped straight to an audio player."""

    name = "piper"

    def __init__(self, binary: str | None = None, model: str | None = None):
        self.binary = binary or os.environ.get("PIPER_BIN") or shutil.which("piper")
        self.model = model or os.environ.get("PIPER_MODEL")
        self.player = shutil.which("afplay") or shutil.which("aplay") or shutil.which("play")

    def probe(self) -> Probe:
        if not self.binary:
            return Probe(False, self.name, "piper not on PATH; set PIPER_BIN")
        if not self.model or not os.path.exists(self.model):
            return Probe(False, self.name, "set PIPER_MODEL to a .onnx voice")
        if not self.player:
            return Probe(False, self.name, "no afplay/aplay/play to render with")
        return Probe(True, self.name, os.path.basename(self.model))

    def say(self, text: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            path = handle.name
        try:
            subprocess.run(
                [self.binary, "-m", self.model, "-f", path],
                input=text, text=True, capture_output=True, check=True, timeout=120,
            )
            subprocess.run([self.player, path], check=False, timeout=120)
        finally:
            os.unlink(path)


def first_available_recognizer() -> tuple[Recognizer | None, list[Probe]]:
    probes = []
    for candidate in (WhisperCppRecognizer(), FasterWhisperRecognizer()):
        probe = candidate.probe()
        probes.append(probe)
        if probe.available:
            return candidate, probes
    return None, probes


def first_available_speaker() -> tuple[Speaker | None, list[Probe]]:
    probes = []
    for candidate in (PiperSpeaker(), MacSaySpeaker()):
        probe = candidate.probe()
        probes.append(probe)
        if probe.available:
            return candidate, probes
    return None, probes


def record_wav(path: str, seconds: float = 6.0, rate: int = 16000) -> str:
    """Record mono 16 kHz from the default input, the rate whisper wants.

    Uses sounddevice if present, else `sox`/`rec`, else raises. Kept separate
    from the recognizers so a caller can hand in a wav from anywhere.
    """
    try:
        import sounddevice
        import numpy
    except ImportError:
        recorder = shutil.which("rec") or shutil.which("sox")
        if not recorder:
            raise RuntimeError(
                "no capture path: pip install sounddevice, or install sox"
            )
        subprocess.run(
            [recorder, "-q", "-d", "-r", str(rate), "-c", "1", "-b", "16", path,
             "trim", "0", str(seconds)],
            check=True, timeout=seconds + 30,
        )
        return path
    frames = sounddevice.rec(
        int(seconds * rate), samplerate=rate, channels=1, dtype="int16"
    )
    sounddevice.wait()
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(numpy.asarray(frames).tobytes())
    return path
