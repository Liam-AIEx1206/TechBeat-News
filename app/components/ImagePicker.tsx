"use client";

import { useEffect, useRef, useState } from "react";

interface ImageResult {
  image: string;
  thumbnail: string;
  title: string;
  source: string;
  url: string;
  width?: number;
  height?: number;
  license?: string;
  creator?: string;
}

interface Props {
  open: boolean;
  initialQuery: string;
  onClose: () => void;
  onPick: (url: string) => void;
}

type Tab = "search" | "upload";

export function ImagePicker({ open, initialQuery, onClose, onPick }: Props) {
  const [tab, setTab]         = useState<Tab>("search");
  const [query, setQuery]     = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [results, setResults] = useState<ImageResult[]>([]);
  const [uploadPreview, setUploadPreview] = useState<string>("");
  const [uploadDragging, setUploadDragging] = useState(false);
  const abortRef  = useRef<AbortController | null>(null);
  const inputRef  = useRef<HTMLInputElement>(null);
  const fileRef   = useRef<HTMLInputElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    if (open) {
      setTab("search");
      setQuery(initialQuery);
      setResults([]);
      setError("");
      setUploadPreview("");
      if (initialQuery.trim()) runSearch(initialQuery);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialQuery]);

  async function runSearch(q: string) {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/image-search?q=${encodeURIComponent(q)}&limit=18`, { signal: ac.signal });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results ?? []);
      if ((data.results ?? []).length === 0) setError("Không tìm thấy ảnh phù hợp. Thử từ khóa khác.");
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Tìm ảnh thất bại");
    } finally {
      setLoading(false);
    }
  }

  function handleFileSelect(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("Chỉ hỗ trợ file ảnh (JPG, PNG, WebP, GIF)");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File quá lớn (tối đa 10MB)");
      return;
    }
    setError("");
    const reader = new FileReader();
    reader.onload = (e) => setUploadPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }

  function confirmUpload() {
    if (uploadPreview) { onPick(uploadPreview); onClose(); }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 fade-in"
      style={{ background: "rgba(0,0,0,0.8)", backdropFilter: "blur(10px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl overflow-hidden fade-up"
        style={{ background: "var(--surface)", border: "1px solid var(--border-2)", boxShadow: "0 40px 100px -10px rgba(0,0,0,0.9)" }}
      >
        {/* ── Header ── */}
        <div className="px-5 py-4 flex items-center gap-3 flex-wrap" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex-1 min-w-[160px]">
            <div className="text-[9px] font-black uppercase tracking-widest mb-0.5" style={{ color: "var(--accent-2)" }}>
              Ảnh minh họa
            </div>
            <h3 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Chọn ảnh cho phân cảnh</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { onPick(""); onClose(); }}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold transition-all"
              style={{ border: "1px solid rgba(248,113,113,0.25)", color: "var(--red)", background: "transparent" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(248,113,113,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              Không dùng ảnh
            </button>
            <button onClick={onClose} className="btn-ghost text-xs px-3 py-1.5">✕ Đóng</button>
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="flex px-5 pt-3 gap-1" style={{ borderBottom: "1px solid var(--border)" }}>
          {(["search", "upload"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); }}
              className="px-4 py-2 text-xs font-bold rounded-t-lg transition-all relative"
              style={{
                color: tab === t ? "var(--accent-2)" : "var(--text-3)",
                background: tab === t ? "rgba(249,115,22,0.08)" : "transparent",
                borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
              }}
            >
              {t === "search" ? "🔍 Tìm kiếm (Openverse)" : "📁 Upload ảnh"}
            </button>
          ))}
        </div>

        {/* ── Search tab ── */}
        {tab === "search" && (
          <>
            <div className="px-5 py-3 flex gap-2" style={{ borderBottom: "1px solid var(--border)" }}>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch(query)}
                placeholder="Từ khóa tiếng Anh cho kết quả tốt hơn..."
                className="input-dark flex-1 text-sm py-2"
              />
              <button onClick={() => runSearch(query)} disabled={loading || !query.trim()} className="btn-primary text-sm px-4 py-2">
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Đang tìm
                  </span>
                ) : "Tìm"}
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4">
              {error && (
                <div className="mb-3 px-4 py-3 rounded-xl text-sm"
                  style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", color: "var(--red)" }}>
                  ⚠ {error}
                </div>
              )}
              {loading && results.length === 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2.5">
                  {Array.from({ length: 12 }).map((_, i) => <div key={i} className="aspect-square rounded-xl shimmer" />)}
                </div>
              )}
              {!loading && results.length === 0 && !error && (
                <div className="text-center py-14" style={{ color: "var(--text-3)" }}>
                  <div className="text-4xl mb-3">🔍</div>
                  <p className="text-sm">Nhập từ khóa rồi bấm Tìm</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-3)" }}>Hoặc chuyển sang tab Upload để dùng ảnh của bạn</p>
                </div>
              )}
              {results.length > 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2.5">
                  {results.map((r, i) => (
                    <button
                      key={r.image + i}
                      onClick={() => { onPick(r.image); onClose(); }}
                      className="group relative aspect-square rounded-xl overflow-hidden transition-all"
                      style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(249,115,22,0.5)")}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                      title={r.title}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={r.thumbnail} alt={r.title} className="w-full h-full object-cover transition-transform group-hover:scale-105" loading="lazy" referrerPolicy="no-referrer" />
                      <div className="absolute inset-0 flex items-end opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ background: "linear-gradient(to top,rgba(0,0,0,0.8) 0%,transparent 60%)" }}>
                        <span className="px-2 py-1.5 text-[9px] text-white font-medium truncate w-full text-left">
                          {r.creator || r.source || r.title}
                        </span>
                      </div>
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-black"
                          style={{ background: "rgba(249,115,22,0.9)", boxShadow: "0 4px 12px rgba(249,115,22,0.5)" }}>✓</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── Upload tab ── */}
        {tab === "upload" && (
          <div className="flex-1 overflow-auto p-5 flex flex-col gap-4">
            {error && (
              <div className="px-4 py-3 rounded-xl text-sm"
                style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", color: "var(--red)" }}>
                ⚠ {error}
              </div>
            )}

            {!uploadPreview ? (
              <div
                className={`drop-zone flex-1 flex flex-col items-center justify-center gap-4 p-10 text-center min-h-[280px] ${uploadDragging ? "dragging" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setUploadDragging(true); }}
                onDragLeave={() => setUploadDragging(false)}
                onDrop={(e) => { e.preventDefault(); setUploadDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFileSelect(f); }}
                onClick={() => fileRef.current?.click()}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); e.target.value = ""; }}
                />
                <div className="text-5xl">🖼️</div>
                <div>
                  <p className="text-sm font-bold mb-1" style={{ color: "var(--text-1)" }}>Kéo ảnh vào đây hoặc click để chọn</p>
                  <p className="text-xs" style={{ color: "var(--text-3)" }}>JPG · PNG · WebP · GIF · tối đa 10MB</p>
                </div>
                <div className="text-xs px-4 py-2 rounded-lg font-semibold"
                  style={{ background: "rgba(249,115,22,0.1)", color: "var(--accent-2)", border: "1px solid rgba(249,115,22,0.2)" }}>
                  Chọn từ máy tính
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="relative rounded-xl overflow-hidden" style={{ background: "var(--bg-2)" }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={uploadPreview} alt="Preview" className="w-full max-h-72 object-contain" />
                </div>
                <div className="flex gap-2 justify-end">
                  <button onClick={() => { setUploadPreview(""); setError(""); }} className="btn-ghost text-sm">
                    ← Chọn ảnh khác
                  </button>
                  <button onClick={confirmUpload} className="btn-primary text-sm px-6">
                    ✓ Dùng ảnh này
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Footer ── */}
        <div className="px-5 py-2.5 flex items-center justify-between text-[10px]"
          style={{ borderTop: "1px solid var(--border)", color: "var(--text-3)" }}>
          <span>Click ảnh để chọn · Ảnh tải về tự động khi bấm Dựng</span>
          <span style={{ color: "rgba(249,115,22,0.4)" }} className="font-semibold">Openverse CC · Upload local</span>
        </div>
      </div>
    </div>
  );
}
