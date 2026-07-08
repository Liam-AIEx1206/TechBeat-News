"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import {
  Sparkles,
  Upload,
  Link as LinkIcon,
  ArrowLeft,
  RefreshCw,
  Save,
  Play,
  Plus,
  ChevronUp,
  ChevronDown,
  Trash2,
  Check,
  X,
  Maximize2,
  AlertTriangle,
  XCircle,
  History,
  LayoutTemplate,
  RotateCcw
} from "lucide-react";
import {
  listStyles, listFonts, createSession, startGenerate, getSession,
  subscribeProgress, retryFailedPages, pageUrl, exportDownloadUrl,
  editPage, getPageMessages, addPage, deletePage, reorderPages,
  generateSpeech, getSpeech, hasActiveRun, saveAsTemplate, stylePreviewUrl,
  extractDoc, extractUrl,
  listVersions, rollbackToVersion, listTemplates, createEditableFromTemplate, setIndexTransition, getIndexTransition,
  type StyleItem, type FontItem, type GeneratedPage, type ExportKind,
  type ChatMessage, type SpeechStyle, type HistoryVersion, type TemplateItem, type IndexTransition,
} from "@/lib/slideEngine";

type Step = "input" | "generating" | "preview";

// Luật thiết kế tiêm vào mọi lần sinh — chống bug ảnh vỡ + ép lấp canvas + tương phản.
// (oh-my-ppt không có ảnh upload → model hay bịa <img src="/path/to..."> gây vỡ.)
// Dùng gạch đầu dòng "—" (KHÔNG dùng "1." vì extractOutlineTitles của oh-my-ppt
// bắt dòng "N." làm tiêu đề trang → sẽ phá outline).
const DESIGN_RULES = `[QUY TẮC THIẾT KẾ — áp dụng cho toàn bộ slide, không phải là mục lục]
— TUYỆT ĐỐI KHÔNG dùng thẻ <img> với đường dẫn giả/placeholder (/path/to, path/to, your-image, example.com, placeholder). Không có ảnh thật thì KHÔNG chèn <img>; thay bằng khối CSS gradient bo góc, emoji/icon SVG inline cỡ lớn, biểu đồ Chart.js, hoặc số liệu lớn làm điểm nhấn.
— KHÔNG để chữ placeholder như [Your Name], [Date]; thiếu dữ liệu thì bỏ dòng.
— LẤP ĐẦY canvas 1600×900: grid/flex nhiều cột, card, panel; tận dụng chiều cao; không để trống quá 25% trang.
— TƯƠNG PHẢN CAO giữa chữ và nền (style pastel/sáng thì chữ đậm & tối màu).
— Tiêu đề mỗi trang là nội dung thật, không ghi chung chung "Bìa"/"Slide 1".`;

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
        <GeneratingStep sessionId={sessionId} title={title} onDone={(pages) => { setInitialPages(pages); setStep("preview"); }} onBack={() => setStep("input")} />
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
                {done ? <Check size={10} strokeWidth={3} /> : s.n}
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

const DEFAULT_FONTS: FontItem[] = [
  { id: "google:poppins", family: "Poppins" },
  { id: "google:inter", family: "Inter" },
  { id: "google:montserrat", family: "Montserrat" },
  { id: "google:space-grotesk", family: "Space Grotesk" },
  { id: "google:bebas-neue", family: "Bebas Neue" },
  { id: "google:playfair-display", family: "Playfair Display" },
  { id: "google:merriweather", family: "Merriweather" },
  { id: "google:caveat", family: "Caveat" },
  { id: "google:dancing-script", family: "Dancing Script" },
  { id: "google:fira-code", family: "Fira Code" },
  { id: "google:noto-sans-sc", family: "Noto Sans SC" },
  { id: "google:noto-serif-sc", family: "Noto Serif SC" },
  { id: "google:zcool-xiaowei", family: "ZCOOL XiaoWei" },
  { id: "google:ma-shan-zheng", family: "Ma Shan Zheng" },
];

/* ─────────────────────────  STEP 1 · INPUT  ───────────────────────── */
function InputStep({ onStarted }: { onStarted: (sessionId: string, title: string) => void }) {
  const [topic, setTopic] = useState("");
  const [pageCount, setPageCount] = useState(6);
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [styleId, setStyleId] = useState("");
  const [fonts, setFonts] = useState<FontItem[]>(DEFAULT_FONTS);
  const [titleFontId, setTitleFontId] = useState("");
  const [bodyFontId, setBodyFontId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [preview, setPreview] = useState<StyleItem | null>(null);
  const [srcMode, setSrcMode] = useState<"topic" | "doc" | "url" | "template">("topic");
  const [content, setContent] = useState("");   // nội dung trích từ doc/url (làm userMessage)
  const [url, setUrl] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [tplId, setTplId] = useState("");

  useEffect(() => {
    if (srcMode === "template" && templates.length === 0) listTemplates().then(setTemplates).catch(() => {});
  }, [srcMode]);

  useEffect(() => {
    (async () => {
      try {
        const [st, ft] = await Promise.all([listStyles(), listFonts().catch(() => ({ googleFonts: [], userFonts: [] }))]);
        setStyles(st);
        if (st[0]) setStyleId(st[0].id);
        const apiFonts = [...(ft.googleFonts || []), ...(ft.userFonts || [])];
        if (apiFonts.length > 0) {
          setFonts(apiFonts);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải được style/font");
      } finally { setLoading(false); }
    })();
  }, []);

  async function handleStart() {
    // Từ mẫu: copy template thành session editable ngay, không cần chủ đề/gen.
    if (srcMode === "template") {
      if (!tplId) { setError("Chọn một mẫu."); return; }
      setBusy(true); setError("");
      try {
        const tpl = templates.find((t) => t.id === tplId);
        const sid = await createEditableFromTemplate(tplId, topic.trim() || tpl?.name || "Bản từ mẫu");
        onStarted(sid, topic.trim() || tpl?.name || "Bản từ mẫu");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tạo được từ mẫu"); setBusy(false);
      }
      return;
    }
    if (!topic.trim()) { setError("Nhập chủ đề trước đã."); return; }
    if (!styleId) { setError("Chọn một phong cách."); return; }
    setBusy(true); setError("");
    try {
      const sid = await createSession({
        topic: topic.trim(), styleId, pageCount,
        fontSelection: (titleFontId || bodyFontId) ? { titleFontId: titleFontId || undefined, bodyFontId: bodyFontId || undefined } : null,
      });
      // Có nội dung trích từ tài liệu/link → dùng làm nguồn; nếu không thì dùng chủ đề.
      const base = content.trim()
        ? `Chủ đề: ${topic.trim()}\n\nDựa trên nội dung sau để làm slide (giữ nguyên ý chính, tiếng Việt):\n\n${content.trim()}`
        : topic.trim();
      await startGenerate(sid, `${base}\n\n${DESIGN_RULES}`);
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

      {/* Nguồn nội dung: chủ đề / tài liệu / link */}
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        {([
          { key: "topic", label: "Chủ đề", icon: Sparkles },
          { key: "doc", label: "Tải tài liệu", icon: Upload },
          { key: "url", label: "Dán link", icon: LinkIcon },
          { key: "template", label: "Từ mẫu", icon: LayoutTemplate }
        ] as const).map(({ key, label, icon: Icon }) => {
          const isSelected = srcMode === key;
          return (
            <button key={key} type="button" onClick={() => setSrcMode(key)} style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 99, fontSize: 12, fontWeight: 700, cursor: "pointer",
              background: isSelected ? "var(--accent)" : "rgba(255,255,255,0.04)",
              color: isSelected ? "#000" : "var(--gray-5)", border: "1px solid var(--gray-3)",
            }}>
              <Icon size={13} />
              {label}
            </button>
          );
        })}
      </div>

      {srcMode === "doc" && (
        <div style={{ marginBottom: 14 }}>
          <input type="file" accept=".docx,.md,.txt,.csv" disabled={extracting}
            onChange={async (e) => {
              const f = e.target.files?.[0]; if (!f) return;
              setExtracting(true); setError("");
              try { const r = await extractDoc(f); setContent(r.text); if (!topic.trim()) setTopic(r.title); }
              catch (er) { setError(er instanceof Error ? er.message : "Đọc tài liệu lỗi"); }
              finally { setExtracting(false); }
            }}
            style={{ fontSize: 13, color: "var(--gray-6)" }} />
          <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 6 }}>Hỗ trợ .docx .md .txt .csv (PDF: dán nội dung hoặc chuyển docx)</div>
        </div>
      )}
      {srcMode === "url" && (
        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." disabled={extracting}
            style={{ ...selectStyle, flex: 1 }} />
          <button type="button" disabled={extracting || !url.trim()} className="btn-ghost" style={{ fontSize: 12 }}
            onClick={async () => {
              setExtracting(true); setError("");
              try { const r = await extractUrl(url.trim()); setContent(r.text); if (!topic.trim()) setTopic(r.title); }
              catch (er) { setError(er instanceof Error ? er.message : "Trích link lỗi"); }
              finally { setExtracting(false); }
            }}>{extracting ? "Đang đọc…" : "Trích xuất"}</button>
        </div>
      )}
      {content && srcMode !== "topic" && srcMode !== "template" && (
        <div style={{ fontSize: 11, color: "#22c55e", marginBottom: 10 }}>✓ Đã lấy {content.length.toLocaleString()} ký tự nội dung — AI sẽ dựa vào đây.</div>
      )}

      {srcMode === "template" ? (
        <>
          <label style={fieldLabel}>Tên bản mới (tuỳ chọn)</label>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Để trống = dùng tên mẫu"
            style={{ ...selectStyle, marginBottom: 16 }} />
          <label style={fieldLabel}>Chọn mẫu đã lưu <span style={{ color: "var(--gray-5)" }}>({templates.length})</span></label>
          {templates.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--gray-5)", padding: "16px 0" }}>Chưa có mẫu nào. Vào một deck rồi bấm &ldquo;Lưu template&rdquo; để tạo mẫu.</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
              {templates.map((t) => {
                const on = t.id === tplId;
                return (
                  <button key={t.id} type="button" onClick={() => setTplId(t.id)} style={{
                    textAlign: "left", padding: 14, borderRadius: 12, cursor: "pointer",
                    background: on ? "rgba(249,115,22,0.1)" : "rgba(255,255,255,0.03)",
                    border: on ? "1.5px solid var(--accent)" : "1px solid var(--gray-3)",
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: on ? "var(--accent)" : "var(--white)" }}>{t.name}</div>
                    <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 3 }}>{t.pageCount ?? "?"} trang{t.styleKey ? ` · ${t.styleKey}` : ""}</div>
                  </button>
                );
              })}
            </div>
          )}
        </>
      ) : (
        <>
          {/* Chủ đề */}
          <label style={fieldLabel}>{srcMode === "topic" ? "Chủ đề / mô tả" : "Tiêu đề bài thuyết trình"}</label>
          <textarea
            value={topic} onChange={(e) => setTopic(e.target.value)} rows={srcMode === "topic" ? 4 : 2}
            placeholder="VD: Giới thiệu game Duck Out — thể loại Extraction Shooter: tổng quan, gameplay loot/shoot/escape, vũ khí, kết luận kêu gọi chơi thử."
            style={{ width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 12, color: "var(--white)", fontSize: 14, padding: "14px 16px", fontFamily: "inherit", lineHeight: 1.6, resize: "vertical" }}
          />

      {/* Số trang + Font */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 20 }}>
        <div style={{ minWidth: 200 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <label style={{ ...fieldLabel, marginBottom: 0 }}>Số trang</label>
            <input
              type="number"
              min={3}
              max={100}
              value={pageCount}
              onChange={(e) => {
                const val = Math.max(3, Math.min(100, Number(e.target.value) || 3));
                setPageCount(val);
              }}
              style={{
                width: 60,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--gray-3)",
                borderRadius: 8,
                color: "var(--accent)",
                fontSize: 13,
                fontWeight: 800,
                textAlign: "center",
                padding: "4px 6px",
              }}
            />
          </div>
          <input
            type="range"
            min={3}
            max={20}
            value={pageCount > 20 ? 20 : pageCount}
            onChange={(e) => setPageCount(Number(e.target.value))}
            style={{ width: "100%", accentColor: "var(--accent)", cursor: "pointer" }}
          />
        </div>
        <div style={{ minWidth: 180, flex: 1 }}>
          <label style={fieldLabel}>Font tiêu đề</label>
          <select value={titleFontId} onChange={(e) => setTitleFontId(e.target.value)} style={selectStyle}>
            <option value="" style={{ background: "#18181b", color: "#fff" }}>AI tự chọn</option>
            {fonts.map((f) => <option key={f.id} value={f.id} style={{ background: "#18181b", color: "#fff" }}>{f.family}</option>)}
          </select>
        </div>
        <div style={{ minWidth: 180, flex: 1 }}>
          <label style={fieldLabel}>Font nội dung</label>
          <select value={bodyFontId} onChange={(e) => setBodyFontId(e.target.value)} style={selectStyle}>
            <option value="" style={{ background: "#18181b", color: "#fff" }}>AI tự chọn</option>
            {fonts.map((f) => <option key={f.id} value={f.id} style={{ background: "#18181b", color: "#fff" }}>{f.family}</option>)}
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
          {filtered.map((s) => (
            <StyleCard key={s.id} style={s} active={s.id === styleId} onSelect={() => setStyleId(s.id)} onZoom={() => setPreview(s)} />
          ))}
        </div>
      )}
        </>
      )}

      {preview && (
        <div onClick={() => setPreview(null)} style={{ position: "fixed", inset: 0, zIndex: 100000, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: 24 }}>
          <div onClick={(e) => e.stopPropagation()} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 18, fontWeight: 800, color: "#fff" }}>{preview.name?.en || preview.label}</span>
            <button onClick={() => setPreview(null)} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <X size={14} />
              Đóng
            </button>
          </div>
          <div onClick={(e) => e.stopPropagation()} style={{ width: "min(1100px,92vw)", aspectRatio: "16/9", borderRadius: 14, overflow: "hidden", border: "1px solid var(--gray-3)", background: "#0b0b12" }}>
            <ScaledSlideFrame url={stylePreviewUrl(preview.styleKey)} title={preview.label} frameKey={`stp-${preview.id}`} />
          </div>
          <button onClick={(e) => { e.stopPropagation(); setStyleId(preview.id); setPreview(null); }} className="btn-primary" style={{ fontSize: 13 }}>Chọn style này</button>
        </div>
      )}

      {error && <div style={{ marginTop: 16, padding: "10px 14px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#fca5a5", fontSize: 13 }}>{error}</div>}

      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button onClick={handleStart} disabled={busy} className="btn-primary" style={{ fontSize: 14, padding: "14px 28px", opacity: busy ? 0.6 : 1 }}>
          {busy ? "Đang khởi tạo…" : srcMode === "template" ? "Dùng mẫu này →" : "Sinh slide →"}
        </button>
      </div>
    </main>
  );
}

/* ─────────────────────────  STEP 2 · GENERATING  ───────────────────────── */
// Nhãn tiến độ engine (zh) → tiếng Việt theo stage
const STAGE_VI: Record<string, string> = {
  preflight: "Đang chuẩn bị", planning: "Đang lập dàn ý",
  generating: "Đang tạo trang", page: "Đang tạo trang",
  finalize: "Đang hoàn tất", finalizing: "Đang hoàn tất",
};
function viLabel(p: any): string | null {
  if (p?.stage && STAGE_VI[p.stage]) return STAGE_VI[p.stage];
  const l = p?.label;
  if (typeof l === "string" && !/[\u4e00-\u9fff]/.test(l)) return l; // giữ nếu không phải chữ Trung
  return null;
}

/** Dịch / làm sạch message lỗi từ slide-engine (có thể là tiếng Trung). */
function sanitizeError(msg: string, failedPages?: GeneratedPage[]): string {
  if (!msg) return "Sinh slide thất bại.";
  // Phát hiện chữ Trung
  const hasChinese = /[\u4e00-\u9fff]/.test(msg);
  if (hasChinese) {
    if (failedPages && failedPages.length > 0) {
      const names = failedPages.map((p) => p.title || `Trang ${p.pageNumber}`).join(", ");
      return `Một số trang sinh thất bại (${failedPages.length} trang lỗi): ${names}. Bạn có thể thử lại các trang lỗi hoặc quay lại để sinh lại toàn bộ.`;
    }
    return "Slide engine gặp lỗi khi sinh trang. Vui lòng thử lại hoặc đổi model."
  }
  return msg;
}

function GeneratingStep({ sessionId, title, onDone, onBack }: { sessionId: string; title: string; onDone: (pages: GeneratedPage[]) => void; onBack: () => void }) {
  const [pages, setPages] = useState<GeneratedPage[]>([]);
  const [label, setLabel] = useState("Đang chuẩn bị…");
  const [progress, setProgress] = useState(4);
  const [total, setTotal] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [error, setError] = useState("");
  const [failedPages, setFailedPages] = useState<GeneratedPage[]>([]);
  const [retrying, setRetrying] = useState(false);
  const doneRef = useRef(false);
  const idleMissRef = useRef(0);

  useEffect(() => {
    const fail = (msg: string, fp?: GeneratedPage[]) => {
      if (doneRef.current) return;
      doneRef.current = true;
      setFailedPages(fp ?? []);
      setError(sanitizeError(msg, fp));
    };
    const unsub = subscribeProgress((ev) => {
      const type = ev?.type ?? ev?.payload?.type;
      if (type === "run_error" || type === "run_aborted") { fail(ev?.message ?? ev?.payload?.message ?? "Sinh slide bị huỷ/timeout."); return; }
      const p = ev?.payload ?? ev;
      const vl = viLabel(p); if (vl) setLabel(vl);
      if (typeof p?.progress === "number") setProgress(Math.max(4, Math.min(99, p.progress)));
      if (typeof p?.totalPages === "number") setTotal(p.totalPages);
    });
    const poll = setInterval(async () => {
      if (doneRef.current) return;
      try {
        const data = await getSession(sessionId);
        setPages(data.generatedPages);
        const pc = Number((data.session as any)?.page_count ?? data.generatedPages.length);
        const gc = Number((data.session as any)?.generated_count ?? data.generatedPages.filter((x) => x.status === "completed").length);
        const fc = Number((data.session as any)?.failed_count ?? data.generatedPages.filter((x) => x.status === "failed").length);
        if (pc > 0) setTotal(pc);
        setCompletedCount(gc);
        if (pc > 0 && gc + fc >= pc) {
          doneRef.current = true;
          clearInterval(poll); unsub();
          const finalPages = data.generatedPages;
          const fp = finalPages.filter((x) => x.status === "failed");
          if (gc === 0) {
            // Tất cả trang đều lỗi
            fail(`${fp.length}/${pc} trang sinh thất bại. Vui lòng thử lại.`, fp);
          } else if (fp.length > 0) {
            // Một số trang lỗi — vào preview nhưng highlight lỗi
            setProgress(100);
            setTimeout(() => onDone(finalPages), 500);
          } else {
            // Tất cả thành công
            setProgress(100);
            setTimeout(() => onDone(finalPages), 500);
          }
          return;
        }
        // Không còn run chạy mà chưa có trang nào xong → thất bại/nghẽn
        if (gc === 0) {
          if (!(await hasActiveRun(sessionId))) {
            if (++idleMissRef.current >= 3) { clearInterval(poll); unsub(); fail("Run đã dừng nhưng chưa tạo được trang nào — thường do LLM timeout hoặc trả sai định dạng. Thử lại hoặc đổi model mạnh hơn."); }
          } else idleMissRef.current = 0;
        }
      } catch { /* thử lại nhịp sau */ }
    }, 1500);
    return () => { clearInterval(poll); unsub(); };
  }, [sessionId]);

  async function handleRetryFailed() {
    setRetrying(true);
    try {
      await retryFailedPages(sessionId);
      // Reset về trạng thái generating
      doneRef.current = false;
      idleMissRef.current = 0;
      setError("");
      setFailedPages([]);
      setProgress(10);
      setLabel("Đang thử lại trang lỗi…");
    } catch {
      setRetrying(false);
    }
  }

  if (error) {
    const hasFailedPages = failedPages.length > 0;
    return (
      <main style={{ maxWidth: 620, margin: "0 auto", padding: "64px clamp(16px,4vw,48px)", textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
          {hasFailedPages ? <AlertTriangle size={40} color="var(--accent)" /> : <XCircle size={40} color="#ef4444" />}
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 12 }}>
          {hasFailedPages ? `${failedPages.length} trang sinh thất bại` : "Sinh slide thất bại"}
        </h1>
        <p style={{ fontSize: 13, color: "var(--gray-6)", lineHeight: 1.6, marginBottom: 24 }}>{error}</p>
        {hasFailedPages && (
          <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, padding: "12px 16px", marginBottom: 24, textAlign: "left" }}>
            {failedPages.map((p, i) => (
              <div key={i} style={{ fontSize: 12, color: "#fca5a5", padding: "3px 0" }}>• {p.title || `Trang ${p.pageNumber}`}</div>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
          {hasFailedPages && (
            <button
              onClick={handleRetryFailed}
              disabled={retrying}
              className="btn-primary"
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
            >
              <RefreshCw size={14} className={retrying ? "animate-spin" : ""} />
              {retrying ? "Đang thử lại…" : "Thử lại trang lỗi"}
            </button>
          )}
          <button onClick={onBack} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, padding: "8px 18px", borderRadius: 8, background: "rgba(255,255,255,0.06)", border: "1px solid var(--gray-3)", color: "var(--gray-6)", cursor: "pointer" }}>
            <ArrowLeft size={14} />
            Sinh lại từ đầu
          </button>
        </div>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "48px clamp(16px,4vw,48px)", textAlign: "center" }}>
      <div style={{ fontSize: 12, color: "var(--gray-5)", marginBottom: 8 }}>Đang sinh slide</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 24, letterSpacing: "-0.02em" }}>{title}</h1>

      <div style={{ height: 8, borderRadius: 99, background: "rgba(255,255,255,0.06)", overflow: "hidden", marginBottom: 12 }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg,#f97316,#fbbf24)", transition: "width 0.4s" }} />
      </div>
      <div style={{ fontSize: 13, color: "var(--accent2, #fb923c)", marginBottom: 28 }}>{label} {total ? `· ${completedCount}/${total} trang` : ""}</div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, textAlign: "left" }}>
        {(total ? Array.from({ length: total }, (_, i) => pages[i]) : pages).map((p, i) => {
          const st = p?.status;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 10, background: "rgba(255,255,255,0.03)", border: "1px solid var(--gray-2)" }}>
              <span style={{
                width: 22, height: 22, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 800,
                background: st === "completed" ? "rgba(34,197,94,0.15)" : st === "failed" ? "rgba(239,68,68,0.15)" : "rgba(249,115,22,0.15)",
                color: st === "completed" ? "#22c55e" : st === "failed" ? "#ef4444" : "var(--accent)",
              }}>{st === "completed" ? <Check size={12} strokeWidth={3} /> : st === "failed" ? <X size={12} strokeWidth={3} /> : (i + 1)}</span>
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

/* ─────────────────────────  STEP 3 · EDITOR (Xem · Sửa AI · Xuất)  ───────────────────────── */
function PreviewStep({ sessionId, title, initialPages, onBack }: { sessionId: string; title: string; initialPages: GeneratedPage[]; onBack: () => void }) {
  const [pages, setPages] = useState<GeneratedPage[]>(initialPages);
  const [active, setActive] = useState(0);
  const [present, setPresent] = useState(false);
  const [exporting, setExporting] = useState<ExportKind | "">("");
  const [busyMsg, setBusyMsg] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [panel, setPanel] = useState<"chat" | "speech">("chat");
  const [showHistory, setShowHistory] = useState(false);
  const [transition, setTransition] = useState<IndexTransition>("none");

  useEffect(() => { getIndexTransition(sessionId).then((t) => setTransition((t as IndexTransition) || "none")).catch(() => {}); }, [sessionId]);

  async function refresh(): Promise<GeneratedPage[]> {
    const data = await getSession(sessionId);
    setPages(data.generatedPages);
    return data.generatedPages;
  }
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [sessionId]);

  const activePage = pages[active];
  const failed = pages.filter((p) => p.status === "failed").length;

  async function waitIdleThenRefresh(label: string) {
    setBusyMsg(label);
    await new Promise((r) => setTimeout(r, 1500));
    for (let i = 0; i < 80; i++) {
      if (!(await hasActiveRun(sessionId))) break;
      await new Promise((r) => setTimeout(r, 1500));
    }
    await refresh();
    setRefreshKey((k) => k + 1);
    setBusyMsg("");
  }

  async function handleExport(kind: ExportKind) {
    setExporting(kind);
    try {
      const res = await fetch(exportDownloadUrl(sessionId, kind), { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `Export ${kind} lỗi`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${title || "slides"}.${kind === "png" ? "zip" : kind}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert(e instanceof Error ? e.message : "Export lỗi"); }
    finally { setExporting(""); }
  }

  async function handleAddPage() {
    const desc = prompt("Nội dung trang mới cần thêm là gì?");
    if (!desc?.trim()) return;
    try { await addPage(sessionId, desc.trim(), activePage ? active + 1 : pages.length); await waitIdleThenRefresh("Đang thêm trang…"); }
    catch (e) { alert(e instanceof Error ? e.message : "Thêm trang lỗi"); }
  }
  async function handleDeletePage(p: GeneratedPage) {
    if (!p.id || !confirm(`Xoá trang "${p.title}"?`)) return;
    try { setBusyMsg("Đang xoá…"); await deletePage(sessionId, p.id); await refresh(); setActive((i) => Math.max(0, i - 1)); }
    catch (e) { alert(e instanceof Error ? e.message : "Xoá lỗi"); }
    finally { setBusyMsg(""); }
  }
  async function move(i: number, dir: -1 | 1) {
    const j = i + dir;
    if (j < 0 || j >= pages.length) return;
    const ids = pages.map((p) => p.id);
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try { setBusyMsg("Đang đổi thứ tự…"); await reorderPages(sessionId, ids); await refresh(); setActive(j); }
    catch (e) { alert(e instanceof Error ? e.message : "Đổi thứ tự lỗi"); }
    finally { setBusyMsg(""); }
  }

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

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 57px)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "12px 24px", borderBottom: "1px solid var(--gray-2)", flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 800, letterSpacing: "-0.02em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 360 }}>{title}</div>
          <div style={{ fontSize: 11, color: "var(--gray-5)" }}>{pages.length} trang {failed > 0 && <span style={{ color: "#ef4444" }}>· {failed} lỗi</span>}</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={onBack} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <ArrowLeft size={14} />
            Slide khác
          </button>
          {failed > 0 && (
            <button onClick={() => { retryFailedPages(sessionId); waitIdleThenRefresh("Đang gen lại trang lỗi…"); }} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--accent2,#fb923c)" }}>
              <RefreshCw size={14} />
              Gen lại {failed} lỗi
            </button>
          )}
          <button onClick={async () => { const n = prompt("Tên template:", title); if (n?.trim()) { try { await saveAsTemplate(sessionId, n.trim()); alert("Đã lưu template ✓"); } catch (e) { alert(e instanceof Error ? e.message : "Lưu template lỗi"); } } }} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <Save size={14} />
            Lưu template
          </button>
          <button onClick={() => setShowHistory(true)} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <History size={14} />
            Lịch sử
          </button>
          <select value={transition} title="Hiệu ứng chuyển trang khi trình chiếu"
            onChange={async (e) => { const t = e.target.value as IndexTransition; setTransition(t); try { await setIndexTransition(sessionId, t); } catch {} }}
            style={{ ...selectStyle, width: "auto", fontSize: 12, padding: "6px 10px" }}>
            <option value="none">Chuyển: Không</option>
            <option value="fade">Chuyển: Mờ dần</option>
            <option value="slide">Chuyển: Trượt</option>
            <option value="zoom">Chuyển: Phóng</option>
            <option value="flip">Chuyển: Lật</option>
            <option value="cube">Chuyển: Khối 3D</option>
          </select>
          <button onClick={() => setPresent(true)} className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <Play size={14} />
            Trình chiếu
          </button>
          {(["pptx", "pdf", "png"] as ExportKind[]).map((k) => (
            <button key={k} onClick={() => handleExport(k)} disabled={!!exporting} className={k === "pptx" ? "btn-primary" : "btn-ghost"} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, opacity: exporting && exporting !== k ? 0.5 : 1 }}>
              {exporting === k ? "Đang xuất…" : `Xuất ${k.toUpperCase()}`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ width: 210, flexShrink: 0, borderRight: "1px solid var(--gray-2)", overflowY: "auto", padding: "12px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
          {pages.map((p, i) => (
            <div key={p.id} style={{
              padding: "8px 10px", borderRadius: 10,
              background: active === i ? "rgba(249,115,22,0.12)" : "rgba(255,255,255,0.03)",
              borderLeft: `3px solid ${active === i ? "var(--accent)" : "transparent"}`,
            }}>
              <button onClick={() => setActive(i)} style={{ display: "block", width: "100%", textAlign: "left", border: "none", background: "transparent", cursor: "pointer", padding: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: active === i ? "var(--accent)" : "var(--white)", marginBottom: 2 }}>
                  Trang {i + 1} {p.status === "failed" && <span style={{ color: "#ef4444" }}>·!</span>}
                </div>
                <div style={{ fontSize: 10, color: "var(--gray-5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</div>
              </button>
              {active === i && (
                <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                  <button onClick={() => move(i, -1)} title="Lên" style={{ ...miniBtn, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <ChevronUp size={12} />
                  </button>
                  <button onClick={() => move(i, 1)} title="Xuống" style={{ ...miniBtn, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <ChevronDown size={12} />
                  </button>
                  <button onClick={() => handleDeletePage(p)} title="Xoá" style={{ ...miniBtn, color: "#ef4444", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              )}
            </div>
          ))}
          <button onClick={handleAddPage} className="btn-ghost" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, fontSize: 11, marginTop: 6 }}>
            <Plus size={13} />
            Thêm trang
          </button>
        </div>

        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: "rgba(0,0,0,0.3)", minWidth: 0, position: "relative" }}>
          <div style={{ width: "100%", maxWidth: "min(1400px, calc((100vh - 180px) * 16 / 9))", aspectRatio: "16/9", borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-2)", background: "#08080f" }}>
            {activePage && pageUrl(activePage) ? (
              <ScaledSlideFrame url={`${pageUrl(activePage)}?k=${refreshKey}`} title={activePage.title} frameKey={`${activePage.id}-${refreshKey}`} />
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--gray-5)", fontSize: 13 }}>Đang tải…</div>
            )}
          </div>
          {busyMsg && (
            <div style={{ position: "absolute", inset: 16, borderRadius: 12, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#fff" }}>
              <div style={{ width: 30, height: 30, border: "3px solid var(--accent)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
              <span style={{ fontSize: 13 }}>{busyMsg}</span>
            </div>
          )}
        </div>

        <div style={{ width: 320, flexShrink: 0, borderLeft: "1px solid var(--gray-2)", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--gray-2)" }}>
            {([["chat", "Sửa bằng AI"], ["speech", "Lời dẫn"]] as const).map(([k, lb]) => (
              <button key={k} onClick={() => setPanel(k)} style={{
                flex: 1, padding: "12px 8px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700,
                background: panel === k ? "rgba(249,115,22,0.1)" : "transparent",
                color: panel === k ? "var(--accent)" : "var(--gray-5)",
                borderBottom: panel === k ? "2px solid var(--accent)" : "2px solid transparent",
              }}>{lb}</button>
            ))}
          </div>
          {panel === "chat"
            ? <ChatEditPanel sessionId={sessionId} page={activePage} disabled={!!busyMsg} onEdit={(ins) => { editPage(sessionId, activePage!.pageId!, ins).catch(() => {}); waitIdleThenRefresh("AI đang sửa trang…"); }} />
            : <SpeechPanel sessionId={sessionId} page={activePage} />}
        </div>
      </div>

      {present && activePage && (
        <div onClick={() => setPresent(false)} style={{ position: "fixed", inset: 0, zIndex: 100000, background: "#000", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: "min(100vw, calc(100vh * 16 / 9))", aspectRatio: "16/9" }} onClick={(e) => e.stopPropagation()}>
            <ScaledSlideFrame url={pageUrl(activePage)} title={activePage.title} frameKey={`present-${activePage.id}`} />
          </div>
          <div style={{ position: "fixed", bottom: 16, left: "50%", transform: "translateX(-50%)", fontSize: 12, color: "rgba(255,255,255,0.6)" }}>← → chuyển · ESC thoát · {active + 1}/{pages.length}</div>
        </div>
      )}

      {showHistory && (
        <HistoryDialog sessionId={sessionId} onClose={() => setShowHistory(false)}
          onRolledBack={() => { setShowHistory(false); waitIdleThenRefresh("Đang khôi phục phiên bản…"); }} />
      )}
    </div>
  );
}

/* Lịch sử phiên bản + khôi phục (history:listVersions / rollbackToVersion) */
function HistoryDialog({ sessionId, onClose, onRolledBack }: { sessionId: string; onClose: () => void; onRolledBack: () => void }) {
  const [versions, setVersions] = useState<HistoryVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  useEffect(() => { listVersions(sessionId).then(setVersions).catch(() => setVersions([])).finally(() => setLoading(false)); }, [sessionId]);

  const kindVi: Record<string, string> = { generate: "Sinh deck", edit: "Sửa AI", addPage: "Thêm trang", deletePages: "Xoá trang", reorder: "Đổi thứ tự", rollback: "Khôi phục", styleSwitch: "Đổi style" };

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 100000, background: "rgba(0,0,0,0.72)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: "min(560px,94vw)", maxHeight: "80vh", display: "flex", flexDirection: "column", background: "linear-gradient(160deg,#161616,#101010)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid var(--gray-2)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800, fontSize: 15 }}><History size={16} /> Lịch sử phiên bản</div>
          <button onClick={onClose} className="btn-ghost" style={{ fontSize: 12 }}>✕ Đóng</button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
          {loading ? <div style={{ padding: 16, color: "var(--gray-5)", fontSize: 13 }}>Đang tải…</div>
            : versions.length === 0 ? <div style={{ padding: 16, color: "var(--gray-5)", fontSize: 13 }}>Chưa có phiên bản nào.</div>
            : versions.map((v) => (
              <div key={v.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 10, marginBottom: 8, background: v.isCurrent ? "rgba(249,115,22,0.1)" : "rgba(255,255,255,0.03)", border: v.isCurrent ? "1px solid var(--accent)" : "1px solid var(--gray-2)" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--white)" }}>{v.title || kindVi[v.kind] || v.kind}
                    {v.isCurrent && <span style={{ marginLeft: 8, fontSize: 10, color: "var(--accent)" }}>● hiện tại</span>}</div>
                  <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 2 }}>{kindVi[v.kind] || v.kind} · {new Date(v.createdAt).toLocaleString("vi-VN")}</div>
                </div>
                {!v.isCurrent && v.isRestorable && (
                  <button disabled={!!busy} onClick={async () => { setBusy(v.id); try { await rollbackToVersion(sessionId, v.id); onRolledBack(); } catch (e) { alert(e instanceof Error ? e.message : "Khôi phục lỗi"); setBusy(""); } }}
                    className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, flexShrink: 0 }}>
                    <RotateCcw size={13} /> {busy === v.id ? "…" : "Khôi phục"}
                  </button>
                )}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

function ChatEditPanel({ sessionId, page, disabled, onEdit }: { sessionId: string; page?: GeneratedPage; disabled: boolean; onEdit: (instruction: string) => void }) {
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  useEffect(() => {
    if (!page?.pageId) { setMsgs([]); return; }
    getPageMessages(sessionId, page.pageId).then(setMsgs).catch(() => setMsgs([]));
  }, [sessionId, page?.pageId, disabled]);

  const quick = ["Đổi màu tiêu đề nổi bật hơn", "Rút gọn nội dung cho gọn", "Thêm một biểu đồ minh hoạ", "Đổi bố cục sinh động hơn"];

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div style={{ flex: 1, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        {msgs.length === 0 && <div style={{ fontSize: 12, color: "var(--gray-5)", lineHeight: 1.6 }}>Bảo AI chỉnh trang <b style={{ color: "var(--white)" }}>{page ? `#${page.pageNumber}` : ""}</b> — ví dụ đổi màu tiêu đề, thêm biểu đồ, rút gọn chữ.</div>}
        {msgs.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "90%", padding: "8px 12px", borderRadius: 10, fontSize: 12, lineHeight: 1.5,
            background: m.role === "user" ? "var(--accent)" : "rgba(255,255,255,0.05)", color: m.role === "user" ? "#000" : "var(--white)" }}>
            {m.content?.slice(0, 500)}
          </div>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: "1px solid var(--gray-2)" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
          {quick.map((q) => <button key={q} disabled={disabled || !page} onClick={() => onEdit(q)} style={{ fontSize: 10, padding: "4px 8px", borderRadius: 99, border: "1px solid var(--gray-3)", background: "transparent", color: "var(--gray-6)", cursor: "pointer" }}>{q}</button>)}
        </div>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder="Nhập yêu cầu chỉnh sửa…" disabled={disabled || !page}
          style={{ width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 8, color: "var(--white)", fontSize: 12, padding: "8px 10px", fontFamily: "inherit", resize: "none" }} />
        <button onClick={() => { if (text.trim()) { onEdit(text.trim()); setText(""); } }} disabled={disabled || !page || !text.trim()} className="btn-primary" style={{ width: "100%", fontSize: 12, marginTop: 6, opacity: disabled || !text.trim() ? 0.5 : 1 }}>
          {disabled ? "Đang xử lý…" : "Gửi cho AI sửa"}
        </button>
      </div>
    </div>
  );
}

function SpeechPanel({ sessionId, page }: { sessionId: string; page?: GeneratedPage }) {
  const [busy, setBusy] = useState(false);
  const [script, setScript] = useState<string>("");
  const [style, setStyle] = useState<SpeechStyle>("conversational");
  async function load() { try { const s = await getSpeech(sessionId); setScript(typeof s === "string" ? s : JSON.stringify(s?.script ?? s ?? "", null, 2)); } catch { /* chưa có */ } }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [sessionId]);
  async function gen(scope: "all" | "single") {
    setBusy(true);
    try { await generateSpeech(sessionId, scope, page?.pageId || "", style); await new Promise((r) => setTimeout(r, 1200)); await load(); }
    catch (e) { alert(e instanceof Error ? e.message : "Gen lời dẫn lỗi"); }
    finally { setBusy(false); }
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div style={{ padding: 12, borderBottom: "1px solid var(--gray-2)", display: "flex", flexDirection: "column", gap: 8 }}>
        <select value={style} onChange={(e) => setStyle(e.target.value as SpeechStyle)} style={{ ...selectStyle, fontSize: 12, padding: "8px 10px" }}>
          <option value="conversational" style={{ background: "#18181b", color: "#fff" }}>Giọng trò chuyện</option>
          <option value="formal" style={{ background: "#18181b", color: "#fff" }}>Trang trọng</option>
          <option value="storytelling" style={{ background: "#18181b", color: "#fff" }}>Kể chuyện</option>
        </select>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={() => gen("single")} disabled={busy || !page} className="btn-ghost" style={{ flex: 1, fontSize: 11 }}>Trang này</button>
          <button onClick={() => gen("all")} disabled={busy} className="btn-primary" style={{ flex: 1, fontSize: 11 }}>{busy ? "Đang tạo…" : "Cả deck"}</button>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 14, fontSize: 12, lineHeight: 1.7, color: "var(--gray-6)", whiteSpace: "pre-wrap" }}>
        {script || "Chưa có lời dẫn. Bấm tạo ở trên."}
      </div>
    </div>
  );
}

const miniBtn: CSSProperties = { flex: 1, fontSize: 11, padding: "3px 0", borderRadius: 6, border: "1px solid var(--gray-3)", background: "rgba(255,255,255,0.04)", color: "var(--gray-6)", cursor: "pointer" };

/** Thẻ style: tên tiếng Anh + slide mẫu thật (thumbnail nạp lazy khi lướt tới) + phóng to. */
function StyleCard({ style, active, onSelect, onZoom }: { style: StyleItem; active: boolean; onSelect: () => void; onZoom: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    const io = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); }
    }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, [seen]);
  return (
    <div ref={ref} onClick={onSelect} style={{
      cursor: "pointer", borderRadius: 12, overflow: "hidden",
      background: active ? "rgba(249,115,22,0.10)" : "rgba(255,255,255,0.03)",
      border: active ? "1.5px solid var(--accent)" : "1px solid var(--gray-3)",
    }}>
      <div style={{ position: "relative", aspectRatio: "16/9", background: "#0b0b12", borderBottom: "1px solid var(--gray-2)" }}>
        {seen ? <ScaledSlideFrame url={stylePreviewUrl(style.styleKey)} title={style.label} frameKey={`th-${style.id}`} />
              : <div style={{ width: "100%", height: "100%" }} />}
        <button onClick={(e) => { e.stopPropagation(); onZoom(); }} title="Xem lớn" style={{
          position: "absolute", top: 6, right: 6, width: 26, height: 26, borderRadius: 6,
          background: "rgba(0,0,0,0.55)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff",
          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Maximize2 size={12} />
        </button>
      </div>
      <div style={{ padding: "8px 10px", fontSize: 12, fontWeight: 700, color: active ? "var(--accent)" : "var(--white)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {style.name?.en || style.label}
      </div>
    </div>
  );
}

/**
 * Trang slide oh-my-ppt là canvas CỐ ĐỊNH 1600×900, không tự co (fit nằm ở
 * index-runtime của deck container). Nên phải scale ở phía ta: render iframe
 * đúng 1600×900 rồi transform scale vừa khung → không cắt, không lệch.
 */
function ScaledSlideFrame({ url, title, frameKey }: { url: string; title: string; frameKey: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth, h = el.clientHeight;
      if (w && h) setScale(Math.min(w / 1600, h / 900));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={ref} style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      <iframe
        key={frameKey}
        src={url}
        title={title}
        scrolling="no"
        style={{
          width: 1600, height: 900, border: "none", flexShrink: 0,
          transform: `scale(${scale})`, transformOrigin: "center center",
          visibility: scale ? "visible" : "hidden",
        }}
      />
    </div>
  );
}

/* ─────────────────────────  styles  ───────────────────────── */
const fieldLabel: CSSProperties = { display: "block", fontSize: 11, fontWeight: 700, color: "var(--gray-5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" };
const selectStyle: CSSProperties = { width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 10, color: "var(--white)", fontSize: 13, padding: "10px 12px" };
