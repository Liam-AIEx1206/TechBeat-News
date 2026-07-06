// electron-log shim: same call surface (log.info/warn/error/debug/verbose/silly),
// backed by console — lets vendored oh-my-ppt code run outside Electron unchanged.
const format = (level, args) => [`[${level}]`, ...args]

const log = {
  info: (...args) => console.log(...format('info', args)),
  warn: (...args) => console.warn(...format('warn', args)),
  error: (...args) => console.error(...format('error', args)),
  debug: (...args) => console.debug(...format('debug', args)),
  verbose: (...args) => console.debug(...format('verbose', args)),
  silly: (...args) => console.debug(...format('silly', args)),
  log: (...args) => console.log(...args),
  scope: () => log,
  transports: { file: { level: false }, console: { level: 'info' } }
}

export default log
export const info = log.info
export const warn = log.warn
export const error = log.error
export const debug = log.debug
