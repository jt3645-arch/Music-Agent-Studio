import traceback

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schemas import RetrieveRequest
from app.services.llm_music_service import recommend_real_songs
from app.services.retrieval_service import retrieve_from_text

router = APIRouter(prefix="/retrieve", tags=["retrieve"])

@router.post("")
def retrieve_endpoint(req: RetrieveRequest):
    try:
        discovery = retrieve_from_text(req.query, req.top_k)
        parsed_targets = discovery.get("parsed_targets") or {}
        preferred_genres = parsed_targets.get("preferred_genres") or []
        evidence = {
            "parsed_targets": parsed_targets,
            "local_matches": discovery.get("results", []),
        }
        recommended_songs = recommend_real_songs(
            query=req.query,
            count=max(1, min(int(req.top_k or 6), 8)),
            preferred_styles=preferred_genres,
            evidence=evidence,
        )
        discovery["recommended_songs"] = recommended_songs
        discovery["listening_interpretation"] = (
            "These songs are selected for the mood, pace, tone, and style in your request."
        )
        return discovery
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Music discovery failed."},
        )
