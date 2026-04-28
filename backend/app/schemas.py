from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class AnalyzeResponse(BaseModel):
    status: str
    predicted_genre: Optional[str] = None
    top3: Optional[List[Any]] = None
    features: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrieveResponse(BaseModel):
    status: str
    parsed_targets: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None


class PlaylistRequest(BaseModel):
    goal: str
    total_minutes: int
    top_k_per_stage: int = 5
    preferred_genres: Optional[List[str]] = None
    custom_plan: Optional[List[Dict[str, Any]]] = None


class PlaylistResponse(BaseModel):
    status: str
    stage_plan: List[Dict[str, Any]]
    playlist: List[Dict[str, Any]]
    explanation: str
