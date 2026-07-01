"use client";

import { useEffect, useRef } from "react";

/** Animated star-field canvas that fills its parent container. */
export function GalaxyCanvas({
  accentHue = 28,        // orange by default
  starCount = 140,
  nebulaOpacity = 0.09,
}: {
  accentHue?: number;
  starCount?: number;
  nebulaOpacity?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    let raf = 0;
    let w = 0, h = 0;

    type Star = { x: number; y: number; z: number; speed: number; r: number; orange: boolean };
    let stars: Star[] = [];

    function init(W: number, H: number) {
      w = W; h = H;
      cv!.width = W * dpr;
      cv!.height = H * dpr;
      cv!.style.width = W + "px";
      cv!.style.height = H + "px";
      stars = Array.from({ length: starCount }, () => ({
        x: Math.random() * W * dpr,
        y: Math.random() * H * dpr,
        z: Math.random() * 0.7 + 0.3,
        speed: Math.random() * 0.35 + 0.05,
        r: Math.random() * 1.4 + 0.25,
        orange: Math.random() < 0.15,
      }));
    }

    let t = 0;
    function frame() {
      if (!ctx) return;
      t += 0.005;
      ctx.fillStyle = "rgba(0,0,0,0.20)";
      ctx.fillRect(0, 0, w * dpr, h * dpr);

      // Nebula glow
      const cx = (w * dpr) / 2 + Math.sin(t * 0.6) * 50 * dpr;
      const cy = (h * dpr) / 2 + Math.cos(t * 0.5) * 30 * dpr;
      const gr = ctx.createRadialGradient(cx, cy, 0, cx, cy, h * dpr * 0.65);
      gr.addColorStop(0, `hsla(${accentHue},95%,60%,${nebulaOpacity})`);
      gr.addColorStop(0.45, `hsla(${accentHue},80%,50%,${nebulaOpacity * 0.4})`);
      gr.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = gr;
      ctx.fillRect(0, 0, w * dpr, h * dpr);

      for (const s of stars) {
        s.y += s.speed * s.z * dpr;
        if (s.y > h * dpr) { s.y = -2; s.x = Math.random() * w * dpr; }
        const alpha = 0.35 + s.z * 0.6;
        ctx.fillStyle = s.orange
          ? `rgba(251,146,60,${alpha})`
          : `rgba(255,255,255,${alpha * 0.8})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * s.z, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }

    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      init(width, height);
    });
    const parent = cv.parentElement;
    if (parent) {
      ro.observe(parent);
      const { offsetWidth: W, offsetHeight: H } = parent;
      init(W, H);
    }
    frame();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [accentHue, starCount, nebulaOpacity]);

  return (
    <canvas
      ref={ref}
      aria-hidden
      style={{
        position: "absolute", inset: 0,
        width: "100%", height: "100%",
        pointerEvents: "none", zIndex: 0,
        borderRadius: "inherit",
      }}
    />
  );
}
