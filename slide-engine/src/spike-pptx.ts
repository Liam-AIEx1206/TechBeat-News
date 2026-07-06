/**
 * P0 spike: chứng minh pipeline HTML → PPTX của oh-my-ppt chạy được headless.
 *
 * Cách chạy:  npm run spike:pptx -- <page1.html> [page2.html ...] [-o out.pptx]
 * Mặc định:   dùng 2 trang preview 1600×900 từ oh-my-ppt/resources/skills.
 *
 * Kết quả mong đợi: file .pptx mở được, mỗi slide = ảnh nền + TEXT BOX THẬT
 * (kiểm chứng editable khi upload Canva).
 */
import path from 'path'
import { existsSync } from 'fs'
import { writeHtmlToPptx, type HtmlToPptxSlide } from '../vendor/main/utils/html-pptx/index'
import {
  extractHtmlPageToPptxSlide,
  closePptxBrowser
} from './renderer-playwright'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')

const DEFAULT_PAGES = [
  path.join(repoRoot, 'oh-my-ppt', 'resources', 'styles', 'minimal-white', 'preview.html'),
  path.join(repoRoot, 'oh-my-ppt', 'resources', 'styles', 'pitch-deck-vc', 'preview.html')
]

async function main(): Promise<void> {
  const args = process.argv.slice(2)
  let outputPath = path.join(repoRoot, 'slide-engine', 'out', 'spike.pptx')
  const pages: string[] = []
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '-o') {
      outputPath = path.resolve(args[i + 1])
      i += 1
    } else {
      pages.push(path.resolve(args[i]))
    }
  }
  if (pages.length === 0) pages.push(...DEFAULT_PAGES)

  for (const p of pages) {
    if (!existsSync(p)) throw new Error(`Không thấy file trang: ${p}`)
  }
  const { mkdirSync } = await import('fs')
  mkdirSync(path.dirname(outputPath), { recursive: true })

  console.log(`[spike] ${pages.length} trang → ${outputPath}`)

  const slides: HtmlToPptxSlide[] = []
  const warnings: string[] = []
  for (const [index, htmlPath] of pages.entries()) {
    const pageId = `page-${index + 1}`
    console.log(`[spike] extract ${pageId}: ${htmlPath}`)
    const started = Date.now()
    const { slide, warning } = await extractHtmlPageToPptxSlide({
      page: { htmlPath, pageId, title: path.basename(path.dirname(htmlPath)) },
      // Trang preview không nhúng ppt-runtime nên không phát print-ready →
      // để timeout ngắn cho spike; trang gen thật sẽ phát tín hiệu ngay.
      timeoutMs: 3000,
      settleMs: 200
    })
    if (warning) warnings.push(warning)
    console.log(
      `[spike]   xong sau ${Date.now() - started}ms — texts=${slide.texts?.length ?? 0} shapes=${slide.shapes?.length ?? 0} images=${slide.images?.length ?? 0} tables=${slide.tables?.length ?? 0} bg=${slide.backgroundImage ? 'yes' : 'no'}`
    )
    slides.push(slide)
  }

  await writeHtmlToPptx(outputPath, {
    title: 'XNEW slide-engine spike',
    author: 'OhMyPPT',
    slides
  })

  console.log(`[spike] ĐÃ GHI ${outputPath}`)
  if (warnings.length) console.log(`[spike] cảnh báo:\n - ${warnings.join('\n - ')}`)

  await closePptxBrowser()
}

main().catch((error) => {
  console.error('[spike] THẤT BẠI:', error)
  closePptxBrowser().finally(() => process.exit(1))
})
