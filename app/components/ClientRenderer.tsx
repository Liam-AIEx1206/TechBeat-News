"use client";

/**
 * ClientRenderer — renders a HyperFrames composition to MP4 entirely
 * in the user's browser using WebCodecs + mp4-muxer.
 *
 * Flow:
 * 1. Load composition HTML in a hidden iframe (same-origin via blob URL)
 * 2. Wait for GSAP timeline registration (window.__timelines)
 * 3. Fetch audio WAV files
 * 4. Seek timeline frame-by-frame, capture iframe to canvas
 * 5. Encode with VideoEncoder (H.264 High) + AudioEncoder (AAC)
 * 6. Mux into MP4 via mp4-muxer
 * 7. Return Blob
 */

import { useCallback, useRef, useState } from "react";
import { Muxer, ArrayBufferTarget } from "mp4-muxer";

// ── Types ────────────────────────────────────────────────────────────────

interface RenderConfig {
  compositionHtml: string;
  audioUrls: string[];     // backend-relative URLs e.g. "/sessions/xxx/assets/p1.wav"
  audioDurations: number[];
  totalDuration: number;
  sessionId?: string;      // optional session ID for relative assets
  fps?: number;            // default 30
  width?: number;           // default 1920
  height?: number;          // default 1080
  onLog?: (msg: string) => void;
}

interface RenderProgress {
  stage: "init" | "capturing" | "encoding" | "muxing" | "uploading" | "done" | "error";
  percent: number;
  message: string;
  currentFrame?: number;
  totalFrames?: number;
}

// ── Hook ─────────────────────────────────────────────────────────────────

export function useClientRender() {
  const [isRendering, setIsRendering] = useState(false);
  const [progress, originalSetProgress] = useState<RenderProgress>({
    stage: "init", percent: 0, message: "",
  });
  const [mp4Blob, setMp4Blob] = useState<Blob | null>(null);
  const [mp4Url, setMp4Url] = useState<string>("");
  const [error, setError] = useState<string>("");
  const cancelRef = useRef(false);

  const startRender = useCallback(async (config: RenderConfig) => {
    const {
      compositionHtml,
      audioUrls,
      audioDurations,
      totalDuration,
      sessionId,
      fps = 30,
      width = 1920,
      height = 1080,
      onLog,
    } = config;

    const setProgress = (p: RenderProgress) => {
      originalSetProgress(p);
      onLog?.(p.message);
    };

    cancelRef.current = false;
    setIsRendering(true);
    setMp4Blob(null);
    setMp4Url("");
    setError("");

    // ── 1. Create hidden iframes with composition ──
    setProgress({ stage: "init", percent: 2, message: "Đang tải composition HTML..." });

    const numWorkers = 2;
    const iframes: HTMLIFrameElement[] = [];

    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    // Inject base tag so relative assets load from backend sessions/sessionId/
    let finalHtml = compositionHtml;
    finalHtml = finalHtml.replace(/<base\b[^>]*>/gi, "");
    const baseHref = sessionId
      ? `${API.replace(/\/$/, "")}/sessions/${sessionId}/`
      : `${API.replace(/\/$/, "")}/`;
    const baseTag = `<base href="${baseHref}">`;
    
    // Ensure Google Fonts stylesheets are loaded with crossorigin="anonymous"
    finalHtml = finalHtml.replace(
      /(<link\b[^>]*href="https:\/\/fonts\.googleapis\.com\/css2\?[^>]*")([^>]*>)/gi,
      (match, p1, p2) => {
        if (!p1.includes("crossorigin")) {
          return `${p1} crossorigin="anonymous"${p2}`;
        }
        return match;
      }
    );
    // Also to preconnect
    finalHtml = finalHtml.replace(
      /(<link\b[^>]*href="https:\/\/fonts\.googleapis\.com"([^>]*preconnect[^>]*)>)/gi,
      (match, p1) => {
        if (!p1.includes("crossorigin")) {
          return p1.replace(">", ' crossorigin="anonymous">');
        }
        return match;
      }
    );

    finalHtml = finalHtml.replace(/<head\b([^>]*)>/i, `<head$1>${baseTag}`);

    // ── Pre-cache and inline scene images to Base64 ──
    setProgress({ stage: "init", percent: 3, message: "Đang chuyển đổi và nén ảnh sang Base64..." });
    try {
      const srcMatches = Array.from(finalHtml.matchAll(/src=["'](assets\/[^"']+)["']/g));
      const uniqueSrcs = Array.from(new Set(srcMatches.map(m => m[1])));

      onLog?.(`[DEBUG] Found unique images to inline: ${JSON.stringify(uniqueSrcs)}`);

      for (const src of uniqueSrcs) {
        if (cancelRef.current) break;
        try {
          const fullUrl = `${baseHref}${src}`;
          onLog?.(`[DEBUG] Inlining image to Base64: ${fullUrl}`);
          const resp = await fetch(fullUrl);
          if (!resp.ok) throw new Error(`HTTP status ${resp.status}`);
          const blob = await resp.blob();
          
          const reader = new FileReader();
          const base64Promise = new Promise<string>((resolve, reject) => {
            reader.onloadend = () => resolve(reader.result as string);
            reader.onerror = reject;
          });
          reader.readAsDataURL(blob);
          const base64Data = await base64Promise;
          
          finalHtml = finalHtml.replaceAll(src, base64Data);
          onLog?.(`[DEBUG] Successfully inlined: ${src}`);
        } catch (err) {
          onLog?.(`[WARNING] Failed to inline image ${src}: ${err}`);
        }
      }
    } catch (err) {
      onLog?.(`[WARNING] Image inlining pre-process error: ${err}`);
    }

    try {
      // Create all iframes in parallel
      const loadPromises = Array.from({ length: numWorkers }).map((_, idx) => {
        return new Promise<HTMLIFrameElement>((resolve, reject) => {
          const iframe = document.createElement("iframe");
          iframe.style.cssText = `
            position: fixed; top: -9999px; left: -9999px;
            width: ${width}px; height: ${height}px;
            border: none; pointer-events: none;
          `;

          const blob = new Blob([finalHtml], { type: "text/html" });
          const blobUrl = URL.createObjectURL(blob);
          
          iframe.src = blobUrl;

          const timeout = setTimeout(() => {
            onLog?.(`[DEBUG] Iframe ${idx} load timeout!`);
            reject(new Error(`Iframe ${idx} load timeout`));
          }, 30000);
          iframe.onload = () => {
            clearTimeout(timeout);
            URL.revokeObjectURL(blobUrl);
            onLog?.(`[DEBUG] Iframe ${idx} onload fired.`);
            resolve(iframe);
          };
          iframe.onerror = () => {
            clearTimeout(timeout);
            URL.revokeObjectURL(blobUrl);
            onLog?.(`[DEBUG] Iframe ${idx} onerror fired!`);
            reject(new Error(`Iframe ${idx} load failed`));
          };

          document.body.appendChild(iframe);
          iframes.push(iframe);
        });
      });

      onLog?.("[DEBUG] Awaiting loadPromises...");
      await Promise.all(loadPromises);
      onLog?.("[DEBUG] loadPromises resolved.");

      if (cancelRef.current) { cleanup(iframes); return; }

      // ── 2. Wait for GSAP timelines in parallel ──────────────────
      setProgress({ stage: "init", percent: 5, message: "Đang chờ GSAP timeline..." });

      const timelinePromises = iframes.map(async (iframe, idx) => {
        let timeline: any = null;
        onLog?.(`[DEBUG] Worker ${idx} starts checking timeline...`);
        for (let i = 0; i < 100; i++) {
          const iframeWin = iframe.contentWindow as (Window & { __timelines?: Record<string, unknown> }) | null;
          if (iframeWin) {
            const timelines = iframeWin.__timelines;
            if (timelines) {
              const key = timelines["main"] ? "main" : Object.keys(timelines)[0];
              if (key) {
                timeline = timelines[key];
                onLog?.(`[DEBUG] Worker ${idx} found timeline on iteration ${i} under key: ${key}`);
                break;
              }
            }
          }
          await sleep(100);
        }
        if (!timeline) {
          onLog?.(`[DEBUG] Worker ${idx} timeline NOT found after 100 iterations.`);
          throw new Error(`GSAP timeline không tìm thấy ở worker ${idx}`);
        }
        return { timeline };
      });

      const timelines = await Promise.all(timelinePromises);
      onLog?.("[DEBUG] All timelines resolved successfully.");

      if (cancelRef.current) { cleanup(iframes); return; }

      // ── 3. Fetch audio files ─────────────────────────────────────
      setProgress({ stage: "init", percent: 8, message: "Đang tải audio files..." });

      const isLocal = API.includes("localhost") || API.includes("127.0.0.1");

      const audioContext = new AudioContext({ sampleRate: 44100 });
      let mergedAudioBuffer: AudioBuffer | null = null;

      if (audioUrls.length > 0) {
        const audioBuffers: AudioBuffer[] = [];
        for (let i = 0; i < audioUrls.length; i++) {
          const audioUrl = isLocal
            ? `${API}${audioUrls[i]}`
            : `/api-backend${audioUrls[i]}`;
          try {
            const resp = await fetch(audioUrl);
            const arrBuf = await resp.arrayBuffer();
            const decoded = await audioContext.decodeAudioData(arrBuf);
            audioBuffers.push(decoded);
          } catch (e) {
            console.warn(`[render] Failed to fetch audio ${i}:`, e);
            const dur = audioDurations[i] || 3;
            audioBuffers.push(
              audioContext.createBuffer(1, Math.ceil(dur * 44100), 44100)
            );
          }
        }

        const totalSamples = audioBuffers.reduce((sum, b) => sum + b.length, 0);
        mergedAudioBuffer = audioContext.createBuffer(1, totalSamples, 44100);
        const channel = mergedAudioBuffer.getChannelData(0);
        let offset = 0;
        for (const buf of audioBuffers) {
          channel.set(buf.getChannelData(0), offset);
          offset += buf.length;
        }
      }

      if (cancelRef.current) { cleanup(iframes); return; }

      // ── 4. Setup encoders + muxer ────────────────────────────────
      setProgress({ stage: "init", percent: 10, message: "Đang cấu hình encoder..." });

      const totalFrames = Math.ceil(totalDuration * fps);
      const muxerTarget = new ArrayBufferTarget();

      const muxer = new Muxer({
        target: muxerTarget,
        video: {
          codec: "avc",
          width,
          height,
        },
        audio: mergedAudioBuffer ? {
          codec: "aac",
          numberOfChannels: 1,
          sampleRate: 44100,
        } : undefined,
        fastStart: "in-memory",
      });

      const videoEncoder = new VideoEncoder({
        output: (chunk, meta) => {
          muxer.addVideoChunk(chunk, meta);
        },
        error: (e) => { throw new Error(`VideoEncoder error: ${e.message}`); },
      });

      videoEncoder.configure({
        codec: "avc1.640028",
        width,
        height,
        bitrate: 8_000_000,
        framerate: fps,
        latencyMode: "quality",
        avc: { format: "avc" },
      });

      let audioEncoder: AudioEncoder | null = null;
      if (mergedAudioBuffer) {
        audioEncoder = new AudioEncoder({
          output: (chunk, meta) => {
            muxer.addAudioChunk(chunk, meta);
          },
          error: (e) => { throw new Error(`AudioEncoder error: ${e.message}`); },
        });

        audioEncoder.configure({
          codec: "mp4a.40.2",
          numberOfChannels: 1,
          sampleRate: 44100,
          bitrate: 128000,
        });
      }

      // ── 5. Parallel Frame-by-frame capture using 3 workers ─────────
      const { toCanvas, getFontEmbedCSS } = await import("html-to-image");

      let fontEmbedCSS = "";
      try {
        const firstDoc = iframes[0].contentDocument;
        if (firstDoc && firstDoc.body) {
          fontEmbedCSS = await getFontEmbedCSS(firstDoc.body);
        }
      } catch (err) {
        console.warn("[ClientRenderer] Error pre-extracting font CSS:", err);
      }

      let nextFrameToCapture = 0;
      let nextFrameToEncode = 0;
      const capturedFrames = new Map<number, ImageBitmap>();
      let workerError: Error | null = null;

      const workerPromises = iframes.map(async (iframe, workerId) => {
        try {
          const iframeDoc = iframe.contentDocument;
          if (!iframeDoc || !iframeDoc.body) throw new Error(`Cannot access iframe ${workerId} document`);

          const timeline = timelines[workerId].timeline;

          while (true) {
            if (cancelRef.current || workerError) break;

            const frameIdx = nextFrameToCapture++;
            if (frameIdx >= totalFrames) break;

            const t = frameIdx / fps;
            timeline.seek(t);

            const capturedCanvas = await toCanvas(iframeDoc.body, {
              width,
              height,
              pixelRatio: 1,
              fontEmbedCSS,
              cacheBust: false,
              style: {
                transform: 'none',
              }
            });

            const bitmap = await createImageBitmap(capturedCanvas);
            capturedFrames.set(frameIdx, bitmap);

            while (frameIdx - nextFrameToEncode > 30 && !cancelRef.current && !workerError) {
              await sleep(10);
            }
          }
        } catch (err) {
          console.error(`[ClientRenderer] Worker ${workerId} failed:`, err);
          workerError = err instanceof Error ? err : new Error(String(err));
        }
      });

      while (nextFrameToEncode < totalFrames) {
        if (cancelRef.current) {
          cleanup(iframes, videoEncoder, audioEncoder);
          return;
        }
        if (workerError) {
          throw workerError;
        }

        if (capturedFrames.has(nextFrameToEncode)) {
          const bitmap = capturedFrames.get(nextFrameToEncode)!;
          capturedFrames.delete(nextFrameToEncode);

          const t = nextFrameToEncode / fps;
          const videoFrame = new VideoFrame(bitmap, {
            timestamp: Math.round(t * 1_000_000),
            duration: Math.round(1_000_000 / fps),
          });

          const keyFrame = nextFrameToEncode % (fps * 2) === 0;
          videoEncoder.encode(videoFrame, { keyFrame });
          videoFrame.close();
          bitmap.close();

          if (nextFrameToEncode % 30 === 0 || nextFrameToEncode === totalFrames - 1) {
            const pct = 10 + Math.round((nextFrameToEncode / totalFrames) * 75);
            setProgress({
              stage: "capturing",
              percent: pct,
              message: `Đang capture frame ${nextFrameToEncode + 1}/${totalFrames} (${numWorkers} workers)`,
              currentFrame: nextFrameToEncode + 1,
              totalFrames,
            });
          }

          nextFrameToEncode++;
        } else {
          await sleep(5);
        }
      }

      await Promise.all(workerPromises);
      if (workerError) throw workerError;

      // ── 6. Encode audio ──────────────────────────────────────────
      if (audioEncoder && mergedAudioBuffer) {
        setProgress({ stage: "encoding", percent: 87, message: "Đang encode audio..." });

        const audioData = new AudioData({
          format: "f32-planar",
          sampleRate: 44100,
          numberOfFrames: mergedAudioBuffer.length,
          numberOfChannels: 1,
          timestamp: 0,
          data: mergedAudioBuffer.getChannelData(0),
        });
        audioEncoder.encode(audioData);
        audioData.close();

        await audioEncoder.flush();
        audioEncoder.close();
      }

      // ── 7. Flush + finalize ──────────────────────────────────────
      setProgress({ stage: "muxing", percent: 90, message: "Đang ghép video + audio..." });
      await videoEncoder.flush();
      videoEncoder.close();
      muxer.finalize();

      const mp4Buffer = muxerTarget.buffer;
      const resultBlob = new Blob([mp4Buffer], { type: "video/mp4" });
      const resultUrl = URL.createObjectURL(resultBlob);

      setMp4Blob(resultBlob);
      setMp4Url(resultUrl);
      setProgress({
        stage: "done",
        percent: 100,
        message: `✓ Hoàn tất — ${(resultBlob.size / (1024 * 1024)).toFixed(1)} MB`,
      });

      return resultBlob;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Render thất bại";
      console.error("[ClientRenderer]", e);
      setError(msg);
      setProgress({ stage: "error", percent: 0, message: msg });
    } finally {
      setIsRendering(false);
    }
  }, []);

  const cancelRender = useCallback(() => {
    cancelRef.current = true;
  }, []);

  return {
    isRendering,
    progress,
    mp4Blob,
    mp4Url,
    error,
    startRender,
    cancelRender,
  };
}

// ── Upload helper ──────────────────────────────────────────────────────

export async function uploadRenderedVideo(
  mp4Blob: Blob,
  opts: {
    title: string;
    sessionId: string;
    compositionHtml: string;
    duration: number;
    userEmail?: string;
    logs?: string;
    onProgress?: (pct: number) => void;
  }
): Promise<{ success: boolean; videoUrl: string; videoPath: string; fileSize: number }> {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const isLocal = API.includes("localhost") || API.includes("127.0.0.1");
  const endpoint = isLocal ? `${API}/upload-render` : `/api/proxy/upload-render`;

  const formData = new FormData();
  formData.append("file", mp4Blob, `${opts.title || "video"}.mp4`);
  formData.append("title", opts.title);
  formData.append("session_id", opts.sessionId);
  formData.append("composition_html", opts.compositionHtml);
  formData.append("duration", String(opts.duration));
  if (opts.logs) {
    formData.append("logs", opts.logs);
  }

  const headers: Record<string, string> = {};
  if (opts.userEmail) {
    headers["x-user-email"] = opts.userEmail;
  }

  const resp = await fetch(endpoint, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!resp.ok) {
    throw new Error(`Upload failed: HTTP ${resp.status}`);
  }

  return resp.json();
}

export async function saveErrorLog(opts: {
  title: string;
  sessionId: string;
  error: string;
  logs: string;
  duration: number;
  userEmail?: string;
}): Promise<{ success: boolean; logUrl: string }> {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const isLocal = API.includes("localhost") || API.includes("127.0.0.1");
  const endpoint = isLocal ? `${API}/save-error-log` : `/api/proxy/save-error-log`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (opts.userEmail) {
    headers["x-user-email"] = opts.userEmail;
  }

  const resp = await fetch(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify({
      title: opts.title,
      sessionId: opts.sessionId,
      error: opts.error,
      logs: opts.logs,
      duration: opts.duration,
    }),
  });

  if (!resp.ok) {
    throw new Error(`Failed to save error log: HTTP ${resp.status}`);
  }

  return resp.json();
}

// ── Helpers ────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function cleanup(
  iframes?: HTMLIFrameElement[],
  videoEncoder?: VideoEncoder | null,
  audioEncoder?: AudioEncoder | null,
) {
  try { iframes?.forEach(iframe => iframe.remove()); } catch {}
  try { if (videoEncoder?.state !== "closed") videoEncoder?.close(); } catch {}
  try { if (audioEncoder?.state !== "closed") audioEncoder?.close(); } catch {}
}
