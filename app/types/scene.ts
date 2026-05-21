export interface Scene {
  id: string;
  index: number;
  title: string;
  narration: string;
  visualDescription: string;
  duration: number; // seconds
  imageQuery?: string; // search query for finding/selecting an image
  imageUrl?: string; // user-picked illustration image URL
}

export interface ScenePlan {
  title: string;
  scenes: Scene[];
  totalDuration: number;
  theme?: ThemeId; // user-selected theme; backend defaults to "cyber-orange" if missing
  voiceId?: string; // ElevenLabs voice_id; backend uses default if missing
  /** Full composition HTML cached by the html-preview stage. When present, the
   *  build pipeline skips the composition stage and uses this directly. */
  compositionHtml?: string;
  /** Per-scene flag — true when narration/title/image was edited after the
   *  last successful HTML generation, so the user knows to regen that scene. */
  sceneRegenFlags?: boolean[];
}

export interface ExtractedContent {
  title: string;
  text: string;
  source: string;
}

/* ───────────────────  THEMES  ─────────────────── */

export type ThemeId =
  | "cyber-orange"
  | "neo-cyan"
  | "violet-pulse"
  | "matrix-green"
  | "crimson-broadcast"
  | "aurora-mint"
  | "y2k-magenta"
  | "gold-editorial";

export interface Theme {
  id: ThemeId;
  name: string;
  tagline: string;
  // Brand colors used by both UI swatch + LLM composition prompt
  bg: string;       // base background
  bg2: string;      // secondary background
  surface: string;  // card surface
  accent: string;   // primary accent
  accent2: string;  // secondary accent (lighter / sister hue)
  accent3: string;  // tertiary highlight
  text1: string;    // headline color
  text2: string;    // body text color
  vibe: string;     // human description fed into prompt
}

export const THEMES: Theme[] = [
  {
    id: "cyber-orange",
    name: "Cyber Orange",
    tagline: "News broadcast premium",
    bg: "#08080f",
    bg2: "#0f0f1a",
    surface: "#141420",
    accent: "#f97316",
    accent2: "#fb923c",
    accent3: "#fbbf24",
    text1: "#f5f3ff",
    text2: "#a09db8",
    vibe: "premium dark news broadcast với accent cam ấm áp, gradient amber, scan-lines tinh tế, không khí editorial cao cấp",
  },
  {
    id: "neo-cyan",
    name: "Neo Cyan",
    tagline: "Tron-style sci-fi grid",
    bg: "#03070d",
    bg2: "#061018",
    surface: "#0a1722",
    accent: "#22d3ee",
    accent2: "#67e8f9",
    accent3: "#a5f3fc",
    text1: "#ecfeff",
    text2: "#7dd3fc",
    vibe: "Tron-inspired neo cyan sci-fi với glow lines, holographic grids, neon edges và data-stream animation",
  },
  {
    id: "violet-pulse",
    name: "Violet Pulse",
    tagline: "Synthwave / vaporwave",
    bg: "#0a0518",
    bg2: "#120a28",
    surface: "#1c1242",
    accent: "#a855f7",
    accent2: "#d946ef",
    accent3: "#f0abfc",
    text1: "#fdf4ff",
    text2: "#c4b5fd",
    vibe: "synthwave/vaporwave aesthetic với gradient tím-magenta, sun-grid retrowave, glow pulses, neon outline",
  },
  {
    id: "matrix-green",
    name: "Matrix Green",
    tagline: "Hacker terminal",
    bg: "#020a04",
    bg2: "#04130a",
    surface: "#062815",
    accent: "#22c55e",
    accent2: "#4ade80",
    accent3: "#86efac",
    text1: "#f0fdf4",
    text2: "#86efac",
    vibe: "matrix hacker terminal với character rain background, monospace typography, scanlines, CRT glow",
  },
  {
    id: "crimson-broadcast",
    name: "Crimson Broadcast",
    tagline: "Breaking news red",
    bg: "#0a0303",
    bg2: "#170808",
    surface: "#241010",
    accent: "#ef4444",
    accent2: "#f87171",
    accent3: "#fbbf24",
    text1: "#fef2f2",
    text2: "#fecaca",
    vibe: "BREAKING NEWS broadcast đỏ-vàng, cảnh báo, urgent ticker style, alert glow",
  },
  {
    id: "aurora-mint",
    name: "Aurora Mint",
    tagline: "Tech calm modern",
    bg: "#031410",
    bg2: "#062420",
    surface: "#0a3530",
    accent: "#10b981",
    accent2: "#34d399",
    accent3: "#a7f3d0",
    text1: "#ecfdf5",
    text2: "#6ee7b7",
    vibe: "aurora borealis xanh mint hiện đại, glassmorphism, soft glow, calm nhưng cao cấp",
  },
  {
    id: "y2k-magenta",
    name: "Y2K Magenta",
    tagline: "Pop / lifestyle",
    bg: "#0d0410",
    bg2: "#1a0825",
    surface: "#27123a",
    accent: "#ec4899",
    accent2: "#f472b6",
    accent3: "#fde047",
    text1: "#fdf4ff",
    text2: "#f9a8d4",
    vibe: "Y2K aesthetic với chrome highlights, bubble shapes, magenta-yellow contrast, playful nhưng vẫn premium",
  },
  {
    id: "gold-editorial",
    name: "Gold Editorial",
    tagline: "Luxury magazine",
    bg: "#0a0805",
    bg2: "#15110a",
    surface: "#221c10",
    accent: "#eab308",
    accent2: "#facc15",
    accent3: "#fde68a",
    text1: "#fefce8",
    text2: "#d6d3d1",
    vibe: "luxury magazine editorial vàng champagne trên đen sang trọng, serif accents, fine-line dividers",
  },
];

export const DEFAULT_THEME: ThemeId = "cyber-orange";

export function getTheme(id?: ThemeId | null): Theme {
  return THEMES.find((t) => t.id === id) ?? THEMES[0];
}
