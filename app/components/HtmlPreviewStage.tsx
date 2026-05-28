"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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

// Trạng thái từng scene trong quá trình gen tuần tự
type SceneGenStatus = "pending" | "generating" | "done" | "error";

function patchThemeInHtml(html: string, newThemeId: ThemeId): string {
  const newTheme = getTheme(newThemeId);
  const rootRegex = /:root\s*\{([^}]*)\}/i;
  const match = html.match(rootRegex);
  if (match) {
    const newRootBlock = `:root {
  --bg: ${newTheme.bg};
  --bg2: ${newTheme.bg2};
  --surface: ${newTheme.surface};
  --accent: ${newTheme.accent};
  --accent2: ${newTheme.accent2};
  --accent3: ${newTheme.accent3};
  --text1: ${newTheme.text1};
  --text2: ${newTheme.text2};
  --glow: ${newTheme.accent}55;
}`;
    return html.replace(rootRegex, newRootBlock);
  }
  return html;
}

export function HtmlPreviewStage({ scenePlan, setScenePlan, onBack, onBuild }: Props) {
  const themeId: ThemeId = scenePlan.theme ?? DEFAULT_THEME;
  const theme = getTheme(themeId);

  const [activeIdx, setActiveIdx]   = useState(0);
  const [pickerOpen, setPickerOpen] = useState(false);

  // ── 5s Voice Preview state ──────────────────────────────────────────
  const [playingPreview, setPlayingPreview] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewAudio, setPreviewAudio] = useState<HTMLAudioElement | null>(null);

  // Cleanup preview audio on unmount or change
  useEffect(() => {
    return () => {
      if (previewAudio) {
        previewAudio.pause();
      }
    };
  }, [previewAudio]);

  // Stop current preview if voiceId changes
  useEffect(() => {
    if (previewAudio) {
      previewAudio.pause();
      setPlayingPreview(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenePlan.voiceId]);

  const handlePlay5sPreview = async () => {
    if (playingPreview) {
      if (previewAudio) {
        previewAudio.pause();
        setPlayingPreview(false);
      }
      return;
    }

    setPreviewLoading(true);
    try {
      const firstSceneText = scenePlan.scenes[0]?.narration ?? "";
      const currentVoiceId = scenePlan.voiceId ?? "edge-vi-VN-NamMinhNeural";
      
      const res = await fetch(`${API}/voices/preview-5s`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_id: currentVoiceId,
          text: firstSceneText,
        }),
      });

      if (!res.ok) throw new Error("Synthesis failed");
      const resData = await res.json();
      const audioUrl = `${API}${resData.url}`;
      
      const audio = new Audio(audioUrl);
      setPreviewAudio(audio);
      setPlayingPreview(true);
      audio.play();
      audio.onended = () => {
        setPlayingPreview(false);
      };
    } catch (e) {
      console.error("Failed to play 5s preview", e);
      alert("Không thể sinh thử âm thanh kịch bản. Vui lòng kiểm tra lại kết nối hoặc giọng đọc!");
    } finally {
      setPreviewLoading(false);
    }
  };

  // ── Gen step-by-step state ──────────────────────────────────────────
  // sceneStatuses[i] = trạng thái của scene i (0-based)
  const [sceneStatuses, setSceneStatuses] = useState<SceneGenStatus[]>(() =>
    scenePlan.scenes.map((_, i) => {
      const hasScene = scenePlan.compositionHtml && (
        scenePlan.compositionHtml.includes(`id="scene${i + 1}"`) ||
        scenePlan.compositionHtml.includes(`id='scene${i + 1}'`) ||
        scenePlan.compositionHtml.includes(`id=scene${i + 1}`)
      );
      return hasScene ? "done" : "pending";
    })
  );
  // Số scene đã gen xong (để tính tiến độ)
  const [genedCount, setGenedCount] = useState<number>(() => {
    if (!scenePlan.compositionHtml) return 0;
    return scenePlan.scenes.filter((_, i) => {
      const html = scenePlan.compositionHtml;
      return html && (
        html.includes(`id="scene${i + 1}"`) ||
        html.includes(`id='scene${i + 1}'`) ||
        html.includes(`id=scene${i + 1}`)
      );
    }).length;
  });
  // Đang gen scene nào? null = không gen
  const [genningIdx, setGenningIdx] = useState<number | null>(null);
  // Error message
  const [genError, setGenError] = useState<string | null>(null);
  // Đang auto-gen tất cả?
  const [isAutoGen, setIsAutoGen] = useState(false);
  const autoGenRef = useRef(false);

  // Context từ backend để tránh lặp layout giữa scenes
  const prevContextRef = useRef<Record<string, unknown>>({
    layout: null,
    visual_pattern: null,
    used_layouts: [],
    used_patterns: [],
  });

  // ── Regen single scene ──────────────────────────────────────────────
  const [regenScene, setRegenScene] = useState<number | null>(null);
  const [regenStatus, setRegenStatus] = useState<"idle" | "running">("idle");

  // ── Scene dirty flags ───────────────────────────────────────────────
  const sceneFlags = scenePlan.sceneRegenFlags ?? [];

  // ── Subtitle toggle ─────────────────────────────────────────────────
  const showSubtitles = scenePlan.subtitlesEnabled !== false;

  // Always points to the latest scenePlan so async functions avoid stale closures.
  const scenePlanRef = useRef(scenePlan);
  useEffect(() => { scenePlanRef.current = scenePlan; });

  const abortRef = useRef<AbortController | null>(null);
  const html = scenePlan.compositionHtml;
  const active = scenePlan.scenes[activeIdx];
  const total = scenePlan.scenes.length;

  // ── Khi scenePlan thay đổi (theme đổi, v.v.) reset statuses ────────
  useEffect(() => {
    if (!html) {
      setSceneStatuses(scenePlan.scenes.map(() => "pending"));
      setGenedCount(0);
      setGenningIdx(null);
      setIsAutoGen(false);
      autoGenRef.current = false;
      prevContextRef.current = { layout: null, visual_pattern: null, used_layouts: [], used_patterns: [] };
    } else {
      setSceneStatuses(prev => {
        return scenePlan.scenes.map((_, i) => {
          const hasScene = html.includes(`id="scene${i + 1}"`) ||
                           html.includes(`id='scene${i + 1}'`) ||
                           html.includes(`id=scene${i + 1}`);
          return hasScene ? "done" : prev[i] === "generating" ? "generating" : "pending";
        });
      });
      const count = scenePlan.scenes.filter((_, i) => {
        return html.includes(`id="scene${i + 1}"`) ||
               html.includes(`id='scene${i + 1}'`) ||
               html.includes(`id=scene${i + 1}`);
      }).length;
      setGenedCount(count);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [html]);

  // ── Gen 1 scene ─────────────────────────────────────────────────────
  const genOneScene = useCallback(async (idx: number): Promise<boolean> => {
    // idx: 0-based
    const plan = scenePlanRef.current;
    const sceneIndex = idx + 1; // 1-based cho API

    setGenningIdx(idx);
    setSceneStatuses(prev => {
      const next = [...prev];
      next[idx] = "generating";
      return next;
    });
    setGenError(null);

    try {
      const res = await fetch(`${API}/gen-scene-one`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: plan.title,
          scenes: plan.scenes,
          totalDuration: plan.totalDuration,
          theme: plan.theme,
          sceneIndex,
          existingHtml: scenePlanRef.current.compositionHtml ?? null,
          previousContext: prevContextRef.current,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }

      const data: {
        html: string;
        sceneIndex: number;
        totalScenes: number;
        done: boolean;
        layout: string | null;
        visualPattern: string | null;
        newContext: Record<string, unknown>;
      } = await res.json();

      // Cập nhật context cho scene tiếp theo
      if (data.newContext) {
        prevContextRef.current = data.newContext;
      }

      // Cập nhật HTML trong scenePlan
      const latest = scenePlanRef.current;
      setScenePlan({
        ...latest,
        compositionHtml: data.html,
        sceneRegenFlags: latest.sceneRegenFlags ?? latest.scenes.map(() => false),
      });

      // Cập nhật status
      setSceneStatuses(prev => {
        const next = [...prev];
        next[idx] = "done";
        return next;
      });
      setGenedCount(prev => prev + 1);
      setActiveIdx(idx); // Tự chuyển preview sang scene vừa gen
      setGenningIdx(null);

      return true;
    } catch (e) {
      if ((e as Error).name === "AbortError") return false;
      setSceneStatuses(prev => {
        const next = [...prev];
        next[idx] = "error";
        return next;
      });
      setGenError(e instanceof Error ? e.message : "Gen scene thất bại");
      setGenningIdx(null);
      return false;
    }
  }, [setScenePlan]);

  // ── Gen scene tiếp theo (1 scene) ───────────────────────────────────
  const handleGenNext = useCallback(async () => {
    const nextIdx = sceneStatuses.findIndex(s => s === "pending" || s === "error");
    if (nextIdx === -1) return;
    await genOneScene(nextIdx);
  }, [sceneStatuses, genOneScene]);

  // ── Gen tất cả còn lại ───────────────────────────────────────────────
  const handleGenAll = useCallback(async () => {
    setIsAutoGen(true);
    autoGenRef.current = true;

    const pendingIdxs = sceneStatuses
      .map((s, i) => (s === "pending" || s === "error" ? i : -1))
      .filter(i => i >= 0);

    for (const idx of pendingIdxs) {
      if (!autoGenRef.current) break;
      const ok = await genOneScene(idx);
      if (!ok) break; // Dừng nếu bị abort hoặc lỗi
    }

    setIsAutoGen(false);
    autoGenRef.current = false;
  }, [sceneStatuses, genOneScene]);

  // ── Dừng auto-gen ────────────────────────────────────────────────────
  const handleStopGen = useCallback(() => {
    autoGenRef.current = false;
    setIsAutoGen(false);
    setGenningIdx(null);
  }, []);

  // ── Regen toàn bộ (đổi theme, v.v.) ─────────────────────────────────
  async function regenFull() {
    setScenePlan({ ...scenePlanRef.current, compositionHtml: undefined, sceneRegenFlags: scenePlan.scenes.map(() => false) });
    // useEffect sẽ reset statuses khi html=undefined
  }

  // ── Regen 1 scene đã gen ─────────────────────────────────────────────
  async function regenOne(idx: number, sceneOverride?: Scene) {
    const currentHtml = scenePlanRef.current.compositionHtml;
    if (!currentHtml) return;
    const sceneForRegen = sceneOverride ?? scenePlanRef.current.scenes[idx];
    setRegenScene(idx + 1);
    setRegenStatus("running");
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
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Regen scene thất bại");
    } finally {
      setRegenScene(null);
      setRegenStatus("idle");
    }
  }

  function changeTheme(id: ThemeId) {
    if (id === scenePlan.theme) return;
    let newHtml = scenePlan.compositionHtml;
    if (newHtml) {
      newHtml = patchThemeInHtml(newHtml, id);
    }
    setScenePlan({
      ...scenePlan,
      theme: id,
      compositionHtml: newHtml,
    });
  }

  function setScene(idx: number, patch: Partial<Scene>) {
    const scenes = scenePlan.scenes.map((s, i) => i === idx ? { ...s, ...patch } : s);
    const flags  = [...(scenePlan.sceneRegenFlags ?? [])];
    flags[idx] = true;
    setScenePlan({ ...scenePlan, scenes, sceneRegenFlags: flags });
  }

  // ── Derived: next pending scene index ────────────────────────────────
  const nextPendingIdx = sceneStatuses.findIndex(s => s === "pending" || s === "error");
  const allDone = sceneStatuses.every(s => s === "done");
  const doneSoFar = sceneStatuses.filter(s => s === "done").length;
  const isGenning = genningIdx !== null;
  const allClean = sceneFlags.every(f => !f);

  // ── Status badge cho scene list ───────────────────────────────────────
  function statusDot(i: number) {
    const st = sceneStatuses[i];
    if (st === "done") {
      return (
        <span style={{
          flexShrink: 0,
          width: 8, height: 8, borderRadius: "50%",
          background: theme.accent,
          boxShadow: `0 0 6px ${theme.accent}`,
        }} />
      );
    }
    if (st === "generating") {
      return (
        <span style={{
          flexShrink: 0,
          width: 10, height: 10,
          border: `2px solid ${theme.accent}`,
          borderTopColor: "transparent",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
          display: "inline-block",
        }} />
      );
    }
    if (st === "error") {
      return (
        <span style={{ flexShrink: 0, fontSize: 10, color: "#f87171" }}>✕</span>
      );
    }
    // pending — mờ
    return (
      <span style={{
        flexShrink: 0,
        width: 8, height: 8, borderRadius: "50%",
        background: "var(--gray-3)",
      }} />
    );
  }

  return (
    <main style={{ maxWidth: 1480, margin: "0 auto", padding: "24px clamp(16px,3vw,32px)" }}>
      {/* Inject spin keyframe */}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>

      {/* ── Header ── */}
      <div className="fade-up" style={{ marginBottom: 20 }}>
        <div className="hero-eyebrow" style={{ marginBottom: 10 }}>
          Bước 3 · Xem trước HTML
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          <h1 style={{ fontSize: "clamp(22px,2.8vw,34px)", fontWeight: 900, letterSpacing: "-0.03em", maxWidth: 720 }}>
            {scenePlan.title}
          </h1>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={onBack} className="btn-ghost" style={{ fontSize: 12 }}>← Quay lại kịch bản</button>
            {html && (
              <button
                onClick={regenFull}
                disabled={isGenning}
                className="btn-ghost"
                style={{ fontSize: 12, opacity: isGenning ? 0.4 : 1 }}
              >
                ↺ Gen lại tất cả
              </button>
            )}
            <button
              onClick={onBuild}
              disabled={!allDone || isGenning}
              className="btn-primary"
              style={{
                background: theme.accent,
                boxShadow: `0 12px 32px -4px ${theme.accent}99`,
                fontSize: 13,
                opacity: (!allDone || isGenning) ? 0.4 : 1,
              }}
            >
              <span>🎬 Dựng video MP4 →</span>
            </button>
          </div>
        </div>

        {/* Dirty flag warning */}
        {!allClean && html && (
          <div style={{ marginTop: 10, fontSize: 11, color: "var(--accent3)" }}>
            ⚠ Có scene đã sửa nhưng chưa regen — bấm "↻ Regen scene" trong panel bên phải để cập nhật.
          </div>
        )}
      </div>

      {/* ── Progress bar + Gen controls ── */}
      <div className="fade-up" style={{
        padding: "16px 20px",
        borderRadius: "var(--r-xl)",
        background: "var(--gray-1)",
        border: `1px solid ${isGenning ? `${theme.accent}66` : "var(--gray-3)"}`,
        marginBottom: 20,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        transition: "border-color 0.3s",
      }}>
        {/* Progress header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {isGenning ? (
              <span style={{
                width: 14, height: 14,
                border: `2px solid ${theme.accent}`,
                borderTopColor: "transparent",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
                display: "inline-block",
                flexShrink: 0,
              }} />
            ) : allDone ? (
              <span style={{ fontSize: 16 }}>✅</span>
            ) : (
              <span style={{ fontSize: 16 }}>🎬</span>
            )}
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--white)" }}>
                {allDone
                  ? `Hoàn tất — ${total} scene đã gen`
                  : isGenning
                  ? `Đang gen scene ${(genningIdx ?? 0) + 1}/${total}…`
                  : doneSoFar === 0
                  ? `Sẵn sàng gen ${total} scene`
                  : `${doneSoFar}/${total} scene đã gen`}
              </div>
              {isGenning && (
                <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 2 }}>
                  Mỗi scene mất ~10-25 giây
                </div>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {isAutoGen ? (
              <button
                onClick={handleStopGen}
                className="btn-ghost"
                style={{ fontSize: 12, borderColor: "#f87171", color: "#f87171" }}
              >
                ⏹ Dừng
              </button>
            ) : allDone ? null : (
              <>
                {nextPendingIdx >= 0 && (
                  <button
                    onClick={handleGenNext}
                    disabled={isGenning}
                    className="btn-primary"
                    style={{
                      fontSize: 12,
                      background: theme.accent,
                      boxShadow: `0 8px 20px -4px ${theme.accent}66`,
                      opacity: isGenning ? 0.5 : 1,
                    }}
                  >
                    {doneSoFar === 0
                      ? "▶ Gen scene 1"
                      : `→ Gen scene ${nextPendingIdx + 1}`}
                  </button>
                )}
                {nextPendingIdx >= 0 && doneSoFar > 0 && (
                  <button
                    onClick={handleGenAll}
                    disabled={isGenning}
                    className="btn-ghost"
                    style={{ fontSize: 12, opacity: isGenning ? 0.5 : 1 }}
                  >
                    ⏭ Gen tất cả còn lại
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div style={{
          height: 4,
          borderRadius: 99,
          background: "var(--gray-3)",
          overflow: "hidden",
        }}>
          <div style={{
            height: "100%",
            width: `${(doneSoFar / total) * 100}%`,
            background: `linear-gradient(90deg, ${theme.accent}, ${theme.accent}bb)`,
            borderRadius: 99,
            transition: "width 0.5s cubic-bezier(0.4,0,0.2,1)",
          }} />
        </div>

        {/* Scene status pills */}
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {scenePlan.scenes.map((s, i) => {
            const st = sceneStatuses[i];
            return (
              <button
                key={s.id}
                onClick={() => { if (st === "done") setActiveIdx(i); }}
                title={`Scene ${i + 1}: ${s.title}`}
                style={{
                  width: 28, height: 24,
                  borderRadius: 6,
                  border: `1px solid ${
                    st === "done" ? `${theme.accent}88` :
                    st === "generating" ? `${theme.accent}44` :
                    st === "error" ? "rgba(248,113,113,0.5)" :
                    "var(--gray-3)"
                  }`,
                  background: st === "done"
                    ? `${theme.accent}22`
                    : st === "generating"
                    ? `${theme.accent}0a`
                    : "var(--gray-2)",
                  cursor: st === "done" ? "pointer" : "default",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
                  color: st === "done" ? theme.accent : "var(--gray-5)",
                  transition: "all 0.2s",
                  position: "relative",
                }}
              >
                {st === "generating" ? (
                  <span style={{
                    width: 8, height: 8,
                    border: `1.5px solid ${theme.accent}`,
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                    animation: "spin 0.8s linear infinite",
                    display: "inline-block",
                  }} />
                ) : (
                  (i + 1).toString().padStart(2, "0")
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Error ── */}
      {genError && (
        <div style={{
          padding: 16, borderRadius: 12, background: "rgba(239,68,68,0.05)",
          border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5", marginBottom: 16, fontSize: 13,
        }}>
          ✕ {genError}
          {nextPendingIdx >= 0 && (
            <button onClick={handleGenNext} className="btn-ghost" style={{ marginLeft: 12, fontSize: 11 }}>
              Thử lại
            </button>
          )}
        </div>
      )}

      {/* ── 3-column editor (chỉ hiện khi đã có HTML) ── */}
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
                const st      = sceneStatuses[i];
                const isDone  = st === "done";
                return (
                  <button
                    key={s.id}
                    onClick={() => { if (isDone) setActiveIdx(i); }}
                    disabled={!isDone}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 12px",
                      borderRadius: 12,
                      border: isActive ? `1px solid ${theme.accent}` : "1px solid var(--gray-3)",
                      background: isActive ? `${theme.accent}1a` : "var(--gray-2)",
                      cursor: isDone ? "pointer" : "default",
                      textAlign: "left",
                      transition: "all 0.2s",
                      opacity: isDone ? 1 : 0.45,
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, flexShrink: 0,
                      borderRadius: 6,
                      background: isActive ? theme.accent : st === "done" ? `${theme.accent}33` : "var(--gray-3)",
                      color: isActive ? "var(--black)" : st === "done" ? theme.accent : "var(--gray-6)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 800,
                    }}>
                      {st === "generating" ? (
                        <span style={{
                          width: 10, height: 10,
                          border: `2px solid ${theme.accent}`,
                          borderTopColor: "transparent",
                          borderRadius: "50%",
                          animation: "spin 0.8s linear infinite",
                          display: "inline-block",
                        }} />
                      ) : (
                        (i + 1).toString().padStart(2, "0")
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 12, fontWeight: 700, color: "var(--white)",
                        whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden",
                      }}>
                        {s.title}
                      </div>
                    </div>
                    <div style={{ flexShrink: 0, display: "flex", gap: 4 }}>
                      {statusDot(i)}
                      {dirty && isDone && (
                        <span title="Đã sửa, chưa regen" style={{
                          width: 8, height: 8, borderRadius: "50%",
                          background: "var(--accent3)",
                          boxShadow: "0 0 8px var(--accent3)",
                        }} />
                      )}
                    </div>
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
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {/* Subtitle toggle */}
                <button
                  id="subtitle-toggle-btn"
                  onClick={() => setScenePlan({ ...scenePlan, subtitlesEnabled: !showSubtitles })}
                  title={showSubtitles ? "Ẩn phụ đề" : "Hiện phụ đề"}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "5px 10px",
                    borderRadius: "var(--r-full)",
                    border: `1px solid ${showSubtitles ? "rgba(249,115,22,0.5)" : "rgba(255,255,255,0.12)"}`,
                    background: showSubtitles ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.04)",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <span style={{
                    display: "inline-flex",
                    width: 28, height: 16,
                    borderRadius: 99,
                    background: showSubtitles ? theme.accent : "rgba(255,255,255,0.15)",
                    position: "relative",
                    transition: "background 0.2s ease",
                    flexShrink: 0,
                  }}>
                    <span style={{
                      position: "absolute",
                      top: 2, left: showSubtitles ? 14 : 2,
                      width: 12, height: 12,
                      borderRadius: "50%",
                      background: "#fff",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
                      transition: "left 0.2s ease",
                    }} />
                  </span>
                  <span style={{
                    fontSize: 10, fontWeight: 700,
                    color: showSubtitles ? theme.accent : "var(--gray-5)",
                    letterSpacing: "0.04em",
                    transition: "color 0.2s ease",
                  }}>
                    {showSubtitles ? "CC ON" : "CC OFF"}
                  </span>
                </button>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--gray-5)" }}>
                  {(activeIdx + 1).toString().padStart(2, "0")} / {total.toString().padStart(2, "0")}
                </div>
              </div>
            </div>
            <ScenePreviewIframe fullHtml={html} sceneIndex={activeIdx + 1} showSubtitles={showSubtitles} />
            <div style={{ marginTop: 8, fontSize: 11, color: "var(--gray-5)" }}>
              {active?.title}
            </div>

            {/* Navigation arrows */}
            <div style={{ display: "flex", gap: 8, marginTop: 10, justifyContent: "center" }}>
              <button
                onClick={() => {
                  let prev = activeIdx - 1;
                  while (prev >= 0 && sceneStatuses[prev] !== "done") prev--;
                  if (prev >= 0) setActiveIdx(prev);
                }}
                disabled={activeIdx === 0 || !sceneStatuses.slice(0, activeIdx).some(s => s === "done")}
                className="btn-ghost"
                style={{ fontSize: 12, padding: "6px 14px" }}
              >
                ← Prev
              </button>
              <button
                onClick={() => {
                  let next = activeIdx + 1;
                  while (next < total && sceneStatuses[next] !== "done") next++;
                  if (next < total) setActiveIdx(next);
                }}
                disabled={!sceneStatuses.slice(activeIdx + 1).some(s => s === "done")}
                className="btn-ghost"
                style={{ fontSize: 12, padding: "6px 14px" }}
              >
                Next →
              </button>
            </div>
          </div>

          {/* RIGHT — edit panel */}
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 18,
            maxHeight: "calc(100vh - 180px)", overflowY: "auto",
            display: "flex", flexDirection: "column", gap: 16,
          }}>
            {sceneStatuses[activeIdx] !== "done" ? (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
                <p style={{ fontSize: 13, color: "var(--gray-5)" }}>
                  Scene {activeIdx + 1} chưa được gen.
                </p>
                {nextPendingIdx === activeIdx && (
                  <button
                    onClick={handleGenNext}
                    disabled={isGenning}
                    className="btn-primary"
                    style={{ marginTop: 12, background: theme.accent, fontSize: 12 }}
                  >
                    ▶ Gen scene {activeIdx + 1}
                  </button>
                )}
              </div>
            ) : (
              <>
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
                    disabled={regenStatus !== "idle" || isGenning}
                    className="btn-primary"
                    style={{
                      flex: 1, fontSize: 12,
                      background: sceneFlags[activeIdx] ? theme.accent : "var(--gray-3)",
                      color: sceneFlags[activeIdx] ? "var(--black)" : "var(--gray-6)",
                      boxShadow: sceneFlags[activeIdx] ? `0 8px 24px -4px ${theme.accent}66` : "none",
                      opacity: (regenStatus !== "idle" || isGenning) ? 0.5 : 1,
                    }}
                  >
                    <span>
                      {regenScene === activeIdx + 1 ? "⏳ Đang regen…" : "↻ Regen scene"}
                    </span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Theme + Voice — full width below ── */}
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
              Đổi theme sẽ cập nhật trực tiếp màu sắc giao diện mà không cần gen lại.
            </p>
          </div>
          <div style={{
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            borderRadius: "var(--r-xl)", padding: 20,
          }}>
            <div className="hero-eyebrow" style={{ fontSize: 10, marginBottom: 12 }}>Giọng đọc TTS</div>

            {/* Premium 5-second Scenario Audio Preview */}
            <div style={{ 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "space-between", 
              marginBottom: 16,
              padding: "10px 14px",
              borderRadius: 12,
              background: "rgba(0,0,0,0.15)",
              border: "1px solid rgba(255,255,255,0.06)"
            }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--white)", marginBottom: 2 }}>
                  🔊 Nghe thử 5s giọng đọc kịch bản
                </div>
                <div style={{ fontSize: 9, color: "var(--gray-6)" }}>
                  Nghe thử giọng đọc thực tế của Phân cảnh 1
                </div>
              </div>
              <button
                type="button"
                onClick={handlePlay5sPreview}
                disabled={previewLoading || scenePlan.scenes.length === 0}
                style={{
                  padding: "6px 14px",
                  borderRadius: 20,
                  background: playingPreview ? "var(--accent)" : "rgba(249,115,22,0.1)",
                  border: `1px solid ${playingPreview ? "var(--accent)" : "rgba(249,115,22,0.3)"}`,
                  color: playingPreview ? "#000" : "var(--accent)",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  transition: "all 0.2s ease",
                  boxShadow: playingPreview ? "0 0 12px var(--accent)" : "none",
                }}
              >
                {previewLoading ? (
                  <span style={{
                    width: 10, height: 10,
                    border: "2px solid currentColor",
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                    animation: "spin 0.8s linear infinite",
                  }} />
                ) : playingPreview ? (
                  <>
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                    <span>Dừng</span>
                  </>
                ) : (
                  <>
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                    <span>Nghe thử 5s</span>
                  </>
                )}
              </button>
            </div>

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
            setScene(activeIdx, { imageUrl: url, imageAsset: undefined });
            if (html && sceneStatuses[activeIdx] === "done") {
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
