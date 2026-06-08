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

// ── Types ────────────────────────────────────────────────────────────────

interface RenderConfig {
  compositionHtml: string;
  audioUrls: string[];     // backend-relative URLs e.g. "/sessions/xxx/assets/p1.wav"
  audioDurations: number[];
  totalDuration: number;
  sessionId?: string;      // optional session ID for relative assets
  fps?: number;            // default 30
  width?: number;           // default 1280
  height?: number;          // default 720
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
      width = 1280,
      height = 720,
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

    setProgress({ stage: "init", percent: 2, message: "Chuẩn bị giao diện quay màn hình..." });

    return new Promise<Blob | undefined>((resolve) => {
        let mediaRecorder: MediaRecorder | null = null;
        
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
          e.preventDefault();
          e.returnValue = "Trang web đang dựng video, nếu bạn tải lại hoặc đóng tab, quá trình sẽ bị hỏng!";
          return e.returnValue;
        };

        const handleVisibilityChange = () => {
          if (document.hidden && mediaRecorder && mediaRecorder.state === "recording") {
            alert("⚠️ CẢNH BÁO: BẠN VỪA CHUYỂN TAB HOẶC THU NHỎ TRÌNH DUYỆT!\n\nHành động này đã khiến hệ thống đồ họa bị hạ xuống 1 FPS để tiết kiệm pin. Video được quay từ giây phút này có thể bị giật lag nghiêm trọng hoặc đứng hình.\n\nSau khi video hoàn tất, vui lòng Xóa video lỗi và Bấm Render lại, VÀ giữ nguyên tab này ở trên cùng màn hình cho đến khi quay xong!");
          }
        };

        window.addEventListener("beforeunload", handleBeforeUnload);
        document.addEventListener("visibilitychange", handleVisibilityChange);
      // Create style element for glassmorphic and premium styling
      const styleEl = document.createElement("style");
      styleEl.id = "hf-render-styles";
      styleEl.textContent = `
        @keyframes hf-pulse {
          0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.4); }
          70% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(249, 115, 22, 0); }
          100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(249, 115, 22, 0); }
        }
        @keyframes hf-glow {
          0% { opacity: 0.6; }
          50% { opacity: 1; }
          100% { opacity: 0.6; }
        }
        .hf-btn-primary {
          background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
          color: white;
          border: none;
          padding: 14px 28px;
          font-size: 16px;
          font-weight: 600;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 4px 14px rgba(249, 115, 22, 0.4);
        }
        .hf-btn-primary:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 20px rgba(249, 115, 22, 0.6);
        }
        .hf-btn-secondary {
          background: rgba(255,255,255,0.08);
          color: #a1a1aa;
          border: 1px solid rgba(255,255,255,0.1);
          padding: 14px 28px;
          font-size: 16px;
          font-weight: 600;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .hf-btn-secondary:hover {
          background: rgba(255,255,255,0.15);
          color: white;
        }
        .hf-card {
          background: rgba(18, 18, 24, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.1);
          backdrop-filter: blur(25px);
          padding: 40px;
          border-radius: 20px;
          width: 90%;
          max-width: 520px;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
      `;
      document.head.appendChild(styleEl);

      const overlay = document.createElement("div");
      overlay.id = "hf-render-overlay";
      overlay.style.cssText = `
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: #09090b;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-family: system-ui, -apple-system, sans-serif;
        color: #f4f4f5;
        overflow: hidden;
      `;
      document.body.appendChild(overlay);

      // Render the instruction card inside overlay
      overlay.innerHTML = `
        <div class="hf-card">
          <h2 style="font-size: 24px; font-weight: 700; margin-top: 0; margin-bottom: 12px; background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Dựng Video AI Tốc Độ Cao
          </h2>
          <p style="font-size: 15px; color: #a1a1aa; line-height: 1.6; margin-bottom: 24px; text-align: left;">
            Để đạt hiệu năng tối đa và giữ nguyên 100% hiệu ứng chuyển cảnh, hệ thống sẽ phát trực tiếp hoạt ảnh và âm thanh rồi tự động ghi lại.
          </p>
          
          <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); padding: 12px 16px; border-radius: 8px; margin-bottom: 24px; text-align: left;">
            <strong style="color: #f87171; display: block; margin-bottom: 4px;">⚠️ LƯU Ý QUAN TRỌNG:</strong>
            <span style="color: #fca5a5; font-size: 14px; line-height: 1.5;">
              KHÔNG ĐƯỢC ĐỔI TAB hoặc THU NHỎ TRÌNH DUYỆT trong lúc đang chạy! Việc đổi tab sẽ làm Chrome tự động tắt đồ họa (giảm xuống 1 FPS) khiến video thu được bị giật lag và mất hình.
            </span>
          </div>

          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin-bottom: 30px; font-size: 14px; line-height: 1.7; text-align: left; width: 100%; box-sizing: border-box;">
            <div style="margin-bottom: 12px; display: flex; align-items: flex-start;">
              <span style="background: #f97316; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 12px; flex-shrink: 0; font-weight: bold; margin-top: 2px;">1</span>
              <div>Click <strong>"Bắt đầu ghi hình"</strong> bên dưới.</div>
            </div>
            <div style="margin-bottom: 12px; display: flex; align-items: flex-start;">
              <span style="background: #f97316; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 12px; flex-shrink: 0; font-weight: bold; margin-top: 2px;">2</span>
              <div>Chọn tab <strong>"DailyByte - Dựng Video AI"</strong> (hoặc tab hiện tại).</div>
            </div>
            <div style="display: flex; align-items: flex-start;">
              <span style="background: #f97316; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 12px; flex-shrink: 0; font-weight: bold; margin-top: 2px;">3</span>
              <div><strong>BẮT BUỘC:</strong> Tích chọn <strong>"Chia sẻ âm thanh của tab"</strong> (Also share tab audio) ở góc dưới bên trái của hộp thoại.</div>
            </div>
          </div>

          <div style="display: flex; gap: 16px; width: 100%; justify-content: center;">
            <button id="btn-cancel" class="hf-btn-secondary" style="flex: 1;">Hủy bỏ</button>
            <button id="btn-start" class="hf-btn-primary" style="flex: 1;">Bắt đầu ghi hình</button>
          </div>
        </div>
      `;

      const cleanupAll = () => {
        document.getElementById("btn-start")?.removeEventListener("click", () => {});
        document.getElementById("btn-cancel")?.removeEventListener("click", handleCancel);
        window.removeEventListener("beforeunload", handleBeforeUnload);
        document.removeEventListener("visibilitychange", handleVisibilityChange);
        try { document.getElementById("hf-render-overlay")?.remove(); } catch {}
        try { document.getElementById("hf-render-styles")?.remove(); } catch {}
        setIsRendering(false);
      };

      const handleCancel = () => {
        cancelRef.current = true;
        cleanupAll();
        setProgress({ stage: "error", percent: 0, message: "Người dùng đã hủy bỏ quá trình ghi hình." });
        resolve(undefined);
      };

      document.getElementById("btn-cancel")?.addEventListener("click", handleCancel);

      document.getElementById("btn-start")?.addEventListener("click", async () => {
        let stream: MediaStream;
        try {
          setProgress({ stage: "init", percent: 5, message: "Đang yêu cầu quyền chia sẻ màn hình..." });
          stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              displaySurface: "browser",
              width: { ideal: width },
              height: { ideal: height },
              frameRate: { ideal: fps }
            },
            audio: {
              echoCancellation: false,
              noiseSuppression: false,
              autoGainControl: false,
              suppressLocalAudioPlayback: false
            } as any,
            preferCurrentTab: true,
          } as any);
        } catch (err) {
          console.error("getDisplayMedia blocked:", err);
          cleanupAll();
          setProgress({ stage: "error", percent: 0, message: "Không thể khởi động: Người dùng từ chối chia sẻ hoặc trình duyệt không hỗ trợ." });
          resolve(undefined);
          return;
        }

        // Verify audio stream track is present
        if (stream.getAudioTracks().length === 0) {
          stream.getTracks().forEach(t => t.stop());
          cleanupAll();
          setProgress({
            stage: "error",
            percent: 0,
            message: "Thiếu đường âm thanh! Vui lòng tích chọn ô 'Chia sẻ âm thanh của tab' ở góc dưới bên trái khi chọn Tab chia sẻ."
          });
          resolve(undefined);
          return;
        }

        // We have stream and audio!
        setProgress({ stage: "init", percent: 7, message: "Đang khởi tạo trình phát hoạt ảnh..." });

        // Prepare overlay UI for recording (hide the instruction card, show centered video)
        overlay.innerHTML = "";

        const container = document.createElement("div");
        container.id = "hf-video-container";
        container.style.cssText = `
          position: fixed;
          top: 0; left: 0;
          width: 100vw;
          height: 100vh;
          overflow: hidden;
          background: #000;
        `;
        overlay.appendChild(container);

        // Setup base tag & finalHtml for iframe
        // Also inject a scale rule so #root fills the full viewport height (no black bars)
        const vpW = window.innerWidth;
        const vpH = window.innerHeight;
        // Use height-constrained contain scale so all content is visible and fills height
        const contentScale = Math.min(vpW / width, vpH / height);
        let API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        // Convert relative API paths (like "/api-backend") to absolute URLs 
        // to prevent `blob:` iframe "Invalid URL" errors and cross-origin blocks
        if (API.startsWith("/")) {
          API = window.location.origin + API;
        }
        let finalHtml = compositionHtml;
        finalHtml = finalHtml.replace(/<base\b[^>]*>/gi, "");
        const baseHref = sessionId
          ? `${API.replace(/\/$/, "")}/sessions/${sessionId}/`
          : `${API.replace(/\/$/, "")}/`;
        const baseTag = `<base href="${baseHref}">`;
        finalHtml = finalHtml.replace(/<head\b([^>]*)>/i, `<head$1>${baseTag}`);

        // Inject CSS so #root fills the capture frame — eliminates black borders without FFmpeg crop:
        // #root is positioned absolutely at the centered offset, then scaled from top-left.
        // This avoids the original body flex-center interfering with our transform calculations.
        const rootOffX = ((vpW - width * contentScale) / 2).toFixed(2);
        const rootOffY = ((vpH - height * contentScale) / 2).toFixed(2);
        const fillCss = `
          <style id="cr-fill">
            html {
              width: ${vpW}px !important;
              height: ${vpH}px !important;
              overflow: hidden !important;
              background: #0a0518 !important;
            }
            body {
              width: ${vpW}px !important;
              height: ${vpH}px !important;
              min-height: ${vpH}px !important;
              overflow: hidden !important;
              display: block !important;
              position: relative !important;
              background: #0a0518 !important;
              margin: 0 !important; padding: 0 !important;
            }
            #root {
              position: absolute !important;
              top: ${rootOffY}px !important;
              left: ${rootOffX}px !important;
              transform-origin: top left !important;
              transform: scale(${contentScale.toFixed(6)}) !important;
              width: ${width}px !important;
              height: ${height}px !important;
            }
          </style>
        `;
        finalHtml = finalHtml.replace(/<\/head>/i, `${fillCss}</head>`);

        // Load iframe in container — sized to match viewport exactly
        const iframe = document.createElement("iframe");
        iframe.allow = "autoplay; fullscreen";
        iframe.style.cssText = `width: ${vpW}px; height: ${vpH}px; border: none; overflow: hidden; display: block;`;
        
        const blobUrl = URL.createObjectURL(new Blob([finalHtml], { type: "text/html" }));
        iframe.src = blobUrl;
        container.appendChild(iframe);

        let timeline: any = null;
        const activeTimeouts: any[] = [];

        const stopStream = () => {
          activeTimeouts.forEach(clearTimeout);
          stream.getTracks().forEach(t => t.stop());
          URL.revokeObjectURL(blobUrl);
          iframe.remove();
        };

        // Listen for track end (if user clicks "Stop sharing" button in browser UI)
        const track = stream.getVideoTracks()[0];
        track.onended = () => {
          if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
          }
        };

        iframe.onload = async () => {
          onLog?.("[DEBUG] Iframe loaded. Looking for GSAP timeline...");
          for (let i = 0; i < 100; i++) {
            if (cancelRef.current) {
              stopStream();
              cleanupAll();
              resolve(undefined);
              return;
            }
            const iframeWin = iframe.contentWindow as (Window & { __timelines?: Record<string, unknown> }) | null;
            if (iframeWin && iframeWin.__timelines) {
              const key = iframeWin.__timelines["main"] ? "main" : Object.keys(iframeWin.__timelines)[0];
              if (key) {
                timeline = iframeWin.__timelines[key];
                break;
              }
            }
            await sleep(100);
          }

          if (!timeline) {
            stopStream();
            cleanupAll();
            setProgress({ stage: "error", percent: 0, message: "Không tìm thấy timeline GSAP trong hoạt ảnh." });
            resolve(undefined);
            return;
          }

          // We have timeline! Add class for graphics optimization if styling targets body.rendering
          try {
            if (iframe.contentDocument && iframe.contentDocument.body) {
              iframe.contentDocument.body.classList.add("rendering");
            }
          } catch {}

          // After stream starts, Chrome shows a share banner that shrinks the viewport.
          // Wait a moment for layout to stabilize before computing crop.
          await sleep(300);

          const currentViewportW = window.innerWidth;
          const currentViewportH = window.innerHeight;

          // Re-apply fill CSS with updated viewport dims if they changed (banner appeared)
          if (currentViewportW !== vpW || currentViewportH !== vpH) {
            const newScale = Math.min(currentViewportW / width, currentViewportH / height);
            const newOffX  = ((currentViewportW - width * newScale) / 2).toFixed(2);
            const newOffY  = ((currentViewportH - height * newScale) / 2).toFixed(2);
            const newScaleStr = newScale.toFixed(6);
            try {
              const doc = iframe.contentDocument;
              const styleEl = doc?.getElementById("cr-fill");
              if (styleEl && doc) {
                styleEl.textContent = `
                  html {
                    width: ${currentViewportW}px !important;
                    height: ${currentViewportH}px !important;
                    overflow: hidden !important;
                    background: #0a0518 !important;
                  }
                  body {
                    width: ${currentViewportW}px !important;
                    height: ${currentViewportH}px !important;
                    min-height: ${currentViewportH}px !important;
                    overflow: hidden !important;
                    display: block !important;
                    position: relative !important;
                    background: #0a0518 !important;
                    margin: 0 !important; padding: 0 !important;
                  }
                  #root {
                    position: absolute !important;
                    top: ${newOffY}px !important;
                    left: ${newOffX}px !important;
                    transform-origin: top left !important;
                    transform: scale(${newScaleStr}) !important;
                    width: ${width}px !important;
                    height: ${height}px !important;
                  }
                `;
              }
              // Also resize container and iframe
              container.style.width = currentViewportW + "px";
              container.style.height = currentViewportH + "px";
              iframe.style.width = currentViewportW + "px";
              iframe.style.height = currentViewportH + "px";
            } catch { /* cross-origin guard */ }
          }

          // Get track settings
          const activeTrack = stream.getVideoTracks()[0];
          const activeSettings = activeTrack.getSettings();
          const activeTrackW = activeSettings.width || currentViewportW;
          const activeTrackH = activeSettings.height || currentViewportH;

          // Compute content crop geometry — this is the key to eliminating black borders.
          //
          // After CSS injection, #root sits at (cssX, cssY) within the iframe/viewport,
          // scaled to (contentW × contentH). contentW/contentH is ALWAYS 16:9 by
          // construction (min-scale preserves the 1920:1080 ratio), so cropping to this
          // region and scaling to 1920×1080 is a perfect uniform scale with no padding.
          //
          // We convert CSS pixels → physical track pixels using Chrome's containment
          // factor `s`, which accounts for DPR and Chrome's resolution limits.
          const curContentScale = Math.min(currentViewportW / width, currentViewportH / height);
          const contentW = width  * curContentScale;   // CSS pixels
          const contentH = height * curContentScale;   // CSS pixels
          const cssX = (currentViewportW - contentW) / 2;
          const cssY = (currentViewportH - contentH) / 2;

          // Chrome containment: tab viewport → track, possibly upscaled/letterboxed
          const s = Math.min(activeTrackW / currentViewportW, activeTrackH / currentViewportH);
          const fitX = (activeTrackW - currentViewportW * s) / 2;
          const fitY = (activeTrackH - currentViewportH * s) / 2;

          // Crop in physical track pixels — round to even for libx264
          const cropX = Math.round(fitX + cssX * s);
          const cropY = Math.round(fitY + cssY * s);
          const rawCropW = Math.round(contentW * s);
          const rawCropH = Math.round(contentH * s);
          const cropW = rawCropW - (rawCropW % 2);
          const cropH = rawCropH - (rawCropH % 2);

          onLog?.(`[DEBUG] Viewport: ${currentViewportW}x${currentViewportH}. Track: ${activeTrackW}x${activeTrackH}. s=${s.toFixed(4)}.`);
          onLog?.(`[DEBUG] Content CSS: ${Math.round(contentW)}x${Math.round(contentH)} at (${Math.round(cssX)}, ${Math.round(cssY)}). Scale: ${curContentScale.toFixed(4)}.`);
          onLog?.(`[DEBUG] Physical crop: ${cropW}x${cropH} at (${cropX}, ${cropY}).`);

          // Configure MediaRecorder with high bitrate for 1080p quality
          let mimeType = 'video/webm;codecs=vp9,opus';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm;codecs=vp8,opus';
          }
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm';
          }

          const chunks: Blob[] = [];
          const recorder = new MediaRecorder(stream, {
            mimeType,
            videoBitsPerSecond: 8_000_000,  // 8 Mbps for high-quality 1080p
          });
          mediaRecorder = recorder; // bind to outer scope for visibility check

          recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) chunks.push(e.data);
          };

          recorder.onstop = () => {
            stopStream();
            cleanupAll();
            
            const resultBlob = new Blob(chunks, { type: mimeType });
            // Attach content crop region — backend uses this to crop the side bars
            // and scale to exactly 1920×1080 with no black borders
            (resultBlob as any).cropX = cropX;
            (resultBlob as any).cropY = cropY;
            (resultBlob as any).cropW = cropW;
            (resultBlob as any).cropH = cropH;
            
            const resultUrl = URL.createObjectURL(resultBlob);
            setMp4Blob(resultBlob);
            setMp4Url(resultUrl);
            
            setProgress({ stage: "muxing", percent: 95, message: "Đang mã hóa và chèn phụ đề..." });
            resolve(resultBlob);
          };

          // Start recording and playback!
          recorder.start();
          timeline.play(0);

          // Play all audios at their start times
          try {
            if (iframe.contentDocument) {
              const audios = Array.from(iframe.contentDocument.querySelectorAll("audio"));
              audios.forEach((audio) => {
                const startOffset = parseFloat(audio.getAttribute("data-start") || "0");
                const vol = parseFloat(audio.getAttribute("data-volume") || "1");
                audio.volume = vol;
                audio.currentTime = 0;
                
                const tId = setTimeout(() => {
                  audio.play().catch(e => console.warn("Audio playback blocked/failed:", e));
                }, startOffset * 1000);
                activeTimeouts.push(tId);
              });
            }
          } catch (e) {
            console.error("Failed to schedule audios:", e);
          }

          // Play all videos
          try {
            if (iframe.contentDocument) {
              const videos = Array.from(iframe.contentDocument.querySelectorAll("video"));
              videos.forEach((video) => {
                video.currentTime = 0;
                video.play().catch(() => {});
              });
            }
          } catch {}

          // Watch duration
          const startPlayTime = performance.now();
          const durationMs = totalDuration * 1000;

          while (performance.now() - startPlayTime < durationMs + 500) {
            if (cancelRef.current || track.readyState === "ended") {
              break;
            }
            const elapsed = performance.now() - startPlayTime;
            const pct = Math.min(90, 10 + Math.round((elapsed / durationMs) * 80));
            setProgress({
              stage: "capturing",
              percent: pct,
              message: `Đang ghi hình: ${Math.round(elapsed / 1000)}s / ${Math.round(totalDuration)}s`,
            });
            await sleep(100);
          }

          if (mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
          }
        };
      });
    });
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
    cropX?: number;
    cropY?: number;
    cropW?: number;
    cropH?: number;
    width?: number;
    height?: number;
    onProgress?: (pct: number) => void;
  }
): Promise<{ success: boolean; videoUrl: string; videoPath: string; fileSize: number }> {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const isLocal = API.includes("localhost") || API.includes("127.0.0.1");
  const endpoint = isLocal ? `${API}/upload-render` : `/api/proxy/upload-render`;

  return new Promise(async (resolve, reject) => {
    const ext = mp4Blob.type.includes("webm") ? "webm" : "mp4";
    const chunkSize = 50 * 1024 * 1024; // 50MB chunks to bypass Cloudflare 100MB limit
    const totalChunks = Math.ceil(mp4Blob.size / chunkSize);
    let uploadedBytes = 0;

    for (let i = 0; i < totalChunks; i++) {
      const chunk = mp4Blob.slice(i * chunkSize, (i + 1) * chunkSize);
      
      const formData = new FormData();
      formData.append("file", chunk, `${opts.title || "video"}.${ext}`);
      formData.append("title", opts.title);
      formData.append("session_id", opts.sessionId);
      formData.append("composition_html", opts.compositionHtml);
      formData.append("duration", String(opts.duration));
      if (opts.logs) formData.append("logs", opts.logs);
      if (opts.cropX !== undefined) formData.append("crop_x", String(opts.cropX));
      if (opts.cropY !== undefined) formData.append("crop_y", String(opts.cropY));
      if (opts.cropW !== undefined) formData.append("crop_w", String(opts.cropW));
      if (opts.cropH !== undefined) formData.append("crop_h", String(opts.cropH));
      if (opts.width !== undefined) formData.append("width", String(opts.width));
      if (opts.height !== undefined) formData.append("height", String(opts.height));
      
      formData.append("chunk_index", String(i));
      formData.append("total_chunks", String(totalChunks));

      try {
        await new Promise<void>((resChunk, rejChunk) => {
          const xhr = new XMLHttpRequest();
          xhr.open("POST", endpoint, true);

          if (opts.userEmail) {
            xhr.setRequestHeader("x-user-email", opts.userEmail);
          }

          if (opts.onProgress) {
            xhr.upload.onprogress = (e) => {
              if (e.lengthComputable) {
                // Calculate total progress including previously uploaded chunks
                const pct = Math.round(((uploadedBytes + e.loaded) / mp4Blob.size) * 100);
                opts.onProgress!(pct);
              }
            };
          }

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              uploadedBytes += chunk.size;
              if (i === totalChunks - 1) {
                try {
                  resolve(JSON.parse(xhr.responseText));
                } catch (err) {
                  reject(new Error("Invalid JSON response"));
                }
              }
              resChunk();
            } else {
              rejChunk(new Error(`Chunk ${i+1}/${totalChunks} upload failed: HTTP ${xhr.status}`));
            }
          };

          xhr.onerror = () => rejChunk(new Error("Network error during upload"));
          xhr.send(formData);
        });
      } catch (error) {
        return reject(error);
      }
    }
  });
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
