/**
 * Pool xoay vòng nhiều API key pinkyne cho slide-engine — khi model config
 * đang active gặp lỗi quota/401/403/429, tự chuyển sang key kế tiếp còn dùng
 * được thay vì để mọi lần sinh sau đó đều thất bại.
 *
 * Đọc từ OPENAI_API_KEYS (phân tách dấu phẩy) trong backend/.env; nếu không
 * có thì chỉ có 1 key (tương thích ngược — không bắt buộc phải cấu hình pool).
 */

const COOLDOWN_MS = 5 * 60 * 1000 // 5 phút

class KeyPool {
  private keys: string[]
  private badUntil = new Map<string, number>()
  private idx = 0

  constructor(keys: string[]) {
    this.keys = keys
  }

  size(): number {
    return this.keys.length
  }

  current(): string | null {
    if (this.keys.length === 0) return null
    const now = Date.now()
    for (let i = 0; i < this.keys.length; i++) {
      const k = this.keys[this.idx % this.keys.length]
      if ((this.badUntil.get(k) || 0) <= now) return k
      this.idx++
    }
    // Tất cả đang cooldown — vẫn trả về key ít mới hỏng nhất để thử (còn hơn không key nào)
    return this.keys.reduce((best, k) => ((this.badUntil.get(k) || 0) < (this.badUntil.get(best) || 0) ? k : best))
  }

  /** Đánh dấu key vừa lỗi (cooldown 5 phút), xoay sang key kế tiếp. Trả về key kế tiếp (nếu có). */
  markBad(key: string, reason = ''): string | null {
    this.badUntil.set(key, Date.now() + COOLDOWN_MS)
    this.idx++
    const now = Date.now()
    const ready = this.keys.filter((k) => (this.badUntil.get(k) || 0) <= now).length
    console.log(`[key-pool] key ...${key.slice(-6)} tạm khóa 5 phút (${reason}) — còn ${ready}/${this.keys.length} key sẵn sàng`)
    return this.current()
  }
}

let pool: KeyPool | null = null

export function getKeyPool(): KeyPool {
  if (!pool) {
    const raw = process.env.OPENAI_API_KEYS || ''
    let keys = raw
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean)
    if (keys.length === 0) {
      const single = process.env.OPENAI_API_KEY || ''
      keys = single ? [single] : []
    }
    pool = new KeyPool(keys)
    if (keys.length > 1) console.log(`[key-pool] đã nạp ${keys.length} key pinkyne để tự xoay khi hết quota`)
  }
  return pool
}

/** Heuristic: message lỗi này có phải do hết quota/key hỏng không (nên xoay key)? */
export function isQuotaError(message: string): boolean {
  const m = (message || '').toLowerCase()
  return ['quota', 'insufficient', 'billing', 'exhausted', 'rate limit', 'token remain'].some((k) => m.includes(k))
}
