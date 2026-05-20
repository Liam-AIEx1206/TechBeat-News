"use client";

import { useEffect, useState } from "react";

interface ElevenVoice {
  voice_id: string;
  name: string;
  gender?: string;
  description?: string;
  category?: string;
}

interface VoicesResponse {
  default_voice_id: string;
  premade: ElevenVoice[];
  custom: ElevenVoice[];
  has_api_key: boolean;
  error: string | null;
}

interface Props {
  value: string | undefined;
  onChange: (id: string) => void;
}

export function VoicePicker({ value, onChange }: Props) {
  const [data, setData] = useState<VoicesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/voices/elevenlabs`)
      .then((r) => r.json())
      .then((d: VoicesResponse) => {
        if (cancelled) return;
        setData(d);
        if (!value && d.default_voice_id) onChange(d.default_voice_id);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "12px 0", fontSize: 12, color: "var(--gray-5)" }}>
        Đang tải danh sách voice...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ fontSize: 12, color: "var(--red)" }}>
        Không tải được voice list: {error || "?"}
      </div>
    );
  }

  const allVoices: ElevenVoice[] = [...data.premade, ...data.custom];
  const selected = value ?? data.default_voice_id;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{
          fontSize: 10, fontWeight: 800, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "var(--gray-5)",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ width: 16, height: 1, background: "var(--accent)" }} />
          Giọng đọc
        </div>
        <div style={{ fontSize: 11, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
          {data.has_api_key ? `${allVoices.length} voices` : "ElevenLabs chưa cấu hình"}
        </div>
      </div>

      {!data.has_api_key && (
        <div style={{
          padding: "12px 16px",
          borderRadius: "var(--r)",
          background: "rgba(251,191,36,0.08)",
          border: "1px solid rgba(251,191,36,0.25)",
          color: "var(--accent3)",
          fontSize: 12, lineHeight: 1.7,
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>⚠ Backend chưa load ELEVENLABS_API_KEY</div>
          <div style={{ color: "var(--gray-6)" }}>
            Hệ thống đang fallback sang gTTS (giọng Google mặc định, nữ AI). Để dùng ElevenLabs:
            <ol style={{ margin: "6px 0 0 18px", padding: 0 }}>
              <li>Lấy key tại{" "}
                <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer"
                  style={{ color: "var(--accent2)", textDecoration: "underline" }}>elevenlabs.io/settings/api-keys</a>
                {" "}— bật quyền <strong>Text to Speech: Access</strong> + <strong>Voices: Read</strong>
              </li>
              <li>Paste vào <code style={{ fontFamily: "var(--font-mono)" }}>backend/.env</code> dòng <code style={{ fontFamily: "var(--font-mono)" }}>ELEVENLABS_API_KEY=sk_...</code></li>
              <li><strong>Restart backend</strong> (uvicorn không tự reload .env)</li>
            </ol>
          </div>
        </div>
      )}

      {data.error && data.has_api_key && (
        <div style={{
          padding: "10px 14px", borderRadius: "var(--r)",
          background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
          color: "var(--red)", fontSize: 12, lineHeight: 1.6,
        }}>
          ⚠ Không gọi được ElevenLabs: {data.error}
          {data.error.includes("401") && (
            <div style={{ marginTop: 6, color: "var(--gray-6)" }}>
              API key cần thêm quyền <code style={{ fontFamily: "var(--font-mono)" }}>Voices: Read</code>.
              Vào{" "}
              <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer"
                style={{ color: "var(--accent2)", textDecoration: "underline" }}>elevenlabs.io/settings/api-keys</a>
              {" "}→ Edit key → bật <strong>Voices: Read</strong> để hiện custom voices.
            </div>
          )}
        </div>
      )}

      {data.has_api_key && !data.error && data.custom.length === 0 && (
        <div style={{
          padding: "10px 14px", borderRadius: "var(--r)",
          background: "rgba(34,211,238,0.05)", border: "1px solid rgba(34,211,238,0.2)",
          color: "#67e8f9", fontSize: 12, lineHeight: 1.6,
        }}>
          ℹ Chưa thấy voice nào trong account. Nếu bạn đã add voice từ Library mà không hiện ở đây,
          API key cần quyền <code style={{ fontFamily: "var(--font-mono)" }}>Voices: Read</code>.
          Edit key tại{" "}
          <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer"
            style={{ color: "var(--accent2)", textDecoration: "underline" }}>elevenlabs.io</a>.
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: 10,
      }}>
        {data.custom.length > 0 && (
          <SectionLabel label="Voices của bạn" count={data.custom.length} />
        )}
        {data.custom.map((v) => (
          <VoiceCard key={v.voice_id} voice={v} active={v.voice_id === selected}
            badge="Custom" onClick={() => onChange(v.voice_id)} />
        ))}

        {data.custom.length > 0 && data.premade.length > 0 && (
          <SectionLabel label="Voice mặc định (premade)" count={data.premade.length} />
        )}
        {data.premade.map((v) => (
          <VoiceCard key={v.voice_id} voice={v} active={v.voice_id === selected}
            badge="Premade" onClick={() => onChange(v.voice_id)} />
        ))}
      </div>
    </div>
  );
}

function SectionLabel({ label, count }: { label: string; count: number }) {
  return (
    <div style={{
      gridColumn: "1 / -1",
      display: "flex", alignItems: "center", gap: 12,
      fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
      textTransform: "uppercase", color: "var(--gray-5)",
      paddingTop: 4,
    }}>
      <span>{label}</span>
      <span style={{
        padding: "2px 8px", borderRadius: 99,
        background: "var(--gray-2)", border: "1px solid var(--gray-3)",
        fontFamily: "var(--font-mono)", fontSize: 10,
      }}>{count}</span>
      <span style={{ flex: 1, height: 1, background: "var(--gray-3)" }} />
    </div>
  );
}

function VoiceCard({
  voice, active, badge, onClick,
}: {
  voice: ElevenVoice;
  active: boolean;
  badge: string;
  onClick: () => void;
}) {
  const initial = voice.name?.[0]?.toUpperCase() ?? "V";
  const isFemale = voice.gender?.toLowerCase() === "female";
  const accentColor = isFemale ? "#ec4899" : "#22d3ee";

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        textAlign: "left",
        position: "relative",
        padding: 14,
        borderRadius: 14,
        border: active ? `1.5px solid var(--accent)` : "1px solid var(--gray-3)",
        background: active ? "rgba(249,115,22,0.06)" : "var(--gray-1)",
        boxShadow: active
          ? "0 0 0 3px rgba(249,115,22,0.13), 0 12px 32px -8px rgba(249,115,22,0.4)"
          : "none",
        cursor: "pointer",
        transition: "all 0.2s var(--ease-out)",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          flexShrink: 0,
          background: `linear-gradient(135deg, ${accentColor}, ${accentColor}99)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, fontWeight: 900, color: "#000",
          boxShadow: active ? `0 0 12px ${accentColor}88` : "none",
        }}>
          {initial}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: active ? "var(--accent)" : "var(--white)",
              letterSpacing: "-0.01em",
            }}>{voice.name}</span>
            {voice.gender && (
              <span style={{
                fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                textTransform: "uppercase", color: "var(--gray-5)",
              }}>· {voice.gender === "female" ? "nữ" : voice.gender === "male" ? "nam" : voice.gender}</span>
            )}
          </div>
          <div style={{
            fontSize: 11, color: "var(--gray-5)",
            lineHeight: 1.45,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}>
            {voice.description || "—"}
          </div>
        </div>
      </div>

      <div style={{
        position: "absolute", top: 10, right: 10,
        fontSize: 9, fontWeight: 800, letterSpacing: "0.08em",
        padding: "2px 7px", borderRadius: 99,
        background: badge === "Custom" ? "rgba(34,211,238,0.15)" : "var(--gray-2)",
        border: `1px solid ${badge === "Custom" ? "rgba(34,211,238,0.35)" : "var(--gray-3)"}`,
        color: badge === "Custom" ? "#67e8f9" : "var(--gray-5)",
      }}>
        {badge}
      </div>

      {active && (
        <div style={{
          position: "absolute", bottom: 10, right: 10,
          width: 18, height: 18, borderRadius: "50%",
          background: "var(--accent)", color: "var(--black)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, fontWeight: 900,
        }}>
          ✓
        </div>
      )}
    </button>
  );
}
