export interface Scene {
  id: string;
  index: number;
  title: string;
  narration: string;
  visualDescription: string;
  duration: number; // seconds
  imageQuery?: string; // search query for finding/selecting an image
  imageUrl?: string;   // user-picked illustration URL (data URL / https / blob)
  /** Local asset path like "assets/scene1.jpg" once the backend has
   *  downloaded/decoded imageUrl. Cleared when imageUrl changes so the next
   *  regen call re-materialises the file. */
  imageAsset?: string;
}

export interface ScenePlan {
  title: string;
  scenes: Scene[];
  totalDuration: number;
  theme?: ThemeId;
  styleId?: string;   // style pack (oh-my-ppt) đã chọn — luồng slide dùng thay theme màu
  voiceId?: string;
  compositionHtml?: string;
  sceneRegenFlags?: boolean[];
  subtitlesEnabled?: boolean;
  sessionId?: string;
  outputType?: "video" | "slide";
  pptxUrl?: string;
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
  | "gold-editorial"
  | "sunset-glow"
  | "iceberg-tech"
  | "ocean-depths"
  | "space-odyssey"
  | "bento-minimal"
  | "forest-eco"
  | "brutalist-bold"
  | "pop-candy"
  | "neon-green-overdrive";

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
  {
    id: "sunset-glow",
    name: "Sunset Glow",
    tagline: "Cozy warm sunset",
    bg: "#0f050b",
    bg2: "#1a0815",
    surface: "#280f20",
    accent: "#f43f5e",
    accent2: "#f97316",
    accent3: "#fef08a",
    text1: "#fff1f2",
    text2: "#fda4af",
    vibe: "lãng mạn hoàng hôn ấm áp phong cách editorial, với sự pha trộn mềm mại của tone đỏ hồng, cam ấm và ánh sáng vàng nhạt",
  },
  {
    id: "iceberg-tech",
    name: "Iceberg Tech",
    tagline: "Minimal cold glacial",
    bg: "#02070f",
    bg2: "#051220",
    surface: "#0a1d33",
    accent: "#38bdf8",
    accent2: "#34d399",
    accent3: "#cbd5e1",
    text1: "#f0f9ff",
    text2: "#93c5fd",
    vibe: "công nghệ lạnh giá tối giản tinh khiết như băng đá, sắc nét với ánh sáng xanh lam và bạc mờ, kết hợp bento hoặc các ô trong suốt",
  },
  {
    id: "ocean-depths",
    name: "Ocean Depths",
    tagline: "Deep sea marine tech",
    bg: "#020712",
    bg2: "#051125",
    surface: "#0a1c3b",
    accent: "#0d9488",
    accent2: "#06b6d4",
    accent3: "#f43f5e",
    text1: "#f0fdfa",
    text2: "#99f6e4",
    vibe: "đại dương sâu thẳm đầy bí ẩn công nghệ cao sinh học biển, màu nền xanh đen sâu thẳm kết hợp xanh teal điện tử và hồng san hô",
  },
  {
    id: "space-odyssey",
    name: "Space Odyssey",
    tagline: "Nebula cosmic sci-fi",
    bg: "#04020a",
    bg2: "#0e051a",
    surface: "#1b0b30",
    accent: "#8b5cf6",
    accent2: "#d946ef",
    accent3: "#ec4899",
    text1: "#faf5ff",
    text2: "#e9d5ff",
    vibe: "không gian vũ trụ cinematic sâu thẳm huyền bí với dải ngân hà nebula tím và supernova hồng rực rỡ",
  },
  {
    id: "bento-minimal",
    name: "Bento Minimal",
    tagline: "Organized Japan tech",
    bg: "#080808",
    bg2: "#121212",
    surface: "#181818",
    accent: "#dc2626",
    accent2: "#f9fafb",
    accent3: "#a1a1aa",
    text1: "#f9fafb",
    text2: "#d4d4d8",
    vibe: "phong cách thiết kế Bento Nhật Bản tối giản, cực kỳ ngăn nắp sạch sẽ, tone xám đen nhám tối giản điểm màu đỏ mặt trời mọc",
  },
  {
    id: "forest-eco",
    name: "Forest Eco",
    tagline: "Nature green bio tech",
    bg: "#020c08",
    bg2: "#051a11",
    surface: "#0a281c",
    accent: "#10b981",
    accent2: "#84cc16",
    accent3: "#34d399",
    text1: "#f0fdf4",
    text2: "#bbf7d0",
    vibe: "xanh sinh thái sinh học tự nhiên eco-tech thân thiện, màu xanh rừng rậm tươi mát phối với xanh đọt chuối ngọc bích",
  },
  {
    id: "brutalist-bold",
    name: "Brutalist Bold",
    tagline: "Retro poster marquee",
    bg: "#0c0c0e",
    bg2: "#19191d",
    surface: "#222227",
    accent: "#ea580c",
    accent2: "#facc15",
    accent3: "#2563eb",
    text1: "#ffffff",
    text2: "#e4e4e7",
    vibe: "nghệ thuật Brutalism nổi loạn phá cách với typography khổng lồ, viền đen dày, bóng đổ 45 độ sắc cạnh",
  },
  {
    id: "pop-candy",
    name: "Pop Candy",
    tagline: "Sweet Kawaii pastels",
    bg: "#0d0615",
    bg2: "#180c29",
    surface: "#23123c",
    accent: "#fda4af",
    accent2: "#a7f3d0",
    accent3: "#c084fc",
    text1: "#fdf4ff",
    text2: "#f5d0fe",
    vibe: "pastel ngọt ngào mộng mơ Kawaii tươi trẻ năng động, sự pha trộn dễ thương giữa đào mọng, soda bạc hà và oải hương",
  },
  {
    id: "neon-green-overdrive",
    name: "Neon Green Overdrive",
    tagline: "eSports athletic energy",
    bg: "#06080d",
    bg2: "#0c111c",
    surface: "#121b2d",
    accent: "#a3e635",
    accent2: "#22c55e",
    accent3: "#0ea5e9",
    text1: "#f0fdf4",
    text2: "#bbf7d0",
    vibe: "thể thao điện tử eSports cực kỳ phấn khích tốc độ cao, đen carbon bóng bọc viền xanh lá chói mắt phản quang",
  },
];

export const DEFAULT_THEME: ThemeId = "cyber-orange";

export function getTheme(id?: ThemeId | null): Theme {
  return THEMES.find((t) => t.id === id) ?? THEMES[0];
}
