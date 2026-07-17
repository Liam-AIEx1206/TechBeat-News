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
  RotateCcw,
  FileUp
} from "lucide-react";
import {
  listStyles, listFonts, createSession, startGenerate, startTemplateGenerate, getSession,
  subscribeProgress, retryFailedPages, pageUrl, exportDownloadUrl,
  editPage, getPageMessages, addPage, deletePage, reorderPages,
  generateSpeech, getSpeech, hasActiveRun, saveAsTemplate, stylePreviewUrl,
  extractDoc, extractUrl,
  listVersions, rollbackToVersion, listTemplates, createEditableFromTemplate, createFromTemplate, templateManifest, setIndexTransition, getIndexTransition,
  importPptxAsSession,
  type StyleItem, type FontItem, type GeneratedPage, type ExportKind,
  type ChatMessage, type SpeechStyle, type HistoryVersion, type TemplateItem, type IndexTransition,
} from "@/lib/slideEngine";
import { GalaxyCanvas } from "@/components/GalaxyCanvas";

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
    <div style={{ minHeight: "100vh", background: "var(--black)", color: "var(--white)", position: "relative" }}>
      {/* Nền galaxy cam giống luồng video */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none" }}>
        <GalaxyCanvas accentHue={28} starCount={200} nebulaOpacity={0.08} />
      </div>
      <div style={{ position: "relative", zIndex: 1 }}>
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
    <header style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "16px 24px", borderBottom: "1px solid var(--gray-2)" }}>
      <a href="/" title="Về trang chủ — xem lịch sử video/slide" style={{ position: "absolute", left: 24, top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", gap: 6, color: "var(--gray-5)", textDecoration: "none", fontSize: 12, fontWeight: 700 }}>
        <ArrowLeft size={14} /> Trang chủ
      </a>
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
  const [srcMode, setSrcMode] = useState<"topic" | "doc" | "url" | "pptx">("topic");
  const [content, setContent] = useState("");   // nội dung trích từ doc/url (làm userMessage)
  const [url, setUrl] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [tplId, setTplId] = useState("");
  const [previewTpl, setPreviewTpl] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setTemplates(await listTemplates().catch(() => []));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải được mẫu");
      } finally { setLoading(false); }
    })();
  }, []);

  async function handleStart() {
    if (!tplId) { setError("Chọn một mẫu thiết kế."); return; }
    const tpl = templates.find((t) => t.id === tplId);
    const name = topic.trim() || tpl?.name || "Bản trình bày";
    const src = content.trim()
      ? `Chủ đề: ${topic.trim()}\n\nDựa trên nội dung sau để làm slide (giữ ý chính, tiếng Việt):\n\n${content.trim()}`
      : topic.trim();
    // Có nội dung → AI điền: số trang phải hợp lệ (≥ 3). Bỏ trống nội dung thì
    // dùng nguyên số trang của mẫu nên không cần kiểm.
    if (src && (!Number.isFinite(pageCount) || pageCount < 3)) {
      setError("Số trang phải từ 3 trở lên — vui lòng nhập lại.");
      return;
    }
    setBusy(true); setError("");
    try {
      if (src) {
        // Có nội dung → AI điền nội dung vào mẫu qua LUỒNG TEMPLATE (giữ thiết kế/màu,
        // fill vào seed pages — không sinh thêm trang mới gây nhân đôi).
        const sid = await createFromTemplate(tplId, name, pageCount);
        await startTemplateGenerate(sid, `${src}\n\nGIỮ NGUYÊN màu sắc, bố cục, phông chữ và phong cách của mẫu; chỉ thay phần chữ sang tiếng Việt theo chủ đề. Không đổi hệ màu.`);
        onStarted(sid, name);
      } else {
        // Không có nội dung → copy nguyên mẫu (khóa 100% màu/bố cục), sửa sau.
        const sid = await createEditableFromTemplate(tplId, name);
        onStarted(sid, name);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được"); setBusy(false);
    }
  }

  const tfiltered = q
    ? templates.filter((t) => `${t.name} ${(t.tags || []).join(" ")}`.toLowerCase().includes(q.toLowerCase()))
    : templates;

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "32px clamp(16px,4vw,48px)" }}>
      <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 8 }}>Tạo slide từ mẫu</div>
          <h1 style={{ fontSize: "clamp(26px,3.4vw,40px)", fontWeight: 900, letterSpacing: "-0.03em" }}>Chọn một mẫu để bắt đầu</h1>
        </div>
        <a href="/slide/library" className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, textDecoration: "none", flexShrink: 0 }}>
          <LayoutTemplate size={14} /> Thư viện Style / Font
        </a>
      </div>

      {/* Nguồn nội dung: chủ đề / tài liệu / link — rồi chọn mẫu thiết kế bên dưới */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {([
          { key: "topic", label: "Chủ đề", icon: Sparkles },
          { key: "doc", label: "Tải tài liệu", icon: Upload },
          { key: "url", label: "Dán link", icon: LinkIcon },
          { key: "pptx", label: "Import PPTX", icon: FileUp }
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

      {srcMode === "pptx" ? (
        <div style={{ padding: "8px 0 4px" }}>
          <label style={fieldLabel}>Chọn file .pptx để mở & chỉnh sửa</label>
          <input type="file" accept=".pptx" disabled={busy}
            onChange={async (e) => {
              const f = e.target.files?.[0]; if (!f) return;
              setBusy(true); setError("");
              try { const sid = await importPptxAsSession(f); onStarted(sid, f.name.replace(/\.pptx$/i, "")); }
              catch (er) { setError(er instanceof Error ? er.message : "Import PPTX lỗi"); setBusy(false); }
            }}
            style={{ fontSize: 13, color: "var(--gray-6)" }} />
          <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 8, lineHeight: 1.5 }}>
            {busy ? "Đang chuyển PPTX thành slide editable…" : "PPTX sẽ được chuyển thành các trang HTML sửa được (chỉnh chữ/bố cục, chat-AI, xuất lại)."}
          </div>
        </div>
      ) : (
        <>
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
          {content && srcMode !== "topic" && (
            <div style={{ fontSize: 11, color: "#22c55e", marginBottom: 10 }}>✓ Đã lấy {content.length.toLocaleString()} ký tự — AI sẽ điền nội dung vào mẫu.</div>
          )}
          <label style={fieldLabel}>{srcMode === "topic" ? "Chủ đề / mô tả (để trống = chỉ lấy mẫu để tự sửa)" : "Tiêu đề bài (tuỳ chọn)"}</label>
          <textarea value={topic} onChange={(e) => setTopic(e.target.value)} rows={srcMode === "topic" ? 3 : 1}
            placeholder="VD: Giới thiệu game Palworld — tổng quan, gameplay, số liệu Steam, kết luận."
            style={{ width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 12, color: "var(--white)", fontSize: 14, padding: "12px 14px", fontFamily: "inherit", lineHeight: 1.6, resize: "vertical", marginBottom: 18 }} />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, gap: 12, flexWrap: "wrap" }}>
            <label style={{ ...fieldLabel, marginBottom: 0 }}>Chọn mẫu thiết kế <span style={{ color: "var(--gray-5)" }}>({templates.length})</span></label>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }} title="Số trang khi AI điền nội dung theo chủ đề (bỏ trống nội dung = dùng nguyên số trang của mẫu)">
                <label style={{ ...fieldLabel, marginBottom: 0 }}>Số trang</label>
                <input type="number" min={3} value={Number.isFinite(pageCount) ? pageCount : ""}
                  placeholder="6"
                  onChange={(e) => { const v = e.target.value; setPageCount(v === "" ? NaN : Math.max(0, Math.floor(Number(v)))); }}
                  style={{ width: 60, background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 8, color: "var(--accent)", fontSize: 13, fontWeight: 800, textAlign: "center", padding: "6px" }} />
              </div>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm mẫu…" style={{ ...selectStyle, width: 200, padding: "8px 12px" }} />
            </div>
          </div>
          {loading ? (
            <div style={{ color: "var(--gray-5)", fontSize: 13, padding: 20 }}>Đang tải mẫu…</div>
          ) : templates.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--gray-5)", padding: "16px 0" }}>Chưa có mẫu nào.</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 14, maxHeight: 480, overflowY: "auto", padding: 4 }}>
              {tfiltered.map((t) => (
                <TemplateCard key={t.id} t={t} selected={t.id === tplId} onSelect={() => setTplId(t.id)} onPreview={() => setPreviewTpl(t.id)} />
              ))}
            </div>
          )}
          {previewTpl && <TemplatePreviewModal templateId={previewTpl} name={templates.find((t) => t.id === previewTpl)?.name} onClose={() => setPreviewTpl(null)}
            onUse={() => { setTplId(previewTpl); setPreviewTpl(null); }} />}
        </>
      )}

      {error && <div style={{ marginTop: 16, padding: "10px 14px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#fca5a5", fontSize: 13 }}>{error}</div>}

      {srcMode !== "pptx" && (
        <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={handleStart} disabled={busy || !tplId} className="btn-primary" style={{ fontSize: 14, padding: "14px 28px", opacity: (busy || !tplId) ? 0.6 : 1 }}>
            {busy ? "Đang tạo…" : "Tạo slide →"}
          </button>
        </div>
      )}
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
  const donePagesRef = useRef<Set<number>>(new Set());

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
      // Đếm trang xong theo sự kiện SSE (luồng template giữ status DB 'pending'
      // tới cuối → không thể dựa vào DB để hiện tiến độ từng trang).
      if ((type === "page_generated" || type === "page_updated") && typeof p?.currentPage === "number") {
        donePagesRef.current.add(p.currentPage);
        setCompletedCount((c) => Math.max(c, donePagesRef.current.size));
      }
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
        setCompletedCount((c) => Math.max(c, gc));
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
  const [addPageOpen, setAddPageOpen] = useState(false);
  const [addPageDesc, setAddPageDesc] = useState("");
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

  async function waitIdleThenRefresh(label: string): Promise<GeneratedPage[]> {
    setBusyMsg(label);
    await new Promise((r) => setTimeout(r, 1500));
    for (let i = 0; i < 80; i++) {
      if (!(await hasActiveRun(sessionId))) break;
      await new Promise((r) => setTimeout(r, 1500));
    }
    const next = await refresh();
    setRefreshKey((k) => k + 1);
    setBusyMsg("");
    return next;
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

  function handleAddPage() {
    setAddPageDesc("");
    setAddPageOpen(true);
  }
  async function submitAddPage() {
    const desc = addPageDesc.trim();
    if (!desc) return;
    const insertAfter = activePage ? active + 1 : pages.length;
    setAddPageOpen(false);
    try {
      const before = pages.length;
      await addPage(sessionId, desc, insertAfter);
      const after = await waitIdleThenRefresh("Đang thêm trang…");
      // Nhảy tới trang mới vừa sinh (thường được chèn ngay sau trang đang xem)
      if (after.length > before) {
        setActive(Math.min(insertAfter, after.length - 1));
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : "Thêm trang lỗi");
    }
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
          <ExportMenu onExport={handleExport} exporting={exporting} />
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

      {addPageOpen && (
        <div
          onClick={() => setAddPageOpen(false)}
          style={{ position: "fixed", inset: 0, zIndex: 100001, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: "min(560px, 92vw)", background: "var(--surface, #141420)", border: "1px solid var(--gray-2, rgba(255,255,255,0.1))", borderRadius: 16, padding: 24, boxShadow: "0 24px 80px rgba(0,0,0,0.55)" }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <Plus size={18} style={{ color: "var(--accent, #f97316)" }} />
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--white, #fff)" }}>Thêm trang mới</div>
            </div>
            <div style={{ fontSize: 13, color: "var(--gray-5, #a09db8)", marginBottom: 14 }}>
              Mô tả nội dung cho trang slide kế tiếp. AI sẽ tạo trang mới bám theo style hiện tại.
            </div>
            <textarea
              autoFocus
              value={addPageDesc}
              onChange={(e) => setAddPageDesc(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submitAddPage(); }
                if (e.key === "Escape") setAddPageOpen(false);
              }}
              placeholder="Ví dụ: Trang tổng kết 3 bài học chính, kèm lời kêu gọi hành động…"
              rows={4}
              style={{ width: "100%", resize: "vertical", padding: "12px 14px", borderRadius: 10, border: "1px solid var(--gray-2, rgba(255,255,255,0.12))", background: "rgba(255,255,255,0.04)", color: "var(--white, #fff)", fontSize: 14, lineHeight: 1.5, outline: "none", fontFamily: "inherit" }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <button onClick={() => setAddPageOpen(false)} className="btn-ghost" style={{ fontSize: 13, padding: "8px 16px" }}>
                Huỷ
              </button>
              <button
                onClick={submitAddPage}
                disabled={!addPageDesc.trim()}
                style={{ fontSize: 13, fontWeight: 700, padding: "8px 18px", borderRadius: 10, border: "none", cursor: addPageDesc.trim() ? "pointer" : "not-allowed", opacity: addPageDesc.trim() ? 1 : 0.5, background: "var(--accent, #f97316)", color: "#1a0f08", display: "flex", alignItems: "center", gap: 6 }}
              >
                <Plus size={14} />
                Tạo trang
              </button>
            </div>
            <div style={{ fontSize: 11, color: "var(--gray-5, #6b6880)", marginTop: 10, textAlign: "right" }}>
              Ctrl/⌘ + Enter để tạo nhanh
            </div>
          </div>
        </div>
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

/* Thẻ template có thumbnail trang đầu + nút xem toàn bộ slide mẫu. */
function TemplateCard({ t, selected, onSelect, onPreview }: { t: TemplateItem; selected: boolean; onSelect: () => void; onPreview: () => void }) {
  const [firstUrl, setFirstUrl] = useState<string>("");
  useEffect(() => { templateManifest(t.id).then((m) => setFirstUrl(m.pages[0]?.url || "")).catch(() => {}); }, [t.id]);
  return (
    <div style={{
      borderRadius: 12, overflow: "hidden", cursor: "pointer", position: "relative",
      background: selected ? "rgba(249,115,22,0.08)" : "rgba(255,255,255,0.03)",
      border: selected ? "1.5px solid var(--accent)" : "1px solid var(--gray-3)",
    }} onClick={onSelect}>
      <div style={{ aspectRatio: "16/9", background: "#0b0b12", position: "relative" }}>
        {firstUrl ? <ScaledSlideFrame url={firstUrl} title={t.name} frameKey={`tplthumb-${t.id}`} />
          : <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--gray-5)", fontSize: 12 }}>Đang tải…</div>}
        <button type="button" title="Xem tất cả slide mẫu"
          onClick={(e) => { e.stopPropagation(); onPreview(); }}
          style={{ position: "absolute", top: 8, right: 8, background: "rgba(0,0,0,0.55)", border: "none", borderRadius: 8, padding: 6, color: "#fff", cursor: "pointer", display: "flex" }}>
          <Maximize2 size={15} />
        </button>
      </div>
      <div style={{ padding: "10px 12px" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: selected ? "var(--accent)" : "var(--white)" }}>{t.name}</div>
        <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 2 }}>{t.pageCount ?? "?"} trang</div>
      </div>
    </div>
  );
}

/* Modal xem toàn bộ slide mẫu của 1 template. */
function TemplatePreviewModal({ templateId, name, onClose, onUse }: { templateId: string; name?: string; onClose: () => void; onUse: () => void }) {
  const [pages, setPages] = useState<{ pageNumber: number; title: string; url: string }[]>([]);
  const [zoom, setZoom] = useState<number | null>(null);   // index slide đang phóng to
  useEffect(() => { templateManifest(templateId).then((m) => setPages(m.pages)).catch(() => {}); }, [templateId]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (zoom === null) return;
      if (e.key === "Escape") setZoom(null);
      if (e.key === "ArrowRight") setZoom((z) => (z === null ? z : Math.min(pages.length - 1, z + 1)));
      if (e.key === "ArrowLeft") setZoom((z) => (z === null ? z : Math.max(0, z - 1)));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoom, pages.length]);
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 1000, display: "flex", flexDirection: "column", padding: "3vh 4vw" }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--black)", border: "1px solid var(--gray-3)", borderRadius: 16, display: "flex", flexDirection: "column", maxHeight: "94vh", overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid var(--gray-2)" }}>
          <div style={{ fontSize: 15, fontWeight: 800 }}>{name || "Mẫu"} <span style={{ color: "var(--gray-5)", fontWeight: 400 }}>· {pages.length} slide mẫu · bấm để phóng to</span></div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onUse} className="btn-primary" style={{ fontSize: 13 }}>Dùng mẫu này →</button>
            <button onClick={onClose} className="btn-ghost" style={{ display: "flex", padding: 8 }}><X size={16} /></button>
          </div>
        </div>
        <div style={{ overflowY: "auto", padding: 20, display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(360px,1fr))", gap: 16 }}>
          {pages.map((p, i) => (
            <div key={p.pageNumber} onClick={() => setZoom(i)} title="Bấm để phóng to" style={{ borderRadius: 10, overflow: "hidden", border: "1px solid var(--gray-3)", cursor: "zoom-in" }}>
              <div style={{ aspectRatio: "16/9", background: "#0b0b12", pointerEvents: "none" }}>
                <ScaledSlideFrame url={p.url} title={p.title} frameKey={`tplprev-${templateId}-${p.pageNumber}`} />
              </div>
              <div style={{ padding: "8px 10px", fontSize: 12, color: "var(--gray-5)" }}>{p.pageNumber}. {p.title}</div>
            </div>
          ))}
        </div>
      </div>
      {zoom !== null && pages[zoom] && (
        <div onClick={(e) => { e.stopPropagation(); setZoom(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.9)", zIndex: 1100, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: "2vh 2vw" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "min(1400px,92vw)", color: "var(--white)" }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>{pages[zoom].pageNumber}. {pages[zoom].title} <span style={{ color: "var(--gray-5)", fontWeight: 400 }}>({zoom + 1}/{pages.length})</span></div>
            <button onClick={(e) => { e.stopPropagation(); setZoom(null); }} className="btn-ghost" style={{ display: "flex", padding: 8 }}><X size={18} /></button>
          </div>
          <div onClick={(e) => e.stopPropagation()} style={{ width: "min(1400px,92vw)", aspectRatio: "16/9", background: "#0b0b12", borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-3)", position: "relative" }}>
            <ScaledSlideFrame url={pages[zoom].url} title={pages[zoom].title} frameKey={`tplzoom-${templateId}-${zoom}`} />
            {zoom > 0 && <button onClick={(e) => { e.stopPropagation(); setZoom(zoom - 1); }} style={navBtn("left")}><ChevronDown size={22} style={{ transform: "rotate(90deg)" }} /></button>}
            {zoom < pages.length - 1 && <button onClick={(e) => { e.stopPropagation(); setZoom(zoom + 1); }} style={navBtn("right")}><ChevronDown size={22} style={{ transform: "rotate(-90deg)" }} /></button>}
          </div>
          <div style={{ fontSize: 12, color: "var(--gray-5)" }}>← → chuyển slide · Esc / bấm nền để đóng</div>
        </div>
      )}
    </div>
  );
}

function navBtn(side: "left" | "right"): CSSProperties {
  return { position: "absolute", top: "50%", [side]: 12, transform: "translateY(-50%)", background: "rgba(0,0,0,0.55)", border: "none", borderRadius: 999, width: 44, height: 44, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", cursor: "pointer" } as CSSProperties;
}

/* Nút "Xuất" gộp — bấm mở 3 lựa chọn PPTX / PDF / PNG cho gọn. */
function ExportMenu({ onExport, exporting }: { onExport: (k: ExportKind) => void; exporting: ExportKind | "" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const items: { k: ExportKind; label: string; desc: string }[] = [
    { k: "pptx", label: "PowerPoint", desc: ".pptx — mở/sửa trên PowerPoint, Canva" },
    { k: "pdf", label: "PDF", desc: ".pdf — chia sẻ, in ấn" },
    { k: "png", label: "Ảnh PNG", desc: ".zip — mỗi trang 1 ảnh" },
  ];
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen((o) => !o)} disabled={!!exporting} className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
        {exporting ? `Đang xuất ${exporting.toUpperCase()}…` : "Xuất"} <ChevronDown size={14} />
      </button>
      {open && !exporting && (
        <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: "var(--black)", border: "1px solid var(--gray-3)", borderRadius: 12, padding: 6, minWidth: 240, zIndex: 60, boxShadow: "0 14px 34px rgba(0,0,0,0.55)" }}>
          {items.map(({ k, label, desc }) => (
            <button key={k} onClick={() => { setOpen(false); onExport(k); }}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "10px 12px", background: "transparent", border: "none", color: "var(--white)", cursor: "pointer", borderRadius: 8 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(249,115,22,0.12)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
              <div style={{ fontSize: 13, fontWeight: 700 }}>{label}</div>
              <div style={{ fontSize: 11, color: "var(--gray-5)", marginTop: 2 }}>{desc}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────  styles  ───────────────────────── */
const fieldLabel: CSSProperties = { display: "block", fontSize: 11, fontWeight: 700, color: "var(--gray-5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" };
const selectStyle: CSSProperties = { width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 10, color: "var(--white)", fontSize: 13, padding: "10px 12px" };
