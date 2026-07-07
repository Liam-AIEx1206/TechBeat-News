/**
 * Electron shim cho slide-engine — chạy code main-process oh-my-ppt NGUYÊN VẸN
 * trên Node server.
 *
 *  - ipcMain.handle → registry; HTTP layer gọi __invokeIpc(channel, ...args)
 *  - webContents.send → __electronShimBus (HTTP layer nối SSE)
 *  - BrowserWindow → CHROMIUM (Playwright): loadURL/executeJavaScript/capturePage
 *    hoạt động thật → mọi pipeline capture của oh-my-ppt (PPTX/PDF/PNG/thumbnail/
 *    MP4) chạy không cần sửa. capturePage trả NativeImage giả (toPNG/toBitmap
 *    BGRA/getSize) khớp API Electron.
 *  - app.getPath('userData') → SLIDE_ENGINE_DATA_DIR ; dialog → __setNextSavePath
 *  - safeStorage → plaintext (code gốc tự fallback)
 */
import { EventEmitter } from 'events'
import path from 'path'
import fs from 'fs'
import os from 'os'
import { chromium } from 'playwright'
import { PNG } from 'pngjs'

// ── Event bus ─────────────────────────────────────────────────────────────
export const __electronShimBus = new EventEmitter()
__electronShimBus.setMaxListeners(500)

// ── app ──────────────────────────────────────────────────────────────────
const dataDir = path.resolve(process.env.SLIDE_ENGINE_DATA_DIR || './data')
fs.mkdirSync(dataDir, { recursive: true })

const pathMap = {
  userData: dataDir,
  appData: path.dirname(dataDir),
  temp: os.tmpdir(),
  home: os.homedir(),
  downloads: path.join(dataDir, 'downloads'),
  documents: path.join(dataDir, 'documents'),
  logs: path.join(dataDir, 'logs'),
  exe: process.execPath,
  desktop: path.join(os.homedir(), 'Desktop')
}

class AppShim extends EventEmitter {
  isPackaged = false
  getPath(name) {
    const resolved = pathMap[name] || path.join(dataDir, name)
    fs.mkdirSync(resolved, { recursive: true })
    return resolved
  }
  getVersion() { return process.env.SLIDE_ENGINE_VERSION || '0.1.0' }
  getName() { return 'slide-engine' }
  getAppPath() { return process.cwd() }
  getLocale() { return process.env.SLIDE_ENGINE_LOCALE || 'en-US' }
  setAppUserModelId() {}
  whenReady() { return Promise.resolve() }
  requestSingleInstanceLock() { return true }
  quit() {}
  exit() {}
  relaunch() {}
  setLoginItemSettings() {}
  on() { return this }
  dock = { hide() {}, show() {} }
}
export const app = new AppShim()

// ── ipcMain ────────────────────────────────────────────────────────────────
const ipcHandlers = new Map()
const ipcListeners = new EventEmitter()

export const ipcMain = {
  handle(channel, handler) { ipcHandlers.set(channel, handler) },
  handleOnce(channel, handler) {
    ipcHandlers.set(channel, async (...args) => { ipcHandlers.delete(channel); return handler(...args) })
  },
  removeHandler(channel) { ipcHandlers.delete(channel) },
  on(channel, listener) { ipcListeners.on(channel, listener); return this },
  once(channel, listener) { ipcListeners.once(channel, listener); return this },
  removeListener(channel, listener) { ipcListeners.removeListener(channel, listener); return this },
  removeAllListeners(channel) { ipcListeners.removeAllListeners(channel); return this }
}

export async function __invokeIpc(channel, ...args) {
  const handler = ipcHandlers.get(channel)
  if (!handler) throw new Error(`[electron-shim] chưa đăng ký ipc channel: ${channel}`)
  return handler(createFakeInvokeEvent(), ...args)
}
export function __listIpcChannels() { return [...ipcHandlers.keys()].sort() }

// ── Playwright browser (chia sẻ) ─────────────────────────────────────────────
let sharedBrowser = null
async function getBrowser() {
  if (sharedBrowser && sharedBrowser.isConnected()) return sharedBrowser
  sharedBrowser = await chromium.launch({ headless: true })
  return sharedBrowser
}
export async function __closeBrowser() {
  if (sharedBrowser) { await sharedBrowser.close().catch(() => {}); sharedBrowser = null }
}

// ── NativeImage giả từ PNG buffer ───────────────────────────────────────────
function makeNativeImage(pngBuffer) {
  let decoded = null
  const decode = () => (decoded ||= PNG.sync.read(pngBuffer))
  return {
    toPNG: () => pngBuffer,
    toJPEG: () => pngBuffer,
    toDataURL: () => `data:image/png;base64,${pngBuffer.toString('base64')}`,
    getSize: () => { const p = decode(); return { width: p.width, height: p.height } },
    isEmpty: () => !pngBuffer || pngBuffer.length === 0,
    // Electron trả BGRA; pngjs cho RGBA → hoán đổi để code pixel-check gốc đúng.
    toBitmap: () => {
      const p = decode()
      const out = Buffer.allocUnsafe(p.data.length)
      for (let i = 0; i < p.data.length; i += 4) {
        out[i] = p.data[i + 2]
        out[i + 1] = p.data[i + 1]
        out[i + 2] = p.data[i]
        out[i + 3] = p.data[i + 3]
      }
      return out
    },
    resize() { return makeNativeImage(pngBuffer) }
  }
}

// ── WebContents (Playwright-backed) ─────────────────────────────────────────
class WebContentsShim extends EventEmitter {
  constructor(win) {
    super()
    this._win = win
    this.id = win._id
    this.session = {
      clearCache: async () => {},
      setProxy: async () => {},
      webRequest: { onBeforeRequest() {}, onHeadersReceived() {} }
    }
    this._consoleHooked = false
  }

  // Gửi event lên renderer → event bus (SSE fan cho web-bridge)
  send(channel, ...args) {
    __electronShimBus.emit('webcontents-send', { channel, args })
    __electronShimBus.emit(channel, ...args)
  }

  async _ensureConsoleHook() {
    if (this._consoleHooked) return
    const page = await this._win._ensurePage()
    this._consoleHooked = true
    page.on('console', (msg) => {
      // Khớp chữ ký Electron: (event, level, message, line, sourceId)
      this.emit('console-message', { preventDefault() {} }, msg.type(), msg.text(), 0, '')
    })
  }

  on(event, listener) {
    super.on(event, listener)
    if (event === 'console-message') void this._ensureConsoleHook()
    return this
  }
  once(event, listener) {
    super.once(event, listener)
    if (event === 'console-message') void this._ensureConsoleHook()
    return this
  }

  async loadURL(url) {
    const page = await this._win._ensurePage()
    await this._ensureConsoleHook()
    await page.goto(url, { waitUntil: 'load', timeout: 60000 })
  }
  async loadFile(filePath) {
    const { pathToFileURL } = await import('url')
    return this.loadURL(pathToFileURL(filePath).toString())
  }
  async executeJavaScript(script) {
    const page = await this._win._ensurePage()
    return page.evaluate(script)
  }
  async capturePage(rect) {
    const page = await this._win._ensurePage()
    const clip = rect && typeof rect.width === 'number'
      ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
      : undefined
    const buf = await page.screenshot({ type: 'png', animations: 'disabled', clip })
    return makeNativeImage(buf)
  }
  setZoomFactor() {}
  getZoomFactor() { return 1 }
  setWindowOpenHandler() {}
  setBackgroundThrottling() {}
  async reload() { const p = this._win._page; if (p) await p.reload() }
  stop() {}
  openDevTools() {}
  isDevToolsOpened() { return false }
  isDestroyed() { return this._win._destroyed }
  getURL() { return this._win._page ? this._win._page.url() : '' }
  removeListener(event, listener) { super.removeListener(event, listener); return this }
}

const allWindows = new Set()
let winSeq = 0

export class BrowserWindow extends EventEmitter {
  static getAllWindows() { return [...allWindows] }
  static getFocusedWindow() { return [...allWindows][0] || null }
  static fromWebContents(wc) { return wc?._win || null }

  constructor(options = {}) {
    super()
    this._id = ++winSeq
    this._destroyed = false
    this._page = null
    this._pagePromise = null
    this._width = options.width || 1600
    this._height = options.height || 900
    this.webContents = new WebContentsShim(this)
    allWindows.add(this)
  }

  get id() { return this._id }

  // Lazy: tạo Playwright page khi cần render (loadURL/capture/execute)
  async _ensurePage() {
    if (this._page) return this._page
    if (!this._pagePromise) {
      this._pagePromise = (async () => {
        const browser = await getBrowser()
        const context = await browser.newContext({
          viewport: { width: this._width, height: this._height },
          deviceScaleFactor: 1
        })
        this._page = await context.newPage()
        this._context = context
        return this._page
      })()
    }
    return this._pagePromise
  }

  async loadURL(url) { return this.webContents.loadURL(url) }
  async loadFile(fp) { return this.webContents.loadFile(fp) }
  show() {}
  hide() {}
  focus() {}
  close() { this.destroy() }
  destroy() {
    if (this._destroyed) return
    this._destroyed = true
    allWindows.delete(this)
    const ctx = this._context
    if (ctx) void ctx.close().catch(() => {})
    this._page = null
    this._context = null
    this.emit('closed')
  }
  isDestroyed() { return this._destroyed }
  isMinimized() { return false }
  isVisible() { return false }
  restore() {}
  maximize() {}
  unmaximize() {}
  isMaximized() { return false }
  setContentSize(w, h) { this._width = w; this._height = h }
  getContentSize() { return [this._width, this._height] }
  getBounds() { return { x: 0, y: 0, width: this._width, height: this._height } }
  setBounds() {}
  setMenu() {}
  setMenuBarVisibility() {}
  setIcon() {}
  setTitle() {}
  getTitle() { return 'slide-engine' }
  center() {}
  setAlwaysOnTop() {}
  flashFrame() {}
}

function createFakeInvokeEvent() {
  const win = BrowserWindow.getFocusedWindow() || new BrowserWindow()
  return {
    sender: win.webContents,
    frameId: 0,
    processId: 0,
    returnValue: undefined,
    reply(channel, ...args) { win.webContents.send(channel, ...args) }
  }
}

// ── dialog ───────────────────────────────────────────────────────────────
let nextSavePath = null
let nextOpenDir = null
export function __setNextSavePath(filePath) { nextSavePath = filePath }
export function __setNextOpenDir(dirPath) { nextOpenDir = dirPath }

export const dialog = {
  async showSaveDialog(_winOrOpts, maybeOpts) {
    const opts = maybeOpts || _winOrOpts || {}
    const filePath = nextSavePath || path.join(app.getPath('downloads'), path.basename(opts.defaultPath || 'output'))
    nextSavePath = null
    fs.mkdirSync(path.dirname(filePath), { recursive: true })
    return { canceled: false, filePath }
  },
  async showOpenDialog(_winOrOpts, maybeOpts) {
    const opts = maybeOpts || _winOrOpts || {}
    const dir = nextOpenDir || path.dirname(opts.defaultPath || app.getPath('downloads'))
    nextOpenDir = null
    fs.mkdirSync(dir, { recursive: true })
    return { canceled: false, filePaths: [dir] }
  },
  async showMessageBox() { return { response: 0, checkboxChecked: false } },
  showErrorBox(title, content) { console.error('[electron-shim dialog]', title, content) }
}

// ── safeStorage / shell / screen / protocol / Menu / Tray / nativeImage ─────
export const safeStorage = {
  isEncryptionAvailable() { return false },
  encryptString(v) { return Buffer.from(String(v), 'utf-8') },
  decryptString(b) { return Buffer.from(b).toString('utf-8') }
}
export const shell = {
  async openExternal() {}, async openPath() { return '' },
  showItemInFolder() {}, beep() {}
}
export const screen = {
  getPrimaryDisplay() {
    return { workAreaSize: { width: 1920, height: 1080 }, size: { width: 1920, height: 1080 },
      bounds: { x: 0, y: 0, width: 1920, height: 1080 }, workArea: { x: 0, y: 0, width: 1920, height: 1080 }, scaleFactor: 1 }
  },
  getAllDisplays() { return [this.getPrimaryDisplay()] },
  getCursorScreenPoint() { return { x: 0, y: 0 } }
}
export const protocol = {
  registerSchemesAsPrivileged() {}, handle() {}, unhandle() {},
  registerFileProtocol() {}, unregisterProtocol() {}
}
export class Menu {
  static buildFromTemplate() { return new Menu() }
  static setApplicationMenu() {}
  static getApplicationMenu() { return null }
  append() {} popup() {} closePopup() {}
}
export class MenuItem {}
export class Tray extends EventEmitter {
  setToolTip() {} setContextMenu() {} setImage() {} destroy() {} isDestroyed() { return false }
}
export class Notification extends EventEmitter {
  static isSupported() { return false }
  show() {} close() {}
}
export const nativeImage = {
  createFromBuffer(buffer) { return makeNativeImage(buffer) },
  createFromPath(p) { try { return makeNativeImage(fs.readFileSync(p)) } catch { return makeNativeImage(Buffer.alloc(0)) } },
  createEmpty() { return makeNativeImage(Buffer.alloc(0)) }
}
export const clipboard = { writeText() {}, readText() { return '' } }
export const net = { async fetch(...a) { return globalThis.fetch(...a) }, online: true }
export const powerSaveBlocker = { start() { return 0 }, stop() {} }
export const crashReporter = { start() {} }
export const session = {
  defaultSession: {
    clearCache: async () => {}, setProxy: async () => {},
    webRequest: { onBeforeRequest() {}, onHeadersReceived() {} },
    protocol: { handle() {}, registerFileProtocol() {} }
  },
  fromPartition() { return this.defaultSession }
}
export const webContents = {
  getAllWebContents() { return BrowserWindow.getAllWindows().map((w) => w.webContents) },
  fromId() { return null }
}
export const globalShortcut = { register() { return false }, unregisterAll() {} }

export default {
  app, ipcMain, BrowserWindow, dialog, safeStorage, shell, screen, protocol,
  Menu, MenuItem, Tray, Notification, nativeImage, clipboard, net,
  powerSaveBlocker, crashReporter, session, webContents, globalShortcut
}
