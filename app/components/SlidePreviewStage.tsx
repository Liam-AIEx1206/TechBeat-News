"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import type { ScenePlan, Scene } from "@/types/scene";
import { getTheme } from "@/types/scene";
import { ImagePicker } from "@/components/ImagePicker";
import { ImageIcon } from "lucide-react";

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
  const { data: session } = useSession();
  // x-user-email: backend dùng để ghi chi phí LLM vào tài khoản user (như video)
  const userEmail = session?.user?.email ?? "";
  const authHeaders: Record<string, string> = userEmail ? { "x-user-email": userEmail } : {};
  const [svgs, setSvgs] = useState<string[]>(() => loadSvgCache(scenePlan.title));
  const [activeIdx, setActiveIdx] = useState(0);
  const [genStates, setGenStates] = useState<("pending" | "loading" | "done" | "error")[]>(
    () => scenePlan.scenes.map((_, i) => loadSvgCache(scenePlan.title)[i] ? "done" : "pending")
  );
  const [errors, setErrors] = useState<(string | null)[]>(scenePlan.scenes.map(() => null));
  const [genAll, setGenAll] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const theme = getTheme(scenePlan.theme);

  // Luồng slide dùng styleId (không phải theme màu) — hiển thị tên style đã chọn
  // thay vì luôn "Cyber Orange" (theme mặc định). Resolve styleId → label từ /styles.
  const [styleLabel, setStyleLabel] = useState("");
  useEffect(() => {
    if (!scenePlan.styleId) return;
    const listUrl = process.env.NODE_ENV === "development" ? `${API}/styles` : `/api/proxy/styles`;
    let alive = true;
    fetch(listUrl)
      .then(r => r.json())
      .then(d => {
        if (!alive) return;
        const found = (d.styles ?? []).find((s: { id: string; label: string }) => s.id === scenePlan.styleId);
        if (found?.label) setStyleLabel(found.label);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [scenePlan.styleId, API]);

  const endpoint = process.env.NODE_ENV === "development"
    ? `${API}/gen-slide-one`
    : `/api/proxy/gen-slide-one`;
  const replaceImageEndpoint = process.env.NODE_ENV === "development"
    ? `${API}/replace-slide-image`
    : `/api/proxy/replace-slide-image`;

  // scenesOverride: dùng khi vừa đổi 1 field (vd. imageUrl) và cần regen NGAY
  // bằng giá trị mới — setScenePlan là async nên đọc từ closure scenePlan.scenes
  // ngay sau khi gọi setScenePlan sẽ dính giá trị CŨ.
  const genSlide = useCallback(async (idx: number, abort?: AbortSignal, scenesOverride?: Scene[]) => {
    const scenes = scenesOverride ?? scenePlan.scenes;
    setGenStates(p => { const n = [...p]; n[idx] = "loading"; return n; });
    setErrors(p => { const n = [...p]; n[idx] = null; return n; });
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          title: scenePlan.title,
          scenes,
          totalDuration: scenePlan.totalDuration,
          theme: scenePlan.theme,
          styleId: scenePlan.styleId,
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
  }, [scenePlan, endpoint, userEmail]);  // eslint-disable-line react-hooks/exhaustive-deps -- authHeaders derive từ userEmail

  // ── Đổi ảnh: KHÔNG regen nội dung nếu slide đã có khung ảnh sẵn ──────────
  const [imagePickerOpen, setImagePickerOpen] = useState(false);
  const [imageSwapping, setImageSwapping] = useState(false);
  const activeSvg = svgs[activeIdx];
  const activeHasImage = !!activeSvg && /<image\b/i.test(activeSvg);

  async function handleImagePick(url: string) {
    if (!url) return; // hideRemoveOption=true nên nhánh này thực tế không kích hoạt
    if (activeHasImage && activeSvg) {
      // Swap nhẹ: chỉ đổi href, giữ nguyên chữ/icon/layout đã sinh — không gọi LLM.
      setImageSwapping(true);
      try {
        const res = await fetch(replaceImageEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ svg: activeSvg, newImageUrl: url }),
        });
        if (!res.ok) throw new Error((await res.json()).detail ?? "Lỗi đổi ảnh");
        const data = await res.json();
        if (data.replaced) {
          setSvgs(prev => {
            const next = [...prev];
            next[activeIdx] = data.svg;
            saveSvgCache(scenePlan.title, next);
            return next;
          });
        }
      } catch (err) {
        setErrors(p => { const n = [...p]; n[activeIdx] = err instanceof Error ? err.message : "Lỗi đổi ảnh"; return n; });
      } finally {
        setImageSwapping(false);
      }
    } else {
      // Slide chưa có khung ảnh — không thể "chỉ thay vị trí ảnh" vì chưa có
      // vị trí nào cả. Gán imageUrl vào scene rồi regen ĐÚNG slide này để
      // model vẽ ra bố cục có ảnh.
      const nextScenes = scenePlan.scenes.map((s, i) => i === activeIdx ? { ...s, imageUrl: url } : s);
      setScenePlan({ ...scenePlan, scenes: nextScenes });
      genSlide(activeIdx, undefined, nextScenes);
    }
  }

  // Gen TUẦN TỰ (như luồng video): xong slide này mới sang slide kế —
  // mỗi slide một call riêng đủ context, không nhồi cả deck vào một lần gen.
  async function genSequential(indices: number[]) {
    if (indices.length === 0) return;
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;
    setGenAll(true);
    for (const i of indices) {
      if (abort.signal.aborted) break;
      setActiveIdx(i); // preview bám theo slide đang gen để user xem tiến độ
      await genSlide(i, abort.signal);
    }
    setGenAll(false);
  }

  /** Regen toàn bộ deck từ đầu */
  function genAll_() {
    return genSequential(scenePlan.scenes.map((_, i) => i));
  }

  /** Các slide CHƯA gen xong (pending/error) theo thứ tự */
  const remainingIdxs = genStates
    .map((s, i) => (s === "done" || s === "loading" ? -1 : i))
    .filter(i => i >= 0);

  /** Gen đúng 1 slide kế tiếp chưa xong */
  function genNext() {
    if (remainingIdxs.length > 0) return genSequential([remainingIdxs[0]]);
  }

  /** Gen lần lượt tất cả slide còn lại (không regen slide đã xong) */
  function genRemaining() {
    return genSequential(remainingIdxs);
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
            {scenePlan.scenes.length} slide · {scenePlan.styleId
              ? `Style: ${styleLabel || scenePlan.styleId}`
              : `Theme: ${theme.name}`}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={onBack} className="btn-ghost" style={{ fontSize: 13 }}>← Quay lại</button>
          {genAll ? (
            <button onClick={stopGen} className="btn-ghost" style={{ fontSize: 13, color: "var(--red)" }}>⬛ Dừng</button>
          ) : (
            <>
              {remainingIdxs.length > 0 && (
                <button onClick={genNext} disabled={anyLoading} className="btn-ghost" style={{ fontSize: 13, borderColor: "rgba(249,115,22,0.35)", color: "var(--accent2)" }}>
                  ▶ Gen slide tiếp theo
                </button>
              )}
              {remainingIdxs.length > 1 && (
                <button onClick={genRemaining} disabled={anyLoading} className="btn-ghost" style={{ fontSize: 13, borderColor: "rgba(249,115,22,0.35)", color: "var(--accent2)" }}>
                  ⏩ Gen {remainingIdxs.length} slide còn lại
                </button>
              )}
              <button onClick={genAll_} disabled={anyLoading} className="btn-ghost" style={{ fontSize: 13 }}>
                ↺ Gen lại tất cả
              </button>
            </>
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

        {/* Middle: SVG preview — chiếm tối đa không gian, SVG scale theo khung */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: "rgba(0,0,0,0.3)", minWidth: 0 }}>
          <div style={{ width: "100%", maxWidth: "min(1400px, calc((100vh - 220px) * 16 / 9))", aspectRatio: "16/9", position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-2)", background: "#08080f", boxShadow: "0 24px 80px rgba(0,0,0,0.55)" }}>
            {svgs[activeIdx] ? (
              <div
                dangerouslySetInnerHTML={{
                  __html: svgs[activeIdx].replace(
                    /<svg\b/i,
                    '<svg style="width:100%;height:100%;display:block" preserveAspectRatio="xMidYMid meet"'
                  ),
                }}
                style={{ width: "100%", height: "100%" }}
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

          {/* Ảnh minh họa */}
          {svgs[activeIdx] && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--gray-5)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                Ảnh minh họa
              </div>
              <button
                onClick={() => setImagePickerOpen(true)}
                disabled={imageSwapping}
                className="btn-ghost"
                style={{ width: "100%", fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, opacity: imageSwapping ? 0.6 : 1 }}
              >
                <ImageIcon size={14} />
                {imageSwapping ? "Đang đổi ảnh..." : activeHasImage ? "Đổi ảnh khác" : "Thêm ảnh cho slide"}
              </button>
              <div style={{ fontSize: 10, color: "var(--gray-6)", marginTop: 6, lineHeight: 1.5 }}>
                {activeHasImage
                  ? "Chỉ thay vị trí ảnh — chữ và bố cục giữ nguyên, không cần regen."
                  : "Slide này chưa có khung ảnh — chọn ảnh sẽ regen lại slide để thêm khung."}
              </div>
            </div>
          )}

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

      <ImagePicker
        open={imagePickerOpen}
        initialQuery={scenePlan.scenes[activeIdx]?.imageQuery || scenePlan.scenes[activeIdx]?.title || ""}
        onClose={() => setImagePickerOpen(false)}
        onPick={handleImagePick}
        hideRemoveOption
      />
    </div>
  );
}
