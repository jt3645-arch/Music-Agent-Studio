from typing import Any, Dict, List, Optional

from app.services.retrieval_service import retrieve_from_text


def auto_plan(goal: str, total_minutes: int) -> List[Dict[str, Any]]:
    total_minutes = max(int(total_minutes), 1)
    goal_lower = goal.lower()

    if "workout" in goal_lower or "gym" in goal_lower or "fitness" in goal_lower:
        warmup = max(1, round(total_minutes * 0.25))
        intense = max(1, round(total_minutes * 0.55))
        cooldown = max(1, total_minutes - warmup - intense)
        if warmup + intense + cooldown > total_minutes:
            intense = max(1, total_minutes - warmup - cooldown)
        return [
            {
                "stage": "warmup",
                "minutes": warmup,
                "tempo_hint": "medium",
                "energy_hint": "medium",
            },
            {
                "stage": "intense",
                "minutes": intense,
                "tempo_hint": "fast",
                "energy_hint": "high",
            },
            {
                "stage": "cooldown",
                "minutes": cooldown,
                "tempo_hint": "slow",
                "energy_hint": "low",
            },
        ]

    if "study" in goal_lower or "focus" in goal_lower:
        settle = max(1, round(total_minutes * 0.25))
        deep_focus = max(1, total_minutes - settle)
        return [
            {
                "stage": "settle_in",
                "minutes": settle,
                "tempo_hint": "slow",
                "energy_hint": "low",
            },
            {
                "stage": "deep_focus",
                "minutes": deep_focus,
                "tempo_hint": "medium",
                "energy_hint": "low-medium",
            },
        ]

    return [
        {
            "stage": "main",
            "minutes": total_minutes,
            "tempo_hint": "medium",
            "energy_hint": "medium",
        }
    ]


def _stage_query(
    goal: str,
    stage: Dict[str, Any],
    preferred_genres: Optional[List[str]],
) -> str:
    parts = [
        goal,
        str(stage.get("stage", "")),
        str(stage.get("tempo_hint", "")),
        str(stage.get("energy_hint", "")),
    ]
    if preferred_genres:
        parts.extend(preferred_genres)
    return " ".join(part for part in parts if part).strip()


def generate_playlist(
    goal: str,
    total_minutes: int,
    preferred_genres=None,
    custom_plan=None,
    top_k_per_stage: int = 5,
):
    stage_plan = custom_plan if custom_plan else auto_plan(goal, total_minutes)
    playlist = []
    used = set()

    for stage in stage_plan:
        stage_name = stage["stage"]
        stage_minutes = stage["minutes"]
        query = _stage_query(goal, stage, preferred_genres)
        retrieval = retrieve_from_text(query, max(top_k_per_stage * 3, top_k_per_stage))

        selected = []
        for row in retrieval["results"]:
            clip_id = row.get("clip_id", "")
            if clip_id in used:
                continue

            used.add(clip_id)
            selected.append(
                {
                    "stage": stage_name,
                    "clip_id": clip_id,
                    "genre": row.get("genre", ""),
                    "audio_path": row.get("audio_path", ""),
                    "tempo_bpm": row.get("tempo_bpm"),
                    "rms_mean": row.get("rms_mean"),
                    "centroid_mean": row.get("centroid_mean"),
                    "final_score": row.get("final_score"),
                    "minutes_allocated": stage_minutes,
                }
            )

            if len(selected) >= top_k_per_stage:
                break

        playlist.extend(selected)

    return {
        "status": "ok",
        "stage_plan": stage_plan,
        "playlist": playlist,
        "explanation": (
            "Built each playlist stage by converting the stage goal into retrieval "
            "targets and ranking clips with the same feature-distance scorer used by /retrieve."
        ),
    }
