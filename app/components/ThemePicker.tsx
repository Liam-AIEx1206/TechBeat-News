"use client";

import { THEMES, type ThemeId, type Theme } from "@/types/scene";

interface Props {
  value: ThemeId;
  onChange: (id: ThemeId) => void;
}

export function ThemePicker({ value, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{
          fontSize: 10, fontWeight: 800, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "var(--gray-5)",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ width: 16, height: 1, background: "var(--accent)" }} />
          Bảng màu chủ đạo
        </div>
        <span style={{ fontSize: 11, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
          {THEMES.length} themes
        </span>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
        gap: 10,
      }}>
        {THEMES.map((t) => (
          <ThemeCard key={t.id} theme={t} active={t.id === value} onClick={() => onChange(t.id)} />
        ))}
      </div>
    </div>
  );
}

function ThemeCard({ theme, active, onClick }: { theme: Theme; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      type="button"
      style={{
        position: "relative",
        textAlign: "left",
        cursor: "pointer",
        padding: 0,
        background: "transparent",
        border: "none",
      }}
    >
      <div
        style={{
          position: "relative",
          height: 92,
          borderRadius: 14,
          overflow: "hidden",
          border: active ? `1.5px solid ${theme.accent}` : "1px solid var(--gray-3)",
          boxShadow: active
            ? `0 0 0 3px ${theme.accent}22, 0 12px 32px -8px ${theme.accent}66`
            : "none",
          transition: "all 0.25s var(--ease-out)",
          background: theme.bg,
        }}
      >
        {/* Animated gradient background mock */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: `
            radial-gradient(ellipse 200px 140px at 20% 20%, ${theme.accent}33 0%, transparent 60%),
            radial-gradient(ellipse 160px 120px at 80% 80%, ${theme.accent2}22 0%, transparent 60%),
            linear-gradient(135deg, ${theme.bg} 0%, ${theme.bg2} 100%)
          `,
        }} />

        {/* Color stripes */}
        <div style={{
          position: "absolute", left: 12, right: 12, bottom: 12,
          display: "flex", gap: 4,
        }}>
          {[theme.accent, theme.accent2, theme.accent3, theme.text1].map((c, i) => (
            <div key={i} style={{
              flex: 1, height: 6, borderRadius: 3,
              background: c,
              boxShadow: i < 3 ? `0 0 8px ${c}66` : "none",
            }} />
          ))}
        </div>

        {/* Mock ticker line */}
        <div style={{
          position: "absolute", top: 12, left: 12, right: 12,
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <span style={{
            fontSize: 8, fontWeight: 800, letterSpacing: "0.12em",
            background: theme.accent, color: theme.bg,
            padding: "2px 6px", borderRadius: 3,
          }}>
            LIVE
          </span>
          <span style={{
            flex: 1, height: 1,
            background: `linear-gradient(90deg, ${theme.accent}66, transparent)`,
          }} />
        </div>

        {active && (
          <div style={{
            position: "absolute", top: 8, right: 8,
            width: 22, height: 22, borderRadius: "50%",
            background: theme.accent, color: theme.bg,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: `0 0 12px ${theme.accent}`,
          }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
        )}
      </div>

      <div style={{
        marginTop: 10,
        display: "flex", flexDirection: "column", gap: 2,
      }}>
        <div style={{
          fontSize: 12, fontWeight: 700,
          color: active ? theme.accent : "var(--white)",
          letterSpacing: "-0.01em",
          transition: "color 0.2s",
        }}>
          {theme.name}
        </div>
        <div style={{ fontSize: 10, color: "var(--gray-5)", letterSpacing: "0.04em" }}>
          {theme.tagline}
        </div>
      </div>
    </button>
  );
}
