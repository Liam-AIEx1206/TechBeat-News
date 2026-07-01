"use client";

import { useState, useRef, useCallback } from "react";
import type { ScenePlan } from "@/types/scene";
import { getTheme } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  setScenePlan: (p: ScenePlan) => void;
  onBack: () => void;
  onExport: () => void;
}

const SLIDE_LS_KEY = "xnew_slide_svgs";

function loadSvgCache(title: string): string[] {
  try {
    const raw = localStorage.getItem(SLIDE_LS_KEY);
    if (!raw) return [];
    const obj = JSON.parse(raw);
    return obj.title === title ? (obj.svgs ?? []) : [];
  } catch { return []; }
}

function saveSvgCache(title: string, svgs: string[]) {
  try { localStorage.setItem(SLIDE_LS_KEY, JSON.stringify({ title, svgs, savedAt: Date.now() })); } catch { /* quota */ }
}

export function SlidePreviewStage({ scenePlan, setScenePlan, onBack, onExport }: Props) {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [svgs, setSvgs] = useState<string[]>(() => loadSvgCache(scenePlan.title));
  const [activeIdx, setActiveIdx] = useState(0);
  const [genStates, setGenStates] = useState<("pending" | "loading" | "done" | "error")[]>(
    () => scenePlan.scenes.map((_, i) => loadSvgCache(scenePlan.title)[i] ? "done" : "pending")
  );
  const [errors, setErrors] = useState<(string | null)[]>(scenePlan.scenes.map(() => null));
  const [genAll, setGenAll] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const theme = getTheme(scenePlan.theme);

  const endpoint = process.env.NODE_ENV === "development"
    ? `${API}/gen-slide-one`
    : `/api/proxy/gen-slide-one`;

  const genSlide = useCallback(async (idx: number, abort?: AbortSignal) => {
    setGenStates(p => { const n = [...p]; n[idx] = "loading"; return n; });
    setErrors(p => { const n = [...p]; n[idx] = null; return n; });
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: scenePlan.title,
          scenes: scenePlan.scenes,
          totalDuration: scenePlan.totalDuration,
          theme: scenePlan.theme,
          sceneIndex: idx,
          sessionId: scenePlan.sessionId,
        }),
        signal: abort,
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Lỗi gen slide");
      const data = await res.json();
      const svg = data.svg as string;
      setSvgs(prev => {
        const next = [...prev];
        next[idx] = svg;
        saveSvgCache(scenePlan.title, next);
        return next;
      });
      setGenStates(p => { const n = [...p]; n[idx] = "done"; return n; });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setErrors(p => { const n = [...p]; n[idx] = err instanceof Error ? err.message : "Lỗi"; return n; });
      setGenStates(p => { const n = [...p]; n[idx] = "error"; return n; });
    }
  }, [scenePlan, endpoint]);

  async function genAll_() {
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;
    setGenAll(true);
    for (let i = 0; i < scenePlan.scenes.length; i++) {
      if (abort.signal.aborted) break;
      await genSlide(i, abort.signal);
    }
    setGenAll(false);
  }

  function stopGen() { abortRef.current?.abort(); setGenAll(false); }

  const allDone = genStates.every(s => s === "done");
  const anyLoading = genStates.some(s => s === "loading");

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--black)", color: "var(--white)" }}>
      {/* Header */}
      <div style={{ padding: "20px 32px", borderBottom: "1px solid var(--gray-2)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent2)", marginBottom: 4 }}>
            Xem trước Slide
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: "-0.02em" }}>{scenePlan.title}</div>
          <div style={{ fontSize: 12, color: "var(--gray-5)", marginTop: 2 }}>
            {scenePlan.scenes.length} slide · Theme: {theme.name}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={onBack} className="btn-ghost" style={{ fontSize: 13 }}>← Quay lại</button>
          {genAll ? (
            <button onClick={stopGen} className="btn-ghost" style={{ fontSize: 13, color: "var(--red)" }}>⬛ Dừng</button>
          ) : (
            <button onClick={genAll_} disabled={anyLoading} className="btn-ghost" style={{ fontSize: 13 }}>
              ↺ Gen tất cả
            </button>
          )}
          <button
            onClick={() => {
              setScenePlan({ ...scenePlan, pptxUrl: undefined });
              onExport();
            }}
            disabled={!allDone}
            className="btn-primary"
            style={{ fontSize: 13, opacity: allDone ? 1 : 0.4, cursor: allDone ? "pointer" : "not-allowed" }}
          >
            <span>Xuất PPTX →</span>
          </button>
        </div>
      </div>

      {/* Body: 3-column */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left: slide list */}
        <div style={{
          width: 200, flexShrink: 0, borderRight: "1px solid var(--gray-2)",
          overflowY: "auto", padding: "12px 8px", display: "flex", flexDirection: "column", gap: 6,
        }}>
          {scenePlan.scenes.map((scene, i) => {
            const st = genStates[i];
            const isActive = activeIdx === i;
            return (
              <button key={i} onClick={() => setActiveIdx(i)} style={{
                padding: "10px 12px", borderRadius: 10, textAlign: "left", border: "none", cursor: "pointer",
                background: isActive ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.03)",
                borderLeft: `3px solid ${isActive ? "var(--accent)" : "transparent"}`,
                transition: "all 0.2s ease",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span style={{
                    width: 18, height: 18, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center",
                    background: st === "done" ? "rgba(34,197,94,0.15)" : st === "loading" ? "rgba(249,115,22,0.15)" : st === "error" ? "rgba(239,68,68,0.15)" : "rgba(255,255,255,0.05)",
                    fontSize: 9, fontWeight: 800,
                    color: st === "done" ? "#22c55e" : st === "loading" ? "var(--accent)" : st === "error" ? "#ef4444" : "var(--gray-5)",
                  }}>
                    {st === "done" ? "✓" : st === "loading" ? "…" : st === "error" ? "!" : i + 1}
                  </span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: isActive ? "var(--accent)" : "var(--white)" }}>
                    Slide {i + 1}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: "var(--gray-5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {scene.title}
                </div>
              </button>
            );
          })}
        </div>

        {/* Middle: SVG preview */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 32, background: "rgba(0,0,0,0.3)" }}>
          <div style={{ width: "100%", maxWidth: 854, aspectRatio: "16/9", position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-2)", background: "#08080f" }}>
            {svgs[activeIdx] ? (
              <div
                dangerouslySetInnerHTML={{ __html: svgs[activeIdx] }}
                style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
              />
            ) : genStates[activeIdx] === "loading" ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "var(--gray-5)" }}>
                <div style={{ width: 32, height: 32, border: "3px solid var(--accent)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                <span style={{ fontSize: 13 }}>Đang tạo slide...</span>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, color: "var(--gray-5)" }}>
                <span style={{ fontSize: 40, opacity: 0.2 }}>🖼</span>
                <span style={{ fontSize: 13 }}>Chưa gen — nhấn "Gen slide này"</span>
                {errors[activeIdx] && <span style={{ fontSize: 11, color: "#ef4444", maxWidth: 300, textAlign: "center" }}>{errors[activeIdx]}</span>}
              </div>
            )}
          </div>
        </div>

        {/* Right: edit panel */}
        <div style={{ width: 280, flexShrink: 0, borderLeft: "1px solid var(--gray-2)", overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--accent2)" }}>
            Slide {activeIdx + 1} / {scenePlan.scenes.length}
          </div>

          {/* Title */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--gray-5)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>Tiêu đề</div>
            <textarea
              value={scenePlan.scenes[activeIdx]?.title ?? ""}
              onChange={(e) => {
                const next = scenePlan.scenes.map((s, i) => i === activeIdx ? { ...s, title: e.target.value } : s);
                setScenePlan({ ...scenePlan, scenes: next });
              }}
              rows={2}
              style={{ width: "100%", resize: "vertical", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 8, color: "var(--white)", fontSize: 13, padding: "10px 12px", fontFamily: "inherit" }}
            />
          </div>

          {/* Narration */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--gray-5)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>Nội dung</div>
            <textarea
              value={scenePlan.scenes[activeIdx]?.narration ?? ""}
              onChange={(e) => {
                const next = scenePlan.scenes.map((s, i) => i === activeIdx ? { ...s, narration: e.target.value } : s);
                setScenePlan({ ...scenePlan, scenes: next });
              }}
              rows={5}
              style={{ width: "100%", resize: "vertical", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 8, color: "var(--white)", fontSize: 12, padding: "10px 12px", fontFamily: "inherit", lineHeight: 1.5 }}
            />
          </div>

          {/* Error */}
          {errors[activeIdx] && (
            <div style={{ padding: "8px 12px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, fontSize: 11, color: "#ef4444" }}>
              {errors[activeIdx]}
            </div>
          )}

          {/* Gen button */}
          <button
            onClick={() => genSlide(activeIdx)}
            disabled={genStates[activeIdx] === "loading"}
            className="btn-primary"
            style={{ fontSize: 13, opacity: genStates[activeIdx] === "loading" ? 0.6 : 1 }}
          >
            <span>{genStates[activeIdx] === "loading" ? "Đang gen..." : genStates[activeIdx] === "done" ? "↺ Regen slide này" : "Gen slide này"}</span>
          </button>

          <div style={{ fontSize: 10, color: "var(--gray-6)", lineHeight: 1.5 }}>
            Sửa tiêu đề hoặc nội dung rồi nhấn Regen để cập nhật slide.
          </div>
        </div>
      </div>
    </div>
  );
}
