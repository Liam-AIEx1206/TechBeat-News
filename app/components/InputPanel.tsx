"use client";

import { useState, useRef, DragEvent } from "react";

interface Props {
  onExtracted: (content: { title: string; text: string; source: string; videoDuration?: number | null }) => void;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
  setError: (v: string) => void;
}

export function InputPanel({ onExtracted, isLoading, setIsLoading, setError }: Props) {
  const [url, setUrl]         = useState("");
  const [dragging, setDragging] = useState(false);
  const [focused, setFocused]   = useState(false);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function extractUrl() {
    if (!url.trim()) return;
    setIsLoading(true); setError("");
    try {
      const res = await fetch(`${API}/extract/url`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Trích xuất thất bại");
      const data = await res.json();
      onExtracted({ ...data, videoDuration });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể trích xuất URL");
    } finally { setIsLoading(false); }
  }

  async function extractFile(file: File) {
    setIsLoading(true); setError("");
    try {
      const form = new FormData(); form.append("file", file);
      const res = await fetch(`${API}/extract/file`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Trích xuất thất bại");
      const data = await res.json();
      onExtracted({ ...data, videoDuration });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể trích xuất file");
    } finally { setIsLoading(false); }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) extractFile(file);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Video Duration Selector — premium design ── */}
      <div>
        <div style={{
          fontSize: 10, fontWeight: 800, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "var(--accent2)",
          marginBottom: 10, display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ width: 20, height: 1, background: "var(--accent)", display: "inline-block" }} />
          Chọn thời lượng video
        </div>
        
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 10,
          background: "rgba(255,255,255,0.03)",
          padding: 6,
          borderRadius: "var(--r-lg)",
          border: "1px solid var(--gray-3)",
        }}>
          {[
            { label: "Tự động", val: null },
            { label: "1 Phút", val: 60 },
            { label: "2 Phút", val: 120 },
            { label: "3 Phút", val: 180 },
            { label: "Không tóm tắt", val: -1 },
          ].map((opt) => {
            const active = videoDuration === opt.val;
            return (
              <button
                key={opt.label}
                onClick={() => setVideoDuration(opt.val)}
                disabled={isLoading}
                style={{
                  padding: "10px 6px",
                  borderRadius: "calc(var(--r-lg) - 4px)",
                  background: active
                    ? "linear-gradient(135deg, #f97316, #ea580c)"
                    : "transparent",
                  color: active ? "#000000" : "var(--gray-5)",
                  border: "none",
                  fontSize: 12,
                  fontWeight: active ? 800 : 600,
                  cursor: "none",
                  transition: "all 0.25s var(--ease-out)",
                  boxShadow: active ? "0 4px 12px rgba(249,115,22,0.2)" : "none",
                }}
                onMouseEnter={(e) => {
                  if (!active && !isLoading) {
                    e.currentTarget.style.color = "var(--white)";
                    e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.color = "var(--gray-5)";
                    e.currentTarget.style.background = "transparent";
                  }
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── URL input — bright, prominent ── */}
      <div>
        <div style={{
          fontSize: 10, fontWeight: 800, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "var(--accent2)",
          marginBottom: 10, display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ width: 20, height: 1, background: "var(--accent)", display: "inline-block" }} />
          🔗 Dán URL bài viết
        </div>

        {/* Input wrapper with glow */}
        <div style={{
          position: "relative",
          borderRadius: "var(--r-lg)",
          padding: 2,
          background: focused
            ? "linear-gradient(135deg, #f97316, #fb923c, #fbbf24)"
            : "linear-gradient(135deg, rgba(249,115,22,0.3), rgba(251,146,60,0.2))",
          transition: "background 0.3s",
          boxShadow: focused ? "0 0 32px rgba(249,115,22,0.25)" : "none",
        }}>
          <div style={{
            display: "flex", gap: 0,
            background: "#161616",
            borderRadius: "calc(var(--r-lg) - 2px)",
            overflow: "hidden",
          }}>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && extractUrl()}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="https://techcrunch.com/..."
              disabled={isLoading}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                padding: "14px 20px",
                color: "#ffffff",
                fontSize: 14,
                fontFamily: "inherit",
              }}
            />
            <button
              onClick={extractUrl}
              disabled={isLoading || !url.trim()}
              style={{
                padding: "14px 24px",
                background: url.trim() && !isLoading
                  ? "linear-gradient(135deg, #f97316, #ea580c)"
                  : "rgba(249,115,22,0.15)",
                border: "none",
                color: url.trim() && !isLoading ? "#000" : "rgba(249,115,22,0.4)",
                fontSize: 13,
                fontWeight: 800,
                letterSpacing: "0.02em",
                cursor: "none",
                transition: "all 0.25s var(--ease-out)",
                whiteSpace: "nowrap",
                flexShrink: 0,
              }}
            >
              {isLoading ? (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    width: 12, height: 12, borderRadius: "50%",
                    border: "2px solid rgba(0,0,0,0.2)", borderTopColor: "#000",
                    animation: "spin 0.8s linear infinite", display: "inline-block",
                  }} />
                  Đang xử lý
                </span>
              ) : "Trích xuất →"}
            </button>
          </div>
        </div>

        {/* Helper text */}
        <p style={{ fontSize: 11, color: "var(--gray-4)", marginTop: 8, paddingLeft: 4 }}>
          Hỗ trợ: TechCrunch, VnExpress, The Verge, Medium, và hầu hết các trang tin tức
        </p>
      </div>

      {/* ── Divider ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1, height: 1, background: "var(--gray-3)" }} />
        <span style={{
          fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
          textTransform: "uppercase", color: "var(--gray-4)",
          padding: "4px 12px", border: "1px solid var(--gray-3)",
          borderRadius: "var(--r-full)",
        }}>hoặc</span>
        <div style={{ flex: 1, height: 1, background: "var(--gray-3)" }} />
      </div>

      {/* ── Drop zone — bright on hover ── */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !isLoading && fileRef.current?.click()}
        style={{
          position: "relative",
          padding: "32px 24px",
          textAlign: "center",
          borderRadius: "var(--r-lg)",
          border: dragging
            ? "1.5px solid rgba(249,115,22,0.7)"
            : "1.5px dashed rgba(255,255,255,0.12)",
          background: dragging
            ? "rgba(249,115,22,0.06)"
            : "rgba(255,255,255,0.03)",
          cursor: "none",
          transition: "all 0.25s var(--ease-out)",
          opacity: isLoading ? 0.4 : 1,
          overflow: "hidden",
        }}
        onMouseEnter={(e) => {
          if (!isLoading) {
            e.currentTarget.style.border = "1.5px dashed rgba(249,115,22,0.4)";
            e.currentTarget.style.background = "rgba(249,115,22,0.03)";
          }
        }}
        onMouseLeave={(e) => {
          if (!dragging) {
            e.currentTarget.style.border = "1.5px dashed rgba(255,255,255,0.12)";
            e.currentTarget.style.background = "rgba(255,255,255,0.03)";
          }
        }}
      >
        {/* Animated corner accents */}
        {[
          { top: 8, left: 8, borderTop: "1.5px solid var(--accent)", borderLeft: "1.5px solid var(--accent)" },
          { top: 8, right: 8, borderTop: "1.5px solid var(--accent)", borderRight: "1.5px solid var(--accent)" },
          { bottom: 8, left: 8, borderBottom: "1.5px solid var(--accent)", borderLeft: "1.5px solid var(--accent)" },
          { bottom: 8, right: 8, borderBottom: "1.5px solid var(--accent)", borderRight: "1.5px solid var(--accent)" },
        ].map((style, i) => (
          <div key={i} style={{ position: "absolute", width: 16, height: 16, opacity: dragging ? 1 : 0.3, transition: "opacity 0.3s", ...style }} />
        ))}

        <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.xlsx,.odt,.odp,.md,.txt"
          style={{ display: "none" }} disabled={isLoading}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) extractFile(f); e.target.value = ""; }} />

        <div style={{ fontSize: 36, marginBottom: 12, filter: dragging ? "drop-shadow(0 0 12px rgba(249,115,22,0.6))" : "none", transition: "filter 0.3s" }}>
          📄
        </div>
        <p style={{ fontSize: 14, fontWeight: 700, color: dragging ? "var(--white)" : "rgba(255,255,255,0.7)", marginBottom: 8, transition: "color 0.2s" }}>
          Kéo file vào đây hoặc click để chọn
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, flexWrap: "wrap" }}>
          {["PDF", "DOCX", "PPTX", "MD", "TXT"].map((ext) => (
            <span key={ext} style={{
              fontSize: 10, fontWeight: 800, padding: "3px 10px",
              borderRadius: "var(--r-full)",
              background: "rgba(249,115,22,0.1)",
              border: "1px solid rgba(249,115,22,0.25)",
              color: "var(--accent2)",
              letterSpacing: "0.06em",
            }}>{ext}</span>
          ))}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
