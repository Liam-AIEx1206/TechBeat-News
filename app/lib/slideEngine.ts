/**
 * Client cho slide-engine (luồng oh-my-ppt) qua proxy /api/proxy/slide/*.
 * Mọi logic sinh/sửa/xuất nằm ở engine; đây chỉ là lớp gọi mỏng cho UI XNEW.
 */
const P = "/api/proxy/slide";

export interface StyleItem {
  id: string;            // uuid — dùng khi tạo session
  styleKey: string;      // slug
  label: string;
  name?: { zh?: string; en?: string };
  description?: string;
  category?: string;
}

export interface FontItem {
  id: string;
  family: string;
  category?: string;
  role?: string;
  scripts?: string[];
}

export interface GeneratedPage {
  id: string;
  pageNumber: number;
  title: string;
  pageId?: string;
  sourceUrl?: string;    // đã rewrite → /fs/... (phục vụ qua proxy)
  status?: string;       // completed | failed | ...
  error?: string | null;
}

export interface SessionData {
  session: Record<string, unknown>;
  messages: unknown[];
  generatedPages: GeneratedPage[];
}

async function invoke<T = unknown>(channel: string, ...args: unknown[]): Promise<T> {
  const res = await fetch(`${P}/invoke/${encodeURIComponent(channel)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ __args: args }),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || `invoke ${channel} lỗi`);
  return data.result as T;
}

export async function listStyles(): Promise<StyleItem[]> {
  const r = await fetch(`${P}/styles`).then((x) => x.json());
  return r.items ?? [];
}

export async function listFonts(): Promise<{ googleFonts: FontItem[]; userFonts: FontItem[] }> {
  return invoke("fonts:list");
}

export interface CreateSessionInput {
  topic: string;
  styleId: string;              // uuid
  pageCount: number;
  fontSelection?: { titleFontId?: string; bodyFontId?: string } | null;
}

export async function createSession(input: CreateSessionInput): Promise<string> {
  const r = await invoke<{ sessionId: string }>("session:create", {
    topic: input.topic,
    styleId: input.styleId,
    pageCount: input.pageCount,
    fontSelection: input.fontSelection ?? undefined,
  });
  return r.sessionId;
}

export async function startGenerate(sessionId: string, userMessage: string): Promise<{ runId: string }> {
  const res = await fetch(`${P}/sessions/${sessionId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userMessage, type: "deck" }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

export async function getSession(sessionId: string): Promise<SessionData> {
  return invoke<SessionData>("session:get", sessionId);
}

export async function retryFailedPages(sessionId: string): Promise<void> {
  await fetch(`${P}/sessions/${sessionId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userMessage: "", type: "deck", retryFailedOnly: true }),
  }).catch(() => {});
}

/** URL trang HTML đã gen để nhúng iframe preview (đi qua proxy /fs). */
export function pageUrl(page: GeneratedPage): string {
  if (!page.sourceUrl) return "";
  // sourceUrl dạng /fs/<abs>; ghép vào proxy
  return page.sourceUrl.startsWith("/fs/") ? `${P}${page.sourceUrl}` : page.sourceUrl;
}

/** SSE tiến độ generate. Trả hàm huỷ. */
export function subscribeProgress(onEvent: (ev: any) => void): () => void {
  const es = new EventSource(`${P}/events`);
  es.addEventListener("generate:chunk", (e: MessageEvent) => {
    try { onEvent(JSON.parse(e.data)); } catch { /* keepalive */ }
  });
  es.onerror = () => { /* trình duyệt tự reconnect */ };
  return () => es.close();
}

export type ExportKind = "pptx" | "pdf" | "png";

/** Tải file export (mở tab tải trực tiếp qua proxy). */
export function exportDownloadUrl(sessionId: string, kind: ExportKind): string {
  return `${P}/sessions/${sessionId}/export/${kind}`;
}
