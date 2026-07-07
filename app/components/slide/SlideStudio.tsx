"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import {
  listStyles, listFonts, createSession, startGenerate, getSession,
  subscribeProgress, retryFailedPages, pageUrl, exportDownloadUrl,
  type StyleItem, type FontItem, type GeneratedPage, type ExportKind,
} from "@/lib/slideEngine";

type Step = "input" | "generating" | "preview";

/* ─────────────────────────  ROOT  ───────────────────────── */
export function SlideStudio() {
  const [step, setStep] = useState<Step>("input");
  const [sessionId, setSessionId] = useState("");
  const [title, setTitle] = useState("");
  const [initialPages, setInitialPages] = useState<GeneratedPage[]>([]);

  return (
    <div style={{ minHeight: "100vh", background: "var(--black)", color: "var(--white)" }}>
      <StudioHeader step={step} />
      {step === "input" && (
        <InputStep
          onStarted={(sid, t) => { setSessionId(sid); setTitle(t); setInitialPages([]); setStep("generating"); }}
        />
      )}
      {step === "generating" && (
        <GeneratingStep sessionId={sessionId} title={title} onDone={(pages) => { setInitialPages(pages); setStep("preview"); }} />
      )}
      {step === "preview" && (
        <PreviewStep sessionId={sessionId} title={title} initialPages={initialPages} onBack={() => setStep("input")} />
      )}
    </div>
  );
}

function StudioHeader({ step }: { step: Step }) {
  const steps: { k: Step; n: number; label: string }[] = [
    { k: "input", n: 1, label: "Nhập" },
    { k: "generating", n: 2, label: "Sinh slide" },
    { k: "preview", n: 3, label: "Xem & Xuất" },
  ];
  const order: Step[] = ["input", "generating", "preview"];
  const cur = order.indexOf(step);
  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "16px 24px", borderBottom: "1px solid var(--gray-2)" }}>
      {steps.map((s, i) => {
        const done = cur > i, active = cur === i;
        return (
          <div key={s.k} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 8, padding: "6px 14px", borderRadius: 99,
              background: active ? "var(--accent)" : done ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.04)",
              color: active ? "#000" : done ? "var(--accent)" : "var(--gray-5)",
              fontSize: 12, fontWeight: 800,
            }}>
              <span style={{ width: 16, height: 16, borderRadius: "50%", background: active ? "rgba(0,0,0,0.2)" : "var(--gray-3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9 }}>
                {done ? "✓" : s.n}
              </span>
              {s.label}
            </div>
            {i < steps.length - 1 && <div style={{ width: 28, height: 2, background: done ? "var(--accent)" : "var(--gray-3)" }} />}
          </div>
        );
      })}
    </header>
  );
}

/* ─────────────────────────  STEP 1 · INPUT  ───────────────────────── */
function InputStep({ onStarted }: { onStarted: (sessionId: string, title: string) => void }) {
  const [topic, setTopic] = useState("");
  const [pageCount, setPageCount] = useState(6);
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [styleId, setStyleId] = useState("");
  const [fonts, setFonts] = useState<FontItem[]>([]);
  const [titleFontId, setTitleFontId] = useState("");
  const [bodyFontId, setBodyFontId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [st, ft] = await Promise.all([listStyles(), listFonts().catch(() => ({ googleFonts: [], userFonts: [] }))]);
        setStyles(st);
        if (st[0]) setStyleId(st[0].id);
        setFonts([...(ft.googleFonts || []), ...(ft.userFonts || [])]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải được style/font");
      } finally { setLoading(false); }
    })();
  }, []);

  async function handleStart() {
    if (!topic.trim()) { setError("Nhập chủ đề trước đã."); return; }
    if (!styleId) { setError("Chọn một phong cách."); return; }
    setBusy(true); setError("");
    try {
      const sid = await createSession({
        topic: topic.trim(), styleId, pageCount,
        fontSelection: (titleFontId || bodyFontId) ? { titleFontId: titleFontId || undefined, bodyFontId: bodyFontId || undefined } : null,
      });
      await startGenerate(sid, topic.trim());
      onStarted(sid, topic.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được phiên");
      setBusy(false);
    }
  }

  const filtered = q
    ? styles.filter((s) => `${s.label} ${s.name?.en} ${s.category} ${s.styleKey}`.toLowerCase().includes(q.toLowerCase()))
    : styles;

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "32px clamp(16px,4vw,48px)" }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 8 }}>Tạo slide bằng AI</div>
        <h1 style={{ fontSize: "clamp(26px,3.4vw,40px)", fontWeight: 900, letterSpacing: "-0.03em" }}>Bạn muốn thuyết trình về điều gì?</h1>
      </div>

      {/* Chủ đề */}
      <label style={fieldLabel}>Chủ đề / mô tả</label>
      <textarea
        value={topic} onChange={(e) => setTopic(e.target.value)} rows={4}
        placeholder="VD: Giới thiệu game Duck Out — thể loại Extraction Shooter: tổng quan, gameplay loot/shoot/escape, vũ khí, kết luận kêu gọi chơi thử."
        style={{ width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 12, color: "var(--white)", fontSize: 14, padding: "14px 16px", fontFamily: "inherit", lineHeight: 1.6, resize: "vertical" }}
      />

      {/* Số trang + Font */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 20 }}>
        <div style={{ minWidth: 200 }}>
          <label style={fieldLabel}>Số trang: <b style={{ color: "var(--accent)" }}>{pageCount}</b></label>
          <input type="range" min={3} max={20} value={pageCount} onChange={(e) => setPageCount(Number(e.target.value))} style={{ width: "100%", accentColor: "var(--accent)" }} />
        </div>
        <div style={{ minWidth: 180, flex: 1 }}>
          <label style={fieldLabel}>Font tiêu đề</label>
          <select value={titleFontId} onChange={(e) => setTitleFontId(e.target.value)} style={selectStyle}>
            <option value="">AI tự chọn</option>
            {fonts.map((f) => <option key={f.id} value={f.id}>{f.family}</option>)}
          </select>
        </div>
        <div style={{ minWidth: 180, flex: 1 }}>
          <label style={fieldLabel}>Font nội dung</label>
          <select value={bodyFontId} onChange={(e) => setBodyFontId(e.target.value)} style={selectStyle}>
            <option value="">AI tự chọn</option>
            {fonts.map((f) => <option key={f.id} value={f.id}>{f.family}</option>)}
          </select>
        </div>
      </div>

      {/* Style picker */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 28, marginBottom: 12 }}>
        <label style={{ ...fieldLabel, marginBottom: 0 }}>Phong cách <span style={{ color: "var(--gray-5)" }}>({styles.length})</span></label>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm phong cách…" style={{ ...selectStyle, width: 220, padding: "8px 12px" }} />
      </div>
      {loading ? (
        <div style={{ color: "var(--gray-5)", fontSize: 13, padding: 20 }}>Đang tải phong cách…</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px,1fr))", gap: 12, maxHeight: 380, overflowY: "auto", padding: 4 }}>
          {filtered.map((s) => {
            const active = s.id === styleId;
            return (
              <button key={s.id} type="button" onClick={() => setStyleId(s.id)} style={{
                textAlign: "left", cursor: "pointer", padding: 14, borderRadius: 12,
                background: active ? "rgba(249,115,22,0.10)" : "rgba(255,255,255,0.03)",
                border: active ? "1.5px solid var(--accent)" : "1px solid var(--gray-3)",
              }}>
                {s.category && <div style={{ fontSize: 8, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: active ? "var(--accent)" : "var(--gray-5)", marginBottom: 6 }}>{s.category}</div>}
                <div style={{ fontSize: 13, fontWeight: 700, color: active ? "var(--accent)" : "var(--white)" }}>{s.name?.en || s.label}</div>
                {s.description && <div style={{ fontSize: 10, color: "var(--gray-5)", lineHeight: 1.4, marginTop: 4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{s.description}</div>}
              </button>
            );
          })}
        </div>
      )}

      {error && <div style={{ marginTop: 16, padding: "10px 14px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#fca5a5", fontSize: 13 }}>{error}</div>}

      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button onClick={handleStart} disabled={busy} className="btn-primary" style={{ fontSize: 14, padding: "14px 28px", opacity: busy ? 0.6 : 1 }}>
          {busy ? "Đang khởi tạo…" : "Sinh slide →"}
        </button>
      </div>
    </main>
  );
}

/* ─────────────────────────  STEP 2 · GENERATING  ───────────────────────── */
function GeneratingStep({ sessionId, title, onDone }: { sessionId: string; title: string; onDone: (pages: GeneratedPage[]) => void }) {
  const [pages, setPages] = useState<GeneratedPage[]>([]);
  const [label, setLabel] = useState("Đang chuẩn bị…");
  const [progress, setProgress] = useState(4);
  const [total, setTotal] = useState(0);
  const doneRef = useRef(false);

  useEffect(() => {
    const unsub = subscribeProgress((ev) => {
      const p = ev?.payload ?? ev;
      if (p?.label) setLabel(p.label);
      if (typeof p?.progress === "number") setProgress(Math.max(4, Math.min(99, p.progress)));
      if (typeof p?.totalPages === "number") setTotal(p.totalPages);
    });
    const poll = setInterval(async () => {
      try {
        const data = await getSession(sessionId);
        setPages(data.generatedPages);
        const pc = Number((data.session as any)?.page_count ?? data.generatedPages.length);
        const gc = Number((data.session as any)?.generated_count ?? data.generatedPages.filter((x) => x.status === "completed").length);
        const fc = Number((data.session as any)?.failed_count ?? data.generatedPages.filter((x) => x.status === "failed").length);
        if (pc > 0) setTotal(pc);
        if (!doneRef.current && pc > 0 && gc + fc >= pc) {
          doneRef.current = true;
          setProgress(100);
          clearInterval(poll); unsub();
          const finalPages = data.generatedPages;
          setTimeout(() => onDone(finalPages), 500);
        }
      } catch { /* thử lại nhịp sau */ }
    }, 1500);
    return () => { clearInterval(poll); unsub(); };
  }, [sessionId]);

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "48px clamp(16px,4vw,48px)", textAlign: "center" }}>
      <div style={{ fontSize: 12, color: "var(--gray-5)", marginBottom: 8 }}>Đang sinh slide</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 24, letterSpacing: "-0.02em" }}>{title}</h1>

      <div style={{ height: 8, borderRadius: 99, background: "rgba(255,255,255,0.06)", overflow: "hidden", marginBottom: 12 }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg,#f97316,#fbbf24)", transition: "width 0.4s" }} />
      </div>
      <div style={{ fontSize: 13, color: "var(--accent2, #fb923c)", marginBottom: 28 }}>{label} {total ? `· ${pages.filter(p => p.status === "completed").length}/${total} trang` : ""}</div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, textAlign: "left" }}>
        {(total ? Array.from({ length: total }, (_, i) => pages[i]) : pages).map((p, i) => {
          const st = p?.status;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 10, background: "rgba(255,255,255,0.03)", border: "1px solid var(--gray-2)" }}>
              <span style={{
                width: 22, height: 22, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 800,
                background: st === "completed" ? "rgba(34,197,94,0.15)" : st === "failed" ? "rgba(239,68,68,0.15)" : "rgba(249,115,22,0.15)",
                color: st === "completed" ? "#22c55e" : st === "failed" ? "#ef4444" : "var(--accent)",
              }}>{st === "completed" ? "✓" : st === "failed" ? "!" : (i + 1)}</span>
              <span style={{ fontSize: 13, color: "var(--white)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {p?.title || `Trang ${i + 1}`}
              </span>
              <span style={{ fontSize: 11, color: "var(--gray-5)" }}>{st === "completed" ? "Xong" : st === "failed" ? "Lỗi" : "…"}</span>
            </div>
          );
        })}
      </div>
    </main>
  );
}

/* ─────────────────────────  STEP 3 · PREVIEW + EXPORT  ───────────────────────── */
function PreviewStep({ sessionId, title, initialPages, onBack }: { sessionId: string; title: string; initialPages: GeneratedPage[]; onBack: () => void }) {
  const [pages, setPages] = useState<GeneratedPage[]>(initialPages);
  const [active, setActive] = useState(0);
  const [present, setPresent] = useState(false);
  const [exporting, setExporting] = useState<ExportKind | "">("");
  const [retrying, setRetrying] = useState(false);

  async function refresh() {
    const data = await getSession(sessionId);
    setPages(data.generatedPages);
  }
  useEffect(() => { refresh(); }, [sessionId]);

  const failed = pages.filter((p) => p.status === "failed").length;

  async function handleExport(kind: ExportKind) {
    setExporting(kind);
    try {
      const res = await fetch(exportDownloadUrl(sessionId, kind), { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `Export ${kind} lỗi`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title || "slides"}.${kind === "png" ? "zip" : kind}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Export lỗi");
    } finally { setExporting(""); }
  }

  // Trình chiếu: phím mũi tên + ESC
  useEffect(() => {
    if (!present) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPresent(false);
      else if (e.key === "ArrowRight" || e.key === " ") setActive((i) => Math.min(pages.length - 1, i + 1));
      else if (e.key === "ArrowLeft") setActive((i) => Math.max(0, i - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [present, pages.length]);

  const activePage = pages[active];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 57px)" }}>
      {/* Toolbar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "14px 24px", borderBottom: "1px solid var(--gray-2)", flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-0.02em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 420 }}>{title}</div>
          <div style={{ fontSize: 11, color: "var(--gray-5)" }}>{pages.length} trang {failed > 0 && <span style={{ color: "#ef4444" }}>· {failed} lỗi</span>}</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={onBack} className="btn-ghost" style={{ fontSize: 12 }}>← Làm slide khác</button>
          {failed > 0 && (
            <button onClick={async () => { setRetrying(true); await retryFailedPages(sessionId); setTimeout(() => { refresh(); setRetrying(false); }, 3000); }} disabled={retrying} className="btn-ghost" style={{ fontSize: 12, color: "var(--accent2,#fb923c)" }}>
              {retrying ? "Đang gen lại…" : `↻ Gen lại ${failed} trang lỗi`}
            </button>
          )}
          <button onClick={() => setPresent(true)} className="btn-ghost" style={{ fontSize: 12 }}>▶ Trình chiếu</button>
          {(["pptx", "pdf", "png"] as ExportKind[]).map((k) => (
            <button key={k} onClick={() => handleExport(k)} disabled={!!exporting} className={k === "pptx" ? "btn-primary" : "btn-ghost"} style={{ fontSize: 12, opacity: exporting && exporting !== k ? 0.5 : 1 }}>
              {exporting === k ? "Đang xuất…" : `Xuất ${k.toUpperCase()}`}
            </button>
          ))}
        </div>
      </div>

      {/* Body: sidebar + preview */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ width: 200, flexShrink: 0, borderRight: "1px solid var(--gray-2)", overflowY: "auto", padding: "12px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
          {pages.map((p, i) => (
            <button key={p.id} onClick={() => setActive(i)} style={{
              padding: "10px 12px", borderRadius: 10, textAlign: "left", border: "none", cursor: "pointer",
              background: active === i ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.03)",
              borderLeft: `3px solid ${active === i ? "var(--accent)" : "transparent"}`,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: active === i ? "var(--accent)" : "var(--white)", marginBottom: 2 }}>
                Trang {i + 1} {p.status === "failed" && <span style={{ color: "#ef4444" }}>·!</span>}
              </div>
              <div style={{ fontSize: 10, color: "var(--gray-5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
            </button>
          ))}
        </div>

        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 20, background: "rgba(0,0,0,0.3)", minWidth: 0 }}>
          <div style={{ width: "100%", maxWidth: "min(1400px, calc((100vh - 180px) * 16 / 9))", aspectRatio: "16/9", borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-2)", background: "#08080f" }}>
            {activePage && pageUrl(activePage) ? (
              <iframe key={activePage.id} src={pageUrl(activePage)} title={activePage.title} scrolling="no" style={{ width: "100%", height: "100%", border: "none", display: "block" }} />
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--gray-5)", fontSize: 13 }}>Chưa có nội dung</div>
            )}
          </div>
        </div>
      </div>

      {/* Trình chiếu fullscreen */}
      {present && activePage && (
        <div onClick={() => setPresent(false)} style={{ position: "fixed", inset: 0, zIndex: 100000, background: "#000", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: "min(100vw, calc(100vh * 16 / 9))", aspectRatio: "16/9" }} onClick={(e) => e.stopPropagation()}>
            <iframe key={activePage.id} src={pageUrl(activePage)} title={activePage.title} scrolling="no" style={{ width: "100%", height: "100%", border: "none" }} />
          </div>
          <div style={{ position: "fixed", bottom: 16, left: "50%", transform: "translateX(-50%)", fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
            ← → chuyển trang · ESC thoát · {active + 1}/{pages.length}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────  styles  ───────────────────────── */
const fieldLabel: CSSProperties = { display: "block", fontSize: 11, fontWeight: 700, color: "var(--gray-5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" };
const selectStyle: CSSProperties = { width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 10, color: "var(--white)", fontSize: 13, padding: "10px 12px" };
