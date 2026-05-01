import traceback

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
from app.services.ast_service import analyze_audio
from app.services.llm_music_service import recommend_real_songs

router = APIRouter(prefix="/analyze", tags=["analyze"])


def _describe_tempo(value):
    if not isinstance(value, (int, float)):
        return "natural tempo"
    if value < 85:
        return "slow tempo"
    if value < 120:
        return "moderate tempo"
    return "fast tempo"


def _describe_energy(value):
    if not isinstance(value, (int, float)):
        return "balanced energy"
    if value >= 0.12:
        return "high energy"
    if value >= 0.06:
        return "medium energy"
    return "low energy"


def _describe_brightness(value):
    if not isinstance(value, (int, float)):
        return "balanced tone"
    if value >= 2800:
        return "bright tone"
    if value >= 1600:
        return "warm tone"
    return "soft tone"


def _describe_texture(value):
    if not isinstance(value, (int, float)):
        return "smooth texture"
    if value >= 0.12:
        return "crisp texture"
    if value >= 0.06:
        return "detailed texture"
    return "smooth texture"


def _listening_interpretation(analysis):
    features = analysis.get("features") or {}
    genre = analysis.get("predicted_genre") or "this style"
    return (
        f"This song is closest to {genre}, with "
        f"{_describe_tempo(features.get('tempo_bpm'))}, "
        f"{_describe_energy(features.get('rms_mean'))}, "
        f"{_describe_brightness(features.get('centroid_mean'))}, and "
        f"{_describe_texture(features.get('zcr_mean'))}."
    )


def _similar_song_query(analysis):
    features = analysis.get("features") or {}
    genre = analysis.get("predicted_genre") or "music"
    return " ".join(
        [
            f"real songs similar to {genre}",
            _describe_tempo(features.get("tempo_bpm")),
            _describe_energy(features.get("rms_mean")),
            _describe_brightness(features.get("centroid_mean")),
            _describe_texture(features.get("zcr_mean")),
        ]
    )


@router.post("")
async def analyze_endpoint(file: UploadFile = File(...)):
    tmp_path = None

    try:
        suffix = Path(file.filename or "").suffix or ".audio"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        analysis = analyze_audio(tmp_path)
        genre = analysis.get("predicted_genre")
        evidence = {
            "predicted_genre": genre,
            "top3": analysis.get("top3"),
            "sound_profile": analysis.get("features"),
        }
        similar_songs = recommend_real_songs(
            query=_similar_song_query(analysis),
            count=6,
            preferred_styles=[genre] if genre else None,
            evidence=evidence,
        )
        analysis["listening_interpretation"] = _listening_interpretation(analysis)
        analysis["similar_songs"] = similar_songs
        analysis["recommended_songs"] = similar_songs
        return analysis
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Audio analysis failed."},
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

