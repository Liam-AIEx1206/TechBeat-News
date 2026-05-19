import os

from openai import OpenAI, AsyncOpenAI

_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None


def _config() -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY chưa được set trong file .env")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.pinkyne.com/v1")
    return api_key, base_url


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key, base_url = _config()
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def get_async_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        api_key, base_url = _config()
        _async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _async_client


def get_model(kind: str = "default") -> str:
    if kind == "scenes":
        return os.getenv("OPENAI_SCENES_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5.5-pro")
    if kind == "composition":
        return os.getenv("OPENAI_COMPOSITION_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5.5-pro")
    return os.getenv("OPENAI_MODEL", "gpt-5.5-pro")
