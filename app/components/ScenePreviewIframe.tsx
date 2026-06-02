"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  /** Full composition HTML (entire <!doctype html>...</html>). */
  fullHtml: string;
  /** 1-indexed scene to preview. */
  sceneIndex: number;
  /** Optional aspect-ratio width/height for the rendered viewport (defaults 1920×1080). */
  width?: number;
  height?: number;
  /** When false, injects CSS to hide .techbeat-subtitles in the preview. Default true. */
  showSubtitles?: boolean;
}

/** Carve scene #N out of the full composition, isolate it inside its own
 *  document so all the surrounding scenes don't fight for visibility, and
 *  show that scene visible at frame 0 (no GSAP timeline running). The
 *  document is sized 1920×1080 and we apply a CSS transform on the iframe
 *  to fit it into the parent container. */
function buildIsolatedDoc(fullHtml: string, sceneIndex: number, apiUrl: string, showSubtitles: boolean): string {
  let doc = fullHtml;

  // Strip ALL <script> tags — GSAP timeline must not run in preview mode.
  // The timeline would immediately hide all scenes via gsap.set opacity:0,
  // fighting our visibility override. Static HTML is all we need here.
  doc = doc.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");

  // ── Base URL for relative paths ──────────────────────────────────────
  // The HTML references images as `assets/scene1.jpg` (relative). Inside an
  // iframe loaded via `srcDoc`, the document URL is `about:srcdoc` so any
  // relative href resolves to nothing → the image appears as a broken/empty
  // box. Injecting a <base href> right after <head> makes the browser
  // resolve every relative URL against the FastAPI backend, which mounts
  // /assets/ at the project's assets/ folder. Strip any existing <base> so
  // ours wins (rare but safe).
  doc = doc.replace(/<base\b[^>]*>/gi, "");
  const baseTag = `<base href="${apiUrl.replace(/\/$/, "")}/">`;

  // Hide all scenes, show only the target. Using both CSS and inline-style
  // removal (via the script below) to handle any leftover inline styles.
  const subtitleHide = showSubtitles ? "" : "\n  .techbeat-subtitles { display: none !important; }";
  const overrideCss = `
<style>
  /* preview-mode: ensure root fills the iframe viewport */
  html, body { width: 1920px; height: 1080px; overflow: hidden; margin: 0; padding: 0; }
  #root { position: relative !important; width: 1920px !important; height: 1080px !important; transform: none !important; }
  /* hide all scenes, show only target */
  .scene { opacity: 0 !important; visibility: hidden !important; display: none !important; }
  #scene${sceneIndex} { opacity: 1 !important; visibility: visible !important; display: block !important; }
  audio { display: none !important; }
  *, *::before, *::after { animation-play-state: paused !important; transition: none !important; }${subtitleHide}
</style>`;

  // Inject base tag right AFTER <head ...> so it precedes anything else,
  // then the CSS override before </head>.
  doc = doc.replace(/<head\b([^>]*)>/i, `<head$1>${baseTag}`);
  doc = doc.replace(/<\/head>/i, overrideCss + "</head>");
  return doc;
}

export function ScenePreviewIframe({ fullHtml, sceneIndex, width = 1920, height = 1080, showSubtitles = true }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  // Resize observer — keep the 1920×1080 stage scaled to fit container
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const cw = entry.contentRect.width;
      setScale(cw / width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [width]);

  const doc = buildIsolatedDoc(fullHtml, sceneIndex, API, showSubtitles);

  return (
    <div
      ref={wrapRef}
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: `${width} / ${height}`,
        background: "#000",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 30px 80px -20px rgba(249,115,22,0.25)",
        border: "1px solid var(--gray-3)",
      }}
    >
      <iframe
        key={`${sceneIndex}-${doc.length}`}
        title={`scene-${sceneIndex}-preview`}
        srcDoc={doc}
        sandbox="allow-scripts allow-same-origin"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: width,
          height: height,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
          border: "none",
          pointerEvents: "none",
        }}
      />
    </div>
  );
}
