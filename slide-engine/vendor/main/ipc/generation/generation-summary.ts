export type GenerationSummaryLocale = 'zh' | 'en' | 'vi'

export function buildLocalCompletedGenerationPageSummary(args: {
  appLocale: GenerationSummaryLocale
  pageTitle: string
}): string {
  return args.appLocale === 'en'
    ? `Completed page "${args.pageTitle}" generation`
    : `已完成《${args.pageTitle}》页面生成`
}
