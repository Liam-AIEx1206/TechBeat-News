"use client";

import { useEffect, useRef, useState } from "react";
import type { Scene, ScenePlan, ThemeId } from "@/types/scene";
import { DEFAULT_THEME, getTheme } from "@/types/scene";
import { ScenePreviewIframe } from "./ScenePreviewIframe";
import { ImagePicker } from "./ImagePicker";
import { ThemePicker } from "./ThemePicker";
import { VoicePicker } from "./VoicePicker";

interface Props {
  scenePlan: ScenePlan;
  setScenePlan: (p: ScenePlan) => void;
  onBack: () => void;
  onBuild: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function HtmlPreviewStage({ scenePlan, setScenePlan, onBack, onBuild }: Props) {
  const themeId: ThemeId = scenePlan.theme ?? DEFAULT_THEME;
  const theme = getTheme(themeId);

  const [activeIdx, setActiveIdx]   = useState(0);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [genStatus, setGenStatus]   = useState<"idle" | "generating" | "regenScene" | "regenAll">("idle");
  const [genLog, setGenLog]         = useState("");
  const [genError, setGenError]     = useState<string | null>(null);
  const [regenScene, setRegenScene] = useState<number | null>(null); // 1-based
  const abortRef = useRef<AbortController | null>(null);
  // Always points to the latest scenePlan so async functions avoid stale closures.
  const scenePlanRef = useRef(scenePlan);
  useEffect(() => { scenePlanRef.current = scenePlan; });

  const sceneFlags = scenePlan.sceneRegenFlags ?? [];
  const html = scenePlan.compositionHtml;
  const active = scenePlan.scenes[activeIdx];

  // Trigger generation whenever compositionHtml is absent.
  // generatingRef prevents double-firing on rapid re-renders.
  const generatingRef = useRef(false);
  useEffect(() => {
    if (!html && !generatingRef.current) {
      generatingRef.current = true;
      void generateFull().finally(() => { generatingRef.current = false; });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [html]);

  function setScene(idx: number, patch: Partial<Scene>) {
    const scenes = scenePlan.scenes.map((s, i) => i === idx ? { ...s, ...patch } : s);
    const flags  = [...(scenePlan.sceneRegenFlags ?? [])];
    flags[idx] = true;
    setScenePlan({ ...scenePlan, scenes, sceneRegenFlags: flags });
  }

  async function generateFull() {
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    setGenStatus("generating");
    setGenLog("");
    setGenError(null);

    // Read from ref so we always use the latest scenePlan (avoids stale closure
    // when this is called from a useEffect triggered by a state update).
    const plan = scenePlanRef.current;

    try {
      const res = await fetch(`${API}/generate-composition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: plan.title,
          scenes: plan.scenes,
          totalDuration: plan.totalDuration,
          theme: plan.theme,
        }),
        signal: abort.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalHtml = "";
      let mergedScenes: Scene[] | null = null;
      let mergedTotalDuration: number | null = null;

      const handle = (line: string) => {
        if (!line.startsWith("data: ")) return;
        let ev: { type: string; text?: string; html?: string; message?: string; mergedScenes?: Scene[]; mergedTotalDuration?: number };
        try { ev = JSON.parse(line.slice(6)); } catch { return; }
        if (ev.type === "chunk" && ev.text) {
          setGenLog(p => (p + ev.text!).slice(-3000));
        } else if (ev.type === "warning" && ev.message) {
          setGenLog(p => `[!] ${ev.message}\n\n${p}`);
        } else if (ev.type === "done" && ev.html) {
          finalHtml = ev.html;
          if (ev.mergedScenes) mergedScenes = ev.mergedScenes;
          if (ev.mergedTotalDuration) mergedTotalDuration = ev.mergedTotalDuration;
        } else if (ev.type === "error") {
          throw new Error(ev.message ?? "Lỗi không xác định");
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const p of parts) handle(p);
      }
      if (buf.trim()) handle(buf);

      if (!finalHtml) throw new Error("Backend không trả về HTML");
      // If the backend merged scenes (groq fallback), apply the merged
      // scene list so TTS at build time matches the HTML 1:1.
      const nextScenes = mergedScenes ?? plan.scenes;
      const nextTotal  = mergedTotalDuration ?? plan.totalDuration;
      setScenePlan({
        ...plan,
        scenes: nextScenes,
        totalDuration: nextTotal,
        compositionHtml: finalHtml,
        sceneRegenFlags: nextScenes.map(() => false),
      });
      setGenStatus("idle");
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setGenError(e instanceof Error ? e.message : "Sinh HTML thất bại");
      setGenStatus("idle");
    }
  }

  /** Regenerate one scene's HTML.
   *
   *  @param idx           0-based scene index
   *  @param sceneOverride pass the latest scene snapshot when state hasn't
   *                       flushed yet (e.g. immediately after picking an
   *                       image — scenePlan.scenes[idx] is still stale). */
  async function regenOne(idx: number, sceneOverride?: Scene) {
    const currentHtml = scenePlanRef.current.compositionHtml;
    if (!currentHtml) return;
    const sceneForRegen = sceneOverride ?? scenePlanRef.current.scenes[idx];
    setRegenScene(idx + 1);
    setGenStatus("regenScene");
    setGenError(null);
    try {
      const res = await fetch(`${API}/regen-scene`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullHtml: currentHtml,
          sceneIndex: idx + 1,
          scene: sceneForRegen,
          theme: scenePlanRef.current.theme,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data: { html: string } = await res.json();
      const latest = scenePlanRef.current;
      const flags = [...(latest.sceneRegenFlags ?? [])];
      flags[idx] = false;
      setScenePlan({ ...latest, compositionHtml: data.html, sceneRegenFlags: flags });
      setGenStatus("idle");
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Regen scene thất bại");
      setGenStatus("idle");
    } finally {
      setRegenScene(null);
    }
  }

  function changeTheme(id: ThemeId) {
    if (id === scenePlan.theme) return;
    // Clearing compositionHtml triggers the useEffect above to re-generate.
    setScenePlan({ ...scenePlan, theme: id, compositionHtml: undefined, sceneRegenFlags: scenePlan.scenes.map(() => false) });
  }

  const total = scenePlan.scenes.length;
  const allClean = sceneFlags.every(f => !f);

  return (
    <main style={{ maxWidth: 1480, margin: "0 auto", padding: "24px clamp(16px,3vw,32px)" }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 20 }}>
        <div className="hero-eyebrow" style={{ marginBottom: 10 }}>
          Bước 3 · Xem trước HTML
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          <h1 style={{ fontSize: "clamp(22px,2.8vw,34px)", fontWeight: 900, letterSpacing: "-0.03em", maxWidth: 720 }}>
            {scenePlan.title}
          </h1>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onBack} className="btn-ghost" style={{ fontSize: 12 }}>← Quay lại kịch bản</button>
            <button
              onClick={onBuild}
              disabled={!html || genStatus !== "idle"}
              className="btn-primary"
              style={{
                background: theme.accent,
                boxShadow: `0 12px 32px -4px ${theme.accent}99`,
                fontSize: 13,
                opacity: (!html || genStatus !== "idle") ? 0.4 : 1,
              }}
            >
              <span>🎬 Dựng video MP4 →</span>
            </button>
          </div>
        </div>
        {!allClean && html && (
          <div style={{ marginTop: 10, fontSize: 11, color: "var(--accent3)" }}>
            ⚠ Có scene đã sửa nhưng chưa regen — bấm “↻ Regen scene” trong panel bên phải để cập nhật preview.
          </div>
        )}
      </div>

      {/* Generating placeholder */}
      {genStatus === "generating" && (
        <div className="fade-up" style={{
          padding: 40, borderRadius: "var(--r-xl)",
          background: "var(--gray-1)", border: "1px solid rgba(249,115,22,0.3)",
          textAlign: "center", marginBottom: 24,
        }}>
          <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 12 }}>
            ⚡ AI đang dựng HTML…
          </div>
          <p style={{ fontSize: 13, color: "var(--gray-5)", marginBottom: 16 }}>
            Đợi ~30-60 giây. Bạn sẽ thấy {total} scene xếp ngang trong vài giây nữa.
          </p>
          <pre style={{
            maxHeight: 200, overflow: "auto", textAlign: "left",
            fontFamily: "var(--font-mono)", fontSize: 11, color: "rgba(249,115,22,0.85)",
            background: "#020204", padding: 16, borderRadius: 8,
            whiteSpace: "pre-wrap", wordBreak: "break-all",
          }}>
            {genLog || "Đang khởi tạo phiên..."}
          </pre>
        </div>
      )}

      {genError && (
        <div style={{
          padding: 16, borderRadius: 12, background: "rgba(239,68,68,0.05)",
          border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5", marginBottom: 16, fontSize: 13,
        }}>
          ✕ {genError}
          <button onClick={() => generateFull()} className="btn-ghost" style={{ marginLeft: 12, fontSize: 11 }}>
            Thử lại
          </button>
        </div>
      )}

      {/* 3-column editor */}
      {html && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "minmax(220px, 280px) minmax(0, 1fr) minmax(280px, 360px)",
          gap: 16,
          alignItems: "start",
        }}>
          {/* LEFT — scene list */}
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 16,
            maxHeight: "calc(100vh - 180px)", overflowY: "auto",
          }}>
            <div className="hero-eyebrow" style={{ marginBottom: 14, fontSize: 10 }}>
              Scenes ({total})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {scenePlan.scenes.map((s, i) => {
                const isActive = i === activeIdx;
                const dirty   = sceneFlags[i];
                return (
                  <button
                    key={s.id}
                    onClick={() => setActiveIdx(i)}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 12px",
                      borderRadius: 12,
                      border: isActive ? `1px solid ${theme.accent}` : "1px solid var(--gray-3)",
                      background: isActive ? `${theme.accent}1a` : "var(--gray-2)",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, flexShrink: 0,
                      borderRadius: 6,
                      background: isActive ? theme.accent : "var(--gray-3)",
                      color: isActive ? "var(--black)" : "var(--gray-6)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 800,
                    }}>
                      {(i + 1).toString().padStart(2, "0")}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 12, fontWeight: 700, color: "var(--white)",
                        whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden",
                      }}>
                        {s.title}
                      </div>
                      <div style={{ fontSize: 10, color: "var(--gray-5)", marginTop: 2 }}>
                        ~{s.duration}s
                      </div>
                    </div>
                    {dirty && (
                      <span title="Đã sửa, chưa regen" style={{
                        flexShrink: 0,
                        width: 8, height: 8, borderRadius: "50%",
                        background: "var(--accent3)",
                        boxShadow: "0 0 8px var(--accent3)",
                      }} />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* CENTER — iframe preview */}
          <div>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 10,
            }}>
              <div className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 0 }}>
                Scene preview · 1920×1080
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--gray-5)" }}>
                {(activeIdx + 1).toString().padStart(2, "0")} / {total.toString().padStart(2, "0")}
              </div>
            </div>
            <ScenePreviewIframe fullHtml={html} sceneIndex={activeIdx + 1} />
            <div style={{ marginTop: 8, fontSize: 11, color: "var(--gray-5)" }}>
              {active?.duration}s · {active?.title}
            </div>
          </div>

          {/* RIGHT — edit panel */}
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 18,
            maxHeight: "calc(100vh - 180px)", overflowY: "auto",
            display: "flex", flexDirection: "column", gap: 16,
          }}>
            <div>
              <div className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 8 }}>
                Tiêu đề scene
              </div>
              <input
                className="input-dark"
                style={{ fontSize: 13, fontWeight: 700 }}
                value={active?.title ?? ""}
                onChange={(e) => setScene(activeIdx, { title: e.target.value })}
              />
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 0 }}>Narration tiếng Việt</span>
                <span style={{ fontSize: 10, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
                  {active?.narration.length ?? 0} chars
                </span>
              </div>
              <textarea
                rows={6}
                className="input-dark"
                style={{ fontSize: 13, resize: "vertical", lineHeight: 1.6 }}
                value={active?.narration ?? ""}
                onChange={(e) => setScene(activeIdx, { narration: e.target.value })}
              />
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 0 }}>Ảnh minh hoạ</span>
                <button onClick={() => setPickerOpen(true)} className="btn-ghost" style={{ fontSize: 10, padding: "4px 10px" }}>
                  ↑ Chọn ảnh
                </button>
              </div>
              {active?.imageUrl ? (
                <div style={{
                  position: "relative", width: "100%", aspectRatio: "16/9",
                  borderRadius: 8, overflow: "hidden", border: "1px solid var(--gray-3)",
                }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={active.imageUrl} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} referrerPolicy="no-referrer" />
                </div>
              ) : (
                <div style={{
                  padding: 20, borderRadius: 8, background: "var(--gray-2)",
                  border: "1px dashed var(--gray-3)", textAlign: "center",
                  fontSize: 11, color: "var(--gray-5)",
                }}>
                  Chưa có ảnh — AI sẽ dùng mock visual (stat / code / grid).
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => regenOne(activeIdx)}
                disabled={genStatus !== "idle"}
                className="btn-primary"
                style={{
                  flex: 1, fontSize: 12,
                  background: sceneFlags[activeIdx] ? theme.accent : "var(--gray-3)",
                  color: sceneFlags[activeIdx] ? "var(--black)" : "var(--gray-6)",
                  boxShadow: sceneFlags[activeIdx] ? `0 8px 24px -4px ${theme.accent}66` : "none",
                  opacity: genStatus !== "idle" ? 0.5 : 1,
                }}
              >
                <span>
                  {regenScene === activeIdx + 1 ? "⏳ Đang regen…" : "↻ Regen scene"}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Theme + Voice — full width below */}
      {html && (
        <div style={{
          marginTop: 24,
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16,
        }}>
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 20,
          }}>
            <div className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 12 }}>Theme video</div>
            <ThemePicker value={themeId} onChange={changeTheme} />
            <p style={{ fontSize: 10, color: "var(--gray-5)", marginTop: 10 }}>
              Đổi theme sẽ regen toàn bộ HTML.
            </p>
          </div>
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 20,
          }}>
            <div className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 12 }}>Giọng đọc TTS</div>
            <VoicePicker
              value={scenePlan.voiceId}
              onChange={(id) => setScenePlan({ ...scenePlan, voiceId: id })}
            />
            <p style={{ fontSize: 10, color: "var(--gray-5)", marginTop: 10 }}>
              Voice không ảnh hưởng HTML — không cần regen.
            </p>
          </div>
        </div>
      )}

      {active && (
        <ImagePicker
          open={pickerOpen}
          initialQuery={active.imageQuery?.trim() || active.title}
          onClose={() => setPickerOpen(false)}
          onPick={(url) => {
            // 1. Update scene state (also marks dirty flag for fallback UI)
            setScene(activeIdx, { imageUrl: url, imageAsset: undefined });
            // 2. Auto-regen the scene so the preview reflects the new image
            //    immediately — the user clearly intended this change. Pass a
            //    fresh scene snapshot because React state hasn't flushed yet.
            if (html) {
              const fresh: Scene = {
                ...scenePlanRef.current.scenes[activeIdx],
                imageUrl: url,
                imageAsset: undefined,
              };
              void regenOne(activeIdx, fresh);
            }
          }}
        />
      )}
    </main>
  );
}
