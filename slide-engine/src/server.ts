/**
 * slide-engine bootstrap — tái hiện đúng trình tự app.whenReady() của
 * oh-my-ppt src/main/index.ts (db → styles → skills → AgentManager → setupIPC),
 * bỏ phần cửa sổ/tray/updater. Toàn bộ nghiệp vụ chạy qua các ipc channel gốc;
 * HTTP layer chỉ là adapter mỏng gọi __invokeIpc + nghe event bus cho SSE.
 *
 * Env:
 *  - SLIDE_ENGINE_PORT      (mặc định 8100)
 *  - SLIDE_ENGINE_DATA_DIR  (mặc định ./data — db, sessions, skills, styles cài đặt)
 */
import express from 'express'
import path from 'path'
import fs from 'fs'
import log from 'electron-log/main.js'
import { BrowserWindow } from 'electron'
import { __invokeIpc, __listIpcChannels, __electronShimBus, __setNextSavePath, __setNextOpenDir } from 'electron'
import { zipSync } from 'fflate'
import { PPTDatabase } from '../vendor/main/db/database'
import { AgentManager } from '../vendor/main/agent'
import { setupIPC } from '../vendor/main/ipc'
import { backfillUserStylePackagesFromDatabase, setStyleDb } from '../vendor/main/utils/style-skills'
import {
  initializeSkills,
  resolveBuiltinSkillsSourcePath,
  resolveInstalledSkillsPath,
  setSkillsRuntime
} from '../vendor/main/skills'
import {
  initializeStyles,
  resolveBundledStylesSourcePath,
  resolveInstalledStylesPath,
  setStylesRuntime
} from '../vendor/main/styles'
import { configureHtmlThumbnailService } from '../vendor/main/utils/html-thumbnail-service'
import { configureModelUsageRecorder } from '../vendor/main/model-usage'

const PORT = Number(process.env.SLIDE_ENGINE_PORT || 8100)

async function bootstrap(): Promise<void> {
  // 1) Database (shim app.getPath('userData') → SLIDE_ENGINE_DATA_DIR)
  const db = new PPTDatabase()
  await db.init()
  configureModelUsageRecorder(db)
  configureHtmlThumbnailService(db)
  await db.failInterruptedThumbnailTasks()
  setStyleDb(db)
  log.info('[server] database initialized')

  // 2) Styles (74 style packs từ resources/styles → thư mục cài đặt + sync db)
  const installedStylesPath = resolveInstalledStylesPath()
  const stylesReadyPromise = initializeStyles({
    bundledSourcePath: resolveBundledStylesSourcePath(),
    installedRootPath: installedStylesPath,
    logger: log
  }).then(async (result) => {
    await db.syncInstalledStylesToDatabase(installedStylesPath)
    await backfillUserStylePackagesFromDatabase(installedStylesPath)
    await db.backfillSessionStyleSnapshots()
    log.info('[server] styles initialized', {
      bundledCount: result.bundledCount,
      copiedCount: result.copiedCount
    })
    return result
  })
  setStylesRuntime({ installedStylesPath, ready: stylesReadyPromise })
  await stylesReadyPromise

  // 3) Skills (chart / data-anim / layout / source-reading)
  const installedSkillsPath = resolveInstalledSkillsPath()
  const skillsReadyPromise = initializeSkills({
    builtinSourcePath: resolveBuiltinSkillsSourcePath(),
    installedRootPath: installedSkillsPath,
    logger: log
  }).then((result) => {
    log.info('[server] skills initialized', {
      builtinCount: result.builtinCount,
      copiedCount: result.copiedCount
    })
    return result
  })
  setSkillsRuntime({ installedSkillsPath, ready: skillsReadyPromise })
  await skillsReadyPromise

  // 4) Agent + IPC (main window giả — webContents.send đổ về event bus)
  const agentManager = new AgentManager(db)
  const mainWindow = new BrowserWindow()
  setupIPC(mainWindow, db, agentManager)
  log.info('[server] IPC handlers registered', { channels: __listIpcChannels().length })

  // 5) Seed model config từ env (đi qua đúng channel gốc của oh-my-ppt)
  await seedModelConfigFromEnv()

  // 6) HTTP adapter
  const app = express()
  app.use(express.json({ limit: '20mb' }))

  app.get('/healthz', (_req, res) => {
    res.json({ ok: true, channels: __listIpcChannels().length })
  })

  app.get('/channels', (_req, res) => {
    res.json({ channels: __listIpcChannels() })
  })

  // Adapter tổng quát: gọi thẳng một ipc channel gốc của oh-my-ppt.
  // Body {__args:[...]} = đúng chữ ký ipcRenderer.invoke(channel, ...args);
  // body thường (object) giữ tương thích các route REST cũ.
  app.post('/invoke/:channel', async (req, res) => {
    try {
      const body = req.body ?? {}
      const args = Array.isArray(body.__args) ? body.__args : [body]
      const result = await __invokeIpc(req.params.channel, ...args)
      res.json({ ok: true, result: rewriteLocalUrls(result) })
    } catch (error) {
      res.status(500).json({
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      })
    }
  })

  // ── Web renderer (UI gốc oh-my-ppt chạy trong browser) ────────────────────
  app.use('/app', express.static(path.join(process.cwd(), 'renderer-dist')))

  // SSE fan TẤT CẢ webContents.send — bridge phía browser dispatch theo channel
  app.get('/events/all', (req, res) => {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive'
    })
    res.write(': connected\n\n')
    const onSend = (payload: { channel: string; args: unknown[] }): void => {
      res.write(`data: ${JSON.stringify(rewriteLocalUrls(payload))}\n\n`)
    }
    __electronShimBus.on('webcontents-send', onSend)
    const keepAlive = setInterval(() => res.write(': ping\n\n'), 15000)
    req.on('close', () => {
      clearInterval(keepAlive)
      __electronShimBus.off('webcontents-send', onSend)
    })
  })

  // File server thay cho file:// + local-asset:// (giới hạn trong data/resources)
  app.get(/^\/fs\/(.+)/, (req, res) => {
    try {
      const raw = decodeURIComponent(req.params[0])
      const abs = path.resolve(raw)
      const roots = [dataDirOf(), path.join(process.cwd(), 'resources')].map((r) => path.resolve(r))
      if (!roots.some((root) => abs.startsWith(root))) {
        res.status(403).json({ error: 'ngoài phạm vi cho phép' })
        return
      }
      if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
        res.status(404).json({ error: 'không thấy file' })
        return
      }
      res.sendFile(abs)
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Upload (bridge getPathForFile): browser không có path local
  app.post('/upload', express.raw({ type: '*/*', limit: '200mb' }), (req, res) => {
    try {
      const uploadDir = path.join(dataDirOf(), 'uploads')
      fs.mkdirSync(uploadDir, { recursive: true })
      // multipart đơn giản: tách phần body sau header boundary
      const contentType = String(req.headers['content-type'] || '')
      const boundary = contentType.split('boundary=')[1]
      if (!boundary) throw new Error('thiếu multipart boundary')
      const buf = req.body as Buffer
      const marker = Buffer.from('\r\n\r\n')
      const headerEnd = buf.indexOf(marker)
      const head = buf.slice(0, headerEnd).toString('utf-8')
      const nameMatch = /filename="([^"]+)"/.exec(head)
      const filename = nameMatch ? path.basename(nameMatch[1]) : `upload-${Date.now()}`
      const tail = Buffer.from(`\r\n--${boundary}--`)
      const endIdx = buf.lastIndexOf(tail)
      const content = buf.slice(headerEnd + marker.length, endIdx > 0 ? endIdx : undefined)
      const outPath = path.join(uploadDir, `${Date.now()}-${filename}`)
      fs.writeFileSync(outPath, content)
      res.json({ path: outPath })
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // SSE: forward mọi generate:chunk (client tự lọc theo sessionId trong payload)
  app.get('/events', (req, res) => {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive'
    })
    res.write(': connected\n\n')
    const onChunk = (...args: unknown[]): void => {
      res.write(`event: generate:chunk\ndata: ${JSON.stringify(args.length === 1 ? args[0] : args)}\n\n`)
    }
    __electronShimBus.on('generate:chunk', onChunk)
    const keepAlive = setInterval(() => res.write(': ping\n\n'), 15000)
    req.on('close', () => {
      clearInterval(keepAlive)
      __electronShimBus.off('generate:chunk', onChunk)
    })
  })

  // Styles cho picker
  app.get('/styles', async (_req, res) => {
    try {
      const result = await __invokeIpc('styles:list', {})
      res.json(result)
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Tạo session + kích hoạt generate (payload đi thẳng vào channel gốc)
  app.post('/sessions', async (req, res) => {
    try {
      const created = await __invokeIpc('session:create', req.body ?? {})
      res.json(created)
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  app.post('/sessions/:id/generate', async (req, res) => {
    try {
      const result = await __invokeIpc('generate:start', {
        ...(req.body ?? {}),
        sessionId: req.params.id
      })
      res.json(result)
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  app.get('/sessions/:id', async (req, res) => {
    try {
      const result = await __invokeIpc('session:get', req.params.id)
      res.json(result)
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Trang HTML đã gen (phục vụ preview qua iframe)
  app.get('/sessions/:id/pages/:pageId.html', async (req, res) => {
    try {
      const session = (await __invokeIpc('session:get', req.params.id)) as {
        project_dir?: string
        projectDir?: string
      }
      const projectDir = session?.project_dir || session?.projectDir
      if (!projectDir) throw new Error('Không tìm thấy projectDir của session')
      const filePath = path.join(projectDir, `${req.params.pageId}.html`)
      if (!fs.existsSync(filePath)) throw new Error(`Không thấy trang: ${req.params.pageId}`)
      res.type('html').send(fs.readFileSync(filePath, 'utf-8'))
    } catch (error) {
      res.status(404).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Xuất PPTX editable: đặt sẵn save path rồi gọi đúng channel export:pptx gốc
  app.post('/sessions/:id/export/pptx', async (req, res) => {
    try {
      const outDir = path.join(dataDirOf(), 'exports')
      fs.mkdirSync(outDir, { recursive: true })
      const outPath = path.join(outDir, `${req.params.id}-${Date.now()}.pptx`)
      __setNextSavePath(outPath)
      const result = (await __invokeIpc('export:pptx', {
        sessionId: req.params.id,
        embedFonts: req.body?.embedFonts !== false,
        imageOnly: req.body?.imageOnly === true
      })) as { success?: boolean; filePath?: string; warnings?: string[] }
      const filePath = result?.filePath || outPath
      if (!fs.existsSync(filePath)) {
        throw new Error(`Export không tạo ra file (${JSON.stringify(result)})`)
      }
      res.download(filePath, path.basename(filePath))
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Xuất PDF
  app.post('/sessions/:id/export/pdf', async (req, res) => {
    try {
      const outDir = path.join(dataDirOf(), 'exports')
      fs.mkdirSync(outDir, { recursive: true })
      const outPath = path.join(outDir, `${req.params.id}-${Date.now()}.pdf`)
      __setNextSavePath(outPath)
      const result = (await __invokeIpc('export:pdf', { sessionId: req.params.id })) as {
        path?: string
        filePath?: string
      }
      const filePath = result?.filePath || result?.path || outPath
      if (!fs.existsSync(filePath)) throw new Error(`Export PDF thất bại (${JSON.stringify(result)})`)
      res.download(filePath, path.basename(filePath))
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  // Xuất PNG → gom thư mục ảnh thành 1 file .zip trả về
  app.post('/sessions/:id/export/png', async (req, res) => {
    try {
      const parent = path.join(dataDirOf(), 'exports')
      fs.mkdirSync(parent, { recursive: true })
      __setNextOpenDir(parent)
      const result = (await __invokeIpc('export:png', { sessionId: req.params.id })) as {
        path?: string
        directoryPath?: string
      }
      const dir = result?.directoryPath || result?.path
      if (!dir || !fs.existsSync(dir)) throw new Error(`Export PNG thất bại (${JSON.stringify(result)})`)
      const files: Record<string, Uint8Array> = {}
      for (const name of fs.readdirSync(dir)) {
        const fp = path.join(dir, name)
        if (fs.statSync(fp).isFile()) files[name] = new Uint8Array(fs.readFileSync(fp))
      }
      const zip = zipSync(files)
      res.setHeader('Content-Type', 'application/zip')
      res.setHeader('Content-Disposition', `attachment; filename="slides-${req.params.id}.zip"`)
      res.end(Buffer.from(zip))
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : String(error) })
    }
  })

  app.listen(PORT, () => {
    log.info(`[server] slide-engine chạy tại http://localhost:${PORT}`)
  })
}

/**
 * Deep-rewrite URL nội bộ Electron → HTTP route browser dùng được:
 *  file:///E:/x/y.html  → /fs/E:/x/y.html   (iframe preview, asset)
 *  local-asset://<path> → /fs/<path>
 */
function rewriteLocalUrls<T>(value: T): T {
  if (typeof value === 'string') {
    let out: string = value
    if (out.includes('file://')) {
      out = out.replace(/file:\/\/\/?/g, '/fs/')
    }
    if (out.includes('local-asset://')) {
      out = out.replace(/local-asset:\/\//g, '/fs/')
    }
    return out as unknown as T
  }
  if (Array.isArray(value)) return value.map((v) => rewriteLocalUrls(v)) as unknown as T
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = rewriteLocalUrls(v)
    }
    return out as unknown as T
  }
  return value
}

function dataDirOf(): string {
  return path.resolve(process.env.SLIDE_ENGINE_DATA_DIR || './data')
}

/**
 * Seed model config từ env qua channel settings:upsertModelConfig (luồng gốc).
 * Ưu tiên SLIDE_ENGINE_*; fallback OPENAI_* (trùng tên với backend/.env).
 */
async function seedModelConfigFromEnv(): Promise<void> {
  const apiKey = process.env.SLIDE_ENGINE_API_KEY || process.env.OPENAI_API_KEY || ''
  if (!apiKey) {
    log.warn('[server] chưa có API key (SLIDE_ENGINE_API_KEY/OPENAI_API_KEY) — generate sẽ lỗi tới khi cấu hình model')
    return
  }
  // Thu muc luu tru session (setting storage_path) — bat buoc truoc session:create
  const fsMod = await import('fs')
  const storageDir = path.join(dataDirOf(), 'storage')
  fsMod.mkdirSync(storageDir, { recursive: true })
  await __invokeIpc('settings:save', { storagePath: storageDir })

  const provider = process.env.SLIDE_ENGINE_MODEL_PROVIDER || 'openai'
  const model = process.env.SLIDE_ENGINE_MODEL || process.env.OPENAI_MODEL || 'gpt-4o'
  const baseUrl = process.env.SLIDE_ENGINE_BASE_URL || process.env.OPENAI_BASE_URL || ''
  const existing = (await __invokeIpc('settings:listModelConfigs')) as {
    configs?: Array<{ id: string; name: string }>
  }
  const found = existing?.configs?.find((c) => c.name === 'xnew-default')
  const saved = (await __invokeIpc('settings:upsertModelConfig', {
    id: found?.id,
    name: 'xnew-default',
    provider,
    model,
    apiKey,
    baseUrl,
    active: true
  })) as { id?: string }
  if (saved?.id) await __invokeIpc('settings:setActiveModelConfig', saved.id)
  log.info('[server] model config seeded', { provider, model, baseUrl: baseUrl || '(default)' })
}

bootstrap().catch((error) => {
  console.error('[server] bootstrap thất bại:', error)
  process.exit(1)
})
