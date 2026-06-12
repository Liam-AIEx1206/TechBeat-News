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
  /** Optional session ID for isolating concurrent users' assets. */
  sessionId?: string;
}

/** Carve scene #N out of the full composition, isolate it inside its own
 *  document so all the surrounding scenes don't fight for visibility, and
 *  show that scene visible at frame 0 (no GSAP timeline running). The
 *  document is sized 1920×1080 and we apply a CSS transform on the iframe
 *  to fit it into the parent container. */
function buildIsolatedDoc(fullHtml: string, sceneIndex: number, apiUrl: string, showSubtitles: boolean, sessionId?: string): string {
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
  const baseHref = sessionId
    ? `${apiUrl.replace(/\/$/, "")}/sessions/${sessionId}/`
    : `${apiUrl.replace(/\/$/, "")}/`;
  const baseTag = `<base href="${baseHref}">`;

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

export function ScenePreviewIframe({ fullHtml, sceneIndex, width = 1920, height = 1080, showSubtitles = true, sessionId }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
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

  const handleLoad = () => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!doc) return;

    // Clean up empty layout items (e.g. stats, cards, steps) where variables are missing
    const isTextEmpty = (el: any) => {
      if (!el) return true;
      const txt = el.textContent.trim();
      if (!txt) return true;
      try {
        return txt.replace(/[^\p{L}\p{N}]/gu, "").length === 0;
      } catch(e) {
        return txt.length <= 2;
      }
    };

    doc.querySelectorAll('.stat-list-card').forEach((card: any) => {
      const num = card.querySelector('.num');
      const title = card.querySelector('.title');
      if (isTextEmpty(num) && isTextEmpty(title)) {
        card.remove();
      }
    });
    doc.querySelectorAll('.glass-card').forEach((card: any) => {
      const title = card.querySelector('.title');
      const desc = card.querySelector('.desc');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        card.remove();
      }
    });
    const featRow: any = doc.querySelector('.feat-row');
    if (featRow) {
      const remaining = featRow.querySelectorAll('.glass-card').length;
      if (remaining > 0) {
        featRow.style.gridTemplateColumns = `repeat(${remaining}, 1fr)`;
      }
    }
    doc.querySelectorAll('.feat-card').forEach((card: any) => {
      const title = card.querySelector('.t');
      const desc = card.querySelector('.d');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        card.remove();
      }
    });
    const featGrid: any = doc.querySelector('.feat-grid');
    if (featGrid) {
      const remaining = featGrid.querySelectorAll('.feat-card');
      const remainingCount = remaining.length;
      if (remainingCount === 3) {
        remaining[2].style.gridColumn = 'span 2';
        featGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
      } else if (remainingCount === 2) {
        featGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
      } else if (remainingCount === 1) {
        featGrid.style.gridTemplateColumns = '1fr';
      }
    }
    doc.querySelectorAll('.agent-card').forEach((card: any) => {
      const role = card.querySelector('.role');
      const desc = card.querySelector('.desc');
      if (isTextEmpty(role) && isTextEmpty(desc)) {
        card.remove();
      }
    });
    const agentGrid: any = doc.querySelector('.agent-grid');
    if (agentGrid) {
      const remaining = agentGrid.querySelectorAll('.agent-card');
      const remainingCount = remaining.length;
      if (remainingCount === 3) {
        remaining[2].style.gridColumn = 'span 2';
        agentGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
      } else if (remainingCount === 2) {
        agentGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
        const pill = agentGrid.querySelector('.agent-grid-center-pill');
        if (pill) pill.remove();
      } else if (remainingCount === 1) {
        agentGrid.style.gridTemplateColumns = '1fr';
        const pill = agentGrid.querySelector('.agent-grid-center-pill');
        if (pill) pill.remove();
      }
    }
    let stepCount = 1;
    doc.querySelectorAll('.step-item').forEach((step: any) => {
      const text = step.querySelector('.step-text');
      if (isTextEmpty(text)) {
        step.remove();
      } else {
        const circle = step.querySelector('.step-circle');
        if (circle) circle.textContent = stepCount++;
      }
    });
    doc.querySelectorAll('.flow-step').forEach((step: any) => {
      const text = step.querySelector('.flow-text');
      if (isTextEmpty(text)) {
        step.remove();
      }
    });
    const flowPipeline: any = doc.querySelector('.flow-pipeline');
    if (flowPipeline) {
      const steps = flowPipeline.querySelectorAll('.flow-step');
      const arrows = flowPipeline.querySelectorAll('.flow-arrow');
      for (let i = arrows.length - 1; i >= steps.length - 1; i--) {
        if (arrows[i]) arrows[i].remove();
      }
      const remainingSteps = steps.length;
      if (remainingSteps === 3) {
        flowPipeline.style.gridTemplateColumns = '1fr 40px 1fr 40px 1fr';
      } else if (remainingSteps === 2) {
        flowPipeline.style.gridTemplateColumns = '1fr 40px 1fr';
      } else if (remainingSteps === 1) {
        flowPipeline.style.gridTemplateColumns = '1fr';
      }
    }
    doc.querySelectorAll('.arch-layer').forEach((layer: any) => {
      layer.querySelectorAll('.arch-node').forEach((node: any) => {
        if (isTextEmpty(node)) {
          node.remove();
        }
      });
      const remaining = layer.querySelectorAll('.arch-node');
      if (remaining.length === 1) {
        remaining[0].style.gridColumn = 'span 2';
      } else if (remaining.length === 0) {
        const arrow: any = layer.nextElementSibling;
        if (arrow && arrow.classList.contains('arch-arrow')) {
          arrow.remove();
        } else {
          const prevArrow: any = layer.previousElementSibling;
          if (prevArrow && prevArrow.classList.contains('arch-arrow')) {
            prevArrow.remove();
          }
        }
        layer.remove();
      }
    });
    doc.querySelectorAll('.formula-pill').forEach((pill: any) => {
      if (isTextEmpty(pill)) {
        const nextOperator: any = pill.nextElementSibling;
        if (nextOperator && nextOperator.classList.contains('formula-operator')) {
          nextOperator.remove();
        } else {
          const prevOperator: any = pill.previousElementSibling;
          if (prevOperator && prevOperator.classList.contains('formula-operator')) {
            prevOperator.remove();
          }
        }
        pill.remove();
      }
    });
    const nodes = ['n1', 'n2', 'n3', 'n4'];
    const paths = doc.querySelectorAll('.mm-svg path');
    nodes.forEach((nClass, idx) => {
      const nodeEl: any = doc.querySelector('.node.' + nClass);
      if (nodeEl) {
        if (isTextEmpty(nodeEl)) {
          nodeEl.remove();
          if (paths[idx]) (paths[idx] as any).remove();
        }
      }
    });
    doc.querySelectorAll('.gantt-row').forEach((row: any) => {
      const label = row.querySelector('.gantt-label');
      const bar = row.querySelector('.gantt-bar');
      if (isTextEmpty(label) && isTextEmpty(bar)) {
        row.remove();
      }
    });
    doc.querySelectorAll('.tl-item').forEach((item: any) => {
      const title = item.querySelector('.t');
      const desc = item.querySelector('.d');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        item.remove();
      }
    });
    doc.querySelectorAll('.checklist-item').forEach((item: any) => {
      const span = item.querySelector('span');
      if (isTextEmpty(span)) {
        item.remove();
      }
    });
    doc.querySelectorAll('.service-card').forEach((card: any) => {
      const title = card.querySelector('.service-title');
      const desc = card.querySelector('.service-desc');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        card.remove();
      }
    });
    const servicesGrid: any = doc.querySelector('.services-grid');
    if (servicesGrid) {
      const remaining = servicesGrid.querySelectorAll('.service-card').length;
      if (remaining > 0) {
        servicesGrid.style.gridTemplateColumns = `repeat(${remaining}, 1fr)`;
      }
    }
    doc.querySelectorAll('.kanban-col').forEach((col: any) => {
      const title = col.querySelector('.status-title');
      if (isTextEmpty(title)) {
        col.remove();
      }
    });
    const kanbanBoard: any = doc.querySelector('.kanban-board');
    if (kanbanBoard) {
      const remaining = kanbanBoard.querySelectorAll('.kanban-col').length;
      if (remaining > 0) {
        kanbanBoard.style.gridTemplateColumns = `repeat(${remaining}, 1fr)`;
      }
    }
    doc.querySelectorAll('.stat-tags .badge, .badge').forEach((badge: any) => {
      if (isTextEmpty(badge)) {
        badge.remove();
      }
    });
    doc.querySelectorAll('.bento-card').forEach((card: any) => {
      const title = card.querySelector('.bento-title');
      const desc = card.querySelector('.bento-desc');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        card.remove();
      }
    });
    const bentoGrid: any = doc.querySelector('.bento-grid');
    if (bentoGrid) {
      const remaining = bentoGrid.querySelectorAll('.bento-card');
      if (remaining.length === 3) {
        remaining[2].style.gridColumn = 'span 2';
        bentoGrid.style.gridTemplateColumns = '1fr 1fr';
        bentoGrid.style.gridTemplateRows = '1fr 1fr';
      } else if (remaining.length === 2) {
        bentoGrid.style.gridTemplateColumns = '1fr 1fr';
        bentoGrid.style.gridTemplateRows = '1fr';
        bentoGrid.style.height = '240px';
      } else if (remaining.length === 1) {
        bentoGrid.style.gridTemplateColumns = '1fr';
        bentoGrid.style.gridTemplateRows = '1fr';
        bentoGrid.style.height = '240px';
      }
    }
    doc.querySelectorAll('.bento-cell').forEach((cell: any) => {
      const title = cell.querySelector('.t');
      const desc = cell.querySelector('.d');
      if (isTextEmpty(title) && isTextEmpty(desc)) {
        cell.remove();
      }
    });
  };

  const doc = buildIsolatedDoc(fullHtml, sceneIndex, API, showSubtitles, sessionId);

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
        ref={iframeRef}
        onLoad={handleLoad}
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
