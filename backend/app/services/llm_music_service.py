import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.services.llm_client import complete_json, get_provider_config


Song = Dict[str, Any]


FALLBACK_SONGS: List[Song] = [
    {
        "title": "Eye of the Tiger",
        "artist": "Survivor",
        "genre": "rock",
        "mood": "driven",
        "energy": "high",
        "tags": ["workout", "gym", "rock", "energetic", "intense"],
    },
    {
        "title": "Don't Stop Me Now",
        "artist": "Queen",
        "genre": "rock",
        "mood": "uplifting",
        "energy": "high",
        "tags": ["workout", "commute", "rock", "fast", "energetic"],
    },
    {
        "title": "Seven Nation Army",
        "artist": "The White Stripes",
        "genre": "rock",
        "mood": "bold",
        "energy": "medium-high",
        "tags": ["rock", "gym", "stomp", "intense"],
    },
    {
        "title": "Mr. Brightside",
        "artist": "The Killers",
        "genre": "indie rock",
        "mood": "anthemic",
        "energy": "high",
        "tags": ["rock", "commute", "energetic", "bright"],
    },
    {
        "title": "Can't Hold Us",
        "artist": "Macklemore & Ryan Lewis feat. Ray Dalton",
        "genre": "hip-hop",
        "mood": "motivational",
        "energy": "high",
        "tags": ["workout", "gym", "hip-hop", "energetic", "fast"],
    },
    {
        "title": "Stronger",
        "artist": "Kanye West",
        "genre": "hip-hop",
        "mood": "confident",
        "energy": "high",
        "tags": ["workout", "hip-hop", "energetic", "gym"],
    },
    {
        "title": "Titanium",
        "artist": "David Guetta feat. Sia",
        "genre": "dance pop",
        "mood": "powerful",
        "energy": "high",
        "tags": ["workout", "pop", "dance", "energetic"],
    },
    {
        "title": "Midnight City",
        "artist": "M83",
        "genre": "electronic",
        "mood": "glowing",
        "energy": "medium-high",
        "tags": ["commute", "bright", "night", "electronic"],
    },
    {
        "title": "Take Five",
        "artist": "The Dave Brubeck Quartet",
        "genre": "jazz",
        "mood": "cool",
        "energy": "medium",
        "tags": ["jazz", "reading", "study", "relaxing"],
    },
    {
        "title": "Blue in Green",
        "artist": "Miles Davis",
        "genre": "jazz",
        "mood": "late-night",
        "energy": "low",
        "tags": ["jazz", "reading", "late night", "calm", "relaxing"],
    },
    {
        "title": "In a Sentimental Mood",
        "artist": "Duke Ellington & John Coltrane",
        "genre": "jazz",
        "mood": "warm",
        "energy": "low",
        "tags": ["jazz", "dinner", "reading", "warm", "late night"],
    },
    {
        "title": "Naima",
        "artist": "John Coltrane",
        "genre": "jazz",
        "mood": "reflective",
        "energy": "low",
        "tags": ["jazz", "calm", "study", "late night"],
    },
    {
        "title": "Misty",
        "artist": "Erroll Garner",
        "genre": "jazz",
        "mood": "soft",
        "energy": "low",
        "tags": ["jazz", "reading", "warm", "relaxing"],
    },
    {
        "title": "Clair de Lune",
        "artist": "Claude Debussy",
        "genre": "classical",
        "mood": "dreamy",
        "energy": "low",
        "tags": ["classical", "study", "sleep", "late night", "calm"],
    },
    {
        "title": "Gymnopedie No. 1",
        "artist": "Erik Satie",
        "genre": "classical",
        "mood": "minimal",
        "energy": "low",
        "tags": ["classical", "study", "reading", "calm", "late night"],
    },
    {
        "title": "Avril 14th",
        "artist": "Aphex Twin",
        "genre": "ambient piano",
        "mood": "delicate",
        "energy": "low",
        "tags": ["study", "late night", "calm", "ambient"],
    },
    {
        "title": "An Ending (Ascent)",
        "artist": "Brian Eno",
        "genre": "ambient",
        "mood": "floating",
        "energy": "low",
        "tags": ["ambient", "study", "sleep", "calm"],
    },
    {
        "title": "Intro",
        "artist": "The xx",
        "genre": "indie electronic",
        "mood": "focused",
        "energy": "medium-low",
        "tags": ["study", "late night", "commute", "minimal"],
    },
    {
        "title": "Come Away With Me",
        "artist": "Norah Jones",
        "genre": "vocal jazz",
        "mood": "intimate",
        "energy": "low",
        "tags": ["dinner", "warm", "relaxing", "jazz"],
    },
    {
        "title": "Harvest Moon",
        "artist": "Neil Young",
        "genre": "folk rock",
        "mood": "warm",
        "energy": "low",
        "tags": ["dinner", "warm", "soft", "relaxing"],
    },
    {
        "title": "Electric Feel",
        "artist": "MGMT",
        "genre": "indie pop",
        "mood": "bright",
        "energy": "medium",
        "tags": ["pop", "commute", "bright", "upbeat"],
    },
    {
        "title": "Levitating",
        "artist": "Dua Lipa",
        "genre": "pop",
        "mood": "sparkling",
        "energy": "high",
        "tags": ["pop", "commute", "bright", "energetic", "dance"],
    },
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _song_query(title: Any, artist: Any) -> str:
    title_text = str(title or "").strip()
    artist_text = str(artist or "").strip()
    return " ".join(part for part in [title_text, artist_text] if part).strip()


def _netease_title_query(title: Any) -> str:
    text = str(title or "").strip()
    cleaned = re.sub(
        r"\s*\((?=[^)]*(cover|remix|version|edit|live|acoustic|feat\.?|ft\.?|with|by))[^)]*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def _safe_url(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("https://") or text.startswith("http://"):
        return text
    return None


def spotify_search_url(title: Any, artist: Any) -> Optional[str]:
    query = _song_query(title, artist)
    if not query:
        return None
    return f"https://open.spotify.com/search/{quote(query)}"


def netease_search_url(title: Any, artist: Any) -> Optional[str]:
    query = _netease_title_query(title)
    if not query:
        return None
    encoded_query = quote(query, safe="")
    return f"https://music.163.com/#/search/m/?s={encoded_query}&type=1"


def normalize_song_links(song: Song) -> Song:
    title = song.get("title")
    artist = song.get("artist")
    normalized = dict(song)
    normalized["spotify_url"] = (
        _safe_url(song.get("spotify_url")) or spotify_search_url(title, artist)
    )
    netease_url = _safe_url(song.get("netease_url"))
    if netease_url and "/search" not in netease_url.lower():
        normalized["netease_url"] = netease_url
    else:
        normalized["netease_url"] = netease_search_url(title, artist)
    return normalized


def _score_song(song: Song, query: str, preferred: List[str], disliked: List[str]) -> int:
    haystack = " ".join(
        [
            str(song.get("title", "")),
            str(song.get("artist", "")),
            str(song.get("genre", "")),
            str(song.get("mood", "")),
            str(song.get("energy", "")),
            " ".join(song.get("tags", [])),
        ]
    )
    normalized = f" {_normalize(haystack)} "
    query_terms = set(_normalize(query).split())
    score = sum(1 for term in query_terms if term and f" {term} " in normalized)
    normalized_query = f" {_normalize(query)} "
    energy = f" {_normalize(str(song.get('energy', '')))} "

    for style in preferred:
        if _normalize(style) and _normalize(style) in normalized:
            score += 4

    for style in disliked:
        if _normalize(style) and _normalize(style) in normalized:
            score -= 6

    low_requested = any(
        f" {term} " in normalized_query
        for term in ["low", "slow", "calm", "cooldown", "sleep", "study", "relaxing"]
    )
    high_requested = any(
        f" {term} " in normalized_query
        for term in ["high", "fast", "intense", "workout", "gym", "energetic", "peak"]
    )

    if low_requested:
        if " low " in energy or "medium low" in energy:
            score += 5
        elif " high " in energy or "medium high" in energy:
            score -= 4
    elif high_requested:
        if " high " in energy or "medium high" in energy:
            score += 5
        elif " low " in energy or "medium low" in energy:
            score -= 3

    return score


def _fallback_recommendations(
    query: str,
    count: int,
    preferred_styles: Optional[List[str]] = None,
    disliked_styles: Optional[List[str]] = None,
    stage_name: Optional[str] = None,
) -> List[Song]:
    preferred = preferred_styles or []
    disliked = disliked_styles or []
    ranked = sorted(
        FALLBACK_SONGS,
        key=lambda song: _score_song(song, query, preferred, disliked),
        reverse=True,
    )

    songs = []
    for song in ranked[:count]:
        stage_text = f" for the {stage_name} stage" if stage_name else ""
        songs.append(
            normalize_song_links(
                {
                    "title": song["title"],
                    "artist": song["artist"],
                    "genre": song.get("genre"),
                    "mood": song.get("mood"),
                    "energy": song.get("energy"),
                    "stage": stage_name,
                    "reason": (
                        f"A best-effort pick{stage_text}: it matches the requested "
                        f"{song.get('mood', 'listening')} mood with {song.get('energy', 'balanced')} energy."
                    ),
                    "verification": "best_effort",
                }
            )
        )
    return songs


def _llm_recommendations(
    query: str,
    count: int,
    preferred_styles: Optional[List[str]],
    disliked_styles: Optional[List[str]],
    stage_name: Optional[str],
    evidence: Optional[Dict[str, Any]],
) -> Optional[List[Song]]:
    provider = get_provider_config()
    if provider.provider == "offline" or not provider.configured:
        return None

    system_prompt = (
        "You recommend real public songs for a music agent. Return only JSON. "
        "Do not invent precise verification claims. If unsure, mark verification as best_effort. "
        "Avoid technical system language. Keep reasons short and listener-facing."
    )
    user_prompt = {
        "request": query,
        "count": count,
        "preferred_styles": preferred_styles or [],
        "disliked_styles": disliked_styles or [],
        "stage_name": stage_name,
        "style_evidence": evidence or {},
        "schema": {
            "recommended_songs": [
                {
                    "title": "song title",
                    "artist": "artist name",
                    "reason": "why it fits",
                    "stage": stage_name,
                    "genre": "optional style",
                    "mood": "optional mood",
                    "energy": "optional energy",
                    "use_case": "optional intro/background/transition/highlight/ending",
                    "spotify_url": "optional exact Spotify track URL",
                    "netease_url": "optional exact NetEase Cloud Music track URL",
                    "verification": "verified_or_best_effort",
                }
            ]
        },
    }

    parsed = complete_json(
        system_prompt,
        user_prompt,
        use_web_search=provider.capabilities.supports_web_search,
    )
    if not parsed:
        return None

    try:
        songs = parsed.get("recommended_songs", [])
        if isinstance(songs, list) and songs:
            cleaned = []
            for song in songs[:count]:
                if not isinstance(song, dict):
                    continue
                if not song.get("title") or not song.get("artist"):
                    continue
                cleaned.append(
                    normalize_song_links(
                        {
                            "title": str(song.get("title", "")),
                            "artist": str(song.get("artist", "")),
                            "reason": str(song.get("reason", "")),
                            "stage": stage_name or song.get("stage"),
                            "genre": song.get("genre"),
                            "mood": song.get("mood"),
                            "energy": song.get("energy"),
                            "use_case": song.get("use_case"),
                            "spotify_url": song.get("spotify_url"),
                            "netease_url": song.get("netease_url"),
                            "verification": "best_effort",
                        }
                    )
                )
            return cleaned or None
    except Exception:
        return None

    return None


def recommend_real_songs(
    query: str,
    count: int = 6,
    preferred_styles: Optional[List[str]] = None,
    disliked_styles: Optional[List[str]] = None,
    stage_name: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> List[Song]:
    songs = _llm_recommendations(
        query=query,
        count=count,
        preferred_styles=preferred_styles,
        disliked_styles=disliked_styles,
        stage_name=stage_name,
        evidence=evidence,
    )
    if songs:
        return songs

    return _fallback_recommendations(
        query=query,
        count=count,
        preferred_styles=preferred_styles,
        disliked_styles=disliked_styles,
        stage_name=stage_name,
    )
