"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { InputPanel } from "@/components/InputPanel";
import { SceneList } from "@/components/SceneList";
import { VideoBuilder } from "@/components/VideoBuilder";
import { UserMenu } from "@/components/UserMenu";
import { ThemePicker } from "@/components/ThemePicker";
import { VoicePicker } from "@/components/VoicePicker";
import { HtmlPreviewStage } from "@/components/HtmlPreviewStage";
import {
  StageTransition,
  CurtainSweep,
  GlobalFXOverlay,
  StaggeredText,
  ParallaxBlob,
  ClipReveal,
} from "@/components/StageTransition";
import { motion } from "motion/react";
import type { ExtractedContent, ScenePlan, ThemeId } from "@/types/scene";
import { DEFAULT_THEME, getTheme } from "@/types/scene";

type Stage = "dashboard" | "input" | "generating" | "preview" | "htmlPreview" | "build";

const TICKER_ITEMS = [
  "TECHBEAT LIVE",
  "AI bản tin tự động",
  "Render 1080p · 30fps",
  "Powered by GPT-4o + HyperFrames",
  "TTS tiếng Việt · Google Cloud",
  "Openverse · ảnh CC",
  "MP4 sẵn sàng đăng",
];

export default function Home() {
  const [stage, setStage] = useState<Stage>("dashboard");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [scenePlan, setScenePlan] = useState<ScenePlan | null>(null);
  const [streamBuffer, setStreamBuffer] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const hasUnsavedProgress = stage === "generating" || stage === "preview" || stage === "htmlPreview" || stage === "build" || (stage === "input" && isLoading);

  // Global beforeunload listener to protect against accidental tab closing/refreshing
  useEffect(() => {
    if (!hasUnsavedProgress) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      const msg = "Tiến trình hiện tại sẽ bị mất nếu bạn rời khỏi hoặc tải lại trang. Bạn có chắc chắn muốn thoát không?";
      e.returnValue = msg;
      return msg;
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedProgress]);

  function go(next: Stage) {
    if (next === stage) return;
    setStage(next);
  }

  async function generateScenes(content: ExtractedContent & { videoDuration?: number | null }) {
    go("generating");
    setError("");
    setStreamBuffer("");
    setScenePlan(null);

    const abort = new AbortController();
    abortRef.current = abort;
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const endpoint = process.env.NODE_ENV === "development"
      ? `${API}/generate-scenes`
      : `/api/proxy/generate-scenes`;

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: content.text,
          title: content.title,
          videoDuration: content.videoDuration,
        }),
        signal: abort.signal,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Tạo kịch bản thất bại");
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      const processLines = (raw: string) => {
        for (const line of raw.split("\n\n")) {
          if (!line.startsWith("data: ")) continue;
          let event: { type: string; text?: string; scenePlan?: unknown; message?: string; llmProvider?: string; llmModel?: string; };
          try { event = JSON.parse(line.slice(6)); } catch { continue; }
          if (event.type === "chunk" && event.text) {
            setStreamBuffer((prev) => prev + event.text);
          } else if (event.type === "warning" && event.message) {
            setStreamBuffer((prev) => `[!] ${event.message}\n\n${prev}`);
          } else if (event.type === "done" && event.scenePlan) {
            if (event.llmProvider || event.llmModel) {
              setStreamBuffer(prev => prev + `\n\nKịch bản: ${event.llmProvider ?? ""}/${event.llmModel ?? ""}`);
            }
            setScenePlan(event.scenePlan as ScenePlan);
            go("preview");
          } else if (event.type === "error") {
            throw new Error(event.message ?? "Lỗi không xác định");
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) { if (buf.trim()) processLines(buf); break; }
        buf += decoder.decode(value, { stream: true });
        const split = buf.split("\n\n");
        buf = split.pop() ?? "";
        processLines(split.join("\n\n") + "\n\n");
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Tạo kịch bản thất bại");
      go("input");
    }
  }

  function handleReset() {
    abortRef.current?.abort();
    setScenePlan(null);
    setStreamBuffer("");
    setError("");
    go("input");
  }

  function handleHome() {
    abortRef.current?.abort();
    setScenePlan(null);
    setStreamBuffer("");
    setError("");
    go("dashboard");
  }

  return (
    <div style={{ minHeight: "100vh", position: "relative", background: "var(--black)" }}>
      <GlobalFXOverlay />
      <CurtainSweep stageKey={stage} accent={scenePlan?.theme ? getTheme(scenePlan.theme).accent : "#f97316"} />

      {stage !== "dashboard" && (
        <AppHeader 
          stage={stage} 
          onHome={handleHome} 
          onReset={handleReset} 
          hasUnsavedProgress={hasUnsavedProgress} 
        />
      )}

      <StageTransition stageKey={stage}>
        {stage === "dashboard" && <Dashboard onStart={() => go("input")} />}
        {stage === "input" && (
          <InputStage
            error={error}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
            setError={setError}
            onExtracted={generateScenes}
          />
        )}
        {stage === "generating" && <GeneratingStage buffer={streamBuffer} onCancel={handleReset} />}
        {stage === "preview" && scenePlan && (
          <PreviewStage scenePlan={scenePlan} setScenePlan={setScenePlan} onBuild={() => go("htmlPreview")} />
        )}
        {stage === "htmlPreview" && scenePlan && (
          <HtmlPreviewStage
            scenePlan={scenePlan}
            setScenePlan={setScenePlan}
            onBack={() => go("preview")}
            onBuild={() => go("build")}
          />
        )}
        {stage === "build" && scenePlan && (
          <main style={{ maxWidth: 1200, margin: "0 auto", padding: "32px clamp(20px,4vw,48px)" }}>
            <VideoBuilder scenePlan={scenePlan} onBack={() => go("htmlPreview")} />
          </main>
        )}
      </StageTransition>
    </div>
  );
}

/* ─────────────────────────  HEADER  ───────────────────────── */

function AppHeader({ 
  stage, 
  onHome, 
  onReset, 
  hasUnsavedProgress 
}: { 
  stage: Stage; 
  onHome: () => void; 
  onReset: () => void; 
  hasUnsavedProgress: boolean; 
}) {
  const steps: { key: Stage; num: number; label: string }[] = [
    { key: "input",       num: 1, label: "Nhập" },
    { key: "preview",     num: 2, label: "Kịch bản" },
    { key: "htmlPreview", num: 3, label: "Xem trước" },
    { key: "build",       num: 4, label: "Dựng" },
  ];
  const order: Stage[] = ["input", "generating", "preview", "htmlPreview", "build"];
  const cur = order.indexOf(stage);

  return (
    <header className="site-header">
      <button
        onClick={() => {
          if (hasUnsavedProgress) {
            if (!window.confirm("Tiến trình hiện tại sẽ bị mất nếu bạn quay về trang chủ. Bạn có chắc chắn muốn thoát không?")) return;
          }
          onHome();
        }}
        style={{
          display: "flex", alignItems: "center", gap: 12,
          background: "transparent", border: "none", cursor: "pointer", color: "inherit",
          padding: 0,
        }}
      >
        <div className="logo-mark">T</div>
        <div style={{ textAlign: "left", lineHeight: 1.1 }}>
          <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: "-0.01em" }}>
            Tech<span style={{ color: "var(--accent)" }}>Beat</span>
          </div>
          <div style={{ fontSize: 9, color: "var(--gray-5)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 600 }}>
            AI News Studio
          </div>
        </div>
      </button>

      <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
        <div className="stepper" style={{ display: "flex" }}>
          {steps.map((s, i) => {
            const sIdx = order.indexOf(s.key);
            const isDone =
              cur > sIdx ||
              (s.key === "preview" && (stage === "htmlPreview" || stage === "build")) ||
              (s.key === "htmlPreview" && stage === "build");
            const isActive =
              stage === s.key ||
              (s.key === "preview" && stage === "generating");
            const cls = isActive ? "active" : isDone ? "done" : "pending";
            return (
              <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div className={`step-pill ${cls}`}>
                  <span style={{
                    width: 14, height: 14, borderRadius: "50%",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 9, fontWeight: 900,
                    background: cls === "active" ? "rgba(0,0,0,0.2)" : cls === "done" ? "rgba(249,115,22,0.15)" : "var(--gray-3)",
                    color: cls === "active" ? "var(--black)" : "inherit",
                  }}>
                    {isDone ? "✓" : s.num}
                  </span>
                  {s.label}
                </div>
                {i < steps.length - 1 && <div className={`step-connector ${isDone ? "done" : ""}`} />}
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {stage !== "input" && (
          <button 
            onClick={() => {
              if (hasUnsavedProgress) {
                if (!window.confirm("Tiến trình hiện tại sẽ bị mất nếu bạn bắt đầu lại. Bạn có chắc chắn muốn hủy không?")) return;
              }
              onReset();
            }} 
            className="btn-ghost" style={{ fontSize: 11 }}>
            ← Bắt đầu lại
          </button>
        )}
        <UserMenu />
      </div>
    </header>
  );
}

/* ─────────────────────────  DASHBOARD  ───────────────────────── */

function Dashboard({ onStart }: { onStart: () => void }) {
  const { data: session } = useSession();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [now, setNow] = useState<string>("");
  const [history, setHistory] = useState<any[]>([]);
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null);
  const [activeVideoTitle, setActiveVideoTitle] = useState<string>("");

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const headers: Record<string, string> = {};
    if (session?.user?.email) {
      headers["X-User-Email"] = session.user.email;
    }
    fetch(`${API}/history/local`, { headers })
      .then(res => res.json())
      .then(data => {
        if (data.history) {
          setHistory(data.history.slice(0, 5));
        }
      })
      .catch(err => console.error("Error loading local history:", err));
  }, [session?.user?.email]);

  // Animated star/galaxy field
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let w = (cv.width = window.innerWidth * window.devicePixelRatio);
    let h = (cv.height = window.innerHeight * window.devicePixelRatio);
    cv.style.width = window.innerWidth + "px";
    cv.style.height = window.innerHeight + "px";

    type Star = { x: number; y: number; z: number; speed: number; r: number; hue: number };
    const stars: Star[] = [];
    const COUNT = 240;
    for (let i = 0; i < COUNT; i++) {
      stars.push({
        x: Math.random() * w,
        y: Math.random() * h,
        z: Math.random() * 0.7 + 0.3,
        speed: Math.random() * 0.4 + 0.05,
        r: Math.random() * 1.6 + 0.3,
        hue: Math.random() < 0.18 ? 28 : 0, // mostly white, some orange
      });
    }

    let t = 0;
    function frame() {
      if (!ctx) return;
      t += 0.005;
      ctx.fillStyle = "rgba(0,0,0,0.18)";
      ctx.fillRect(0, 0, w, h);

      // Nebula glow
      const cx = w / 2 + Math.sin(t * 0.6) * 60;
      const cy = h / 2 + Math.cos(t * 0.5) * 40;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, h * 0.7);
      grad.addColorStop(0, "rgba(249,115,22,0.10)");
      grad.addColorStop(0.4, "rgba(249,115,22,0.04)");
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      for (const s of stars) {
        s.y += s.speed * s.z * window.devicePixelRatio;
        if (s.y > h) {
          s.y = -2;
          s.x = Math.random() * w;
        }
        const alpha = 0.4 + s.z * 0.6;
        if (s.hue > 0) {
          ctx.fillStyle = `rgba(251,146,60,${alpha})`;
        } else {
          ctx.fillStyle = `rgba(255,255,255,${alpha * 0.85})`;
        }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * s.z, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }
    frame();

    function onResize() {
      w = cv!.width = window.innerWidth * window.devicePixelRatio;
      h = cv!.height = window.innerHeight * window.devicePixelRatio;
      cv!.style.width = window.innerWidth + "px";
      cv!.style.height = window.innerHeight + "px";
    }
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  // Live clock
  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setNow(
        d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        + " · " +
        d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{
      position: "relative",
      width: "100%",
      minHeight: "100vh",
      background: "radial-gradient(ellipse at center, #0a0510 0%, #000 60%)",
    }}>
      {/* Fixed decorative layer — canvas + blobs + vignette stay in viewport while content scrolls */}
      <div aria-hidden style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
        <canvas
          ref={canvasRef}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        />

        {/* Parallax glow blobs */}
        <ParallaxBlob size={520} color="rgba(249,115,22,0.18)" top="-10%" left="5%" duration={16} />
        <ParallaxBlob size={420} color="rgba(251,146,60,0.12)" bottom="-15%" right="-5%" duration={20} delay={1.5} />
        <ParallaxBlob size={300} color="rgba(251,191,36,0.08)" top="40%" right="20%" duration={14} delay={3} />

        {/* Vignette */}
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.85) 100%)",
        }} />
      </div>

      {/* User menu top-right — fixed so it stays in viewport while scrolling */}
      <div style={{ position: "fixed", top: 24, right: 28, zIndex: 30 }}>
        <UserMenu />
      </div>

      {/* LIVE badge top-left — fixed */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        style={{
          position: "fixed", top: 24, left: 28, zIndex: 30,
          display: "flex", alignItems: "center", gap: 16,
        }}
      >
        <div className="badge badge-accent badge-dot" style={{ background: "rgba(239,68,68,0.12)", borderColor: "rgba(239,68,68,0.3)", color: "#fca5a5" }}>
          <span style={{ background: "var(--red)" }} />
          On Air
        </div>
        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--gray-5)", letterSpacing: "0.1em" }}>
          {now}
        </div>
      </motion.div>

      {/* Ticker bottom — fixed */}
      <motion.div
        initial={{ y: 60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.7, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
        style={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 20 }}
      >
        <div className="ticker-wrap">
          <div className="ticker-track">
            {[...TICKER_ITEMS, ...TICKER_ITEMS].map((it, i) => (
              <div key={i} className="ticker-item">
                <span>●</span> {it}
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Center content — scrollable; centers vertically when short, grows when history list is long */}
      <div style={{
        position: "relative", zIndex: 10,
        minHeight: "100vh",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "80px 24px 120px",
        textAlign: "center",
      }}>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="hero-eyebrow"
          style={{ marginBottom: 28 }}
        >
          AI News Studio · Bản tin tự động
        </motion.div>

        <h1
          style={{
            fontSize: "clamp(48px, 9vw, 140px)",
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: "-0.05em",
            marginBottom: 24,
            paddingTop: "0.15em",
          }}
        >
          <span style={{ display: "block" }}>
            <StaggeredText text="Cinematic" className="shine-cinematic" />
          </span>
          <span style={{ display: "block" }}>
            <StaggeredText text="Tech News" className="shine-technews" />
          </span>
        </h1>

        <motion.div
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { staggerChildren: 0.25, delayChildren: 0.6 }
            }
          }}
          style={{
            fontSize: "clamp(16px, 1.6vw, 20px)",
            lineHeight: 1.6,
            marginBottom: 24,
            maxWidth: 600,
            color: "var(--gray-6)",
            fontWeight: 500,
          }}
        >
          {["Turn", "Tech", "Stories", "into", "Dynamic", "Videos"].map((word, i) => {
            const isOrange = word === "Dynamic" || word === "Videos";
            const isBold = word === "Tech" || word === "Stories" || isOrange;
            return (
              <motion.span
                key={i}
                variants={{
                  hidden: { opacity: 0 },
                  visible: { 
                    opacity: 1, 
                    transition: { duration: 0.01 }
                  }
                }}
                style={{
                  display: "inline-block",
                  marginRight: "0.28em",
                  color: isOrange ? "var(--accent)" : isBold ? "var(--white)" : "inherit",
                  fontWeight: isBold ? 800 : 500,
                  textShadow: isOrange ? "0 0 12px rgba(249,115,22,0.25)" : "none",
                }}
              >
                {word}
              </motion.span>
            );
          })}
          {/* Blinking typewriter cursor */}
          <span className="blinking-cursor" />
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.55 }}
          transition={{ duration: 1, delay: 1.4 }}
          style={{
            fontSize: 13,
            color: "var(--white)",
            maxWidth: 500,
            lineHeight: 1.6,
            marginBottom: 48,
          }}
        >
          Dán link bài viết — AI tóm tắt, viết kịch bản, đọc tiếng Việt và xuất MP4 1080p.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.9, ease: [0.34, 1.56, 0.64, 1] }}
          style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}
        >
          <motion.button
            onClick={onStart}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="btn-primary"
            style={{
              padding: "18px 36px",
              fontSize: 14,
              borderRadius: "var(--r-full)",
              boxShadow: "0 0 0 1px rgba(249,115,22,0.5), 0 12px 48px -8px rgba(249,115,22,0.6)",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
              Bắt đầu tạo video
              <span style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                width: 20, height: 20, borderRadius: "50%",
                background: "rgba(0,0,0,0.18)", fontSize: 11,
              }}>→</span>
            </span>
          </motion.button>

          <motion.a
            href="/history"
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="btn-ghost"
            style={{
              padding: "18px 28px",
              fontSize: 12,
              borderRadius: "var(--r-full)",
              borderColor: "rgba(255,255,255,0.15)",
              backdropFilter: "blur(10px)",
              background: "rgba(255,255,255,0.03)",
              textDecoration: "none",
            }}
          >
            Lịch sử video
          </motion.a>
        </motion.div>

        {/* Highlight 5 latest videos */}
        {history.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.95 }}
            style={{
              marginTop: 48,
              width: "100%",
              maxWidth: 640,
              textAlign: "left",
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              borderRadius: "var(--r-lg)",
              padding: "16px 20px",
              backdropFilter: "blur(10px)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", boxShadow: "0 0 8px var(--accent)" }} />
                <h3 style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)" }}>
                  BẢN TIN MỚI NHẤT HÔM NAY
                </h3>
              </div>
              <a href="/history" style={{ fontSize: 10, color: "var(--accent)", textDecoration: "none", fontWeight: 700 }}>
                Xem tất cả →
              </a>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {history.map((h) => {
                const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
                const videoUrl = h.video_url || "";
                const videoFullUrl = videoUrl.startsWith("http") ? videoUrl : (videoUrl ? `${API}${videoUrl}` : "");
                
                return (
                  <div
                    key={h.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                      padding: "8px 12px",
                      borderRadius: "var(--r)",
                      background: "rgba(255, 255, 255, 0.01)",
                      border: "1px solid rgba(255, 255, 255, 0.03)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                    onClick={() => {
                      setActiveVideoUrl(videoFullUrl);
                      setActiveVideoTitle(h.title);
                    }}
                    className="scene-card"
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 12, color: "var(--accent)" }}></span>
                      <h4 style={{ fontSize: 12, fontWeight: 700, color: "var(--white)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", margin: 0, padding: 0 }}>
                        {h.title}
                      </h4>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 10, color: "var(--gray-5)" }}>
                        {new Date(h.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <div className="badge badge-accent" style={{ background: "rgba(249,115,22,0.06)", borderColor: "rgba(249,115,22,0.15)", fontSize: 8, padding: "2px 6px" }}>
                        {Math.floor(h.duration / 60)}:{(h.duration % 60).toString().padStart(2, '0')}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Video Player Modal */}
        {activeVideoUrl && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 9999,
              background: "rgba(0, 0, 0, 0.85)",
              backdropFilter: "blur(12px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 24,
            }}
            onClick={() => setActiveVideoUrl(null)}
          >
            <div
              style={{
                position: "relative",
                width: "100%",
                maxWidth: 960,
                background: "var(--gray-1)",
                border: "1px solid var(--gray-3)",
                borderRadius: "var(--r-lg)",
                overflow: "hidden",
              }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--gray-3)", background: "rgba(0,0,0,0.5)" }}>
                <h3 style={{ fontSize: 14, fontWeight: 800, color: "var(--white)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "80%", margin: 0 }}>
                  {activeVideoTitle}
                </h3>
                <button
                  onClick={() => setActiveVideoUrl(null)}
                  className="btn-ghost"
                  style={{ padding: "4px 10px", fontSize: 11 }}
                >
                  ✕ Đóng
                </button>
              </div>
              <video src={activeVideoUrl} controls autoPlay style={{ width: "100%", display: "block" }} />
            </div>
          </div>
        )}

        {/* Stats row */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.05 }}
          style={{
            marginTop: 80,
            display: "flex",
            gap: 48,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {[
            { k: "1080p", v: "30fps · MP4" },
            { k: "6–8", v: "phân cảnh / video" },
            { k: "vi-VN", v: "TTS tiếng Việt" },
            { k: "GPT-4o", v: "Premium AI" },
          ].map((s, i) => (
            <motion.div
              key={s.k}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 1.1 + i * 0.08 }}
              style={{ textAlign: "center" }}
            >
              <div style={{
                fontSize: 24, fontWeight: 900, letterSpacing: "-0.02em",
                color: "var(--white)", lineHeight: 1,
                marginBottom: 6,
              }}>{s.k}</div>
              <div style={{
                fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
                textTransform: "uppercase", color: "var(--gray-5)",
              }}>{s.v}</div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

/* ─────────────────────────  INPUT STAGE  ───────────────────────── */

function InputStage({
  error, isLoading, setIsLoading, setError, onExtracted,
}: {
  error: string;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
  setError: (v: string) => void;
  onExtracted: (c: ExtractedContent) => void;
}) {
  return (
    <main style={{
      maxWidth: 1280, margin: "0 auto",
      padding: "clamp(40px, 6vw, 80px) clamp(20px, 4vw, 48px)",
      display: "grid",
      gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1.1fr)",
      gap: "clamp(32px, 5vw, 80px)",
      alignItems: "center",
    }}>
      {/* Left — copy */}
      <div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="hero-eyebrow"
          style={{ marginBottom: 28 }}
        >
          Bước 1 · Cung cấp nội dung
        </motion.div>

        <h1 style={{
          fontSize: "clamp(40px, 5.5vw, 72px)",
          fontWeight: 900, lineHeight: 1.05, letterSpacing: "-0.04em",
          marginBottom: 28,
          paddingTop: "0.12em",
        }}>
          <StaggeredText text="Dán link" accentWord="link" /><br />
          <StaggeredText text="hoặc kéo" /><br />
          <StaggeredText text="file vào." />
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.65 }}
          style={{
            fontSize: 16, color: "var(--gray-6)",
            lineHeight: 1.7, maxWidth: 460, marginBottom: 36,
          }}
        >
          AI tự đọc bài viết, viết kịch bản 6–8 phân cảnh, sinh prompt ảnh, và sẵn sàng dựng video.
          Bạn vẫn kiểm soát mọi bước trước khi render.
        </motion.p>

        {/* Process steps */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[
            { n: "01", t: "Trích xuất nội dung", d: "Bài viết → văn bản sạch" },
            { n: "02", t: "AI viết kịch bản", d: "Phân cảnh + lời dẫn tiếng Việt" },
            { n: "03", t: "Xem trước & chỉnh sửa", d: "Theme · giọng đọc · ảnh minh hoạ" },
            { n: "04", t: "Render MP4 1080p", d: "GSAP + TTS + FFmpeg" },
          ].map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.8 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              style={{
                display: "flex", alignItems: "center", gap: 16,
                padding: "12px 0",
                borderTop: "1px solid var(--gray-3)",
              }}
            >
              <span style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11, fontWeight: 700, color: "var(--accent)",
                letterSpacing: "0.05em", flexShrink: 0,
              }}>{s.n}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--white)" }}>{s.t}</div>
                <div style={{ fontSize: 12, color: "var(--gray-5)", marginTop: 2 }}>{s.d}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right — input card */}
      <ClipReveal direction="right" delay={0.2}>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              marginBottom: 20, padding: "12px 16px",
              borderRadius: "var(--r)",
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.25)",
              color: "var(--red)", fontSize: 13,
            }}
          >
            Lỗi: {error}
          </motion.div>
        )}

        <div className="input-card" style={{
          background: "linear-gradient(180deg, var(--gray-1) 0%, #0a0a0a 100%)",
          position: "relative",
          overflow: "hidden",
        }}>
          {/* Decorative corner glow */}
          <div style={{
            position: "absolute", top: -60, right: -60,
            width: 200, height: 200, borderRadius: "50%",
            background: "radial-gradient(circle, rgba(249,115,22,0.18), transparent 70%)",
            pointerEvents: "none",
          }} />

          <div style={{ position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
              <div className="badge badge-accent badge-dot">
                <span /> Sẵn sàng nhận nội dung
              </div>
              <div style={{ fontSize: 10, color: "var(--gray-5)", fontFamily: "var(--font-mono)", letterSpacing: "0.08em" }}>
                STEP_01 / 04
              </div>
            </div>

            <InputPanel
              onExtracted={onExtracted}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              setError={setError}
            />
          </div>
        </div>

        <p style={{
          marginTop: 16, textAlign: "center",
          fontSize: 11, color: "var(--gray-5)",
        }}>
          Nội dung của bạn được xử lý qua API riêng tư · không lưu công khai
        </p>
      </ClipReveal>
    </main>
  );
}

/* ─────────────────────────  GENERATING STAGE  ───────────────────────── */

function GeneratingStage({ buffer, onCancel }: { buffer: string; onCancel: () => void }) {
  const preRef = useRef<HTMLPreElement>(null);
  useEffect(() => {
    preRef.current?.scrollTo({ top: preRef.current.scrollHeight, behavior: "smooth" });
  }, [buffer]);

  const charCount = buffer.length;

  return (
    <main style={{
      maxWidth: 900, margin: "0 auto",
      padding: "clamp(40px, 8vw, 96px) clamp(20px, 4vw, 48px)",
    }}>
      <div className="fade-up" style={{ textAlign: "center", marginBottom: 40 }}>
        <div className="hero-eyebrow" style={{ justifyContent: "center", display: "inline-flex", marginBottom: 24 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "var(--accent)",
            boxShadow: "0 0 12px var(--accent)",
            animation: "dot-blink 1.2s ease-in-out infinite",
          }} />
          AI đang viết kịch bản
        </div>
        <h1 style={{
          fontSize: "clamp(36px, 5vw, 64px)",
          fontWeight: 900, lineHeight: 1, letterSpacing: "-0.04em",
          marginBottom: 16,
        }}>
          <span className="gradient-text">AI</span> đang suy nghĩ...
        </h1>
        <p style={{ fontSize: 14, color: "var(--gray-5)", maxWidth: 480, margin: "0 auto" }}>
          Phân tích bài viết và tạo 6–8 phân cảnh có lời dẫn tiếng Việt tự nhiên.
          Quá trình này thường mất 20–40 giây.
        </p>
      </div>

      {/* Stream output */}
      <div className="terminal fade-up" style={{ padding: 20, animationDelay: "0.15s" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["#ef4444", "#fbbf24", "#22c55e"].map(c => (
                <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
              ))}
            </div>
            <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(249,115,22,0.5)" }}>
              llm_stream.log
            </span>
          </div>
          <span style={{ fontSize: 10, color: "var(--gray-5)", fontFamily: "var(--font-mono)" }}>
            {charCount.toLocaleString()} ký tự
          </span>
        </div>
        <pre
          ref={preRef}
          style={{
            maxHeight: 360, minHeight: 200,
            overflow: "auto", whiteSpace: "pre-wrap",
            lineHeight: 1.7, fontSize: 12,
            color: "rgba(249,115,22,0.85)",
          }}
        >
          {buffer || "Đang khởi tạo phiên với AI API..."}
          <span style={{
            display: "inline-block",
            width: 8, height: 14,
            background: "var(--accent)",
            verticalAlign: "middle",
            marginLeft: 2,
            animation: "dot-blink 1s steps(2) infinite",
          }} />
        </pre>
      </div>

      <div className="fade-up" style={{ display: "flex", justifyContent: "center", marginTop: 32, animationDelay: "0.3s" }}>
        <button
          onClick={() => {
            if (window.confirm("AI đang viết kịch bản. Nếu huỷ bây giờ, toàn bộ tiến trình này sẽ bị mất.\n\nBạn có chắc chắn muốn huỷ không?")) {
              onCancel();
            }
          }}
          className="btn-ghost"
          style={{ borderColor: "rgba(239,68,68,0.3)", color: "var(--red)" }}
        >
          ✕ Huỷ và quay lại
        </button>
      </div>
    </main>
  );
}

/* ─────────────────────────  PREVIEW STAGE  ───────────────────────── */

function PreviewStage({
  scenePlan, setScenePlan, onBuild,
}: {
  scenePlan: ScenePlan;
  setScenePlan: (p: ScenePlan) => void;
  onBuild: () => void;
}) {
  const themeId: ThemeId = scenePlan.theme ?? DEFAULT_THEME;
  const theme = getTheme(themeId);

  return (
    <main style={{ maxWidth: 1280, margin: "0 auto", padding: "32px clamp(20px,4vw,48px)" }}>
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <div className="hero-eyebrow" style={{ marginBottom: 14 }}>
          Bước 2 · Xem trước & chỉnh sửa
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <h1 style={{
            fontSize: "clamp(28px, 3.5vw, 44px)",
            fontWeight: 900, lineHeight: 1.05, letterSpacing: "-0.03em",
            maxWidth: 720,
          }}>
            {scenePlan.title}
          </h1>
          <button
            onClick={onBuild}
            className="btn-primary magnetic"
            style={{
              background: theme.accent,
              boxShadow: `0 12px 32px -4px ${theme.accent}99`,
            }}
          >
            <span>→ Xem trước HTML</span>
          </button>
        </div>
      </div>

      {/* Theme picker card */}
      <div className="fade-up" style={{
        marginBottom: 24,
        padding: "clamp(20px,3vw,28px)",
        background: "var(--gray-1)",
        border: "1px solid var(--gray-3)",
        borderRadius: "var(--r-xl)",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: -80, right: -80,
          width: 240, height: 240, borderRadius: "50%",
          background: `radial-gradient(circle, ${theme.accent}26, transparent 70%)`,
          pointerEvents: "none",
        }} />
        <div style={{ position: "relative" }}>
          <ThemePicker
            value={themeId}
            onChange={(id) => setScenePlan({ ...scenePlan, theme: id })}
          />
        </div>
      </div>

      {/* Voice picker card */}
      <div className="fade-up" style={{
        marginBottom: 32,
        padding: "clamp(20px,3vw,28px)",
        background: "var(--gray-1)",
        border: "1px solid var(--gray-3)",
        borderRadius: "var(--r-xl)",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: -60, left: -60,
          width: 200, height: 200, borderRadius: "50%",
          background: `radial-gradient(circle, ${theme.accent2}22, transparent 70%)`,
          pointerEvents: "none",
        }} />
        <div style={{ position: "relative" }}>
          <VoicePicker
            value={scenePlan.voiceId}
            onChange={(id) => setScenePlan({ ...scenePlan, voiceId: id })}
          />
        </div>
      </div>

      <SceneList scenePlan={scenePlan} onChange={setScenePlan} />
    </main>
  );
}
