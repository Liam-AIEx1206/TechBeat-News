import os
from dataclasses import dataclass

from openai import OpenAI, AsyncOpenAI


# ─── Provider chain ──────────────────────────────────────────────────────
# Each provider is tried in order. On a quota / billing error, we move to
# the next one. Add a new provider by appending to PROVIDER_CHAIN below
# and supplying the corresponding env vars.

@dataclass
class Provider:
    name: str               # short label for logs/UI ("primary", "anthropic", "groq")
    api_key_env: str        # env var holding the key (None disables this provider)
    base_url_env: str       # env var holding the base URL (has a sensible default)
    base_url_default: str   # default URL when env var is unset
    model_env: str          # env var for the model id
    model_default: str      # default model id

    # Per-task model overrides — fall back to model_default
    scenes_model_env: str | None = None
    composition_model_env: str | None = None
    ocr_model_env: str | None = None

    @property
    def api_key(self) -> str | None:
        v = os.getenv(self.api_key_env)
        return v if v and v.strip() else None

    @property
    def base_url(self) -> str:
        return os.getenv(self.base_url_env, self.base_url_default)

    def model_for(self, kind: str) -> str:
        if kind == "scenes" and self.scenes_model_env:
            v = os.getenv(self.scenes_model_env)
            if v: return v
        if kind == "composition" and self.composition_model_env:
            v = os.getenv(self.composition_model_env)
            if v: return v
        if kind == "ocr" and self.ocr_model_env:
            v = os.getenv(self.ocr_model_env)
            if v: return v
        return os.getenv(self.model_env, self.model_default)


PROVIDER_CHAIN: list[Provider] = [
    # 1. Primary — pinkyne (or whatever proxy the user pointed OPENAI_BASE_URL to)
    Provider(
        name="primary",
        api_key_env="OPENAI_API_KEY",
        base_url_env="OPENAI_BASE_URL",
        base_url_default="https://api.pinkyne.com/v1",
        model_env="OPENAI_MODEL",
        model_default="gpt-5.5-pro",
        scenes_model_env="OPENAI_SCENES_MODEL",
        composition_model_env="OPENAI_COMPOSITION_MODEL",
        ocr_model_env="OPENAI_OCR_MODEL",
    ),
    # 2. Groq — generous free tier, Llama 3.3 70B
    Provider(
        name="groq",
        api_key_env="GROQ_API_KEY",
        base_url_env="GROQ_BASE_URL",
        base_url_default="https://api.groq.com/openai/v1",
        model_env="GROQ_MODEL",
        model_default="llama-3.3-70b-versatile",
        scenes_model_env="GROQ_SCENES_MODEL",
        composition_model_env="GROQ_COMPOSITION_MODEL",
        ocr_model_env="GROQ_OCR_MODEL",
    ),
    # 3. Groq fallback — same key, Llama 4 Scout when 70B hits TPD cap
    # TPM: 30K (vs 12K for 70B), TPD: 500K (vs 100K) — much more headroom
    Provider(
        name="groq-fast",
        api_key_env="GROQ_API_KEY",
        base_url_env="GROQ_BASE_URL",
        base_url_default="https://api.groq.com/openai/v1",
        model_env="GROQ_FAST_MODEL",
        model_default="meta-llama/llama-4-scout-17b-16e-instruct",
        scenes_model_env=None,
        composition_model_env=None,
        ocr_model_env=None,
    ),
]


# Convenience: ANTHROPIC_API_KEY is a more conventional name; fall back to it.
def _resolve_provider_key(p: Provider) -> str | None:
    key = p.api_key
    if key:
        return key
    if p.name == "anthropic":
        v = os.getenv("ANTHROPIC_API_KEY")
        if v and v.strip():
            return v
    return None


# ─── Client cache ────────────────────────────────────────────────────────
_async_clients: dict[str, AsyncOpenAI] = {}
_sync_client: OpenAI | None = None


def _make_async(p: Provider) -> AsyncOpenAI | None:
    """Lazy-init an AsyncOpenAI for provider `p`. Returns None if no key."""
    if p.name in _async_clients:
        return _async_clients[p.name]
    key = _resolve_provider_key(p)
    if not key:
        return None
    client = AsyncOpenAI(api_key=key, base_url=p.base_url, timeout=45.0)
    _async_clients[p.name] = client
    return client


def get_client() -> OpenAI:
    """Sync client for primary provider (legacy callers)."""
    global _sync_client
    if _sync_client is not None:
        return _sync_client
    primary = PROVIDER_CHAIN[0]
    key = _resolve_provider_key(primary)
    if not key:
        raise ValueError(f"{primary.api_key_env} chưa được set trong file .env")
    _sync_client = OpenAI(api_key=key, base_url=primary.base_url)
    return _sync_client


def get_async_client() -> AsyncOpenAI:
    """Async client for primary provider (legacy callers)."""
    primary = PROVIDER_CHAIN[0]
    c = _make_async(primary)
    if c is None:
        raise ValueError(f"{primary.api_key_env} chưa được set trong file .env")
    return c


def get_model(kind: str = "default") -> str:
    """Primary model id (legacy callers)."""
    return PROVIDER_CHAIN[0].model_for(kind)


def configured_providers() -> list[Provider]:
    """Providers in the chain that actually have credentials set."""
    return [p for p in PROVIDER_CHAIN if _resolve_provider_key(p)]


def log_provider_status() -> None:
    """Print which providers are active/skipped — call once at startup."""
    print("[LLM] == Provider chain ==")
    for p in PROVIDER_CHAIN:
        key = _resolve_provider_key(p)
        if key:
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
            print(f"[LLM]   OK {p.name:12s} key={masked}  url={p.base_url}")
        else:
            print(f"[LLM]   -- {p.name:12s} (key '{p.api_key_env}' chua set -> bo qua)")
    print("[LLM] ==================")


# --- Quota / billing detection -------------------------------------------

def _is_quota_or_billing_error(e: Exception) -> bool:
    """Heuristic: does this error mean 'this provider can't fulfil the
    request, try the next one' (vs. a real bug we shouldn't paper over)?"""
    msg = str(e).lower()
    keywords = (
        "quota", "balance", "insufficient", "payment_required", "paid_plan",
        "billing", "credit", "exhausted", "out of credits",
        "rate limit", "rate_limit", "free users",
        "invalid tokens",  # Pinkyne: "used invalid tokens multiple times"
        # Groq on-demand tier sometimes wraps TPM/context errors as 400 with
        # these messages. Treat them as quota-style so the chain falls
        # through to groq-fast (Scout 17B, looser caps) instead of aborting.
        "reduce the length", "messages or completion",
        "request too large", "context length", "context_length_exceeded",
        "too many tokens", "timeout", "timed out", "connect timeout"
    )
    if any(k in msg for k in keywords):
        return True
    if type(e).__name__ in ("APITimeoutError", "TimeoutException", "ConnectTimeout"):
        return True
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    if code in (402, 429, 502, 504):  # 402 = payment required, 429 = rate limit / quota, 502/504 = gateway timeout
        return True
    return False


# ─── Public API ──────────────────────────────────────────────────────────

async def chat_completions_with_fallback(*, model_kind: str, kwargs_factory=None, **kwargs):
    """Try each configured provider in order. Return on first success.

    Returns (response, provider_name). The response is the same shape as a
    normal OpenAI SDK call — callers iterate streams and read `.choices[0]`
    exactly as before.

    Two ways to pass request params:
      - Static `**kwargs` — same params for every provider (legacy).
      - `kwargs_factory(provider_name) -> dict` — per-provider customisation.
        Use this when paid providers should get the full prompt + large
        max_tokens budget but free-tier providers (Groq) need a compact
        prompt and small budget to fit their TPM cap.

    Special static kwarg `_primary_model` overrides the primary provider's
    model only (used by OCR which has its own model env var).
    """
    primary_model_override = kwargs.pop("_primary_model", None)

    providers = configured_providers()
    if not providers:
        raise RuntimeError(
            "Không có provider nào được cấu hình. "
            "Set ít nhất OPENAI_API_KEY, FALLBACK_API_KEY, hoặc GROQ_API_KEY trong .env."
        )

    last_err: Exception | None = None
    tried: list[str] = []

    for i, p in enumerate(providers):
        client = _make_async(p)
        if client is None:
            continue
        # Build per-provider kwargs. Factory wins over static kwargs.
        call_kwargs = dict(kwargs)
        if kwargs_factory is not None:
            call_kwargs = dict(kwargs_factory(p.name))
        model = primary_model_override if (i == 0 and primary_model_override) else p.model_for(model_kind)
        try:
            resp = await client.chat.completions.create(model=model, **call_kwargs)
            if i > 0:
                print(f"[llm] Used fallback provider '{p.name}' (model={model}). "
                      f"Skipped: {tried}")
            return resp, p.name, model  # (response, provider_name, model_name)
        except Exception as e:
            tried.append(f"{p.name}={type(e).__name__}")
            last_err = e
            if not _is_quota_or_billing_error(e):
                print(f"[llm] Provider '{p.name}' failed with non-quota error "
                      f"({type(e).__name__}: {e}). Aborting chain.")
                raise
            print(f"[llm] Provider '{p.name}' quota exhausted ({type(e).__name__}: {e}). "
                  f"Trying next in chain...")
            continue

    msg_lines = [
        "Tất cả LLM provider đều hết quota hoặc lỗi billing.",
        "Đã thử: " + ", ".join(p.name for p in providers),
        "Hãy nạp tiền hoặc thêm provider khác (GROQ_API_KEY=... có free tier)."
    ]
    raise RuntimeError("\n".join(msg_lines)) from last_err
