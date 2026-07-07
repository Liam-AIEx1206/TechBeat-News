export const THINKING_PARAMETER_MODES = ['auto', 'omit'] as const

export type ThinkingParameterMode = (typeof THINKING_PARAMETER_MODES)[number]

// COMPAT slide-engine: mặc định 'omit' (gốc 'auto'). Deploy XNEW luôn dùng proxy
// OpenAI-compatible reject arg 'thinking' → 429. Worker deepagents không nhận
// binding runtime nên phải đổi DEFAULT. Xem slide-engine/VENDOR.md.
export const DEFAULT_THINKING_PARAMETER_MODE: ThinkingParameterMode = 'omit'

export const normalizeThinkingParameterMode = (value: unknown): ThinkingParameterMode => {
  return THINKING_PARAMETER_MODES.includes(value as ThinkingParameterMode)
    ? (value as ThinkingParameterMode)
    : DEFAULT_THINKING_PARAMETER_MODE
}
