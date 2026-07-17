export type AppLocale = 'zh' | 'en' | 'vi'

export type ProgressStatusKey =
  | 'understanding'
  | 'planning'
  | 'preparing'
  | 'generating'
  | 'checking'
  | 'retrying'
  | 'finalizing'
  | 'completed'
  | 'failed'
  | 'canceled'

const PROGRESS_TEXT: Record<ProgressStatusKey, Record<AppLocale, string>> = {
  understanding: {
    zh: '理解需求',
    en: 'Understanding request',
    vi: 'Đang phân tích yêu cầu'
  },
  planning: {
    zh: '规划结构',
    en: 'Planning structure',
    vi: 'Đang lên bố cục'
  },
  preparing: {
    zh: '准备画布',
    en: 'Preparing canvas',
    vi: 'Đang chuẩn bị khung slide'
  },
  generating: {
    zh: '生成页面',
    en: 'Generating pages',
    vi: 'Đang sinh trang'
  },
  checking: {
    zh: '检查页面',
    en: 'Checking pages',
    vi: 'Đang kiểm tra trang'
  },
  retrying: {
    zh: '正在重试',
    en: 'Retrying',
    vi: 'Đang thử lại'
  },
  finalizing: {
    zh: '正在收尾',
    en: 'Finalizing',
    vi: 'Đang hoàn tất'
  },
  completed: {
    zh: '已完成',
    en: 'Completed',
    vi: 'Đã xong'
  },
  failed: {
    zh: '已失败',
    en: 'Failed',
    vi: 'Thất bại'
  },
  canceled: {
    zh: '已取消',
    en: 'Canceled',
    vi: 'Đã huỷ'
  }
}

const LABEL_MAP: Array<[RegExp, ProgressStatusKey]> = [
  [/取消|cancel/i, 'canceled'],
  [/失败|错误|fail|error/i, 'failed'],
  [/重试|retry/i, 'retrying'],
  [/完成|已生成|已更新|已创建|complete|completed|done|generated|updated|created/i, 'completed'],
  [/检查|验证|校验|check|verif|validation/i, 'checking'],
  [/规划|结构|大纲|整理.*大纲|plan|structur|outline/i, 'planning'],
  [/画布|准备|本地.*就绪|canvas|prepar|ready/i, 'preparing'],
  [/理解|分析|understand|analyz/i, 'understanding'],
  [/生成|写入|更新|填充|generate|generating|writing|updating|filling/i, 'generating'],
  [/收尾|finaliz/i, 'finalizing']
]

export const normalizeLocale = (locale: AppLocale | undefined): AppLocale =>
  locale === 'en' ? 'en' : locale === 'zh' ? 'zh' : 'vi'

export const progressText = (locale: AppLocale | undefined, key: ProgressStatusKey): string =>
  PROGRESS_TEXT[key][normalizeLocale(locale)]

export const normalizeProgressLabel = (rawLabel: string | undefined): ProgressStatusKey => {
  const label = (rawLabel || '').trim()
  if (!label) return 'generating'
  for (const [pattern, key] of LABEL_MAP) {
    if (pattern.test(label)) return key
  }
  return 'generating'
}

export const progressLabel = (
  locale: AppLocale | undefined,
  rawLabel: string | undefined
): string => progressText(locale, normalizeProgressLabel(rawLabel))

export const progressDisplayLabel = (
  locale: AppLocale | undefined,
  rawLabel: string | undefined
): string => {
  const label = (rawLabel || '').trim()
  if (/^(?:P\d+\b|第\s*\d+\s*页)/i.test(label)) return label
  return progressLabel(locale, label)
}
