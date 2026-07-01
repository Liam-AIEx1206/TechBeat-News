"use client";

import { useState, useRef, useEffect } from "react";
import type { ScenePlan } from "@/types/scene";
import { useSession } from "next-auth/react";
import { useClientRender, uploadRenderedVideo, saveErrorLog } from "./ClientRenderer";
import { Palette, Mic, AudioLines } from "lucide-react";
import { GalaxyCanvas } from "./GalaxyCanvas";

interface Props {
  scenePlan: ScenePlan;
  onBack: () => void;
}

type StageKey = "composition" | "save" | "tts" | "whisper" | "render";
type StageState = "pending" | "active" | "done" | "error";

const STAGES: { key: StageKey; label: string; detail: string }[] = [
  { key: "composition", label: "Sinh HTML",      detail: "LLM viết composition + GSAP" },
  { key: "save",        label: "Lưu file",       detail: "Ghi index.html vào project" },
  { key: "tts",         label: "Giọng đọc",      detail: "OpenAI / Edge TTS" },
  { key: "whisper",     label: "Nhận dạng",      detail: "Whisper API — timestamp từng từ" },
  { key: "render",      label: "Render MP4",     detail: "Chromium + FFmpeg" },
];

function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${m}m ${rem.toString().padStart(2, "0")}s`;
}

export function VideoBuilder({ scenePlan, onBack }: Props) {
  const { data: session } = useSession();
  const [running, setRunning]         = useState(false);
  const [done, setDone]               = useState(false);
  const [stageStates, setStageStates] = useState<Record<StageKey, StageState>>({ composition:"pending", save:"pending", tts:"pending", whisper:"pending", render:"pending" });
  const [stageDetail, setStageDetail] = useState<Record<StageKey, string>>({ composition:"", save:"", tts:"", whisper:"", render:"" });
  const [stageStart,  setStageStart]  = useState<Record<StageKey, number | null>>({ composition:null, save:null, tts:null, whisper:null, render:null });
  const [stageElapsed,setStageElapsed]= useState<Record<StageKey, number>>({ composition:0, save:0, tts:0, whisper:0, render:0 });
  const [totalStart,  setTotalStart]  = useState<number | null>(null);
  const [totalElapsed, setTotalElapsed] = useState<number>(0);
  const [renderLog, setRenderLog]     = useState<string[]>([]);
  const [compStream, setCompStream]   = useState<string>("");
  const [compChars, setCompChars]     = useState(0);
  const [videoUrl, setVideoUrl]       = useState("");
  const [videoPath, setVideoPath]     = useState("");
  const [error, setError]             = useState("");
  const [progress, setProgress]       = useState(0);
  const [ttsEngine, setTtsEngine]     = useState("");
  const [buildLog,  setBuildLog]      = useState<string[]>([]);
  const [actualDuration, setActualDuration] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const logRef   = useRef<HTMLPreElement>(null);
  const compRef  = useRef<HTMLPreElement>(null);
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const [renderMode, setRenderMode] = useState<"client" | "server">("client");
  const [supported, setSupported] = useState<boolean>(true);

  const { startRender, cancelRender, progress: clientProgress, isRendering: clientRendering } = useClientRender();

  // Detect WebCodecs capabilities
  useEffect(() => {
    import("@/lib/browserCapabilities").then(async ({ canRenderClientSide }) => {
      const isOk = await canRenderClientSide();
      setSupported(isOk);
      if (!isOk) {
        setRenderMode("server");
      }
    });
  }, []);

  // Sync client rendering progress messages and percentage to stage states
  useEffect(() => {
    if (renderMode === "client" && clientRendering) {
      setProgress(clientProgress.percent);
      if (clientProgress.message) {
        setStageDetail(p => ({ ...p, render: clientProgress.message }));
      }
    }
  }, [clientProgress, clientRendering, renderMode]);

    // Tick interval for live timer display (only while running)
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const now = performance.now();
      // Update total
      if (totalStart !== null) setTotalElapsed(now - totalStart);
      // Update active stage elapsed
      setStageElapsed(prev => {
        const next = { ...prev };
        (Object.entries(stageStart) as [StageKey, number | null][]).forEach(([k, s]) => {
          if (s !== null && stageStates[k] === "active") next[k] = now - s;
        });
        return next;
      });
    }, 100);
    return () => clearInterval(id);
  }, [running, totalStart, stageStart, stageStates]);


  function startStage(key: StageKey, message?: string) {
    const now = performance.now();
    setStageStates(p => ({ ...p, [key]: "active" }));
    setStageStart(p => ({ ...p, [key]: now }));
    if (message !== undefined) setStageDetail(p => ({ ...p, [key]: message }));
  }

  function setStateOnly(key: StageKey, state: StageState, detail?: string) {
    setStageStates(p => ({ ...p, [key]: state }));
    if (detail !== undefined) setStageDetail(p => ({ ...p, [key]: detail }));
  }

  function finishStage(key: StageKey, state: "done" | "error" | "skipped", detail?: string) {
    const now = performance.now();
    const status: StageState = state === "skipped" ? "done" : state;
    setStageStates(p => ({ ...p, [key]: status }));
    setStageStart(p => {
      const startTime = p[key];
      if (startTime !== null) {
        setStageElapsed(prev => ({ ...prev, [key]: now - startTime }));
      }
      return { ...p, [key]: null };
    });
    if (detail !== undefined) setStageDetail(p => ({ ...p, [key]: detail }));
  }

  async function build() {
    const startNow = performance.now();
    const localRenderLog: string[] = ["Bắt đầu quá trình dựng hình trên trình duyệt..."];
    let assetsData: any = null;

    setRunning(true); setDone(false); setError(""); setVideoUrl(""); setVideoPath("");
    setRenderLog([]); setCompStream(""); setCompChars(0); setProgress(0); setTtsEngine(""); setBuildLog([]);
    setActualDuration(null);
    setStageStates({ composition:"active", save:"pending", tts:"pending", whisper:"pending", render:"pending" });
    setStageDetail({ composition:"Đang gọi LLM...", save:"", tts:"", whisper:"", render:"" });
    setStageStart({ composition: startNow, save:null, tts:null, whisper:null, render:null });
    setStageElapsed({ composition:0, save:0, tts:0, whisper:0, render:0 });
    setTotalStart(startNow);
    setTotalElapsed(0);

    const abort = new AbortController(); abortRef.current = abort;
    try {
      const isLocal = API.includes("localhost") || API.includes("127.0.0.1");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session?.user?.email) {
        headers["X-User-Email"] = session.user.email;
      }

      if (renderMode === "client") {
        const endpoint = isLocal ? `${API}/build-assets` : `/api/proxy/build-assets`;
        const res = await fetch(endpoint, {
          method: "POST", headers,
          body: JSON.stringify(scenePlan), signal: abort.signal,
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `HTTP ${res.status}`);
        const reader = res.body!.getReader(); const decoder = new TextDecoder(); let buf = "";

        const handle = (ev: Record<string, unknown>) => {
          if (ev.type === "stage" && ev.stage) {
            const k = ev.stage as StageKey;
            if (k === "render") return; // don't start render stage from server events
            if (ev.status === "start") startStage(k, (ev.message as string) ?? "");
            else if (ev.status === "progress") {
              if (k === "composition" && ev.chars) {
                setCompChars(ev.chars as number);
                setStateOnly(k, "active", `${(ev.chars as number).toLocaleString()} ký tự...`);
              }
              else if (k === "tts" && ev.scene) setStateOnly(k, "active", `Phân cảnh ${ev.scene}/${ev.of}...`);
            } else if (ev.status === "done") {
              finishStage(k, "done", ev.path ? `✓ ${(ev.path as string).split(/[\\/]/).pop()}` : "✓ Hoàn tất");
              if (k === "tts") {
                if (ev.engine) setTtsEngine(ev.engine as string);
                if (ev.actualDuration) setActualDuration(ev.actualDuration as number);
              }
            }
            else if (ev.status === "skipped") finishStage(k, "skipped", "Bỏ qua");
          } else if (ev.type === "comp_chunk" && ev.text) {
            setCompStream(p => {
              const next = p + (ev.text as string);
              setTimeout(() => compRef.current?.scrollTo(0, 99999), 30);
              return next.slice(-8000);
            });
          } else if (ev.type === "assets_ready") {
            assetsData = ev;
          } else if (ev.type === "error") {
            finishStage((ev.stage as StageKey) ?? "composition", "error", (ev.message as string) ?? "Lỗi");
            throw new Error((ev.message as string) ?? "Pipeline thất bại");
          }
        };

        const processLines = (raw: string) => {
          for (const line of raw.split("\n\n")) {
            if (!line.startsWith("data: ")) continue;
            try { handle(JSON.parse(line.slice(6))); } catch { /* skip */ }
          }
        };

        while (true) {
          const { done: sd, value } = await reader.read();
          if (sd) { if (buf.trim()) processLines(buf); break; }
          buf += decoder.decode(value, { stream: true });
          const split = buf.split("\n\n"); buf = split.pop() ?? "";
          processLines(split.join("\n\n") + "\n\n");
        }

        if (abort.signal.aborted) return;
        if (!assetsData) throw new Error("Không nhận được dữ liệu assets từ server");

        // Bắt đầu render trên Client
        startStage("render", "Đang dựng video trên trình duyệt...");
        
        const blob = await startRender({
          compositionHtml: assetsData.compositionHtml,
          audioUrls: assetsData.audioUrls,
          audioDurations: assetsData.audioDurations,
          totalDuration: assetsData.totalDuration,
          sessionId: assetsData.sessionId,
          fps: 30,
          width: 1920,
          height: 1080,
          onLog: (msg) => {
            localRenderLog.push(msg);
            setRenderLog(p => {
              const next = [...p.slice(-100), msg];
              setTimeout(() => logRef.current?.scrollTo(0, 99999), 50);
              return next;
            });
          }
        });

        if (!blob) throw new Error("Dựng video trên trình duyệt thất bại");
        if (abort.signal.aborted) return;

        // Upload video lên server
        setStateOnly("render", "active", "Đang tải video lên server để lưu lịch sử...");
        const logsText = [
          "=== BACKEND BUILD LOGS ===",
          ...(assetsData?.buildLog || []),
          "",
          "=== CLIENT RENDER LOGS ===",
          ...localRenderLog,
        ].join("\n");
        const uploadRes = await uploadRenderedVideo(blob, {
          title: scenePlan.title,
          sessionId: assetsData.sessionId,
          compositionHtml: assetsData.compositionHtml,
          duration: assetsData.totalDuration,
          userEmail: session?.user?.email ?? undefined,
          logs: logsText,
          cropX: (blob as any).cropX,
          cropY: (blob as any).cropY,
          cropW: (blob as any).cropW,
          cropH: (blob as any).cropH,
          width: 1920,
          height: 1080,
          onProgress: (pct) => {
            if (pct < 100) {
              setStateOnly("render", "active", `Đang tải video lên server (${pct}%)...`);
              setProgress(95 + (pct * 0.04));
            } else {
              setStateOnly("render", "active", "Đang xử lý phụ đề và mã hóa H.264...");
              setProgress(99);
            }
          }
        });

        if (!uploadRes.success) throw new Error("Lưu video trên server thất bại");

        finishStage("render", "done", `✓ Hoàn tất (${uploadRes.fileSize} MB)`);
        setProgress(100);
        if (uploadRes.videoUrl) setVideoUrl(uploadRes.videoUrl);
        if (uploadRes.videoPath) setVideoPath(uploadRes.videoPath);
        if (assetsData.buildLog) setBuildLog(assetsData.buildLog);
        setDone(true);
        setTotalElapsed(performance.now() - startNow);

      } else {
        // Server mode (Original)
        const endpoint = isLocal ? `${API}/build-video` : `/api/proxy/build-video`;
        const res = await fetch(endpoint, {
          method: "POST", headers,
          body: JSON.stringify(scenePlan), signal: abort.signal,
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `HTTP ${res.status}`);
        const reader = res.body!.getReader(); const decoder = new TextDecoder(); let buf = "";

        const handle = (ev: Record<string, unknown>) => {
          if (ev.type === "stage" && ev.stage) {
            const k = ev.stage as StageKey;
            if (ev.status === "start") startStage(k, (ev.message as string) ?? "");
            else if (ev.status === "progress") {
              if (k === "composition" && ev.chars) {
                setCompChars(ev.chars as number);
                setStateOnly(k, "active", `${(ev.chars as number).toLocaleString()} ký tự...`);
              }
              else if (k === "tts" && ev.scene) setStateOnly(k, "active", `Phân cảnh ${ev.scene}/${ev.of}...`);
            } else if (ev.status === "log" && ev.line) {
              setRenderLog(p => { const n = [...p.slice(-100), ev.line as string]; setTimeout(() => logRef.current?.scrollTo(0, 99999), 50); return n; });
              const m = (ev.line as string).match(/(\d+)%/); if (m) setProgress(parseInt(m[1], 10));
            } else if (ev.status === "done") {
              finishStage(k, "done", ev.path ? `✓ ${(ev.path as string).split(/[\\/]/).pop()}` : "✓ Hoàn tất");
              if (k === "tts") {
                if (ev.engine) setTtsEngine(ev.engine as string);
                if (ev.actualDuration) setActualDuration(ev.actualDuration as number);
              }
            }
            else if (ev.status === "skipped") finishStage(k, "skipped", "Bỏ qua");
          } else if (ev.type === "comp_chunk" && ev.text) {
            setCompStream(p => {
              const next = p + (ev.text as string);
              setTimeout(() => compRef.current?.scrollTo(0, 99999), 30);
              return next.slice(-8000);
            });
          } else if (ev.type === "queue") {
            const msg = (ev.message as string) ?? "Đang chờ hàng đợi render...";
            setStateOnly("render", "active", msg);
            setRenderLog(p => [...p, msg]);
          } else if (ev.type === "warning") {
            const msg = (ev.message as string) ?? "";
            setRenderLog(p => [...p, `Lỗi: ${msg}`]);
            setStateOnly("composition", "active", msg.slice(0, 80));
          } else if (ev.type === "done") {
            finishStage("render", "done", "✓ Hoàn tất");
            setProgress(100);
            if (ev.videoUrl) setVideoUrl(ev.videoUrl as string);
            if (ev.videoPath) setVideoPath(ev.videoPath as string);
            if (ev.buildLog) setBuildLog(ev.buildLog as string[]);
            setDone(true);
            setTotalElapsed(performance.now() - startNow);
          } else if (ev.type === "error") {
            finishStage((ev.stage as StageKey) ?? "composition", "error", (ev.message as string) ?? "Lỗi");
            if (ev.log) setRenderLog(p => [...p, "── error ──", ev.log as string]);
            throw new Error((ev.message as string) ?? "Pipeline thất bại");
          }
        };

        const processLines = (raw: string) => {
          for (const line of raw.split("\n\n")) {
            if (!line.startsWith("data: ")) continue;
            try { handle(JSON.parse(line.slice(6))); } catch { /* skip */ }
          }
        };

        while (true) {
          const { done: sd, value } = await reader.read();
          if (sd) { if (buf.trim()) processLines(buf); break; }
          buf += decoder.decode(value, { stream: true });
          const split = buf.split("\n\n"); buf = split.pop() ?? "";
          processLines(split.join("\n\n") + "\n\n");
        }
      }
    } catch (err) {
      if (abort.signal.aborted) return;
      const errMsg = err instanceof Error ? err.message : "Build thất bại";
      setError(errMsg);
      setStateOnly("render", "error", errMsg);

      // Save error log to server
      try {
        const logsText = [
          "=== BACKEND BUILD LOGS ===",
          ...(assetsData?.buildLog || []),
          "",
          "=== CLIENT RENDER LOGS ===",
          ...localRenderLog,
        ].join("\n");

        await saveErrorLog({
          title: scenePlan.title,
          sessionId: (assetsData && assetsData.sessionId) || scenePlan.sessionId || "",
          error: errMsg,
          logs: logsText,
          duration: (assetsData && assetsData.totalDuration) || scenePlan.totalDuration || 0,
          userEmail: session?.user?.email ?? undefined,
        });
      } catch (logErr) {
        console.error("Failed to save error log:", logErr);
      }
    } finally {
      setRunning(false);
      setTotalElapsed(performance.now() - startNow);
    }
  }

  const fullVideoUrl = videoUrl ? `${API}${videoUrl}` : "";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Error banner */}
      {error && (
        <div style={{ padding: "12px 18px", borderRadius: 14, background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--red)", fontSize: 13 }}>
          Lỗi: {error}
        </div>
      )}

      {/* ── Main build panel ── */}
      <div style={{
        background: "linear-gradient(180deg, rgba(20,15,11,0.72) 0%, rgba(10,8,6,0.82) 100%)",
        border: `1px solid ${done ? "rgba(34,197,94,0.35)" : "rgba(249,115,22,0.32)"}`,
        borderRadius: 28,
        overflow: "hidden",
        position: "relative",
        boxShadow: done
          ? "0 0 0 1px rgba(34,197,94,0.08), 0 24px 60px -24px rgba(34,197,94,0.35), inset 0 1px 0 rgba(255,255,255,0.05)"
          : running
          ? "0 0 0 1px rgba(249,115,22,0.12), 0 24px 70px -20px rgba(249,115,22,0.5), inset 0 1px 0 rgba(255,255,255,0.06)"
          : "0 0 0 1px rgba(249,115,22,0.06), 0 20px 60px -28px rgba(249,115,22,0.28), inset 0 1px 0 rgba(255,255,255,0.05)",
        transition: "border-color 1.2s ease, box-shadow 1.2s ease",
      }}>
        {/* Top ambient glow — shifts color by state */}
        <div style={{
          position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)",
          width: 800, height: 280, pointerEvents: "none", zIndex: 0,
          background: running
            ? "radial-gradient(ellipse at top, rgba(249,115,22,0.22) 0%, transparent 65%)"
            : done
            ? "radial-gradient(ellipse at top, rgba(34,197,94,0.14) 0%, transparent 65%)"
            : "radial-gradient(ellipse at top, rgba(249,115,22,0.12) 0%, transparent 65%)",
          transition: "background 1.2s ease",
        }} />

        {/* ── Header ── */}
        <div style={{ padding: "36px 44px 32px", position: "relative", zIndex: 1 }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 32, flexWrap: "wrap" }}>

            {/* Left: status + title + meta */}
            <div style={{ flex: 1, minWidth: 0 }}>
              {/* Status pill */}
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8, marginBottom: 20,
                padding: "5px 14px", borderRadius: 99,
                background: running ? "rgba(249,115,22,0.1)" : done ? "rgba(34,197,94,0.1)" : "rgba(255,255,255,0.05)",
                border: `1px solid ${running ? "rgba(249,115,22,0.28)" : done ? "rgba(34,197,94,0.28)" : "rgba(255,255,255,0.1)"}`,
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
                  background: running ? "#f97316" : done ? "#22c55e" : "var(--gray-4)",
                  boxShadow: running ? "0 0 8px rgba(249,115,22,0.8)" : done ? "0 0 8px rgba(34,197,94,0.8)" : "none",
                  animation: running ? "dot-blink 1.2s ease-in-out infinite" : "none",
                }} />
                <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", color: running ? "var(--accent)" : done ? "#22c55e" : "var(--gray-5)" }}>
                  {done ? "Video sẵn sàng" : running ? "Đang dựng..." : "Chuẩn bị dựng"}
                </span>
              </div>

              <h2 style={{
                fontSize: "clamp(22px, 2.8vw, 40px)", fontWeight: 900,
                letterSpacing: "-0.035em", lineHeight: 1.06, color: "var(--white)", marginBottom: 18,
                display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
              }}>
                {scenePlan.title}
              </h2>

              {/* Metadata pills */}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {[
                  { label: `${scenePlan.scenes.length} phân cảnh`, cyan: false },
                  { label: renderMode === "client" ? "1280×720" : "1920×1080", cyan: false },
                  { label: "30fps", cyan: false },
                  ...(ttsEngine ? [{ label: `TTS · ${ttsEngine}`, cyan: true }] : []),
                ].map((p, i) => (
                  <span key={i} style={{
                    fontSize: 11, fontWeight: 700, padding: "4px 11px", borderRadius: 99,
                    border: `1px solid ${p.cyan ? "rgba(103,232,249,0.25)" : "rgba(255,255,255,0.1)"}`,
                    color: p.cyan ? "#67e8f9" : "var(--gray-5)",
                    background: p.cyan ? "rgba(103,232,249,0.05)" : "transparent",
                  }}>{p.label}</span>
                ))}
              </div>
            </div>

            {/* Right: big timer + controls */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 16, flexShrink: 0 }}>
              {(running || done) && (
                <div style={{
                  textAlign: "right", padding: "18px 24px", borderRadius: 18,
                  background: done ? "rgba(34,197,94,0.07)" : "rgba(249,115,22,0.07)",
                  border: `1px solid ${done ? "rgba(34,197,94,0.2)" : "rgba(249,115,22,0.15)"}`,
                }}>
                  <div style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 8 }}>Elapsed</div>
                  <div style={{
                    fontFamily: "var(--font-mono)", fontSize: 34, fontWeight: 800, lineHeight: 1, letterSpacing: "-0.02em",
                    color: done ? "#22c55e" : "var(--accent)",
                    textShadow: done ? "0 0 24px rgba(34,197,94,0.5)" : "0 0 24px rgba(249,115,22,0.45)",
                  }}>
                    {fmtMs(totalElapsed)}
                  </div>
                </div>
              )}

              {/* Controls */}
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
                {/* Render mode toggle */}
                {!running && !done && (
                  <div style={{
                    display: "flex", background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 99, padding: 3, gap: 3,
                  }}>
                    <button onClick={() => setRenderMode("client")} disabled={!supported}
                      style={{
                        padding: "7px 15px", borderRadius: 99, fontSize: 11, fontWeight: 800, border: "none",
                        cursor: supported ? "pointer" : "not-allowed",
                        background: renderMode === "client" ? "var(--accent)" : "transparent",
                        color: renderMode === "client" ? "#000" : supported ? "var(--gray-5)" : "var(--gray-3)",
                        transition: "all 0.2s", opacity: supported ? 1 : 0.4,
                      }}
                      title={!supported ? "Trình duyệt không hỗ trợ WebCodecs" : "Render bằng WebCodecs"}
                    >Client</button>
                    <button onClick={() => setRenderMode("server")}
                      style={{
                        padding: "7px 15px", borderRadius: 99, fontSize: 11, fontWeight: 800, border: "none",
                        cursor: "pointer",
                        background: renderMode === "server" ? "var(--accent)" : "transparent",
                        color: renderMode === "server" ? "#000" : "var(--gray-5)",
                        transition: "all 0.2s",
                      }}
                      title="Render trên server VPS"
                    >☁ Server</button>
                  </div>
                )}
                {!running && !done && <button onClick={onBack} className="btn-ghost">← Quay lại</button>}
                {!running && (
                  <button onClick={build} className="btn-primary magnetic">
                    <span>{done ? "Dựng lại" : "Bắt đầu dựng"}</span>
                  </button>
                )}
                {running && (
                  <button onClick={() => {
                    if (window.confirm("Hệ thống đang dựng video. Nếu huỷ bây giờ, tiến trình sẽ dừng lại.\n\nBạn có chắc chắn muốn huỷ không?")) {
                      abortRef.current?.abort(); cancelRender(); setRunning(false);
                    }
                  }} className="btn-ghost" style={{ borderColor: "rgba(239,68,68,0.3)", color: "var(--red)" }}>
                    Huỷ
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Thin divider */}
        <div style={{ height: 1, background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 30%, rgba(255,255,255,0.07) 70%, transparent)", margin: "0 44px", position: "relative", zIndex: 1 }} />

        {/* ── Stage pipeline (horizontal, flex-based connectors) ── */}
        <div style={{ padding: "28px 44px 32px", position: "relative", zIndex: 1 }}>
          {/* Top row: icons + connectors inline */}
          <div style={{ display: "flex", alignItems: "center", marginBottom: 20 }}>
            {STAGES.map((s, idx) => {
              const state = stageStates[s.key];
              const isActive = state === "active";
              const isDone   = state === "done";
              const isError  = state === "error";
              // connector to the right of this node (not after the last)
              const nextState = idx < STAGES.length - 1 ? stageStates[STAGES[idx + 1].key] : null;
              const connectorDone = isDone && (nextState === "done" || nextState === "active");

              return (
                <div key={s.key} style={{ display: "flex", alignItems: "center", flex: idx < STAGES.length - 1 ? "1" : "0 0 auto" }}>
                  {/* Icon node */}
                  <div style={{
                    width: 52, height: 52, borderRadius: 15, flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 17, fontWeight: 900, position: "relative",
                    backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)",
                    background: isActive ? "linear-gradient(135deg, #f97316, #ea580c)"
                               : isDone ? "rgba(34,197,94,0.14)"
                               : isError ? "rgba(239,68,68,0.12)"
                               : "rgba(255,255,255,0.07)",
                    border: isActive ? "1.5px solid rgba(249,115,22,0.6)"
                           : isDone ? "1px solid rgba(34,197,94,0.35)"
                           : isError ? "1px solid rgba(239,68,68,0.25)"
                           : "1px solid rgba(255,255,255,0.14)",
                    color: isActive ? "#fff" : isDone ? "#22c55e" : isError ? "var(--red)" : "var(--gray-3)",
                    boxShadow: isActive ? "0 8px 24px -4px rgba(249,115,22,0.5)" : isDone ? "0 0 12px rgba(34,197,94,0.18)" : "0 4px 16px -6px rgba(0,0,0,0.5)",
                    transition: "all 0.35s ease",
                  }}>
                    {isDone ? (
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                        <path d="M4 10l4.5 4.5L16 6" stroke="#22c55e" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    ) : isError ? "!" : idx + 1}
                    {isActive && (
                      <span style={{
                        position: "absolute", inset: -7, borderRadius: 22,
                        border: "1.5px solid rgba(249,115,22,0.35)",
                        animation: "ping 1.5s ease-out infinite",
                      }} />
                    )}
                  </div>

                  {/* Connector line to next node */}
                  {idx < STAGES.length - 1 && (
                    <div style={{
                      flex: 1, height: 2, margin: "0 6px",
                      background: "rgba(255,255,255,0.07)",
                      borderRadius: 1, overflow: "hidden",
                    }}>
                      <div style={{
                        height: "100%",
                        width: connectorDone ? "100%" : isActive ? "50%" : "0%",
                        background: connectorDone
                          ? "linear-gradient(90deg, #22c55e, #86efac)"
                          : "linear-gradient(90deg, #f97316, #fb923c)",
                        transition: "width 0.7s ease",
                        boxShadow: (connectorDone || isActive) ? "0 0 6px rgba(249,115,22,0.4)" : "none",
                      }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Bottom row: labels aligned under each icon */}
          <div style={{ display: "flex" }}>
            {STAGES.map((s, idx) => {
              const state = stageStates[s.key];
              const detail = s.key === "render" && renderMode === "client" && !stageDetail[s.key]
                ? "Render trên trình duyệt (WebCodecs)"
                : stageDetail[s.key] || s.detail;
              const elapsed = stageElapsed[s.key];
              const isActive = state === "active";
              const isDone   = state === "done";

              return (
                <div key={s.key} style={{
                  flex: idx < STAGES.length - 1 ? "1" : "0 0 auto",
                  paddingRight: idx < STAGES.length - 1 ? 8 : 0,
                }}>
                  <div style={{
                    fontSize: 11, fontWeight: 800, marginBottom: 4,
                    color: isActive ? "var(--white)" : isDone ? "rgba(255,255,255,0.55)" : "var(--gray-4)",
                  }}>
                    {s.label}
                  </div>
                  <div style={{ fontSize: 10, color: isActive ? "rgba(251,146,60,0.9)" : "var(--gray-4)", lineHeight: 1.5, maxWidth: 120 }}>
                    {detail}
                  </div>
                  {elapsed > 0 && (
                    <div style={{
                      fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700, marginTop: 5,
                      color: isActive ? "var(--accent)" : isDone ? "#22c55e" : "var(--gray-5)",
                    }}>
                      {fmtMs(elapsed)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Render progress bar ── */}
        {(running || done) && stageStates.render !== "pending" && (
          <div style={{ padding: "0 44px 36px", position: "relative", zIndex: 1 }} className="fade-up">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gray-5)" }}>Render Progress</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 800, color: done ? "#22c55e" : "var(--accent)" }}>{progress}%</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)", position: "relative", overflow: "visible" }}>
              <div style={{
                height: "100%", borderRadius: 3,
                width: `${progress}%`,
                background: done
                  ? "linear-gradient(90deg, #16a34a, #22c55e, #4ade80)"
                  : "linear-gradient(90deg, #c2410c, #f97316, #fb923c)",
                transition: "width 0.35s ease",
                boxShadow: done ? "0 0 16px rgba(34,197,94,0.55)" : "0 0 16px rgba(249,115,22,0.65)",
                position: "relative",
              }}>
                {!done && progress > 2 && progress < 100 && (
                  <span style={{
                    position: "absolute", right: -4, top: "50%", transform: "translateY(-50%)",
                    width: 8, height: 8, borderRadius: "50%",
                    background: "#fff", boxShadow: "0 0 12px rgba(249,115,22,0.95)",
                  }} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Composition LLM stream ── */}
      {(stageStates.composition === "active" || (compStream && stageStates.composition === "done")) && compStream && (
        <div className="terminal p-4 fade-up" style={{ borderColor: "rgba(168,85,247,0.2)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ display: "flex", gap: 6 }}>
                {["#a855f7", "#fbbf24", "#22c55e"].map(c => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />)}
              </div>
              <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(168,85,247,0.65)" }}>composition.html (live stream)</span>
            </div>
            <span style={{ fontSize: 10, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>{compChars.toLocaleString()} ký tự</span>
          </div>
          <pre ref={compRef} style={{ maxHeight: 220, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all", lineHeight: 1.6, fontSize: 11, color: "rgba(216,180,254,0.85)" }}>
            {compStream}
          </pre>
        </div>
      )}

      {/* ── Render log ── */}
      {(running || renderLog.length > 0) && stageStates.render !== "pending" && (
        <div className="terminal p-4 fade-up">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["#ef4444","#fbbf24","#22c55e"].map(c => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />)}
            </div>
            <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(249,115,22,0.4)" }}>render log</span>
          </div>
          <pre ref={logRef} style={{ maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap", lineHeight: 1.7, fontSize: 11 }}>
            {renderLog.length > 0 ? renderLog.join("\n") : "Đang khởi động Chromium..."}
          </pre>
        </div>
      )}

      {/* ── Video result ── */}
      {done && fullVideoUrl && (
        <div style={{
          background: "linear-gradient(180deg, rgba(11,18,13,0.72) 0%, rgba(6,10,7,0.82) 100%)",
          border: "1px solid rgba(34,197,94,0.35)",
          borderRadius: 28, overflow: "hidden", position: "relative",
          boxShadow: "0 0 0 1px rgba(34,197,94,0.08), 0 24px 60px -24px rgba(34,197,94,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
        }} className="fade-up">
          <GalaxyCanvas accentHue={140} starCount={110} nebulaOpacity={0.12} />
          {/* Green glow top */}
          <div style={{
            position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)",
            width: 600, height: 180, pointerEvents: "none", zIndex: 0,
            background: "radial-gradient(ellipse at top, rgba(34,197,94,0.14) 0%, transparent 65%)",
          }} />

          <div style={{ padding: "32px 40px", position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 20, marginBottom: 24 }}>
              <div>
                <div style={{
                  display: "inline-flex", alignItems: "center", gap: 8, marginBottom: 14,
                  padding: "5px 14px", borderRadius: 99,
                  background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.28)",
                }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", boxShadow: "0 0 8px rgba(34,197,94,0.8)" }} />
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", color: "#22c55e" }}>Video đã render xong</span>
                </div>
                <p style={{ fontSize: 17, fontWeight: 900, color: "var(--white)", letterSpacing: "-0.02em", marginBottom: 10 }}>
                  {scenePlan.title}<span style={{ color: "var(--gray-5)", fontWeight: 500 }}>.mp4</span>
                </p>
                <p style={{ fontSize: 11, color: "var(--gray-5)" }}>
                  Tổng thời gian: <span style={{ color: "#22c55e", fontWeight: 700, fontFamily: "var(--font-mono)" }}>{fmtMs(totalElapsed)}</span>
                  {Object.entries(stageElapsed).filter(([, v]) => v > 0).map(([k, v]) => (
                    <span key={k} style={{ marginLeft: 12 }}>
                      {k}: <span style={{ color: "var(--accent2)", fontFamily: "var(--font-mono)", fontWeight: 700 }}>{fmtMs(v)}</span>
                    </span>
                  ))}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <a href={fullVideoUrl} download className="btn-ghost" style={{ fontSize: 12 }}>⬇ Tải xuống</a>
                <a href={fullVideoUrl} target="_blank" rel="noreferrer" className="btn-primary" style={{ fontSize: 12 }}>
                  <span>↗ Mở tab mới</span>
                </a>
              </div>
            </div>

            <video src={fullVideoUrl} controls style={{ width: "100%", borderRadius: 16, background: "#000", aspectRatio: "16/9" }} />

            {videoPath && (
              <p style={{ fontSize: 10, marginTop: 14, fontFamily: "var(--font-mono)", color: "var(--gray-4)", background: "rgba(255,255,255,0.03)", padding: "8px 14px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.06)", wordBreak: "break-all" }}>
                {videoPath}
              </p>
            )}

            {buildLog.length > 0 && (
              <div style={{ marginTop: 16, padding: "14px 18px", borderRadius: 12, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 10 }}>Build Summary — Models & Tools</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {buildLog.map((line, i) => {
                    let icon = null;
                    let text = line;
                    if (line.startsWith("🎨 ")) { icon = <Palette size={14} style={{ display: "inline-block", marginRight: 6, verticalAlign: "-3px" }} />; text = line.replace("🎨 ", ""); }
                    else if (line.startsWith("🎙️ ")) { icon = <Mic size={14} style={{ display: "inline-block", marginRight: 6, verticalAlign: "-3px" }} />; text = line.replace("🎙️ ", ""); }
                    else if (line.startsWith("🎤 ")) { icon = <AudioLines size={14} style={{ display: "inline-block", marginRight: 6, verticalAlign: "-3px" }} />; text = line.replace("🎤 ", ""); }
                    return (
                      <div key={i} style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--accent2)", lineHeight: 1.5 }}>
                        {icon}{text}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        @keyframes ping {
          0%   { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
