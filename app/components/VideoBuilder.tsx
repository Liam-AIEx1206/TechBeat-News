"use client";

import { useState, useRef, useEffect } from "react";
import type { ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onBack: () => void;
}

type StageKey = "composition" | "save" | "tts" | "whisper" | "render";
type StageState = "pending" | "active" | "done" | "error";

const STAGES: { key: StageKey; label: string; detail: string; icon: string }[] = [
  { key: "composition", label: "Sinh HTML",      detail: "LLM viết composition + GSAP",    icon: "🎨" },
  { key: "save",        label: "Lưu file",       detail: "Ghi index.html vào project",     icon: "💾" },
  { key: "tts",         label: "Giọng đọc",      detail: "ElevenLabs / gTTS",              icon: "🎙️" },
  { key: "whisper",     label: "Nhận dạng",      detail: "Whisper API — timestamp từng từ", icon: "🎤" },
  { key: "render",      label: "Render MP4",     detail: "Chromium + FFmpeg",              icon: "🎬" },
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
      const res = await fetch(`${API}/build-video`, {
        method: "POST", headers: { "Content-Type": "application/json" },
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
            return next.slice(-8000); // cap to avoid memory bloat
          });
        } else if (ev.type === "warning") {
          const msg = (ev.message as string) ?? "";
          setRenderLog(p => [...p, `⚠ ${msg}`]);
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
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Build thất bại");
    } finally {
      setRunning(false);
      setTotalElapsed(performance.now() - startNow);
    }
  }

  const fullVideoUrl = videoUrl ? `${API}${videoUrl}` : "";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {error && (
        <div className="fade-up px-4 py-3 rounded-xl text-sm"
          style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--red)" }}>
          ⚠ {error}
        </div>
      )}

      {/* Header card */}
      <div style={{ background: "var(--gray-1)", border: "1px solid var(--gray-3)", borderRadius: "var(--r-xl)", padding: "clamp(20px,3vw,32px)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 28 }}>
          <div>
            <div className="hero-eyebrow" style={{ marginBottom: 10 }}>
              {done ? "✓ Video sẵn sàng" : running ? "Đang dựng..." : "Chuẩn bị dựng"}
            </div>
            <h2 style={{ fontSize: "clamp(20px,2.5vw,32px)", fontWeight: 900, letterSpacing: "-0.03em", lineHeight: 1.1, marginBottom: 8 }}>
              {scenePlan.title}
            </h2>
            <p style={{ fontSize: 12, color: "var(--gray-5)" }}>
              <span style={{ color: "var(--accent2)", fontWeight: 700 }}>{scenePlan.scenes.length} phân cảnh</span>
              {actualDuration && (
                <>
                  {" · "}
                  <span style={{ color: "var(--accent2)", fontWeight: 700 }}>{actualDuration}s</span>
                </>
              )}
              {" · "}1920×1080 · 30fps
              {ttsEngine && (<>{" · "}<span style={{ color: "#67e8f9", fontWeight: 700 }}>TTS: {ttsEngine}</span></>)}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {/* Total elapsed timer */}
            {(running || done) && (
              <div style={{
                display: "flex", flexDirection: "column", alignItems: "flex-end",
                padding: "8px 14px", borderRadius: "var(--r)",
                background: done ? "rgba(34,197,94,0.08)" : "var(--gray-2)",
                border: done ? "1px solid rgba(34,197,94,0.3)" : "1px solid var(--gray-3)",
                minWidth: 110,
              }}>
                <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gray-5)" }}>Tổng thời gian</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 800, color: done ? "#22c55e" : "var(--accent)" }}>
                  {fmtMs(totalElapsed)}
                </span>
              </div>
            )}
            {!running && !done && <button onClick={onBack} className="btn-ghost">← Quay lại</button>}
            {!running && (
              <button onClick={build} className="btn-primary magnetic">
                <span>🎬 {done ? "Dựng lại" : "Bắt đầu dựng"}</span>
              </button>
            )}
            {running && (
              <button onClick={() => { abortRef.current?.abort(); setRunning(false); }} className="btn-ghost"
                style={{ borderColor: "rgba(239,68,68,0.3)", color: "var(--red)" }}>
                Huỷ
              </button>
            )}
          </div>
        </div>

        {/* Stage grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
          {STAGES.map((s, idx) => {
            const state = stageStates[s.key];
            const detail = stageDetail[s.key];
            const elapsed = stageElapsed[s.key];
            return (
              <div key={s.key} className={`stage-card ${state === "active" ? "stage-active" : state === "done" ? "stage-done" : state === "error" ? "stage-error" : ""}`}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <div style={{
                    position: "relative", width: 28, height: 28, borderRadius: "var(--r-sm)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 900, flexShrink: 0,
                    background: state === "active" ? "var(--accent)" : state === "done" ? "rgba(34,197,94,0.15)" : state === "error" ? "rgba(239,68,68,0.15)" : "var(--gray-3)",
                    color: state === "active" ? "var(--black)" : state === "done" ? "var(--green)" : state === "error" ? "var(--red)" : "var(--gray-5)",
                  }}>
                    {state === "done" ? "✓" : state === "error" ? "!" : state === "active" ? s.icon : idx + 1}
                    {state === "active" && (
                      <span style={{ position: "absolute", inset: 0, borderRadius: "var(--r-sm)", border: "1px solid var(--accent)", animation: "ping 1.2s ease-out infinite" }} />
                    )}
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 800, color: "var(--white)", flex: 1 }}>{s.label}</span>
                  {/* Per-stage timer */}
                  {elapsed > 0 && (
                    <span style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11, fontWeight: 700,
                      color: state === "active" ? "var(--accent)" : state === "done" ? "#22c55e" : "var(--gray-5)",
                    }}>
                      {fmtMs(elapsed)}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: 11, color: "var(--gray-5)", lineHeight: 1.5, minHeight: 28 }}>
                  {detail || s.detail}
                </p>
              </div>
            );
          })}
        </div>

        {/* Progress */}
        {(running || done) && stageStates.render !== "pending" && (
          <div style={{ marginTop: 20 }} className="fade-up">
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 800, marginBottom: 8 }}>
              <span style={{ textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--gray-5)" }}>Render progress</span>
              <span style={{ color: "var(--accent2)" }}>{progress}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Composition LLM stream preview */}
      {(stageStates.composition === "active" || (compStream && stageStates.composition === "done")) && compStream && (
        <div className="terminal p-4 fade-up" style={{ borderColor: "rgba(168,85,247,0.2)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ display: "flex", gap: 6 }}>
                {["#a855f7", "#fbbf24", "#22c55e"].map(c => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />)}
              </div>
              <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(168,85,247,0.65)" }}>composition.html (live stream)</span>
            </div>
            <span style={{ fontSize: 10, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
              {compChars.toLocaleString()} ký tự
            </span>
          </div>
          <pre ref={compRef} style={{
            maxHeight: 220, overflow: "auto",
            whiteSpace: "pre-wrap", wordBreak: "break-all",
            lineHeight: 1.6, fontSize: 11,
            color: "rgba(216,180,254,0.85)",
          }}>
            {compStream}
          </pre>
        </div>
      )}

      {/* Render log */}
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

      {/* Video result */}
      {done && fullVideoUrl && (
        <div style={{ background: "var(--gray-1)", border: "1px solid var(--gray-3)", borderRadius: "var(--r-xl)", padding: "clamp(20px,3vw,32px)" }} className="fade-up">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
            <div>
              <div className="hero-eyebrow" style={{ marginBottom: 8 }}>✓ Video đã render xong</div>
              <p style={{ fontSize: 15, fontWeight: 800, color: "var(--white)" }}>{scenePlan.title}.mp4</p>
              <p style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 6 }}>
                Tổng thời gian dựng: <span style={{ color: "#22c55e", fontWeight: 700, fontFamily: "var(--font-mono)" }}>{fmtMs(totalElapsed)}</span>
                {Object.entries(stageElapsed).filter(([, v]) => v > 0).map(([k, v]) => (
                  <span key={k} style={{ marginLeft: 12, color: "var(--gray-5)" }}>
                    {k}: <span style={{ color: "var(--accent2)", fontFamily: "var(--font-mono)" }}>{fmtMs(v)}</span>
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
          <video src={fullVideoUrl} controls style={{ width: "100%", borderRadius: "var(--r-lg)", background: "#000", aspectRatio: "16/9" }} />
          {videoPath && (
            <p style={{ fontSize: 10, marginTop: 12, fontFamily: "var(--font-mono)", color: "var(--gray-4)", background: "var(--gray-2)", padding: "8px 12px", borderRadius: "var(--r-sm)", wordBreak: "break-all" }}>
              📁 {videoPath}
            </p>
          )}

          {/* Build Summary */}
          {buildLog.length > 0 && (
            <div style={{ marginTop: 16, padding: "14px 18px", borderRadius: "var(--r)", background: "var(--gray-2)", border: "1px solid var(--gray-3)" }}>
              <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 10 }}>
                🛠 Build Summary — Models &amp; Tools
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {buildLog.map((line, i) => (
                  <div key={i} style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--accent2)", lineHeight: 1.5 }}>
                    {line}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <style>{`@keyframes ping { 0% { transform: scale(1); opacity: 0.8; } 100% { transform: scale(1.8); opacity: 0; } }`}</style>
    </div>
  );
}
