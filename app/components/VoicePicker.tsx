"use client";

import { useEffect, useState } from "react";

interface ElevenVoice {
  voice_id: string;
  name: string;
  gender?: string;
  description?: string;
  category?: string;
  actor?: string;
  traits?: string;
  service?: string;
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
  
  // Audio state
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [audioInstance, setAudioInstance] = useState<HTMLAudioElement | null>(null);
  
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

  // Cleanup audio instance on unmount or change
  useEffect(() => {
    return () => {
      if (audioInstance) {
        audioInstance.pause();
      }
    };
  }, [audioInstance]);

  const handlePlayDemo = async (voiceId: string) => {
    if (playingVoiceId === voiceId) {
      if (audioInstance) {
        audioInstance.pause();
        setPlayingVoiceId(null);
      }
      return;
    }

    if (audioInstance) {
      audioInstance.pause();
    }

    try {
      const res = await fetch(`${API}/voices/demo?voice_id=${encodeURIComponent(voiceId)}`);
      const resData = await res.json();
      const audioUrl = `${API}${resData.url}`;
      
      const audio = new Audio(audioUrl);
      setAudioInstance(audio);
      setPlayingVoiceId(voiceId);
      audio.play();
      audio.onended = () => {
        setPlayingVoiceId(null);
      };
    } catch (e) {
      console.error("Failed to play voice demo", e);
    }
  };

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
          Giọng đọc & Diễn viên ảo
        </div>
        <div style={{ fontSize: 11, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
          {allVoices.length} giọng có sẵn
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
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Trải nghiệm chất lượng âm thanh Pro-Max</div>
          <div style={{ color: "var(--gray-6)" }}>
            Bấm nút <strong style={{ color: "var(--accent)" }}>Play</strong> trên các thẻ giọng đọc để nghe thử demo chất giọng.
          </div>
        </div>
      )}

      {data.error && data.has_api_key && (
        <div style={{
          padding: "10px 14px", borderRadius: "var(--r)",
          background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
          color: "var(--red)", fontSize: 12, lineHeight: 1.6,
        }}>
          Lỗi nạp custom voice: {data.error}
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: 12,
      }}>
        {data.custom.length > 0 && (
          <SectionLabel label="Voices của bạn" count={data.custom.length} />
        )}
        {data.custom.map((v) => (
          <VoiceCard 
            key={v.voice_id} 
            voice={v} 
            active={v.voice_id === selected}
            badge="Custom" 
            onClick={() => onChange(v.voice_id)} 
            isPlaying={playingVoiceId === v.voice_id}
            onPlayDemo={handlePlayDemo}
          />
        ))}

        {data.premade.length > 0 && (
          <SectionLabel label="Danh sách giọng đọc cao cấp" count={data.premade.length} />
        )}
        {data.premade.map((v) => (
          <VoiceCard 
            key={v.voice_id} 
            voice={v} 
            active={v.voice_id === selected}
            badge="Premade" 
            onClick={() => onChange(v.voice_id)} 
            isPlaying={playingVoiceId === v.voice_id}
            onPlayDemo={handlePlayDemo}
          />
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
      paddingTop: 8,
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

interface VoiceCardProps {
  voice: ElevenVoice;
  active: boolean;
  badge: string;
  onClick: () => void;
  isPlaying: boolean;
  onPlayDemo: (voiceId: string) => void;
}

function VoiceCard({
  voice, active, badge, onClick, isPlaying, onPlayDemo,
}: VoiceCardProps) {
  const initial = voice.name?.[0]?.toUpperCase() ?? "V";
  const isFemale = voice.gender?.toLowerCase() === "female";
  const accentColor = isFemale ? "#ec4899" : "#22d3ee";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick();
        }
      }}
      style={{
        textAlign: "left",
        position: "relative",
        padding: "16px 14px",
        borderRadius: 16,
        border: active ? `2px solid var(--accent)` : "1px solid var(--gray-3)",
        background: active ? "rgba(249,115,22,0.06)" : "var(--gray-1)",
        boxShadow: active
          ? "0 0 0 3px rgba(249,115,22,0.15), 0 12px 32px -8px rgba(249,115,22,0.3)"
          : "0 4px 12px rgba(0,0,0,0.1)",
        cursor: "pointer",
        transition: "all 0.25s var(--ease-out)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Left Side: Avatar with Hover/Active Play Overlay */}
        <div style={{ position: "relative", flexShrink: 0 }}>
          <div style={{
            width: 38, height: 38, borderRadius: "50%",
            background: `linear-gradient(135deg, ${accentColor}, ${accentColor}99)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15, fontWeight: 900, color: "#000",
            boxShadow: active ? `0 0 12px ${accentColor}66` : "none",
            transition: "all 0.2s ease",
          }}>
            {initial}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span style={{
              fontSize: 14, fontWeight: 800,
              color: active ? "var(--accent)" : "var(--white)",
              letterSpacing: "-0.01em",
            }}>{voice.name}</span>
            {voice.gender && (
              <span style={{
                fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                textTransform: "uppercase", color: "var(--gray-5)",
              }}>
                · {voice.gender === "female" ? "nữ" : voice.gender === "male" ? "nam" : voice.gender}
              </span>
            )}
          </div>
          <div style={{
            fontSize: 11, color: "var(--gray-6)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.02em",
          }}>
            {voice.service || "Premium Voice"}
          </div>
        </div>
      </div>

      {/* Trait & Details Block */}
      <div style={{ 
        background: "rgba(0,0,0,0.15)", 
        padding: "8px 10px", 
        borderRadius: 8,
        fontSize: 11,
        lineHeight: 1.4,
        color: "var(--gray-5)",
      }}>
        {voice.traits && (
          <div style={{ marginBottom: 4 }}>
            <span style={{ color: "var(--accent2)", fontWeight: 700 }}>Tính chất: </span>
            <span style={{ color: "var(--white)" }}>{voice.traits}</span>
          </div>
        )}
        <div style={{ 
          fontSize: 10, 
          color: "var(--gray-6)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}>
          {voice.description}
        </div>
      </div>

      {/* Action Buttons Footer Area */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 2 }}>
        {/* Play Demo Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onPlayDemo(voice.voice_id);
          }}
          style={{
            padding: "5px 12px",
            borderRadius: 20,
            background: isPlaying ? "rgba(249,115,22,0.2)" : "rgba(255,255,255,0.06)",
            border: `1px solid ${isPlaying ? "var(--accent)" : "rgba(255,255,255,0.12)"}`,
            color: isPlaying ? "var(--accent)" : "var(--white)",
            fontSize: 11,
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.2s ease",
            boxShadow: isPlaying ? "0 0 8px rgba(249,115,22,0.3)" : "none",
          }}
        >
          {isPlaying ? (
            <>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
              <span>Dừng nghe</span>
            </>
          ) : (
            <>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
              <span>Nghe thử giọng</span>
            </>
          )}
        </button>

        {/* Selected indicator */}
        {active ? (
          <span style={{
            fontSize: 10,
            fontWeight: 800,
            color: "var(--accent)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
          }}>
            Đang Chọn
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </span>
        ) : (
          <span style={{ fontSize: 10, color: "var(--gray-6)" }}>Chọn giọng</span>
        )}
      </div>

      {/* Top right Badge */}
      <div style={{
        position: "absolute", top: 12, right: 12,
        fontSize: 9, fontWeight: 800, letterSpacing: "0.08em",
        padding: "2px 7px", borderRadius: 99,
        background: badge === "Custom" ? "rgba(34,211,238,0.15)" : "var(--gray-2)",
        border: `1px solid ${badge === "Custom" ? "rgba(34,211,238,0.35)" : "var(--gray-3)"}`,
        color: badge === "Custom" ? "#67e8f9" : "var(--gray-5)",
      }}>
        {badge}
      </div>
    </div>
  );
}
