"use client";

import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";

const HEADLINES = [
  "BREAKING: OpenAI ra mắt GPT-5 với khả năng lý luận vượt trội",
  "NÓNG: Google DeepMind công bố AlphaFold 3 giải mã protein phức tạp",
  "CẬP NHẬT: Apple Intelligence tích hợp AI vào toàn bộ hệ sinh thái iOS 19",
  "MỚI NHẤT: Meta AI đạt 1 tỷ người dùng sau 6 tháng ra mắt",
  "KHẨN: Nvidia H200 GPU cháy hàng toàn cầu, giá tăng 300%",
  "BREAKING: Microsoft Copilot thay thế hoàn toàn trợ lý Cortana",
];

const STATS = [
  { label: "TIN MỚI HÔM NAY", value: "247" },
  { label: "NGUỒN THEO DÕI", value: "1.2K" },
  { label: "VIDEO ĐÃ TẠO", value: "89K" },
];

export default function LoginPage() {
  const [time, setTime]           = useState("");
  const [date, setDate]           = useState("");
  const [tickerIdx, setTickerIdx] = useState(0);
  const [tickerVisible, setTickerVisible] = useState(true);
  const [glitch, setGlitch]       = useState(false);

  // Clock
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }));
      setDate(now.toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Headline rotator
  useEffect(() => {
    const id = setInterval(() => {
      setTickerVisible(false);
      setTimeout(() => {
        setTickerIdx(i => (i + 1) % HEADLINES.length);
        setTickerVisible(true);
      }, 400);
    }, 4000);
    return () => clearInterval(id);
  }, []);

  // Random glitch effect
  useEffect(() => {
    const id = setInterval(() => {
      setGlitch(true);
      setTimeout(() => setGlitch(false), 150);
    }, 5000 + Math.random() * 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#000", overflow: "hidden", position: "relative", fontFamily: "var(--font-geist-sans), system-ui, sans-serif" }}>

      {/* ── Scanlines overlay ── */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none",
        backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)",
      }} />

      {/* ── Noise texture ── */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none", opacity: 0.03,
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
      }} />

      {/* ── Background: dark grid ── */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0,
        backgroundImage: `
          linear-gradient(rgba(249,115,22,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(249,115,22,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "60px 60px",
      }} />

      {/* ── Glow orbs ── */}
      <div style={{ position: "fixed", top: -200, left: -200, width: 600, height: 600, borderRadius: "50%", background: "radial-gradient(circle, rgba(249,115,22,0.08) 0%, transparent 70%)", filter: "blur(40px)", zIndex: 0 }} />
      <div style={{ position: "fixed", bottom: -200, right: -100, width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(239,68,68,0.06) 0%, transparent 70%)", filter: "blur(40px)", zIndex: 0 }} />

      {/* ── TOP BAR — broadcast style ── */}
      <div style={{
        position: "relative", zIndex: 10,
        background: "rgba(0,0,0,0.95)",
        borderBottom: "2px solid #f97316",
        padding: "0 32px",
        height: 48,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        boxShadow: "0 2px 20px rgba(249,115,22,0.3)",
      }}>
        {/* Left: Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 6,
            background: "linear-gradient(135deg, #f97316, #ea580c)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, fontWeight: 900, color: "#000",
            boxShadow: "0 0 12px rgba(249,115,22,0.6)",
          }}>T</div>
          <div>
            <span style={{ fontSize: 16, fontWeight: 900, letterSpacing: "-0.02em", color: "#fff" }}>Tech</span>
            <span style={{ fontSize: 16, fontWeight: 900, letterSpacing: "-0.02em", color: "#f97316" }}>Beat</span>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#666", marginLeft: 8 }}>AI NEWS NETWORK</span>
          </div>
        </div>

        {/* Center: LIVE indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "#ef4444", padding: "3px 10px", borderRadius: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff", animation: "live-blink 1s ease-in-out infinite" }} />
            <span style={{ fontSize: 11, fontWeight: 900, color: "#fff", letterSpacing: "0.1em" }}>LIVE</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(249,115,22,0.15)", border: "1px solid rgba(249,115,22,0.3)", padding: "3px 10px", borderRadius: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#f97316", animation: "live-blink 1.5s ease-in-out infinite" }} />
            <span style={{ fontSize: 11, fontWeight: 800, color: "#f97316", letterSpacing: "0.08em" }}>ON AIR</span>
          </div>
        </div>

        {/* Right: Clock */}
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 18, fontWeight: 900, color: "#fff", letterSpacing: "0.05em", fontVariantNumeric: "tabular-nums", fontFamily: "var(--font-geist-mono), monospace" }}>{time}</div>
          <div style={{ fontSize: 9, color: "#666", textTransform: "uppercase", letterSpacing: "0.08em" }}>{date}</div>
        </div>
      </div>

      {/* ── BREAKING NEWS TICKER ── */}
      <div style={{
        position: "relative", zIndex: 10,
        background: "#f97316",
        height: 36,
        display: "flex", alignItems: "center",
        overflow: "hidden",
      }}>
        <div style={{
          background: "#000", color: "#f97316",
          padding: "0 16px", height: "100%",
          display: "flex", alignItems: "center",
          fontSize: 11, fontWeight: 900, letterSpacing: "0.1em",
          whiteSpace: "nowrap", flexShrink: 0,
          borderRight: "2px solid #f97316",
        }}>
          BREAKING
        </div>
        <div style={{
          flex: 1, padding: "0 20px",
          fontSize: 13, fontWeight: 700, color: "#000",
          opacity: tickerVisible ? 1 : 0,
          transform: tickerVisible ? "translateY(0)" : "translateY(8px)",
          transition: "opacity 0.3s, transform 0.3s",
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
        }}>
          {HEADLINES[tickerIdx]}
        </div>
        <div style={{
          background: "#000", color: "#f97316",
          padding: "0 16px", height: "100%",
          display: "flex", alignItems: "center",
          fontSize: 11, fontWeight: 700,
          whiteSpace: "nowrap", flexShrink: 0,
          borderLeft: "2px solid rgba(0,0,0,0.2)",
        }}>
          {tickerIdx + 1}/{HEADLINES.length}
        </div>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div style={{
        position: "relative", zIndex: 5,
        display: "flex", minHeight: "calc(100vh - 84px)",
      }}>

        {/* LEFT — News visual panel */}
        <div style={{
          flex: 1, padding: "48px 56px",
          display: "flex", flexDirection: "column", justifyContent: "space-between",
          borderRight: "1px solid rgba(249,115,22,0.15)",
          position: "relative", overflow: "hidden",
        }}>
          {/* Category badge */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              background: "#f97316", color: "#000",
              padding: "4px 12px", borderRadius: 4,
              fontSize: 10, fontWeight: 900, letterSpacing: "0.12em", textTransform: "uppercase",
            }}>TIN CÔNG NGHỆ</div>
            <div style={{
              border: "1px solid rgba(249,115,22,0.4)", color: "#f97316",
              padding: "4px 12px", borderRadius: 4,
              fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
            }}>AI · KHOA HỌC · ĐỔI MỚI</div>
          </div>

          {/* Main headline */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#f97316", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 24, height: 1, background: "#f97316", display: "inline-block" }} />
              BẢN TIN AI · CẬP NHẬT HẰNG NGÀY
            </div>
            <h1 style={{
              fontSize: "clamp(48px, 5.5vw, 88px)",
              fontWeight: 900, lineHeight: 1.08,
              letterSpacing: "-0.04em", color: "#fff",
              marginBottom: 28,
              filter: glitch ? "blur(1px)" : "none",
              transform: glitch ? "translateX(2px)" : "none",
              transition: "filter 0.05s, transform 0.05s",
            }}>
              <span style={{ display: "block" }}>Tin công</span>
              <span style={{ display: "block" }}>nghệ <span style={{ color: "#f97316", fontStyle: "italic", paddingRight: "0.08em" }}>thành</span></span>
              <span style={{ display: "block" }}>video</span>
            </h1>
            <p style={{ fontSize: 15, color: "#888", lineHeight: 1.7, maxWidth: 400 }}>
              Dán link bài viết — AI tóm tắt, viết kịch bản tiếng Việt và xuất MP4 sẵn sàng đăng.
            </p>
          </div>

          {/* Stats bar */}
          <div style={{
            display: "flex", gap: 0,
            border: "1px solid rgba(249,115,22,0.2)",
            borderRadius: 8, overflow: "hidden",
          }}>
            {STATS.map((s, i) => (
              <div key={s.label} style={{
                flex: 1, padding: "16px 20px",
                borderRight: i < STATS.length - 1 ? "1px solid rgba(249,115,22,0.15)" : "none",
                background: "rgba(249,115,22,0.03)",
              }}>
                <div style={{ fontSize: 9, fontWeight: 800, color: "#666", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>{s.label}</div>
                <div style={{ fontSize: 28, fontWeight: 900, color: "#f97316", letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums" }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Corner decoration */}
          <div style={{ position: "absolute", top: 20, right: 20, width: 60, height: 60, borderTop: "2px solid rgba(249,115,22,0.2)", borderRight: "2px solid rgba(249,115,22,0.2)" }} />
          <div style={{ position: "absolute", bottom: 20, left: 20, width: 60, height: 60, borderBottom: "2px solid rgba(249,115,22,0.2)", borderLeft: "2px solid rgba(249,115,22,0.2)" }} />
        </div>

        {/* RIGHT — Login panel */}
        <div style={{
          width: "42%", minWidth: 420,
          padding: "48px 56px",
          display: "flex", flexDirection: "column", justifyContent: "center",
          position: "relative",
          background: "rgba(10,10,10,0.8)",
        }}>
          {/* Panel header */}
          <div style={{
            background: "rgba(249,115,22,0.08)",
            border: "1px solid rgba(249,115,22,0.2)",
            borderRadius: 8, padding: "12px 16px",
            marginBottom: 32,
            display: "flex", alignItems: "center", gap: 10,
          }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#f97316", boxShadow: "0 0 8px #f97316", animation: "live-blink 2s ease-in-out infinite" }} />
            <span style={{ fontSize: 11, fontWeight: 800, color: "#f97316", letterSpacing: "0.1em", textTransform: "uppercase" }}>
              Truy cập hệ thống
            </span>
            <span style={{ marginLeft: "auto", fontSize: 10, color: "#555", fontFamily: "monospace" }}>
              AUTH_v2.0
            </span>
          </div>

          <div style={{ marginBottom: 36 }}>
            <h2 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.03em", color: "#fff", marginBottom: 8, lineHeight: 1.1 }}>
              Đăng nhập<br />
              <span style={{ color: "#f97316" }}>TechBeat</span>
            </h2>
            <p style={{ fontSize: 13, color: "#555", lineHeight: 1.6 }}>
              Xác thực để truy cập hệ thống tạo bản tin AI
            </p>
          </div>

          {/* Google button */}
          <button
            onClick={() => signIn("google", { callbackUrl: "/" })}
            style={{
              width: "100%",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 12,
              padding: "16px 24px",
              background: "#fff",
              border: "none", borderRadius: 8,
              fontSize: 15, fontWeight: 800, color: "#111",
              cursor: "pointer",
              transition: "all 0.2s",
              boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
              marginBottom: 16,
              position: "relative", overflow: "hidden",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = "0 8px 32px rgba(249,115,22,0.3)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "0 4px 24px rgba(0,0,0,0.4)";
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Đăng nhập với Google
          </button>

          {/* Divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
            <span style={{ fontSize: 10, color: "#444", fontWeight: 700, letterSpacing: "0.08em" }}>BẢO MẬT</span>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
          </div>

          {/* Security badges */}
          <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
            {[
              { label: "OAuth 2.0", icon: <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg> },
              { label: "Mã hóa TLS", icon: <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg> },
              { label: "Google Verified", icon: <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><polyline points="20 6 9 17 4 12" /></svg> }
            ].map(b => (
              <div key={b.label} style={{
                flex: 1, padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 6, fontSize: 10, color: "#555", fontWeight: 600,
              }}>
                {b.icon}
                <span>{b.label}</span>
              </div>
            ))}
          </div>

          <p style={{ fontSize: 11, color: "#444", textAlign: "center", lineHeight: 1.6 }}>
            Bằng cách đăng nhập, bạn đồng ý với{" "}
            <span style={{ color: "#f97316", cursor: "pointer" }}>Điều khoản</span>
            {" "}và{" "}
            <span style={{ color: "#f97316", cursor: "pointer" }}>Chính sách bảo mật</span>
          </p>

          {/* Bottom system info */}
          <div style={{
            position: "absolute", bottom: 24, left: 56, right: 56,
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: 10, color: "#333", fontFamily: "monospace" }}>SYS: ONLINE</span>
            <span style={{ fontSize: 10, color: "#333", fontFamily: "monospace" }}>v2.0.0</span>
          </div>
        </div>
      </div>

      {/* ── BOTTOM STATUS BAR ── */}
      <div style={{
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 10,
        background: "rgba(0,0,0,0.95)",
        borderTop: "1px solid rgba(249,115,22,0.2)",
        height: 28,
        display: "flex", alignItems: "center",
        padding: "0 24px", gap: 24,
        fontSize: 10, color: "#555", fontFamily: "monospace",
      }}>
        <span style={{ color: "#f97316", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 6 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "#f97316" }} />
          TECHBEAT AI
        </span>
        <span>GPT-4o + HyperFrames + gTTS</span>
        <span style={{ marginLeft: "auto" }}>1920×1080 · 30fps · Tiếng Việt</span>
        <span>© 2026</span>
      </div>

      <style>{`
        @keyframes live-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
