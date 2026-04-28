from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_client import get_provider_status, set_runtime_provider


router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderSelection(BaseModel):
    provider: str


@router.get("/llm")
def get_llm_settings():
    return get_provider_status()


@router.post("/llm")
def update_llm_settings(selection: ProviderSelection):
    set_runtime_provider(selection.provider)
    return get_provider_status()
