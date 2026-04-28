import traceback
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.agent_service import run_agent_turn, run_image_agent_turn


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


@router.post("")
def agent_endpoint(req: AgentRequest):
    try:
        return run_agent_turn(req.message, req.context)
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "The music agent could not complete this turn.",
            },
        )


@router.post("/image")
async def agent_image_endpoint(
    message: str = Form(""),
    context: str = Form("{}"),
    image: UploadFile = File(...),
):
    try:
        content_type = image.content_type or ""
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": "Please choose a JPG, PNG, or WebP image.",
                },
            )

        try:
            parsed_context = json.loads(context) if context else {}
        except json.JSONDecodeError:
            parsed_context = {}

        image_bytes = await image.read()
        return run_image_agent_turn(
            message=message or "Recommend BGM for this photo",
            image_bytes=image_bytes,
            content_type=content_type,
            context=parsed_context,
        )
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "The music agent could not read this image.",
            },
        )
