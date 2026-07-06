/** Smoke: mở UI web oh-my-ppt, đợi app render, log lỗi console, chụp màn hình. */
import { chromium } from 'playwright'

async function main(): Promise<void> {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text().slice(0, 200))
  })
  page.on('pageerror', (err) => errors.push(`pageerror: ${String(err).slice(0, 200)}`))

  await page.goto('http://localhost:8100/app/', { waitUntil: 'load', timeout: 30000 })
  await page.waitForTimeout(4000)

  const rootHtml = await page.evaluate(
    () => document.getElementById('root')?.innerHTML.length ?? 0
  )
  const title = await page.title()
  console.log(`[smoke] title=${title} rootHtmlLength=${rootHtml}`)
  console.log(`[smoke] console errors (${errors.length}):`)
  for (const e of errors.slice(0, 10)) console.log('  -', e)

  await page.screenshot({ path: 'out/smoke-ui.png', fullPage: false })
  console.log('[smoke] screenshot → out/smoke-ui.png')
  await browser.close()
}

main().catch((e) => {
  console.error('[smoke] FAILED:', e)
  process.exit(1)
})
