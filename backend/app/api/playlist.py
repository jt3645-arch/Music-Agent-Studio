import traceback

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schemas import PlaylistRequest
from app.services.agent_service import build_real_song_playlist_plan
from app.services.playlist_service import generate_playlist

router = APIRouter(prefix="/playlist", tags=["playlist"])

@router.post("")
def playlist_endpoint(req: PlaylistRequest):
    try:
        plan = generate_playlist(
            goal=req.goal,
            total_minutes=req.total_minutes,
            preferred_genres=req.preferred_genres,
            custom_plan=req.custom_plan,
            top_k_per_stage=req.top_k_per_stage,
        )
        evidence = {
            "stage_plan": plan.get("stage_plan", []),
            "local_matches": plan.get("playlist", []),
        }
        real_song_plan = build_real_song_playlist_plan(
            goal=req.goal,
            stage_plan=plan.get("stage_plan", []),
            preferred_styles=req.preferred_genres or [],
            disliked_styles=[],
            evidence=evidence,
        )
        plan["playlist_plan"] = real_song_plan
        plan["recommended_songs"] = real_song_plan.get("recommended_songs", [])
        plan["total_estimated_minutes"] = sum(
            int(stage.get("minutes", 0) or 0)
            for stage in plan.get("stage_plan", [])
        )
        return plan
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Playlist planning failed."},
        )
