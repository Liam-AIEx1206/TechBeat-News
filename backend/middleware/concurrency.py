import asyncio
from dataclasses import dataclass, field

@dataclass
class ConcurrencyLimiter:
    """Giới hạn số tác vụ nặng chạy đồng thời."""
    max_renders: int = 2        # Playwright render (nặng nhất)
    max_llm_calls: int = 5      # LLM API calls (scenes/composition/gen-scene-one)
    max_tts: int = 3            # TTS synthesis

    _render_sem: asyncio.Semaphore = field(init=False)
    _llm_sem: asyncio.Semaphore = field(init=False)
    _tts_sem: asyncio.Semaphore = field(init=False)

    # Tracking
    _render_queue: int = 0
    _llm_queue: int = 0

    def __post_init__(self):
        self._render_sem = asyncio.Semaphore(self.max_renders)
        self._llm_sem = asyncio.Semaphore(self.max_llm_calls)
        self._tts_sem = asyncio.Semaphore(self.max_tts)

    @property
    def render_queue_size(self) -> int:
        return self._render_queue

    @property
    def llm_queue_size(self) -> int:
        return self._llm_queue

limiter = ConcurrencyLimiter()
