from app.services.llm_client import get_provider_status


def llm_status():
    return get_provider_status()
