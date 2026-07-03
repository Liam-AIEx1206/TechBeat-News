"use client";

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import type { ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onBack: () => void;
}

const BUILD_KEY = "xnew_slide_build_state";
const SLIDE_LS_KEY = "xnew_slide_svgs";

type StageKey = "finalize" | "convert";
type StageState = "pending" | "active" | "done" | "error";

const STAGES: { key: StageKey; label: string; detail: string }[] = [
  { key: "finalize", label: "Chuẩn bị SVG",    detail: "Xử lý & tối ưu SVG" },
  { key: "convert",  label: "Xuất PPTX",        detail: "svg_to_pptx → DrawingML native shapes" },
];

function loadBuild(title: string) {
  try {
    const raw = localStorage.getItem(BUILD_KEY);
    if (!raw) return null;
    const b = JSON.parse(raw);
    if (b.title !== title || Date.now() - b.savedAt > 86_400_000) { localStorage.removeItem(BUILD_KEY); return null; }
    return b;
  } catch { return null; }
}

function saveBuild(title: string, patch: object) {
  try {
    const prev = loadBuild(title) ?? {};
    localStorage.setItem(BUILD_KEY, JSON.stringify({ ...prev, ...patch, title, savedAt: Date.now() }));
  } catch { /* quota */ }
}

function loadSvgs(title: string): string[] {
  try {
    const raw = localStorage.getItem(SLIDE_LS_KEY);
    if (!raw) return [];
    const obj = JSON.parse(raw);
    return obj.title === title ? (obj.svgs ?? []) : [];
  } catch { return []; }
}

export function SlideExporter({ scenePlan, onBack }: Props) {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const { data: session } = useSession();
  const userEmail = session?.user?.email ?? "";
  const saved = loadBuild(scenePlan.title);

  const [running, setRunning]           = useState(false);
  const [downloading, setDownloading]   = useState(false);
  const [done, setDone]                 = useState(saved?.done ?? false);
  const [pptxUrl, setPptxUrl]           = useState<string>(saved?.pptxUrl ?? "");
  const [error, setError]               = useState<string>(saved?.error ?? "");
  const [slideErrors, setSlideErrors]   = useState<{index: number; message: string}[]>([]);
  const [status, setStatus]             = useState<string>(saved?.done ? "Hoàn tất" : "Sẵn sàng");
  const [stageStates, setStageStates]   = useState<Record<StageKey, StageState>>(
    saved?.stageStates ?? { finalize: "pending", convert: "pending" }
  );
  const abortRef = useRef<AbortController | null>(null);

  const fullPptxUrl = pptxUrl ? `${API}${pptxUrl}` : "";

  const endpoint = process.env.NODE_ENV === "development"
    ? `${API}/build-slides`
    : `/api/proxy/build-slides`;

  function setStage(key: StageKey, state: StageState) {
    setStageStates(p => ({ ...p, [key]: state }));
  }

  async function build() {
    const svgs = loadSvgs(scenePlan.title);
    if (!svgs.length || svgs.some(s => !s)) {
      setError("Chưa gen đủ SVG cho tất cả slide — quay lại màn Xem trước để gen.");
      return;
    }

    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    setRunning(true); setDone(false); setError(""); setPptxUrl(""); setSlideErrors([]);
    setStageStates({ finalize: "active", convert: "pending" });
    setStatus("Đang xử lý...");
    localStorage.removeItem(BUILD_KEY);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(userEmail ? { "x-user-email": userEmail } : {}) },
        body: JSON.stringify({
          title: scenePlan.title,
          scenes: scenePlan.scenes,
          svgs,
          theme: scenePlan.theme,
          sessionId: scenePlan.sessionId,
        }),
        signal: abort.signal,
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Build thất bại");

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      const handle = (ev: {type: string; message?: string; pptxUrl?: string; index?: number; fileSize?: number}) => {
        if (ev.type === "status") {
          setStatus(ev.message ?? "");
          if (ev.message?.includes("finalize") || ev.message?.includes("Chuẩn bị")) {
            setStage("finalize", "active");
          } else if (ev.message?.includes("convert") || ev.message?.includes("PPTX")) {
            setStage("finalize", "done");
            setStage("convert", "active");
          }
        } else if (ev.type === "warning") {
          setStatus(`⚠ ${ev.message}`);
        } else if (ev.type === "slide_error") {
          setSlideErrors(p => [...p, { index: ev.index ?? 0, message: ev.message ?? "Lỗi" }]);
        } else if (ev.type === "done" && ev.pptxUrl) {
          setStage("finalize", "done");
          setStage("convert", "done");
          setPptxUrl(ev.pptxUrl);
          setDone(true);
          setStatus(`Hoàn tất · ${ev.fileSize ?? "?"} MB`);
          saveBuild(scenePlan.title, { done: true, pptxUrl: ev.pptxUrl, stageStates: { finalize: "done", convert: "done" }, error: "" });
        } else if (ev.type === "error") {
          throw new Error(ev.message ?? "Lỗi pipeline");
        }
      };

      while (true) {
        const { done: sd, value } = await reader.read();
        if (sd) { if (buf.trim()) { for (const ln of buf.split("\n\n")) { if (ln.startsWith("data: ")) { try { handle(JSON.parse(ln.slice(6))); } catch {} } } } break; }
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n"); buf = parts.pop() ?? "";
        for (const ln of parts) { if (ln.startsWith("data: ")) { try { handle(JSON.parse(ln.slice(6))); } catch {} } }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const msg = err instanceof Error ? err.message : "Build thất bại";
      setError(msg);
      setStatus("Lỗi");
      setStageStates(p => {
        const next = { ...p };
        (Object.keys(next) as StageKey[]).forEach(k => { if (next[k] === "active") next[k] = "error"; });
        return next;
      });
      saveBuild(scenePlan.title, { done: false, error: msg });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {error && (
        <div style={{ padding: "12px 18px", borderRadius: 14, background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--red)", fontSize: 13 }}>
          Lỗi: {error}
        </div>
      )}

      {slideErrors.length > 0 && (
        <div style={{ padding: "12px 18px", borderRadius: 14, background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)", fontSize: 12, color: "#ef4444" }}>
          {slideErrors.map((e, i) => <div key={i}>Slide {e.index + 1}: {e.message}</div>)}
        </div>
      )}

      {/* Main panel */}
      <div style={{
        background: "linear-gradient(180deg, rgba(20,15,11,0.72) 0%, rgba(10,8,6,0.82) 100%)",
        border: `1px solid ${done ? "rgba(34,197,94,0.35)" : "rgba(249,115,22,0.32)"}`,
        borderRadius: 28, overflow: "hidden", position: "relative",
        boxShadow: done
          ? "0 0 0 1px rgba(34,197,94,0.08), 0 24px 60px -24px rgba(34,197,94,0.35)"
          : running
          ? "0 0 0 1px rgba(249,115,22,0.12), 0 24px 70px -20px rgba(249,115,22,0.5)"
          : "0 0 0 1px rgba(249,115,22,0.06), 0 20px 60px -28px rgba(249,115,22,0.28)",
      }}>
        <div style={{ padding: "28px 32px" }}>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{
                  padding: "4px 12px", borderRadius: 20, fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase",
                  background: done ? "rgba(34,197,94,0.12)" : running ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.06)",
                  color: done ? "#22c55e" : running ? "var(--accent)" : "var(--gray-5)",
                  border: `1px solid ${done ? "rgba(34,197,94,0.25)" : running ? "rgba(249,115,22,0.25)" : "rgba(255,255,255,0.08)"}`,
                }}>
                  {done ? "✓ PPTX Sẵn sàng" : running ? "Đang xuất..." : "Chuẩn bị xuất"}
                </span>
              </div>
              <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: "-0.02em", marginBottom: 8 }}>{scenePlan.title}</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span style={{ padding: "3px 10px", background: "rgba(255,255,255,0.05)", borderRadius: 20, fontSize: 11, color: "var(--gray-5)", fontWeight: 600 }}>
                  {scenePlan.scenes.length} slide
                </span>
                <span style={{ padding: "3px 10px", background: "rgba(255,255,255,0.05)", borderRadius: 20, fontSize: 11, color: "var(--gray-5)", fontWeight: 600 }}>
                  PPTX · native shapes
                </span>
              </div>
            </div>
          </div>

          {/* Status */}
          {status && (
            <div style={{ fontSize: 12, color: "var(--gray-5)", marginBottom: 16, fontFamily: "var(--font-mono)" }}>
              {status}
            </div>
          )}

          {/* Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            {!running && !done && (
              <button onClick={() => { localStorage.removeItem(BUILD_KEY); onBack(); }} className="btn-ghost">← Quay lại</button>
            )}
            {!running && (
              <button onClick={build} className="btn-primary magnetic">
                <span>{done ? "Xuất lại" : "Bắt đầu xuất PPTX"}</span>
              </button>
            )}
            {running && (
              <button onClick={() => abortRef.current?.abort()} className="btn-ghost" style={{ color: "var(--red)" }}>
                ⬛ Huỷ
              </button>
            )}
          </div>
        </div>

        {/* Pipeline stages */}
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", padding: "20px 32px", display: "flex", gap: 24 }}>
          {STAGES.map((s, i) => {
            const st = stageStates[s.key];
            return (
              <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {i > 0 && <div style={{ width: 32, height: 1, background: "rgba(255,255,255,0.08)" }} />}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
                    background: st === "done" ? "rgba(34,197,94,0.12)" : st === "active" ? "rgba(249,115,22,0.12)" : st === "error" ? "rgba(239,68,68,0.12)" : "rgba(255,255,255,0.04)",
                    border: `1px solid ${st === "done" ? "rgba(34,197,94,0.25)" : st === "active" ? "rgba(249,115,22,0.25)" : st === "error" ? "rgba(239,68,68,0.25)" : "rgba(255,255,255,0.08)"}`,
                    fontSize: 14,
                    color: st === "done" ? "#22c55e" : st === "active" ? "var(--accent)" : st === "error" ? "#ef4444" : "var(--gray-5)",
                  }}>
                    {st === "done" ? "✓" : st === "active" ? "…" : st === "error" ? "!" : i + 1}
                  </div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: st === "pending" ? "var(--gray-5)" : "var(--white)" }}>{s.label}</div>
                    <div style={{ fontSize: 10, color: "var(--gray-6)" }}>{s.detail}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Result download */}
      {done && fullPptxUrl && (
        <div style={{
          padding: "28px 32px", borderRadius: 24, background: "rgba(34,197,94,0.04)",
          border: "1px solid rgba(34,197,94,0.2)", display: "flex", flexDirection: "column", gap: 16,
        }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#22c55e" }}>✓ PPTX đã sẵn sàng tải xuống</div>
          <div style={{ fontSize: 17, fontWeight: 900 }}>
            {scenePlan.title}<span style={{ color: "var(--gray-5)", fontWeight: 400 }}>.pptx</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--gray-5)" }}>
            File PPTX với native DrawingML shapes — có thể chỉnh sửa trực tiếp trong PowerPoint / Keynote / LibreOffice / Canva.
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {/* Tải qua fetch→blob thay vì <a href download>: URL backend là
                cross-origin ở dev nên browser BỎ QUA thuộc tính download và
                điều hướng thẳng tới file → bắn dialog "Leave site?" rất khó
                chịu. Blob + object URL tải trong nền, không rời trang. */}
            <button
              onClick={async () => {
                if (downloading) return;
                setDownloading(true);
                try {
                  const res = await fetch(fullPptxUrl);
                  if (!res.ok) throw new Error(`HTTP ${res.status}`);
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `${scenePlan.title.replace(/[\\/:*?"<>|]/g, "_")}.pptx`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  setTimeout(() => URL.revokeObjectURL(url), 5000);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Tải file thất bại");
                } finally {
                  setDownloading(false);
                }
              }}
              disabled={downloading}
              className="btn-primary"
              style={{ fontSize: 13, opacity: downloading ? 0.6 : 1 }}
            >
              <span>{downloading ? "Đang tải..." : "⬇ Tải xuống PPTX"}</span>
            </button>
            {/* Browser không render được .pptx — "mở tab mới" chỉ tải lại file.
                Xem online cần Office viewer của Microsoft, và viewer đó phải
                tải được file → chỉ hoạt động khi app deploy public (không
                phải localhost). */}
            {typeof window !== "undefined" && !/^(localhost|127\.|192\.168\.|10\.)/.test(window.location.hostname) && (
              <a
                href={`https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(new URL(fullPptxUrl, window.location.origin).href)}`}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost"
                style={{ textDecoration: "none", fontSize: 13 }}
              >
                ↗ Xem online (PowerPoint)
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
