import asyncio
from dataclasses import dataclass, field

import os

@dataclass
class ConcurrencyLimiter:
    """Giới hạn số tác vụ nặng chạy đồng thời."""
    max_renders: int = int(os.getenv("CONCURRENCY_MAX_RENDERS", "30"))
    max_llm_calls: int = int(os.getenv("CONCURRENCY_MAX_LLM_CALLS", "20"))
    max_tts: int = int(os.getenv("CONCURRENCY_MAX_TTS", "20"))

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
