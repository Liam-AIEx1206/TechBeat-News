/**
 * Playwright port of oh-my-ppt's src/main/utils/html-pptx/renderer.ts.
 *
 * Đây là file DUY NHẤT được thay thế trong pipeline xuất PPTX: bản gốc dùng
 * Electron BrowserWindow (không chạy được trên web server); bản này giữ nguyên
 * từng bước của luồng gốc — load trang → freeze animation → chạy các browser
 * script y hệt (import verbatim từ browser-scripts.ts) → trích text box →
 * chụp nền có retry chống lem chữ → trả về HtmlToPptxSlide cùng schema.
 *
 * Khác biệt kỹ thuật duy nhất:
 *  - BrowserWindow → chromium page (viewport 1600×900, deviceScaleFactor 1)
 *  - webContents.executeJavaScript(script) → page.evaluate(script)
 *  - webContents.capturePage() → page.screenshot({clip}) + pngjs decode
 *    (Electron toBitmap() trả BGRA; pngjs trả RGBA — xử lý trong pixel check)
 *  - console-message listener → page.on('console') cho tín hiệu print-ready
 */
import { chromium, type Browser, type Page } from 'playwright'
import { PNG } from 'pngjs'
import { pathToFileURL } from 'url'
import log from 'electron-log/main.js'
import {
  buildHtmlToPptxExtractScript,
  normalizeExtractedHtmlToPptxSlide,
  type HtmlToPptxSlide,
  type HtmlToPptxTextBox
} from '../vendor/main/utils/html-pptx/index'
import {
  FREEZE_PAGE_FOR_PPTX_SCRIPT,
  HIDE_FOR_PPTX_BACKGROUND_SCRIPT,
  RESET_SCALE_FOR_PPTX_CAPTURE_SCRIPT,
  WAIT_FOR_PPTX_CAPTURE_FRAME_SCRIPT,
  MARK_KATEX_BLOCKS_SCRIPT,
  COLLECT_KATEX_BLOCK_RECTS_SCRIPT,
  COLLECT_PPTX_ANIMATION_TRACES_SCRIPT
} from '../vendor/main/utils/html-pptx/browser-scripts'

export interface HtmlPageForPptx {
  htmlPath: string
  pageId: string
  title?: string
}

export interface HtmlPageToPptxSlideOptions {
  page: HtmlPageForPptx
  timeoutMs: number
  settleMs: number
}

export interface HtmlPageToPptxSlideResult {
  slide: HtmlToPptxSlide
  warning?: string
}

const PPTX_CAPTURE_WIDTH = 1600
const PPTX_CAPTURE_HEIGHT = 900
const PPTX_SLIDE_WIDTH_IN = 13.333
const PPTX_SLIDE_HEIGHT_IN = 7.5
const PPTX_BACKGROUND_CAPTURE_ATTEMPTS = 3
const TEXT_RESIDUE_MAX_BOXES = 24
const TEXT_RESIDUE_GRID_COLUMNS = 18
const TEXT_RESIDUE_GRID_ROWS = 10
const TEXT_RESIDUE_COLOR_DISTANCE = 62
const TEXT_RESIDUE_RATIO_THRESHOLD = 0.075

// Giống PRINT_READY_PREFIX trong src/main/ipc/context.ts của oh-my-ppt:
// runtime trang phát console message `__PPT_PRINT_READY__...:<pageId>` khi vẽ xong.
const PRINT_READY_PREFIX = '__PPT_PRINT_READY__'

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

// ── Browser lifecycle ─────────────────────────────────────────────────────────

let sharedBrowser: Browser | null = null

async function getBrowser(): Promise<Browser> {
  if (sharedBrowser && sharedBrowser.isConnected()) return sharedBrowser
  sharedBrowser = await chromium.launch({ headless: true })
  return sharedBrowser
}

export async function closePptxBrowser(): Promise<void> {
  if (sharedBrowser) {
    await sharedBrowser.close().catch(() => {})
    sharedBrowser = null
  }
}

const createPptxPage = async (): Promise<Page> => {
  const browser = await getBrowser()
  const context = await browser.newContext({
    viewport: { width: PPTX_CAPTURE_WIDTH, height: PPTX_CAPTURE_HEIGHT },
    deviceScaleFactor: 1
  })
  return context.newPage()
}

// ── Pixel helpers (port từ renderer.ts; pngjs = RGBA thay vì BGRA) ───────────

const parseHexColor = (value?: string): { r: number; g: number; b: number } | null => {
  const normalized = String(value || '')
    .trim()
    .replace(/^#/, '')
  if (/^[0-9a-f]{3}$/i.test(normalized)) {
    const [r, g, b] = normalized.split('').map((char) => Number.parseInt(`${char}${char}`, 16))
    return { r, g, b }
  }
  if (!/^[0-9a-f]{6}$/i.test(normalized)) return null
  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16)
  }
}

const colorDistance = (
  left: { r: number; g: number; b: number },
  right: { r: number; g: number; b: number }
): number => {
  const dr = left.r - right.r
  const dg = left.g - right.g
  const db = left.b - right.b
  return Math.sqrt(dr * dr + dg * dg + db * db)
}

const pixelMatchesTextColor = (
  rgba: Buffer,
  index: number,
  target: { r: number; g: number; b: number }
): boolean => {
  const r = rgba[index] ?? 0
  const g = rgba[index + 1] ?? 0
  const b = rgba[index + 2] ?? 0
  return colorDistance({ r, g, b }, target) <= TEXT_RESIDUE_COLOR_DISTANCE
}

const hasTextResidueInCapture = (
  png: PNG,
  texts: HtmlToPptxTextBox[]
): { suspicious: boolean; checkedBoxes: number; maxRatio: number } => {
  if (texts.length === 0) return { suspicious: false, checkedBoxes: 0, maxRatio: 0 }
  const size = { width: png.width, height: png.height }
  const bitmap = png.data
  if (!size.width || !size.height || bitmap.length < size.width * size.height * 4) {
    return { suspicious: false, checkedBoxes: 0, maxRatio: 0 }
  }
  const pxPerInX = size.width / PPTX_SLIDE_WIDTH_IN
  const pxPerInY = size.height / PPTX_SLIDE_HEIGHT_IN
  const candidates = texts
    .filter((text) => {
      const color = parseHexColor(text.color)
      return Boolean(
        color &&
          text.text.trim().length >= 2 &&
          text.w > 0.05 &&
          text.h > 0.03 &&
          (text.opacity ?? 1) > 0.05
      )
    })
    .sort((a, b) => b.fontSize * b.w * b.h - a.fontSize * a.w * a.h)
    .slice(0, TEXT_RESIDUE_MAX_BOXES)

  let checkedBoxes = 0
  let maxRatio = 0
  for (const text of candidates) {
    const target = parseHexColor(text.color)
    if (!target) continue
    const left = Math.max(0, Math.floor(text.x * pxPerInX))
    const top = Math.max(0, Math.floor(text.y * pxPerInY))
    const right = Math.min(size.width - 1, Math.ceil((text.x + text.w) * pxPerInX))
    const bottom = Math.min(size.height - 1, Math.ceil((text.y + text.h) * pxPerInY))
    const width = right - left
    const height = bottom - top
    if (width < 4 || height < 4) continue

    checkedBoxes += 1
    let samples = 0
    let textLikePixels = 0
    const columns = Math.min(TEXT_RESIDUE_GRID_COLUMNS, Math.max(3, Math.floor(width / 3)))
    const rows = Math.min(TEXT_RESIDUE_GRID_ROWS, Math.max(3, Math.floor(height / 3)))
    for (let row = 0; row < rows; row += 1) {
      const y = Math.min(bottom, top + Math.floor(((row + 0.5) * height) / rows))
      for (let column = 0; column < columns; column += 1) {
        const x = Math.min(right, left + Math.floor(((column + 0.5) * width) / columns))
        const index = (y * size.width + x) * 4
        samples += 1
        if (pixelMatchesTextColor(bitmap, index, target)) {
          textLikePixels += 1
        }
      }
    }
    if (samples === 0) continue
    const ratio = textLikePixels / samples
    maxRatio = Math.max(maxRatio, ratio)
    if (textLikePixels >= 8 && ratio >= TEXT_RESIDUE_RATIO_THRESHOLD) {
      return { suspicious: true, checkedBoxes, maxRatio }
    }
  }

  return { suspicious: false, checkedBoxes, maxRatio }
}

// ── Capture helpers ──────────────────────────────────────────────────────────

const screenshotPng = async (
  page: Page,
  clip?: { x: number; y: number; width: number; height: number }
): Promise<Buffer> =>
  page.screenshot({
    type: 'png',
    animations: 'disabled',
    clip: clip ?? { x: 0, y: 0, width: PPTX_CAPTURE_WIDTH, height: PPTX_CAPTURE_HEIGHT }
  })

const capturePptxBackgroundWithRetry = async (
  page: Page,
  pageId: string,
  texts: HtmlToPptxTextBox[],
  hideScript?: string
): Promise<{ png: Buffer; warning?: string }> => {
  let lastPng: Buffer | null = null
  let lastCheck: ReturnType<typeof hasTextResidueInCapture> | null = null
  const script = hideScript || HIDE_FOR_PPTX_BACKGROUND_SCRIPT

  for (let attempt = 1; attempt <= PPTX_BACKGROUND_CAPTURE_ATTEMPTS; attempt += 1) {
    await page.evaluate(script)
    await page.evaluate(WAIT_FOR_PPTX_CAPTURE_FRAME_SCRIPT)
    await sleep(process.platform === 'win32' ? 180 : 80)
    await page.evaluate(WAIT_FOR_PPTX_CAPTURE_FRAME_SCRIPT)

    const pngBuffer = await screenshotPng(page)
    const decoded = PNG.sync.read(pngBuffer)
    const check = hasTextResidueInCapture(decoded, texts)
    lastPng = pngBuffer
    lastCheck = check
    if (!check.suspicious) {
      if (attempt > 1) {
        log.info('[export:pptx] background capture recovered after retry', {
          pageId,
          attempt,
          checkedBoxes: check.checkedBoxes,
          maxRatio: Number(check.maxRatio.toFixed(3))
        })
      }
      return { png: pngBuffer }
    }

    log.warn('[export:pptx] background capture text residue detected', {
      pageId,
      attempt,
      checkedBoxes: check.checkedBoxes,
      maxRatio: Number(check.maxRatio.toFixed(3))
    })
  }

  if (!lastPng) {
    throw new Error(`PPTX background capture failed for ${pageId}`)
  }
  return {
    png: lastPng,
    warning: `Trang ${pageId} có thể còn lem chữ trong ảnh nền, đã dùng ảnh chụp lần cuối.${
      lastCheck ? ` Tỉ lệ phát hiện ${Number(lastCheck.maxRatio.toFixed(3))}` : ''
    }`
  }
}

// ── Print-ready signal (console message, giống ipc/context.ts) ──────────────

const waitForPrintReadySignal = (
  page: Page,
  pageId: string,
  timeoutMs: number
): Promise<{ timedOut: boolean; reportedPageId?: string }> =>
  new Promise((resolve) => {
    let done = false
    let timeoutRef: NodeJS.Timeout | null = null

    const finalize = (timedOut: boolean, reportedPageId?: string): void => {
      if (done) return
      done = true
      if (timeoutRef) clearTimeout(timeoutRef)
      page.off('console', onConsole)
      resolve({ timedOut, reportedPageId })
    }

    const extractReportedPageId = (message: string): string | null => {
      const prefixIndex = message.indexOf(PRINT_READY_PREFIX)
      if (prefixIndex < 0) return null
      const suffix = message.slice(prefixIndex + PRINT_READY_PREFIX.length)
      const colonIndex = suffix.indexOf(':')
      if (colonIndex < 0) return null
      return suffix.slice(colonIndex + 1).trim() || null
    }

    const onConsole = (msg: { text: () => string }): void => {
      const reported = extractReportedPageId(msg.text())
      if (!reported) return
      if (reported === pageId || reported === 'page-unknown') {
        finalize(false, reported)
      }
    }

    timeoutRef = setTimeout(() => finalize(true), Math.max(500, timeoutMs))
    page.on('console', onConsole)
  })

// ── Load & freeze (port loadAndFreezePptxPage) ───────────────────────────────

const loadAndFreezePptxPage = async (
  page: Page,
  pageInfo: HtmlPageForPptx,
  timeoutMs: number,
  settleMs: number
): Promise<{ timedOut: boolean }> => {
  const pageUrl = new URL(pathToFileURL(pageInfo.htmlPath).toString())
  pageUrl.searchParams.set('fit', 'off')
  pageUrl.searchParams.set('print', '1')
  pageUrl.searchParams.set('export', '1')
  pageUrl.searchParams.set('pageId', pageInfo.pageId)
  pageUrl.searchParams.set('printTimeoutMs', String(timeoutMs))
  pageUrl.searchParams.set('_ts', String(Date.now()))

  const readyWaitPromise = waitForPrintReadySignal(page, pageInfo.pageId, timeoutMs)

  await page.goto(pageUrl.toString(), { waitUntil: 'load', timeout: timeoutMs + 15000 })
  await page.evaluate(FREEZE_PAGE_FOR_PPTX_SCRIPT)
  const readyResult = await readyWaitPromise
  if (readyResult.timedOut) {
    log.warn('[export:pptx] print ready timeout', {
      pageId: pageInfo.pageId,
      htmlPath: pageInfo.htmlPath,
      timeoutMs
    })
  }

  await sleep(settleMs)
  await page.evaluate(FREEZE_PAGE_FOR_PPTX_SCRIPT)
  await sleep(450)
  await page.evaluate(FREEZE_PAGE_FOR_PPTX_SCRIPT)
  await sleep(80)

  return readyResult
}

const captureFullPage = async (page: Page): Promise<Buffer> => {
  await page.evaluate(WAIT_FOR_PPTX_CAPTURE_FRAME_SCRIPT)
  await sleep(process.platform === 'win32' ? 180 : 80)
  await page.evaluate(WAIT_FOR_PPTX_CAPTURE_FRAME_SCRIPT)
  return screenshotPng(page)
}

// ── Public API (cùng chữ ký nghiệp vụ với renderer.ts gốc) ───────────────────

/** Chế độ ảnh: cả trang thành 1 ảnh nền (fallback / imageOnly). */
export const captureHtmlPageToPptxImageSlide = async ({
  page: pageInfo,
  timeoutMs,
  settleMs
}: HtmlPageToPptxSlideOptions): Promise<HtmlPageToPptxSlideResult> => {
  const page = await createPptxPage()

  try {
    const readyResult = await loadAndFreezePptxPage(page, pageInfo, timeoutMs, settleMs)

    await page.evaluate(RESET_SCALE_FOR_PPTX_CAPTURE_SCRIPT)

    const png = await captureFullPage(page)

    const slide: HtmlToPptxSlide = {
      title: pageInfo.title,
      texts: [],
      shapes: [],
      images: [],
      tables: [],
      backgroundImage: {
        dataUri: `data:image/png;base64,${png.toString('base64')}`,
        mimeType: 'image/png',
        x: 0,
        y: 0,
        w: PPTX_SLIDE_WIDTH_IN,
        h: PPTX_SLIDE_HEIGHT_IN,
        alt: pageInfo.title
      }
    }

    return {
      slide,
      warning: readyResult.timedOut
        ? `Trang ${pageInfo.pageId} không phát tín hiệu print-ready, đã xuất theo trạng thái hiện tại`
        : undefined
    }
  } finally {
    await page.context().close().catch(() => {})
  }
}

/** Chế độ editable: text box thật + ảnh nền đã giấu chữ (mặc định). */
export const extractHtmlPageToPptxSlide = async ({
  page: pageInfo,
  timeoutMs,
  settleMs
}: HtmlPageToPptxSlideOptions): Promise<HtmlPageToPptxSlideResult> => {
  const page = await createPptxPage()

  try {
    const readyResult = await loadAndFreezePptxPage(page, pageInfo, timeoutMs, settleMs)

    // Đánh dấu khối công thức trước khi trích text để bỏ qua chúng
    await page.evaluate(MARK_KATEX_BLOCKS_SCRIPT)

    const extracted = await page.evaluate(
      buildHtmlToPptxExtractScript({
        pageWidthPx: PPTX_CAPTURE_WIDTH,
        pageHeightPx: PPTX_CAPTURE_HEIGHT,
        maxShapes: 240,
        maxImages: 40
      })
    )

    const slide = normalizeExtractedHtmlToPptxSlide(extracted, pageInfo.title)

    try {
      const traces = await page.evaluate(COLLECT_PPTX_ANIMATION_TRACES_SCRIPT)
      if (Array.isArray(traces) && traces.length > 0) {
        slide.animationTraces = traces
      }
    } catch (error) {
      log.warn('[export:pptx] animation trace collection failed', {
        pageId: pageInfo.pageId,
        error: error instanceof Error ? error.message : String(error)
      })
    }

    // Reset scale SAU khi trích (trích dùng toạ độ đã scale), TRƯỚC khi chụp nền
    await page.evaluate(RESET_SCALE_FOR_PPTX_CAPTURE_SCRIPT)

    // Chụp các khối công thức thành ảnh overlay
    const blockRects = (await page.evaluate(COLLECT_KATEX_BLOCK_RECTS_SCRIPT)) as Array<{
      x: number
      y: number
      w: number
      h: number
    }>
    for (const rect of blockRects) {
      const pad = 2
      const captureRect = {
        x: Math.max(0, rect.x - pad),
        y: Math.max(0, rect.y - pad),
        width: Math.min(PPTX_CAPTURE_WIDTH, rect.w + pad * 2),
        height: Math.min(PPTX_CAPTURE_HEIGHT, rect.h + pad * 2)
      }
      const png = await screenshotPng(page, captureRect)
      const dataUri = `data:image/png;base64,${png.toString('base64')}`
      if (!slide.overlayImages) slide.overlayImages = []
      slide.overlayImages.push({
        dataUri,
        mimeType: 'image/png',
        x: (captureRect.x / PPTX_CAPTURE_WIDTH) * PPTX_SLIDE_WIDTH_IN,
        y: (captureRect.y / PPTX_CAPTURE_HEIGHT) * PPTX_SLIDE_HEIGHT_IN,
        w: (captureRect.width / PPTX_CAPTURE_WIDTH) * PPTX_SLIDE_WIDTH_IN,
        h: (captureRect.height / PPTX_CAPTURE_HEIGHT) * PPTX_SLIDE_HEIGHT_IN,
        alt: 'formula'
      })
    }

    // Chụp nền: giữ phần trang trí, giấu chữ + shape/ảnh đã trích riêng
    const backgroundCapture = await capturePptxBackgroundWithRetry(
      page,
      pageInfo.pageId,
      slide.texts,
      HIDE_FOR_PPTX_BACKGROUND_SCRIPT
    )
    slide.backgroundImage = {
      dataUri: `data:image/png;base64,${backgroundCapture.png.toString('base64')}`,
      mimeType: 'image/png',
      x: 0,
      y: 0,
      w: PPTX_SLIDE_WIDTH_IN,
      h: PPTX_SLIDE_HEIGHT_IN,
      alt: pageInfo.title
    }

    return {
      slide,
      warning: [
        readyResult.timedOut
          ? `Trang ${pageInfo.pageId} không phát tín hiệu print-ready, đã xuất theo trạng thái hiện tại`
          : '',
        backgroundCapture.warning || ''
      ]
        .filter(Boolean)
        .join('; ')
    }
  } finally {
    await page.context().close().catch(() => {})
  }
}
