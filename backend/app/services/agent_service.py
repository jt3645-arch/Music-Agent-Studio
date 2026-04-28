import re
from typing import Any, Dict, List, Optional

from app.services.llm_music_service import recommend_real_songs
from app.services.playlist_service import auto_plan, generate_playlist
from app.services.retrieval_service import retrieve_from_text
from app.services.vision_service import analyze_visual_mood


GENRE_TERMS = [
    "rock",
    "hip-hop",
    "hip hop",
    "hiphop",
    "jazz",
    "classical",
    "pop",
    "metal",
    "reggae",
    "disco",
    "blues",
    "country",
    "ambient",
    "electronic",
    "folk",
]


def _normalize_style(style: str) -> str:
    normalized = style.strip().lower()
    if normalized == "hip hop" or normalized == "hiphop":
        return "hip-hop"
    return normalized


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        normalized = _normalize_style(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _extract_minutes(message: str) -> Optional[int]:
    match = re.search(r"(\d{1,3})\s*(?:-| )?\s*minute", message.lower())
    if match:
        return max(1, int(match.group(1)))
    return None


def _extract_styles_after(prefix: str, message: str) -> List[str]:
    lower = message.lower()
    styles = []
    for term in GENRE_TERMS:
        if f"{prefix} {term}" in lower:
            styles.append(term)
    return _unique(styles)


def _extract_mentioned_styles(message: str) -> List[str]:
    lower = message.lower()
    styles = []
    for term in GENRE_TERMS:
        if term in lower:
            styles.append(term)
    return _unique(styles)


def _detect_intent(message: str, context: Dict[str, Any]) -> str:
    lower = message.lower()
    refinement_terms = [
        "more ",
        "less ",
        "make it",
        "shorten",
        "longer",
        "faster",
        "slower",
        "cooldown",
        "warmup",
    ]
    playlist_terms = [
        "playlist",
        "mix",
        "minutes",
        "minute",
        "workout",
        "study",
        "commute",
        "sleep",
        "dinner",
        "warmup",
        "cooldown",
    ]
    discovery_terms = [
        "similar",
        "mood",
        "genre",
        "relaxing",
        "energetic",
        "jazz",
        "rock",
        "hip-hop",
        "hip hop",
        "find",
        "song",
        "songs",
        "music",
    ]

    if any(term in lower for term in refinement_terms) and context.get("last_action"):
        return "refine"

    if "uploaded" in lower or "reference track" in lower or "reference song" in lower:
        return "reference_audio"

    if any(term in lower for term in playlist_terms):
        return "playlist"

    if any(term in lower for term in discovery_terms):
        return "music_discovery"

    return context.get("last_action") or "music_discovery"


def _apply_refinements(message: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
    lower = message.lower()
    preferred = list(preferences.get("preferred_styles") or [])
    disliked = list(preferences.get("disliked_styles") or [])

    preferred.extend(_extract_styles_after("more", lower))
    disliked.extend(_extract_styles_after("less", lower))

    mentioned = _extract_mentioned_styles(lower)
    if not ("less" in lower or "more" in lower):
        preferred.extend(mentioned)

    if (
        "faster" in lower
        or "more energetic" in lower
        or "higher energy" in lower
        or "more upbeat" in lower
        or "upbeat" in lower
    ):
        preferences["energy_direction"] = "more energetic"
    elif "slower" in lower or "calmer" in lower or "less energetic" in lower:
        preferences["energy_direction"] = "calmer"

    minutes = _extract_minutes(lower)
    if minutes:
        preferences["duration"] = minutes

    preferences["preferred_styles"] = _unique(preferred)
    preferences["disliked_styles"] = _unique(disliked)
    return preferences


def _stage_time_ranges(stages: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    cursor = 0
    ranges = []
    for stage in stages:
        start = cursor
        cursor += int(stage.get("minutes", 0) or 0)
        ranges.append({"start": start, "end": cursor})
    return ranges


def _shorten_cooldown_if_requested(message: str, stage_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lower = message.lower()
    if "shorten" not in lower or "cooldown" not in lower:
        return stage_plan

    adjusted = [dict(stage) for stage in stage_plan]
    for stage in adjusted:
        if "cooldown" in str(stage.get("stage", "")).lower():
            original = max(1, int(stage.get("minutes", 1)))
            stage["minutes"] = max(1, round(original * 0.6))
            break
    return adjusted


def _playlist_plan_from_stage_plan(
    goal: str,
    stage_plan: List[Dict[str, Any]],
    preferred_styles: List[str],
    disliked_styles: List[str],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    ranges = _stage_time_ranges(stage_plan)
    stages = []
    all_songs = []
    used_song_keys = set()

    for index, stage in enumerate(stage_plan):
        stage_name = str(stage.get("stage", f"stage {index + 1}"))
        local_matches = [
            match
            for match in evidence.get("local_matches", [])
            if str(match.get("stage", stage_name)) == stage_name
        ]
        stage_evidence = {
            **evidence,
            "stage": stage,
            "local_matches": local_matches,
        }
        stage_query = " ".join(
            [
                goal,
                stage_name,
                str(stage.get("tempo_hint", "")),
                str(stage.get("energy_hint", "")),
                " ".join(preferred_styles),
            ]
        )
        songs = recommend_real_songs(
            query=stage_query,
            count=8,
            preferred_styles=preferred_styles,
            disliked_styles=disliked_styles,
            stage_name=stage_name,
            evidence=stage_evidence,
        )
        unique_songs = []
        for song in songs:
            key = (
                str(song.get("title", "")).strip().lower(),
                str(song.get("artist", "")).strip().lower(),
            )
            if key in used_song_keys:
                continue
            used_song_keys.add(key)
            unique_songs.append(song)
            if len(unique_songs) >= 4:
                break
        songs = unique_songs or songs[:4]
        all_songs.extend(songs)
        stages.append(
            {
                "stage": stage_name,
                "minutes": stage.get("minutes", 0),
                "time_range": ranges[index],
                "intended_mood": stage.get("tempo_hint", "natural movement"),
                "energy_level": stage.get("energy_hint", "balanced energy"),
                "recommended_songs": songs,
            }
        )

    return {
        "stages": stages,
        "recommended_songs": all_songs,
        "explanation": (
            "The listening arc is shaped by time, energy, and style preferences, "
            "then filled with real song suggestions for each stage."
        ),
    }


def _visual_music_query(
    message: str,
    visual_profile: Dict[str, Any],
    preferences: Dict[str, Any],
) -> str:
    parts = [
        message,
        "real songs and short-video BGM for a visual mood",
        str(visual_profile.get("scene_summary", "")),
        str(visual_profile.get("visual_mood", "")),
        str(visual_profile.get("energy_level", "")),
        " ".join(str(tag) for tag in visual_profile.get("aesthetic_tags", [])[:8]),
        str(visual_profile.get("recommended_music_direction", "")),
        str(visual_profile.get("short_video_bgm_direction", "")),
        str(preferences.get("energy_direction", "")),
        " ".join(preferences.get("preferred_styles") or []),
    ]
    return " ".join(part for part in parts if part).strip()


def _add_bgm_use_cases(songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    use_cases = [
        "intro",
        "background",
        "transition",
        "emotional highlight",
        "cinematic ending",
        "background",
    ]
    enriched = []
    for index, song in enumerate(songs):
        item = dict(song)
        item["use_case"] = item.get("use_case") or use_cases[index % len(use_cases)]
        enriched.append(item)
    return enriched


def build_real_song_playlist_plan(
    goal: str,
    stage_plan: List[Dict[str, Any]],
    preferred_styles: Optional[List[str]] = None,
    disliked_styles: Optional[List[str]] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _playlist_plan_from_stage_plan(
        goal=goal,
        stage_plan=stage_plan,
        preferred_styles=preferred_styles or [],
        disliked_styles=disliked_styles or [],
        evidence=evidence or {},
    )


def _clean_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    return dict(context)


def run_agent_turn(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    context = _clean_context(context)
    preferences = {
        "previous_user_request": context.get("previous_user_request", ""),
        "current_goal": context.get("current_goal", ""),
        "preferred_styles": list(context.get("preferred_styles") or []),
        "disliked_styles": list(context.get("disliked_styles") or []),
        "duration": context.get("duration"),
        "energy_direction": context.get("energy_direction", "balanced"),
        "last_action": context.get("last_action", ""),
        "stage_plan": context.get("stage_plan") or [],
        "last_visual_profile": context.get("last_visual_profile")
        or context.get("visual_profile"),
    }
    preferences = _apply_refinements(message, preferences)
    intent = _detect_intent(message, context)

    duration = _extract_minutes(message) or preferences.get("duration") or 40
    preferred_styles = list(preferences.get("preferred_styles") or [])
    disliked_styles = list(preferences.get("disliked_styles") or [])
    current_goal = message if intent != "refine" else preferences.get("current_goal") or message

    recommended_songs: List[Dict[str, Any]] = []
    playlist_plan = None
    evidence: Dict[str, Any] = {}

    if (
        intent == "refine"
        and preferences.get("last_action") == "visual_mood"
        and preferences.get("last_visual_profile")
    ):
        visual_profile = preferences["last_visual_profile"]
        visual_query = _visual_music_query(message, visual_profile, preferences)
        recommended_songs = _add_bgm_use_cases(
            recommend_real_songs(
                query=visual_query,
                count=6,
                preferred_styles=preferred_styles,
                disliked_styles=disliked_styles,
                evidence={"visual_profile": visual_profile},
            )
        )
        preferences["last_action"] = "visual_mood"
        preferences["current_goal"] = message
        answer_text = (
            "I kept the same visual atmosphere and reshaped the BGM direction "
            "for your follow-up."
        )
        follow_ups = [
            "Make it more cinematic",
            "Make it more upbeat",
            "Give me a softer version",
            "Find short-video background music",
        ]
        preferences["previous_user_request"] = message
        return {
            "answer_text": answer_text,
            "detected_intent": "visual_refine",
            "recommended_songs": recommended_songs,
            "playlist_plan": None,
            "visual_profile": visual_profile,
            "updated_preferences": preferences,
            "follow_up_suggestions": follow_ups,
        }

    if intent in {"playlist", "refine"} and (
        "playlist" in message.lower()
        or "mix" in message.lower()
        or preferences.get("last_action") == "playlist"
        or intent == "playlist"
    ):
        stage_plan = preferences.get("stage_plan") or auto_plan(current_goal, int(duration))
        stage_plan = _shorten_cooldown_if_requested(message, stage_plan)

        try:
            local_plan = generate_playlist(
                goal=current_goal,
                total_minutes=int(duration),
                preferred_genres=preferred_styles or None,
                custom_plan=stage_plan,
                top_k_per_stage=3,
            )
            evidence = {
                "stage_plan": local_plan.get("stage_plan", stage_plan),
                "local_matches": local_plan.get("playlist", [])[:8],
            }
            stage_plan = local_plan.get("stage_plan", stage_plan)
        except Exception as exc:
            evidence = {"note": "Local style evidence was unavailable.", "error": str(exc)}

        playlist_plan = _playlist_plan_from_stage_plan(
            goal=current_goal,
            stage_plan=stage_plan,
            preferred_styles=preferred_styles,
            disliked_styles=disliked_styles,
            evidence=evidence,
        )
        recommended_songs = playlist_plan["recommended_songs"]
        preferences["last_action"] = "playlist"
        preferences["stage_plan"] = stage_plan
        preferences["duration"] = duration
        preferences["current_goal"] = current_goal
        answer_text = (
            "I shaped this as a real-song playlist journey with stages, energy flow, "
            "and track suggestions you can refine."
        )
    else:
        discovery_query = message
        if intent == "reference_audio" and context.get("audio_context"):
            audio_context = context["audio_context"]
            discovery_query = (
                f"real songs with a similar mood to {audio_context.get('predicted_genre', 'this song')} "
                f"with {preferences.get('energy_direction', 'balanced')} energy"
            )

        try:
            retrieval = retrieve_from_text(discovery_query, 6)
            evidence = {
                "parsed_targets": retrieval.get("parsed_targets"),
                "local_matches": retrieval.get("results", [])[:6],
            }
        except Exception as exc:
            evidence = {"note": "Local style evidence was unavailable.", "error": str(exc)}

        recommended_songs = recommend_real_songs(
            query=discovery_query,
            count=6,
            preferred_styles=preferred_styles,
            disliked_styles=disliked_styles,
            evidence=evidence,
        )
        preferences["last_action"] = "music_discovery"
        preferences["current_goal"] = discovery_query
        answer_text = (
            "Here are real song suggestions tuned to the mood, style, and energy you described."
        )

    preferences["previous_user_request"] = message

    follow_ups = [
        "Make it more energetic",
        "More rock, less hip-hop",
        "Shorten the cooldown",
        "Give me a calmer version",
    ]
    if preferences.get("last_action") == "music_discovery":
        follow_ups = [
            "Make it warmer",
            "More jazz, less pop",
            "Find a late-night version",
            "Turn this into a 45-minute playlist",
        ]

    return {
        "answer_text": answer_text,
        "detected_intent": intent,
        "recommended_songs": recommended_songs,
        "playlist_plan": playlist_plan,
        "visual_profile": None,
        "updated_preferences": preferences,
        "follow_up_suggestions": follow_ups,
    }


def run_image_agent_turn(
    message: str,
    image_bytes: bytes,
    content_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = _clean_context(context)
    preferences = {
        "previous_user_request": context.get("previous_user_request", ""),
        "current_goal": context.get("current_goal", ""),
        "preferred_styles": list(context.get("preferred_styles") or []),
        "disliked_styles": list(context.get("disliked_styles") or []),
        "duration": context.get("duration"),
        "energy_direction": context.get("energy_direction", "balanced"),
        "last_action": context.get("last_action", ""),
        "stage_plan": context.get("stage_plan") or [],
        "last_visual_profile": context.get("last_visual_profile")
        or context.get("visual_profile"),
    }
    preferences = _apply_refinements(message, preferences)

    visual_profile = analyze_visual_mood(image_bytes, content_type, message)
    if isinstance(visual_profile, dict) and visual_profile.get("status") == "unsupported":
        preferences["previous_user_request"] = message
        preferences["last_action"] = "visual_mood"
        return {
            "answer_text": str(
                visual_profile.get(
                    "friendly_message",
                    "This model cannot read images directly. Describe the image mood, and I'll recommend music from that.",
                )
            ),
            "detected_intent": "visual_mood",
            "recommended_songs": [],
            "playlist_plan": None,
            "visual_profile": None,
            "updated_preferences": preferences,
            "follow_up_suggestions": [
                "Describe the visual mood",
                "Make it more cinematic",
                "Make it more upbeat",
                "Find short-video background music",
            ],
        }

    if not visual_profile:
        preferences["previous_user_request"] = message
        preferences["last_action"] = "visual_mood"
        return {
            "answer_text": (
                "I couldn't read the image clearly. You can describe the mood "
                "or scene, and I will recommend music from that."
            ),
            "detected_intent": "visual_mood",
            "recommended_songs": [],
            "playlist_plan": None,
            "visual_profile": None,
            "updated_preferences": preferences,
            "follow_up_suggestions": [
                "Describe the visual mood",
                "Make it more cinematic",
                "Make it more upbeat",
                "Find short-video background music",
            ],
        }

    preferred_styles = list(preferences.get("preferred_styles") or [])
    disliked_styles = list(preferences.get("disliked_styles") or [])
    visual_query = _visual_music_query(message, visual_profile, preferences)
    recommended_songs = _add_bgm_use_cases(
        recommend_real_songs(
            query=visual_query,
            count=6,
            preferred_styles=preferred_styles,
            disliked_styles=disliked_styles,
            evidence={"visual_profile": visual_profile},
        )
    )

    preferences["previous_user_request"] = message
    preferences["current_goal"] = message or "BGM for this photo"
    preferences["last_action"] = "visual_mood"
    preferences["last_visual_profile"] = visual_profile

    return {
        "answer_text": (
            "The image suggests a visible atmosphere that can pair well with "
            "these BGM and song ideas."
        ),
        "detected_intent": "visual_mood",
        "recommended_songs": recommended_songs,
        "playlist_plan": None,
        "visual_profile": visual_profile,
        "updated_preferences": preferences,
        "follow_up_suggestions": [
            "Make it more cinematic",
            "Make it more upbeat",
            "Give me a softer version",
            "Find short-video background music",
        ],
    }
