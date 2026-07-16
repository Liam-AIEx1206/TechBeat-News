"""
Pool xoay vòng nhiều API key pinkyne — khi 1 key hết quota/bị lỗi 401/403/429,
tự chuyển sang key kế tiếp còn dùng được thay vì làm cả luồng thất bại.

Đọc từ OPENAI_API_KEYS (phân tách dấu phẩy) trong .env; nếu không có thì dùng
OPENAI_API_KEY đơn lẻ (tương thích ngược, không cần đổi .env để chạy được).
"""
import os
import time
import threading

_COOLDOWN_SECONDS = 300  # 5 phút — đủ để quota có thể hồi phục, tránh đập liên tục vào key vừa hỏng


class KeyPool:
    def __init__(self, keys: list[str]):
        self._keys = keys
        self._bad_until: dict[str, float] = {}
        self._idx = 0
        self._lock = threading.Lock()

    def current(self) -> str | None:
        """Trả về key hiện dùng được (bỏ qua các key đang cooldown)."""
        with self._lock:
            if not self._keys:
                return None
            n = len(self._keys)
            now = time.time()
            for _ in range(n):
                k = self._keys[self._idx % n]
                if self._bad_until.get(k, 0) <= now:
                    return k
                self._idx += 1
            # Tất cả đều đang cooldown — vẫn trả về key ít mới hỏng nhất để thử (còn hơn không key nào)
            return min(self._keys, key=lambda k: self._bad_until.get(k, 0))

    def mark_bad(self, key: str, reason: str = "") -> str | None:
        """Đánh dấu key vừa lỗi (cooldown 5 phút), xoay sang key kế tiếp. Trả về key kế tiếp (nếu có)."""
        with self._lock:
            self._bad_until[key] = time.time() + _COOLDOWN_SECONDS
            self._idx += 1
            now = time.time()
            ready = sum(1 for k in self._keys if self._bad_until.get(k, 0) <= now)
            tail = key[-6:] if len(key) >= 6 else key
            print(f"[key-pool] key ...{tail} tạm khóa 5 phút ({reason}) — còn {ready}/{len(self._keys)} key sẵn sàng")
        return self.current()

    def size(self) -> int:
        return len(self._keys)


_pool: KeyPool | None = None


def get_pool() -> KeyPool:
    global _pool
    if _pool is None:
        raw = os.getenv("OPENAI_API_KEYS", "").strip()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            single = os.getenv("OPENAI_API_KEY", "").strip()
            keys = [single] if single else []
        _pool = KeyPool(keys)
        if len(keys) > 1:
            print(f"[key-pool] đã nạp {len(keys)} key pinkyne để tự xoay khi hết quota")
    return _pool


def is_quota_error(status_code: int | None, message: str) -> bool:
    """Heuristic dùng chung: lỗi này có nên xoay sang key/provider khác không?"""
    if status_code in (401, 402, 403, 429):
        return True
    msg = (message or "").lower()
    return any(k in msg for k in ("quota", "insufficient", "billing", "exhausted", "rate limit", "token remain"))
