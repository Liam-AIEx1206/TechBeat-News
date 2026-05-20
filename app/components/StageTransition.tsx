"use client";

import { motion, AnimatePresence, type Variants } from "motion/react";
import { ReactNode } from "react";

/* ─────────────────────────  STAGE WIPE TRANSITION  ───────────────────────── */

// Diagonal masked wipe — old stage clips out from top-left to bottom-right,
// new stage clips in from bottom-right to top-left. Plus an orange flash sweep
// on top to feel cinematic.

const stageVariants: Variants = {
  initial: {
    opacity: 0,
    clipPath: "polygon(0 0, 0 0, 0 100%, 0 100%)",
    filter: "blur(8px)",
  },
  enter: {
    opacity: 1,
    clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)",
    filter: "blur(0px)",
    transition: {
      clipPath: { duration: 0.85, ease: [0.76, 0, 0.24, 1] },
      opacity: { duration: 0.45, ease: "easeOut", delay: 0.1 },
      filter:  { duration: 0.45, ease: "easeOut", delay: 0.15 },
    },
  },
  exit: {
    opacity: 0,
    clipPath: "polygon(100% 0, 100% 0, 100% 100%, 100% 100%)",
    filter: "blur(8px)",
    transition: {
      clipPath: { duration: 0.7, ease: [0.76, 0, 0.24, 1] },
      opacity: { duration: 0.3, ease: "easeIn", delay: 0.1 },
      filter:  { duration: 0.3, ease: "easeIn" },
    },
  },
};

interface StageTransitionProps {
  stageKey: string;
  children: ReactNode;
}

export function StageTransition({ stageKey, children }: StageTransitionProps) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={stageKey}
        variants={stageVariants}
        initial="initial"
        animate="enter"
        exit="exit"
        style={{
          willChange: "clip-path, opacity, filter",
          minHeight: "100vh",
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/* ─────────────────────────  CURTAIN SWEEP  ─────────────────────────
   A separate fixed overlay that flashes an orange gradient sweep
   across the screen each time the stage changes.
*/

const curtainVariants: Variants = {
  initial: { x: "-110%", opacity: 0 },
  enter: {
    x: ["−110%", "0%", "110%"] as never,
    opacity: [0, 1, 0],
    transition: {
      duration: 1.2,
      ease: [0.76, 0, 0.24, 1],
      times: [0, 0.5, 1],
    },
  },
  exit: { opacity: 0 },
};

export function CurtainSweep({ stageKey, accent = "#f97316" }: { stageKey: string; accent?: string }) {
  return (
    <AnimatePresence>
      <motion.div
        key={`curtain-${stageKey}`}
        variants={curtainVariants}
        initial="initial"
        animate="enter"
        exit="exit"
        aria-hidden
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 90,
          pointerEvents: "none",
          background: `linear-gradient(115deg,
            transparent 0%,
            transparent 35%,
            ${accent}22 45%,
            ${accent}88 50%,
            ${accent}22 55%,
            transparent 65%,
            transparent 100%
          )`,
          mixBlendMode: "screen",
          transform: "skewX(-12deg) scaleX(1.2)",
        }}
      />
    </AnimatePresence>
  );
}

/* ─────────────────────────  STAGGERED TEXT REVEAL  ───────────────────────── */

const textContainer: Variants = {
  initial: {},
  enter: {
    transition: { staggerChildren: 0.07, delayChildren: 0.2 },
  },
};

const textWord: Variants = {
  initial: { y: "120%", opacity: 0, rotate: 6 },
  enter: {
    y: 0,
    opacity: 1,
    rotate: 0,
    transition: { duration: 0.85, ease: [0.16, 1, 0.3, 1] },
  },
};

interface StaggeredTextProps {
  text: string;
  accentWord?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function StaggeredText({ text, accentWord, className, style }: StaggeredTextProps) {
  const words = text.split(" ");
  return (
    <motion.span
      variants={textContainer}
      initial="initial"
      animate="enter"
      className={className}
      style={{ display: "inline-block", lineHeight: 1.15, ...style }}
    >
      {words.map((w, i) => (
        <span
          key={i}
          style={{
            display: "inline-block",
            overflow: "hidden",
            paddingRight: "0.25em",
            paddingTop: "0.18em",
            paddingBottom: "0.18em",
            verticalAlign: "top",
          }}
        >
          <motion.span
            variants={textWord}
            style={{
              display: "inline-block",
              fontStyle: w === accentWord ? "italic" : "normal",
              paddingRight: w === accentWord ? "0.12em" : 0,
            }}
            className={w === accentWord ? "gradient-text" : undefined}
          >
            {w}
          </motion.span>
        </span>
      ))}
    </motion.span>
  );
}

/* ─────────────────────────  GLOBAL OVERLAY (scanlines + noise) ───────────────────────── */

export function GlobalFXOverlay() {
  return (
    <>
      {/* Scanlines */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 80,
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.018) 3px, rgba(255,255,255,0.018) 4px)",
          mixBlendMode: "overlay",
        }}
      />
      {/* SVG noise */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 81,
          opacity: 0.025,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </>
  );
}

/* ─────────────────────────  PARALLAX LAYER  ─────────────────────────
   Wrap content in a motion.div whose y is bound to scroll progress.
   For our use it's mounted inside Dashboard for the floating glow blobs.
*/

interface ParallaxBlobProps {
  size: number;
  color: string;
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  delay?: number;
  duration?: number;
}

export function ParallaxBlob({
  size, color, top, left, right, bottom,
  delay = 0, duration = 14,
}: ParallaxBlobProps) {
  return (
    <motion.div
      aria-hidden
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{
        opacity: 1,
        scale: 1,
        x: [0, 40, -20, 0],
        y: [0, -30, 20, 0],
      }}
      transition={{
        opacity: { duration: 2, delay },
        scale: { duration: 2, delay },
        x: { duration, repeat: Infinity, ease: "easeInOut", delay },
        y: { duration: duration * 0.85, repeat: Infinity, ease: "easeInOut", delay },
      }}
      style={{
        position: "absolute",
        width: size, height: size,
        borderRadius: "50%",
        top, left, right, bottom,
        background: `radial-gradient(circle, ${color}, transparent 70%)`,
        filter: "blur(60px)",
        pointerEvents: "none",
      }}
    />
  );
}

/* ─────────────────────────  CLIP-PATH IMAGE REVEAL  ───────────────────────── */

interface ClipRevealProps {
  children: ReactNode;
  delay?: number;
  direction?: "left" | "right" | "up" | "down";
}

export function ClipReveal({ children, delay = 0, direction = "left" }: ClipRevealProps) {
  const initial =
    direction === "left"  ? "polygon(0 0, 0 0, 0 100%, 0 100%)"
  : direction === "right" ? "polygon(100% 0, 100% 0, 100% 100%, 100% 100%)"
  : direction === "up"    ? "polygon(0 0, 100% 0, 100% 0, 0 0)"
  :                          "polygon(0 100%, 100% 100%, 100% 100%, 0 100%)";

  return (
    <motion.div
      initial={{ clipPath: initial }}
      animate={{ clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)" }}
      transition={{ duration: 1, ease: [0.76, 0, 0.24, 1], delay }}
      style={{ willChange: "clip-path" }}
    >
      {children}
    </motion.div>
  );
}
