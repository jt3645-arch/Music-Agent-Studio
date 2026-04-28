import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.config import (
    DASHSCOPE_API_KEY,
    DEEPSEEK_API_KEY,
    ENABLE_WEB_SEARCH,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    VISION_MODEL_NAME,
)


ProviderName = str

SUPPORTED_PROVIDERS = {"openai", "deepseek", "qwen", "offline"}
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_runtime_provider: Optional[ProviderName] = None


@dataclass
class ProviderCapabilities:
    supports_text: bool
    supports_vision: bool
    supports_web_search: bool
    supports_json_output: bool


@dataclass
class LLMProviderConfig:
    provider: ProviderName
    model: str
    vision_model: str
    api_key: str
    base_url: Optional[str]
    configured: bool
    capabilities: ProviderCapabilities


def _normalize_provider(provider: Optional[str]) -> ProviderName:
    value = (provider or LLM_PROVIDER or "openai").strip().lower()
    if value not in SUPPORTED_PROVIDERS:
        return "offline"
    return value


def _qwen_supports_vision(model_name: str) -> bool:
    normalized = model_name.lower()
    return "vl" in normalized or "vision" in normalized or "omni" in normalized


def _capabilities(provider: ProviderName, model_name: str) -> ProviderCapabilities:
    if provider == "offline":
        return ProviderCapabilities(
            supports_text=True,
            supports_vision=False,
            supports_web_search=False,
            supports_json_output=False,
        )

    if provider == "openai":
        return ProviderCapabilities(
            supports_text=True,
            supports_vision=True,
            supports_web_search=ENABLE_WEB_SEARCH,
            supports_json_output=True,
        )

    if provider == "deepseek":
        return ProviderCapabilities(
            supports_text=True,
            supports_vision=False,
            supports_web_search=False,
            supports_json_output=True,
        )

    return ProviderCapabilities(
        supports_text=True,
        supports_vision=_qwen_supports_vision(model_name),
        supports_web_search=False,
        supports_json_output=True,
    )


def set_runtime_provider(provider: str) -> LLMProviderConfig:
    global _runtime_provider
    _runtime_provider = _normalize_provider(provider)
    return get_provider_config()


def get_provider_config() -> LLMProviderConfig:
    provider = _normalize_provider(_runtime_provider)
    base_url = LLM_BASE_URL.strip() or None
    model = LLM_MODEL
    vision_model = VISION_MODEL_NAME or LLM_MODEL

    if provider == "openai":
        api_key = OPENAI_API_KEY
    elif provider == "deepseek":
        api_key = DEEPSEEK_API_KEY
        base_url = base_url or DEEPSEEK_BASE_URL
        if model == "gpt-5-mini":
            model = "deepseek-chat"
            vision_model = "deepseek-chat"
    elif provider == "qwen":
        api_key = DASHSCOPE_API_KEY
        base_url = base_url or QWEN_BASE_URL
        if model == "gpt-5-mini":
            model = "qwen-plus"
            vision_model = "qwen-plus"
    else:
        api_key = ""
        base_url = None
        model = "offline"
        vision_model = "offline"

    return LLMProviderConfig(
        provider=provider,
        model=model,
        vision_model=vision_model,
        api_key=api_key,
        base_url=base_url,
        configured=bool(api_key) if provider != "offline" else True,
        capabilities=_capabilities(provider, vision_model),
    )


def get_provider_status() -> Dict[str, Any]:
    config = get_provider_config()
    caps = config.capabilities
    return {
        "provider": config.provider,
        "model": config.model,
        "vision_model": config.vision_model,
        "configured": config.configured,
        "capabilities": {
            "supports_text": caps.supports_text,
            "supports_vision": caps.supports_vision,
            "supports_web_search": caps.supports_web_search,
            "supports_json_output": caps.supports_json_output,
        },
    }


def _client(config: LLMProviderConfig):
    if config.provider == "offline" or not config.configured:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    if config.base_url:
        return OpenAI(api_key=config.api_key, base_url=config.base_url)
    return OpenAI(api_key=config.api_key)


def extract_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("No JSON object found in LLM response.")


def complete_json(
    system_prompt: str,
    user_payload: Dict[str, Any],
    *,
    use_web_search: bool = False,
) -> Optional[Dict[str, Any]]:
    config = get_provider_config()
    if not config.configured or config.provider == "offline":
        return None

    client = _client(config)
    if client is None:
        return None

    user_text = json.dumps(user_payload, default=str)

    if (
        config.provider == "openai"
        and use_web_search
        and config.capabilities.supports_web_search
    ):
        try:
            response = client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                tools=[{"type": "web_search_preview"}],
                tool_choice="auto",
            )
            return extract_json_object(getattr(response, "output_text", ""))
        except Exception:
            traceback.print_exc()

    try:
        completion = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
        )
        return extract_json_object(completion.choices[0].message.content or "")
    except Exception:
        traceback.print_exc()
        return None


def complete_vision_json(
    system_prompt: str,
    user_payload: Dict[str, Any],
    image_data_uri: str,
) -> Optional[Dict[str, Any]]:
    config = get_provider_config()
    if (
        not config.configured
        or config.provider == "offline"
        or not config.capabilities.supports_vision
    ):
        return None

    client = _client(config)
    if client is None:
        return None

    user_text = json.dumps(user_payload, default=str)

    if config.provider == "openai":
        try:
            response = client.responses.create(
                model=config.vision_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_text},
                            {"type": "input_image", "image_url": image_data_uri},
                        ],
                    },
                ],
            )
            return extract_json_object(getattr(response, "output_text", ""))
        except Exception:
            traceback.print_exc()

    try:
        completion = client.chat.completions.create(
            model=config.vision_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        return extract_json_object(completion.choices[0].message.content or "")
    except Exception:
        traceback.print_exc()
        return None
