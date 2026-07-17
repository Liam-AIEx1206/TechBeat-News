import type { IpcContext } from '../context'

export type AppLocale = 'zh' | 'en' | 'vi'

// XNEW dùng tiếng Việt làm mặc định. Các lời gọi cũ chỉ truyền (zh, en) — khi
// không có bản tiếng Việt riêng thì dùng bản tiếng Anh (dễ đọc hơn tiếng Trung
// với người Việt). Truyền tham số `vi` khi muốn câu tiếng Việt chuẩn.
export const uiText = (locale: AppLocale, zh: string, en: string, vi?: string): string => {
  if (locale === 'en') return en
  if (locale === 'zh') return zh
  return vi ?? en
}

export async function readAppLocale(ctx: Pick<IpcContext, 'db'>): Promise<AppLocale> {
  const locale = await ctx.db.getSetting<string>('locale').catch(() => 'vi')
  if (locale === 'en') return 'en'
  if (locale === 'zh') return 'zh'
  return 'vi'
}
