"use client";

import { useState, useRef } from "react";
import type { ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onBack: () => void;
}

type StageKey = "composition" | "save" | "tts" | "render";
type StageState = "pending" | "active" | "done" | "error";

interface StageInfo {
  key: StageKey;
  label: string;
  detail: string;
  icon: string;
}

const STAGES: StageInfo[] = [
  { key: "composition", label: "Sinh HTML composition", detail: "Claude Sonnet 4.6 viết HTML + GSAP timeline", icon: "🎨" },
  { key: "save", label: "Lưu index.html", detail: "Ghi vào my-video/", icon: "💾" },
  { key: "tts", label: "Tổng hợp giọng đọc", detail: "Google TTS tiếng Việt cho mỗi scene", icon: "🎙️" },
  { key: "render", label: "Render MP4", detail: "Headless Chromium + FFmpeg, 2–3 phút", icon: "🎬" },
];

export function VideoBuilder({ scenePlan, onBack }: Props) {
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [stageStates, setStageStates] = useState<Record<StageKey, StageState>>({
    composition: "pending",
    save: "pending",
    tts: "pending",
    render: "pending",
  });
  const [stageDetail, setStageDetail] = useState<Record<StageKey, string>>({
    composition: "",
    save: "",
    tts: "",
    render: "",
  });
  const [renderLog, setRenderLog] = useState<string[]>([]);
  const [videoUrl, setVideoUrl] = useState("");
  const [videoPath, setVideoPath] = useState("");
  const [error, setError] = useState("");
  const [renderProgress, setRenderProgress] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  function setStage(key: StageKey, state: StageState, detail?: string) {
    setStageStates((prev) => ({ ...prev, [key]: state }));
    if (detail !== undefined) {
      setStageDetail((prev) => ({ ...prev, [key]: detail }));
    }
  }

  async function build() {
    setRunning(true);
    setDone(false);
    setError("");
    setVideoUrl("");
    setVideoPath("");
    setRenderLog([]);
    setRenderProgress(0);
    setStageStates({ composition: "active", save: "pending", tts: "pending", render: "pending" });
    setStageDetail({ composition: "Đang gọi LLM...", save: "", tts: "", render: "" });

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const res = await fetch(`${API}/build-video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scenePlan),
        signal: abort.signal,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      const handle = (event: {
        type: string;
        stage?: StageKey;
        status?: string;
        message?: string;
        chars?: number;
        scene?: number;
        of?: number;
        line?: string;
        path?: string;
        videoUrl?: string;
        videoPath?: string;
        log?: string;
      }) => {
        if (event.type === "stage" && event.stage) {
          const k = event.stage;
          if (event.status === "start") {
            setStage(k, "active", event.message ?? "");
          } else if (event.status === "progress") {
            if (k === "composition" && event.chars) {
              setStage(k, "active", `${event.chars.toLocaleString()} ký tự đã sinh...`);
            } else if (k === "tts" && event.scene && event.of) {
              setStage(k, "active", `Phân cảnh ${event.scene}/${event.of}...`);
            }
          } else if (event.status === "log" && event.line) {
            setRenderLog((prev) => [...prev.slice(-40), event.line!]);
            const m = event.line.match(/(\d+)%/);
            if (m) setRenderProgress(parseInt(m[1], 10));
          } else if (event.status === "done") {
            setStage(k, "done", event.path ? `Đã lưu: ${event.path.split(/[\\/]/).pop()}` : "Hoàn tất");
          } else if (event.status === "skipped") {
            setStage(k, "done", "Đã bỏ qua");
          }
        } else if (event.type === "done") {
          setStage("render", "done", "Hoàn tất");
          setRenderProgress(100);
          if (event.videoUrl) setVideoUrl(event.videoUrl);
          if (event.videoPath) setVideoPath(event.videoPath);
          setDone(true);
        } else if (event.type === "error") {
          const stage = (event.stage as StageKey) ?? "composition";
          setStage(stage, "error", event.message ?? "Lỗi");
          if (event.log) setRenderLog((prev) => [...prev, "--- error log ---", event.log!]);
          throw new Error(event.message ?? "Pipeline thất bại");
        }
      };

      const processLines = (raw: string) => {
        const lines = raw.split("\n\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            handle(JSON.parse(line.slice(6)));
          } catch {
            // skip malformed
          }
        }
      };

      while (true) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) {
          if (buf.trim()) processLines(buf);
          break;
        }
        buf += decoder.decode(value, { stream: true });
        const split = buf.split("\n\n");
        buf = split.pop() ?? "";
        processLines(split.join("\n\n") + "\n\n");
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Build thất bại");
    } finally {
      setRunning(false);
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setRunning(false);
  }

  const fullVideoUrl = videoUrl ? `${API}${videoUrl}` : "";

  return (
    <div className="space-y-5">
      {error && (
        <div className="px-5 py-4 bg-red-50/80 backdrop-blur border border-red-200 rounded-2xl text-sm text-red-700 fade-up">
          ⚠ {error}
        </div>
      )}

      <div className="glass-strong rounded-3xl p-7">
        <div className="flex items-start justify-between mb-7 flex-wrap gap-4">
          <div>
            <p className="text-[10px] font-black text-orange-700 uppercase tracking-widest mb-1.5">
              {done ? "✓ Video sẵn sàng" : running ? "Đang dựng video..." : "Chuẩn bị dựng video"}
            </p>
            <h2 className="text-2xl font-black text-stone-900 mb-1">
              {scenePlan.title}
            </h2>
            <p className="text-xs text-stone-500">
              <span className="text-orange-700 font-semibold">{scenePlan.scenes.length} phân cảnh</span> ·
              <span className="text-orange-700 font-semibold ml-1">{scenePlan.totalDuration}s</span> ·
              1920×1080 · 30fps
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!running && !done && (
              <button
                onClick={onBack}
                className="text-sm px-4 py-2.5 rounded-xl border border-stone-200 text-stone-600 hover:bg-stone-50 font-semibold transition-colors"
              >
                ← Quay lại
              </button>
            )}
            {!running && (
              <button
                onClick={build}
                className="btn-glow px-6 py-3 rounded-xl text-white font-bold flex items-center gap-2"
              >
                <span className="text-lg">🎬</span>
                <span>{done ? "Dựng lại" : "Bắt đầu dựng"}</span>
              </button>
            )}
            {running && (
              <button
                onClick={cancel}
                className="text-sm px-4 py-2.5 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 font-semibold transition-colors"
              >
                Huỷ
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {STAGES.map((stage, idx) => {
            const state = stageStates[stage.key];
            const detail = stageDetail[stage.key];
            return (
              <div
                key={stage.key}
                className={`relative rounded-2xl p-4 transition-all duration-500 ${
                  state === "active"
                    ? "bg-gradient-to-br from-orange-100 to-orange-50 ring-2 ring-orange-400 shadow-lg shadow-orange-500/30"
                    : state === "done"
                    ? "bg-orange-50/80 ring-1 ring-orange-300/60"
                    : state === "error"
                    ? "bg-red-50 ring-1 ring-red-300"
                    : "bg-white/40 ring-1 ring-stone-200/60"
                }`}
              >
                <div className="flex items-center gap-2.5 mb-2">
                  <div
                    className={`relative w-8 h-8 rounded-xl flex items-center justify-center text-sm font-black transition-all ${
                      state === "active"
                        ? "bg-gradient-to-br from-orange-500 to-orange-600 text-white shadow-md shadow-orange-500/40"
                        : state === "done"
                        ? "bg-orange-500 text-white"
                        : state === "error"
                        ? "bg-red-500 text-white"
                        : "bg-stone-200 text-stone-500"
                    }`}
                  >
                    {state === "done" ? "✓" : state === "error" ? "!" : state === "active" ? stage.icon : idx + 1}
                    {state === "active" && (
                      <span className="absolute inset-0 rounded-xl border-2 border-orange-400 animate-ping" />
                    )}
                  </div>
                  <span className="text-xs font-bold text-stone-800 leading-tight">
                    {stage.label}
                  </span>
                </div>
                <p className="text-[11px] text-stone-500 leading-relaxed min-h-[32px]">
                  {detail || stage.detail}
                </p>
              </div>
            );
          })}
        </div>

        {running && stageStates.render !== "pending" && (
          <div className="mt-5 fade-up">
            <div className="flex items-center justify-between text-[11px] text-stone-500 mb-1.5 font-semibold">
              <span className="uppercase tracking-wider text-orange-700">Render progress</span>
              <span className="text-orange-700">{renderProgress}%</span>
            </div>
            <div className="h-2 rounded-full bg-orange-100 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all duration-500 shadow-sm shadow-orange-500/40"
                style={{ width: `${renderProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {(running || renderLog.length > 0) && stageStates.render !== "pending" && (
        <div className="rounded-3xl p-5 bg-stone-900/95 backdrop-blur border border-stone-800 shadow-xl shadow-stone-900/20 fade-up">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
              <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
            </div>
            <p className="text-[10px] text-orange-400 font-bold uppercase tracking-widest ml-2">
              Render log
            </p>
          </div>
          <pre className="text-[11px] text-orange-200/90 font-mono whitespace-pre-wrap leading-relaxed max-h-56 overflow-auto">
            {renderLog.length > 0 ? renderLog.join("\n") : "Đang khởi động Chromium..."}
          </pre>
        </div>
      )}

      {done && fullVideoUrl && (
        <div className="glass-strong rounded-3xl p-5 fade-up">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div>
              <p className="text-[10px] font-black text-orange-700 uppercase tracking-widest mb-0.5">
                ✓ Video đã render xong
              </p>
              <p className="text-base font-bold text-stone-900">{scenePlan.title}.mp4</p>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={fullVideoUrl}
                download
                className="text-sm px-4 py-2.5 rounded-xl border border-orange-200 text-orange-700 hover:bg-orange-50 font-semibold transition-colors flex items-center gap-1.5"
              >
                <span>⬇</span>
                <span>Tải xuống</span>
              </a>
              <a
                href={fullVideoUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-glow text-sm px-4 py-2.5 rounded-xl text-white font-bold flex items-center gap-1.5"
              >
                <span>↗</span>
                <span>Mở tab mới</span>
              </a>
            </div>
          </div>

          <video
            src={fullVideoUrl}
            controls
            className="w-full rounded-2xl bg-black shadow-2xl shadow-orange-900/20"
            style={{ aspectRatio: "16 / 9" }}
          />

          {videoPath && (
            <p className="text-[10px] text-stone-400 mt-3 font-mono break-all bg-stone-100/60 px-3 py-1.5 rounded-lg">
              📁 {videoPath}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
