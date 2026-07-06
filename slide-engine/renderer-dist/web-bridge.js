/**
 * web-bridge: giả lập window.electron (@electron-toolkit/preload) trong browser.
 * invoke → POST /invoke/:channel {__args}; on → SSE /events/all; getPathForFile → /upload.
 * Nhờ đó renderer React gốc của oh-my-ppt chạy nguyên vẹn ngoài Electron.
 */
;(function () {
  var listeners = new Map() // channel -> Set<fn>

  function addListener(channel, fn) {
    if (!listeners.has(channel)) listeners.set(channel, new Set())
    listeners.get(channel).add(fn)
    return function () { removeListener(channel, fn) }
  }
  function removeListener(channel, fn) {
    var set = listeners.get(channel)
    if (set) set.delete(fn)
  }
  function dispatch(channel, args) {
    var set = listeners.get(channel)
    if (!set) return
    var event = { sender: null, preventDefault: function () {} }
    set.forEach(function (fn) {
      try { fn.apply(null, [event].concat(args)) } catch (e) { console.error('[bridge]', channel, e) }
    })
  }

  // SSE: server fan mọi webContents.send({channel,args})
  function connectEvents() {
    var es = new EventSource('/events/all')
    es.onmessage = function (msg) {
      try {
        var data = JSON.parse(msg.data)
        dispatch(data.channel, data.args || [])
      } catch (e) { /* bỏ qua dòng keepalive */ }
    }
    es.onerror = function () {
      es.close()
      setTimeout(connectEvents, 2000)
    }
  }
  connectEvents()

  async function invoke(channel) {
    var args = Array.prototype.slice.call(arguments, 1)
    var res = await fetch('/invoke/' + encodeURIComponent(channel), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ __args: args })
    })
    var data = await res.json()
    if (!data.ok) throw new Error(data.error || 'invoke ' + channel + ' failed')
    return data.result
  }

  window.electron = {
    ipcRenderer: {
      invoke: invoke,
      send: function (channel) {
        var args = Array.prototype.slice.call(arguments, 1)
        fetch('/invoke/' + encodeURIComponent(channel), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ __args: args, __fireAndForget: true })
        }).catch(function () {})
      },
      on: function (channel, fn) { return addListener(channel, fn) },
      once: function (channel, fn) {
        var off = addListener(channel, function () {
          off()
          fn.apply(null, arguments)
        })
        return off
      },
      removeListener: removeListener,
      removeAllListeners: function (channel) { listeners.delete(channel) }
    },
    process: {
      platform: 'linux',
      versions: { electron: '38.0.0-web', chrome: '120', node: '24' },
      env: {}
    },
    webFrame: {
      setZoomFactor: function () {},
      setZoomLevel: function () {},
      insertCSS: function () {}
    },
    webUtils: {
      getPathForFile: uploadForPath
    },
    getPathForFile: uploadForPath
  }

  /** Browser không có path local → upload lên server, trả path phía server. */
  function uploadForPath(file) {
    // Đồng bộ không thể — trả Promise; nơi gọi trong renderer đều await được path
    return uploadFile(file)
  }
  async function uploadFile(file) {
    var form = new FormData()
    form.append('file', file, file.name)
    var res = await fetch('/upload', { method: 'POST', body: form })
    var data = await res.json()
    if (!data.path) throw new Error(data.error || 'upload thất bại')
    return data.path
  }
})()
