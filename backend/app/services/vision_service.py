import base64
import colorsys
import io
from typing import Any, Dict, List, Optional

from app.services.llm_client import complete_vision_json, get_provider_config


VisualProfile = Dict[str, Any]


def _data_uri(image_bytes: bytes, content_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _palette_from_image(image) -> List[str]:
    small = image.copy()
    small.thumbnail((120, 120))
    palette_image = small.convert("P", palette=1, colors=5)
    palette = palette_image.getpalette() or []
    colors = palette_image.getcolors(maxcolors=120 * 120) or []
    colors = sorted(colors, key=lambda item: item[0], reverse=True)
    hex_colors = []
    for _, index in colors[:5]:
        offset = index * 3
        rgb = tuple(palette[offset : offset + 3])
        if len(rgb) == 3:
            hex_colors.append(_hex_color(rgb))
    return hex_colors


def _local_visual_profile(image_bytes: bytes) -> Optional[VisualProfile]:
    try:
        from PIL import Image, ImageStat
    except Exception:
        return None

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None

    sample = image.copy()
    sample.thumbnail((256, 256))
    stat = ImageStat.Stat(sample)
    red, green, blue = [float(value) for value in stat.mean[:3]]
    brightness = (red + green + blue) / 3.0
    saturation_values = [
        colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[1]
        for r, g, b in sample.getdata()
    ]
    saturation = sum(saturation_values) / max(1, len(saturation_values))

    if blue > red + 18:
        temperature = "cool"
    elif red > blue + 18:
        temperature = "warm"
    else:
        temperature = "neutral"

    if brightness < 86:
        light = "low-lit"
    elif brightness > 178:
        light = "bright"
    else:
        light = "soft-lit"

    if saturation > 0.42:
        color_energy = "vivid"
    elif saturation < 0.18:
        color_energy = "muted"
    else:
        color_energy = "balanced"

    if light == "low-lit":
        visual_mood = "moody, cinematic, and reflective"
        energy_level = "low-medium"
    elif temperature == "cool":
        visual_mood = "calm, blue-toned, and spacious"
        energy_level = "low"
    elif temperature == "warm" and light == "bright":
        visual_mood = "warm, bright, and upbeat"
        energy_level = "medium-high"
    elif color_energy == "vivid":
        visual_mood = "colorful, lively, and expressive"
        energy_level = "medium-high"
    else:
        visual_mood = "balanced, natural, and reflective"
        energy_level = "medium"

    tags = [temperature, light, color_energy]
    if "cinematic" in visual_mood:
        tags.append("cinematic")
    if energy_level.startswith("low"):
        tags.append("ambient-friendly")
    if "upbeat" in visual_mood or "lively" in visual_mood:
        tags.append("short-video-ready")

    return {
        "scene_summary": (
            f"The image has a {light}, {temperature} visual atmosphere with "
            f"{color_energy} color intensity."
        ),
        "visual_mood": visual_mood,
        "color_palette": _palette_from_image(image),
        "energy_level": energy_level,
        "aesthetic_tags": tags,
        "recommended_music_direction": (
            "Pair this visual with music that follows the color temperature, "
            "lighting, and overall pacing of the image."
        ),
        "short_video_bgm_direction": (
            "Use a clear intro, a steady background bed, and a gentle ending "
            "that leaves room for the visual atmosphere."
        ),
        "source": "visual_atmosphere",
    }


def _clean_profile(profile: Dict[str, Any]) -> VisualProfile:
    return {
        "scene_summary": str(profile.get("scene_summary") or ""),
        "visual_mood": str(profile.get("visual_mood") or ""),
        "color_palette": list(profile.get("color_palette") or [])[:6],
        "energy_level": str(profile.get("energy_level") or "balanced"),
        "aesthetic_tags": list(profile.get("aesthetic_tags") or [])[:8],
        "recommended_music_direction": str(
            profile.get("recommended_music_direction") or ""
        ),
        "short_video_bgm_direction": str(
            profile.get("short_video_bgm_direction") or ""
        ),
        "source": str(profile.get("source") or "visual_atmosphere"),
    }


def _llm_visual_profile(
    image_bytes: bytes,
    content_type: str,
    message: str,
) -> Optional[VisualProfile]:
    provider = get_provider_config()
    if not provider.configured or not provider.capabilities.supports_vision:
        return None

    data_uri = _data_uri(image_bytes, content_type)
    system_prompt = (
        "Analyze the image for visual atmosphere and music pairing. "
        "Do not claim to know anyone's true internal emotion. "
        "Describe only visible scene atmosphere, colors, pacing, and aesthetic style. "
        "Return only JSON."
    )
    user_prompt = {
        "user_request": message,
        "schema": {
            "scene_summary": "short visual description",
            "visual_mood": "safe visible mood description",
            "color_palette": ["color words or hex colors"],
            "energy_level": "low/medium/high",
            "aesthetic_tags": ["cinematic", "warm", "minimal"],
            "recommended_music_direction": "music direction",
            "short_video_bgm_direction": "BGM direction",
        },
    }

    parsed = complete_vision_json(system_prompt, user_prompt, data_uri)
    if not parsed:
        return None

    return _clean_profile(parsed)


def analyze_visual_mood(
    image_bytes: bytes,
    content_type: str,
    message: str = "",
) -> Optional[VisualProfile]:
    provider = get_provider_config()
    if (
        provider.provider in {"offline", "deepseek"}
        or not provider.capabilities.supports_vision
    ):
        return {
            "status": "unsupported",
            "friendly_message": (
                "This model cannot read images directly. Describe the image "
                "mood, and I'll recommend music from that."
            ),
        }

    profile = _llm_visual_profile(image_bytes, content_type, message)
    if profile:
        profile["source"] = "visual_atmosphere"
        return profile

    return _local_visual_profile(image_bytes)
