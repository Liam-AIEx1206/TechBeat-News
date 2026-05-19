"use client";

import { useState, useRef } from "react";
import { InputPanel } from "@/components/InputPanel";
import { SceneList } from "@/components/SceneList";
import { VideoBuilder } from "@/components/VideoBuilder";
import type { ExtractedContent, ScenePlan } from "@/types/scene";

type Stage = "input" | "generating" | "preview" | "build";

export default function Home() {
  const [stage, setStage] = useState<Stage>("input");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [scenePlan, setScenePlan] = useState<ScenePlan | null>(null);
  const [streamBuffer, setStreamBuffer] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function generateScenes(content: ExtractedContent) {
    setStage("generating");
    setError("");
    setStreamBuffer("");
    setScenePlan(null);

    const abort = new AbortController();
    abortRef.current = abort;

    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    try {
      const res = await fetch(`${API}/generate-scenes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content.text, title: content.title }),
        signal: abort.signal,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Tạo kịch bản thất bại");
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      function processLines(raw: string) {
        const lines = raw.split("\n\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let event: { type: string; text?: string; scenePlan?: unknown; message?: string };
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (event.type === "chunk" && event.text) {
            setStreamBuffer((prev) => prev + event.text);
          } else if (event.type === "done" && event.scenePlan) {
            setScenePlan(event.scenePlan as ScenePlan);
            setStage("preview");
          } else if (event.type === "error") {
            throw new Error(event.message ?? "Lỗi không xác định");
          }
        }
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
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
      setError(err instanceof Error ? err.message : "Tạo kịch bản thất bại");
      setStage("input");
    }
  }

  function handleExtracted(content: ExtractedContent) {
    generateScenes(content);
  }

  function handleReset() {
    abortRef.current?.abort();
    setStage("input");
    setScenePlan(null);
    setStreamBuffer("");
    setError("");
  }

  const stepperItems: { key: Stage; num: number; label: string }[] = [
    { key: "input", num: 1, label: "Nhập" },
    { key: "preview", num: 2, label: "Kịch bản" },
    { key: "build", num: 3, label: "Dựng video" },
  ];

  return (
    <div className="min-h-screen relative">
      <header className="sticky top-0 z-20 px-6 py-4 glass border-b border-white/40">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 via-orange-600 to-amber-700 flex items-center justify-center text-white text-lg font-black shadow-lg shadow-orange-500/40">
                T
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-orange-400 animate-pulse" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-bold text-stone-900 text-base">
                Tech<span className="gradient-text">Beat</span>
              </span>
              <span className="text-[10px] text-orange-700/80 font-medium uppercase tracking-wider">
                Tin công nghệ thành video
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-1.5 text-xs">
            {stepperItems.map((s, idx) => {
              const stageOrder: Stage[] = ["input", "generating", "preview", "build"];
              const currentIdx = stageOrder.indexOf(stage);
              const sIdx = stageOrder.indexOf(s.key);
              const isDone = currentIdx > sIdx || (s.key === "preview" && stage === "build");
              const isActive =
                stage === s.key ||
                (s.key === "preview" && stage === "generating");

              return (
                <div key={s.key} className="flex items-center gap-1.5">
                  <div
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full font-semibold transition-all ${
                      isDone
                        ? "bg-orange-100 text-orange-700"
                        : isActive
                        ? "btn-glow text-white"
                        : "bg-stone-100/70 text-stone-400"
                    }`}
                  >
                    <span
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${
                        isDone || isActive ? "bg-white/30 text-white" : "bg-stone-300 text-stone-600"
                      }`}
                    >
                      {isDone ? "✓" : s.num}
                    </span>
                    <span>{s.label}</span>
                  </div>
                  {idx < stepperItems.length - 1 && (
                    <span className={`w-3 h-px ${isDone ? "bg-orange-400" : "bg-stone-300"}`} />
                  )}
                </div>
              );
            })}
          </div>

          {stage !== "input" && (
            <button
              onClick={handleReset}
              className="text-sm px-3 py-1.5 rounded-full text-stone-600 hover:text-orange-700 hover:bg-orange-50 font-medium transition-colors"
            >
              ← Bắt đầu lại
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {stage === "input" && (
          <div className="max-w-2xl mx-auto fade-up">
            <div className="text-center mb-10">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-100/80 text-orange-700 text-xs font-semibold mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
                Tin công nghệ · Bản tin AI hằng ngày
              </div>
              <h1 className="text-5xl sm:text-6xl font-black mb-4 leading-tight tracking-tight">
                Tin công nghệ thành{" "}
                <span className="gradient-text">video</span>
                <br />
                mỗi ngày, vài phút
              </h1>
              <p className="text-stone-600 text-base max-w-lg mx-auto">
                Dán link bài viết hoặc upload tài liệu — TechBeat tóm tắt, viết kịch bản, đọc tiếng Việt và xuất MP4 sẵn sàng đăng.
              </p>
            </div>

            {error && (
              <div className="mb-4 px-4 py-3 bg-red-50/80 backdrop-blur border border-red-200 rounded-xl text-sm text-red-700 fade-up">
                ⚠ {error}
              </div>
            )}

            <div className="glass-strong rounded-3xl p-7">
              <InputPanel
                onExtracted={handleExtracted}
                isLoading={isLoading}
                setIsLoading={setIsLoading}
                setError={setError}
              />
            </div>

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { num: "1", label: "Trích xuất", desc: "URL, PDF, DOCX, PPTX", icon: "📥" },
                { num: "2", label: "Lập kế hoạch", desc: "AI sinh kịch bản tiếng Việt", icon: "🧠" },
                { num: "3", label: "Dựng video", desc: "HTML + TTS + MP4", icon: "🎬" },
              ].map((step, i) => (
                <div
                  key={step.num}
                  className="glass rounded-2xl p-4 fade-up"
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xl">{step.icon}</span>
                    <span className="font-bold text-stone-900 text-sm">{step.label}</span>
                  </div>
                  <p className="text-xs text-stone-500 leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {stage === "generating" && (
          <div className="max-w-2xl mx-auto text-center fade-up">
            <div className="relative inline-block mb-8">
              <div className="w-20 h-20 rounded-full border-4 border-orange-200" />
              <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-orange-500 border-t-transparent animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center text-3xl">
                ✨
              </div>
            </div>
            <h2 className="text-2xl font-bold text-stone-900 mb-2">
              Đang viết kịch bản cho video...
            </h2>
            <p className="text-sm text-stone-500 mb-8">
              Claude Haiku đang phân tích nội dung và chia thành các phân cảnh.
            </p>
            {streamBuffer && (
              <div className="glass rounded-2xl p-5 text-left max-h-72 overflow-auto">
                <p className="text-[10px] text-orange-700 font-bold uppercase tracking-wider mb-2">
                  Output stream
                </p>
                <pre className="text-xs text-stone-700 font-mono whitespace-pre-wrap break-all leading-relaxed">
                  {streamBuffer}
                </pre>
              </div>
            )}
          </div>
        )}

        {stage === "preview" && scenePlan && (
          <div className="fade-up">
            {error && (
              <div className="mb-4 px-4 py-3 bg-red-50/80 backdrop-blur border border-red-200 rounded-xl text-sm text-red-700">
                ⚠ {error}
              </div>
            )}

            <div className="glass-strong rounded-3xl p-6 mb-6 flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-xs font-bold text-orange-700 uppercase tracking-wider mb-1">
                  ✓ Kịch bản đã sẵn sàng
                </p>
                <h2 className="text-2xl font-bold text-stone-900">{scenePlan.title}</h2>
                <p className="text-xs text-stone-500 mt-1">
                  <span className="text-orange-700 font-semibold">{scenePlan.scenes.length} phân cảnh</span> ·
                  thời lượng dự kiến <span className="text-orange-700 font-semibold">{scenePlan.totalDuration}s</span>
                </p>
              </div>
              <button
                onClick={() => setStage("build")}
                className="btn-glow px-6 py-3 rounded-2xl text-white font-bold text-sm flex items-center gap-2"
              >
                <span>🎬</span>
                <span>Dựng video</span>
                <span>→</span>
              </button>
            </div>

            <SceneList scenePlan={scenePlan} onChange={setScenePlan} />

            <div className="mt-8 flex justify-center">
              <button
                onClick={() => setStage("build")}
                className="btn-glow px-8 py-4 rounded-2xl text-white font-bold text-base flex items-center gap-3"
              >
                <span className="text-xl">🎬</span>
                <span>Dựng video ngay</span>
                <span>→</span>
              </button>
            </div>
          </div>
        )}

        {stage === "build" && scenePlan && (
          <div className="fade-up">
            <VideoBuilder
              scenePlan={scenePlan}
              onBack={() => setStage("preview")}
            />
          </div>
        )}
      </main>

      <footer className="max-w-6xl mx-auto px-6 py-8 text-center text-xs text-stone-400">
        TechBeat · Tin công nghệ tóm tắt mỗi ngày · Claude + HyperFrames + gTTS · <span className="text-orange-600 font-semibold">tiếng Việt</span>
      </footer>
    </div>
  );
}
