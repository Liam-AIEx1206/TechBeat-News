"use client";

import { useEffect, useState } from "react";

/** Style pack (oh-my-ppt format) trả từ backend GET /styles */
interface StylePack {
  id: string;
  label: string;
  labelEn?: string;
  description?: string;
  category?: string;
  palette: Record<string, string>;
  hasPreview?: boolean;
}

interface Props {
  value?: string;                 // styleId đang chọn
  onChange: (id: string) => void;
}

export function StylePicker({ value, onChange }: Props) {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const listUrl = process.env.NODE_ENV === "development" ? `${API}/styles` : `/api/proxy/styles`;
  const previewBase = process.env.NODE_ENV === "development" ? `${API}/styles` : `/api/proxy/styles`;

  const [styles, setStyles] = useState<StylePack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch(listUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (alive) setStyles(data.styles ?? []);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Không tải được style");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [listUrl]);

  if (loading) {
    return <div style={{ fontSize: 12, color: "var(--gray-5)", padding: 8 }}>Đang tải style…</div>;
  }
  if (error || styles.length === 0) {
    return (
      <div style={{ fontSize: 12, color: "var(--gray-5)", lineHeight: 1.6, padding: 8 }}>
        {error ? `Lỗi: ${error}. ` : ""}Chưa có style nào. Thả thư mục style (style.json + SKILL.md +
        preview.html) vào <code>backend/templates/styles/</code> — xem README ở đó.
      </div>
    );
  }

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
      gap: 12,
    }}>
      {styles.map((s) => (
        <StyleCard
          key={s.id}
          style={s}
          active={s.id === value}
          previewUrl={s.hasPreview ? `${previewBase}/${s.id}/preview` : ""}
          onClick={() => onChange(s.id)}
        />
      ))}
    </div>
  );
}

function StyleCard({ style, active, previewUrl, onClick }: {
  style: StylePack; active: boolean; previewUrl: string; onClick: () => void;
}) {
  const p = style.palette || {};
  const accent = p.accent || "#6366f1";
  const swatches = [p.accent, p.accent2, p.accent3, p.text1].filter(Boolean) as string[];

  return (
    <button
      onClick={onClick}
      type="button"
      style={{ textAlign: "left", cursor: "pointer", padding: 0, background: "transparent", border: "none" }}
    >
      <div style={{
        position: "relative",
        height: 116,
        borderRadius: 14,
        overflow: "hidden",
        border: active ? `1.5px solid ${accent}` : "1px solid var(--gray-3)",
        boxShadow: active ? `0 0 0 3px ${accent}22, 0 12px 32px -8px ${accent}66` : "none",
        transition: "all 0.25s var(--ease-out)",
        background: p.bg || "#0b0b12",
      }}>
        {previewUrl ? (
          // Thumbnail = preview.html thật của style, thu nhỏ 1280×720 vào khung.
          <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
            <iframe
              src={previewUrl}
              title={style.label}
              scrolling="no"
              style={{
                width: 1280, height: 720, border: "none",
                transform: "scale(0.1719)",  // 220px / 1280
                transformOrigin: "top left",
              }}
            />
          </div>
        ) : (
          // Không có preview → mock gradient + swatch từ palette
          <>
            <div style={{
              position: "absolute", inset: 0,
              backgroundImage: `radial-gradient(ellipse 200px 140px at 20% 20%, ${accent}33 0%, transparent 60%), linear-gradient(135deg, ${p.bg || "#0b0b12"} 0%, ${p.bg2 || "#14141f"} 100%)`,
            }} />
            <div style={{ position: "absolute", left: 12, right: 12, bottom: 12, display: "flex", gap: 4 }}>
              {swatches.map((c, i) => (
                <div key={i} style={{ flex: 1, height: 6, borderRadius: 3, background: c, boxShadow: i < 3 ? `0 0 8px ${c}66` : "none" }} />
              ))}
            </div>
          </>
        )}

        {style.category && (
          <span style={{
            position: "absolute", top: 8, left: 8,
            fontSize: 8, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase",
            background: "rgba(0,0,0,0.55)", color: "#fff", padding: "2px 6px", borderRadius: 4,
          }}>
            {style.category}
          </span>
        )}
        {active && (
          <div style={{
            position: "absolute", top: 8, right: 8, width: 22, height: 22, borderRadius: "50%",
            background: accent, color: p.bg || "#000",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 900, boxShadow: `0 0 12px ${accent}`,
          }}>✓</div>
        )}
      </div>

      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: active ? accent : "var(--white)", letterSpacing: "-0.01em" }}>
          {style.label}
        </div>
        {style.description && (
          <div style={{
            fontSize: 10, color: "var(--gray-5)", letterSpacing: "0.02em", lineHeight: 1.4,
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {style.description}
          </div>
        )}
      </div>
    </button>
  );
}
