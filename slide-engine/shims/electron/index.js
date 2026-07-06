/**
 * Electron shim cho slide-engine.
 *
 * Mục tiêu: code main-process của oh-my-ppt (vendor/main) chạy NGUYÊN VẸN trên
 * Node server. Shim tái hiện đúng phần API surface được dùng:
 *  - ipcMain.handle(...)  → registry; HTTP layer gọi qua __invokeIpc(channel, payload)
 *  - webContents.send(...) → phát lên __electronShimBus (HTTP layer nối vào SSE)
 *  - app.getPath('userData') → SLIDE_ENGINE_DATA_DIR (mặc định ./data)
 *  - dialog.showSaveDialog → trả path do HTTP layer đặt trước (__setNextSavePath)
 *  - safeStorage.isEncryptionAvailable() → false (code gốc tự fallback plaintext)
 *  - BrowserWindow/Menu/Tray/protocol/shell/screen → stub vô hại
 */
import { EventEmitter } from 'events'
import path from 'path'
import fs from 'fs'
import os from 'os'

// ── Event bus: mọi webContents.send đổ về đây ────────────────────────────────
export const __electronShimBus = new EventEmitter()
__electronShimBus.setMaxListeners(200)

// ── app ──────────────────────────────────────────────────────────────────────
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
  getVersion() {
    return process.env.SLIDE_ENGINE_VERSION || '0.1.0'
  }
  getName() {
    return 'slide-engine'
  }
  getAppPath() {
    return process.cwd()
  }
  getLocale() {
    return process.env.SLIDE_ENGINE_LOCALE || 'en-US'
  }
  setAppUserModelId() {}
  whenReady() {
    return Promise.resolve()
  }
  requestSingleInstanceLock() {
    return true
  }
  quit() {}
  exit() {}
  relaunch() {}
  setLoginItemSettings() {}
  dock = { hide() {}, show() {} }
}
export const app = new AppShim()

// ── ipcMain: registry + __invokeIpc cho HTTP layer ──────────────────────────
const ipcHandlers = new Map()
const ipcListeners = new EventEmitter()

export const ipcMain = {
  handle(channel, handler) {
    ipcHandlers.set(channel, handler)
  },
  handleOnce(channel, handler) {
    ipcHandlers.set(channel, async (...args) => {
      ipcHandlers.delete(channel)
      return handler(...args)
    })
  },
  removeHandler(channel) {
    ipcHandlers.delete(channel)
  },
  on(channel, listener) {
    ipcListeners.on(channel, listener)
    return this
  },
  once(channel, listener) {
    ipcListeners.once(channel, listener)
    return this
  },
  removeListener(channel, listener) {
    ipcListeners.removeListener(channel, listener)
    return this
  },
  removeAllListeners(channel) {
    ipcListeners.removeAllListeners(channel)
    return this
  }
}

/** HTTP layer gọi channel như renderer gọi ipcRenderer.invoke. */
export async function __invokeIpc(channel, ...args) {
  const handler = ipcHandlers.get(channel)
  if (!handler) throw new Error(`[electron-shim] chưa đăng ký ipc channel: ${channel}`)
  const event = createFakeInvokeEvent()
  return handler(event, ...args)
}

export function __listIpcChannels() {
  return [...ipcHandlers.keys()].sort()
}

// ── WebContents / BrowserWindow ──────────────────────────────────────────────
class WebContentsShim extends EventEmitter {
  constructor(win) {
    super()
    this._win = win
    this.session = {
      clearCache: async () => {},
      setProxy: async () => {},
      webRequest: { onBeforeRequest() {}, onHeadersReceived() {} }
    }
  }
  send(channel, ...args) {
    __electronShimBus.emit('webcontents-send', { channel, args })
    __electronShimBus.emit(channel, ...args)
  }
  setZoomFactor() {}
  getZoomFactor() {
    return 1
  }
  setWindowOpenHandler() {}
  setBackgroundThrottling() {}
  async executeJavaScript() {
    throw new Error(
      '[electron-shim] executeJavaScript không hỗ trợ — render HTML dùng Playwright (đã thay renderer.ts)'
    )
  }
  async capturePage() {
    throw new Error('[electron-shim] capturePage không hỗ trợ — dùng Playwright renderer')
  }
  isDestroyed() {
    return this._win?._destroyed ?? false
  }
  getURL() {
    return ''
  }
  async loadURL() {}
  openDevTools() {}
  isDevToolsOpened() {
    return false
  }
}

const allWindows = new Set()

export class BrowserWindow extends EventEmitter {
  static getAllWindows() {
    return [...allWindows]
  }
  static getFocusedWindow() {
    return [...allWindows][0] || null
  }
  static fromWebContents(wc) {
    return wc?._win || null
  }
  constructor(_options = {}) {
    super()
    this._destroyed = false
    this.webContents = new WebContentsShim(this)
    allWindows.add(this)
  }
  async loadURL() {}
  async loadFile() {}
  show() {}
  hide() {}
  focus() {}
  close() {
    this.destroy()
  }
  destroy() {
    if (this._destroyed) return
    this._destroyed = true
    allWindows.delete(this)
    this.emit('closed')
  }
  isDestroyed() {
    return this._destroyed
  }
  isMinimized() {
    return false
  }
  isVisible() {
    return true
  }
  restore() {}
  maximize() {}
  unmaximize() {}
  isMaximized() {
    return false
  }
  setContentSize() {}
  getContentSize() {
    return [1600, 900]
  }
  getBounds() {
    return { x: 0, y: 0, width: 1600, height: 900 }
  }
  setBounds() {}
  setMenu() {}
  setMenuBarVisibility() {}
  setIcon() {}
  setTitle() {}
  getTitle() {
    return 'slide-engine'
  }
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
    reply(channel, ...args) {
      win.webContents.send(channel, ...args)
    }
  }
}

// ── dialog: save path do HTTP layer đặt trước mỗi lần export ────────────────
let nextSavePath = null
export function __setNextSavePath(filePath) {
  nextSavePath = filePath
}

export const dialog = {
  async showSaveDialog(_winOrOpts, maybeOpts) {
    const opts = maybeOpts || _winOrOpts || {}
    const filePath =
      nextSavePath || path.join(app.getPath('downloads'), path.basename(opts.defaultPath || 'output'))
    nextSavePath = null
    fs.mkdirSync(path.dirname(filePath), { recursive: true })
    return { canceled: false, filePath }
  },
  async showOpenDialog() {
    return { canceled: true, filePaths: [] }
  },
  async showMessageBox() {
    return { response: 0, checkboxChecked: false }
  },
  showErrorBox(title, content) {
    console.error('[electron-shim dialog]', title, content)
  }
}

// ── safeStorage: không mã hoá → code gốc fallback plaintext ─────────────────
export const safeStorage = {
  isEncryptionAvailable() {
    return false
  },
  encryptString(value) {
    return Buffer.from(String(value), 'utf-8')
  },
  decryptString(buffer) {
    return Buffer.from(buffer).toString('utf-8')
  }
}

// ── shell / screen / protocol / Menu / Tray / nativeImage ───────────────────
export const shell = {
  async openExternal() {},
  async openPath() {
    return ''
  },
  showItemInFolder() {},
  beep() {}
}

export const screen = {
  getPrimaryDisplay() {
    return {
      workAreaSize: { width: 1920, height: 1080 },
      size: { width: 1920, height: 1080 },
      bounds: { x: 0, y: 0, width: 1920, height: 1080 },
      workArea: { x: 0, y: 0, width: 1920, height: 1080 },
      scaleFactor: 1
    }
  },
  getAllDisplays() {
    return [this.getPrimaryDisplay()]
  },
  getCursorScreenPoint() {
    return { x: 0, y: 0 }
  }
}

export const protocol = {
  registerSchemesAsPrivileged() {},
  handle() {},
  unhandle() {},
  registerFileProtocol() {},
  unregisterProtocol() {}
}

export class Menu {
  static buildFromTemplate() {
    return new Menu()
  }
  static setApplicationMenu() {}
  static getApplicationMenu() {
    return null
  }
  append() {}
  popup() {}
  closePopup() {}
}

export class MenuItem {}

export class Tray extends EventEmitter {
  constructor() {
    super()
  }
  setToolTip() {}
  setContextMenu() {}
  setImage() {}
  destroy() {}
  isDestroyed() {
    return false
  }
  on() {
    return this
  }
}

export class Notification extends EventEmitter {
  static isSupported() {
    return false
  }
  show() {}
  close() {}
}

export const nativeImage = {
  createFromBuffer(buffer) {
    return {
      toPNG: () => buffer,
      toJPEG: () => buffer,
      toDataURL: () => `data:image/png;base64,${Buffer.from(buffer).toString('base64')}`,
      getSize: () => ({ width: 0, height: 0 }),
      isEmpty: () => !buffer || buffer.length === 0,
      resize() {
        return this
      }
    }
  },
  createFromPath() {
    return this.createFromBuffer(Buffer.alloc(0))
  },
  createEmpty() {
    return this.createFromBuffer(Buffer.alloc(0))
  }
}

export const clipboard = {
  writeText() {},
  readText() {
    return ''
  }
}

export const net = {
  async fetch(...args) {
    return globalThis.fetch(...args)
  },
  online: true
}

export const powerSaveBlocker = {
  start() {
    return 0
  },
  stop() {}
}

export const crashReporter = { start() {} }

export const session = {
  defaultSession: {
    clearCache: async () => {},
    setProxy: async () => {},
    webRequest: { onBeforeRequest() {}, onHeadersReceived() {} },
    protocol: { handle() {}, registerFileProtocol() {} }
  },
  fromPartition() {
    return this.defaultSession
  }
}

export const webContents = {
  getAllWebContents() {
    return BrowserWindow.getAllWindows().map((w) => w.webContents)
  },
  fromId() {
    return null
  }
}

export const globalShortcut = { register() { return false }, unregisterAll() {} }

export default {
  app,
  ipcMain,
  BrowserWindow,
  dialog,
  safeStorage,
  shell,
  screen,
  protocol,
  Menu,
  MenuItem,
  Tray,
  Notification,
  nativeImage,
  clipboard,
  net,
  powerSaveBlocker,
  crashReporter
}
