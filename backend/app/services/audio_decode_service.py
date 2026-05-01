import contextlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class PreparedAudio:
    path: str
    was_converted: bool = False
    source_error: Optional[str] = None


def _read_probe(path: str) -> None:
    import librosa

    y, _ = librosa.load(path, sr=16000, mono=True, duration=1.0)
    if y is None or len(y) == 0:
        raise ValueError("Audio file has no readable samples.")


def _ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        executable = shutil.which("ffmpeg")
        if executable:
            return executable
        raise RuntimeError(
            "No audio converter is available. Install imageio-ffmpeg or FFmpeg."
        )


def _convert_to_wav(input_path: str, target_sr: int = 22050) -> str:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    output_path = handle.name
    handle.close()

    command = [
        _ffmpeg_executable(),
        "-nostdin",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(target_sr),
        "-f",
        "wav",
        output_path,
    ]

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        Path(output_path).unlink(missing_ok=True)
        raise

    if completed.stderr:
        print(completed.stderr)

    return output_path


@contextlib.contextmanager
def prepare_audio_for_analysis(input_path: str) -> Iterator[PreparedAudio]:
    converted_path: Optional[str] = None

    try:
        try:
            _read_probe(input_path)
            prepared_audio = PreparedAudio(path=input_path, was_converted=False)
        except Exception as direct_read_error:
            converted_path = _convert_to_wav(input_path)
            _read_probe(converted_path)
            prepared_audio = PreparedAudio(
                path=converted_path,
                was_converted=True,
                source_error=str(direct_read_error),
            )

        yield prepared_audio
    finally:
        if converted_path:
            Path(converted_path).unlink(missing_ok=True)
