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
  source?: string;       // 'builtin' | 'user'
  editable?: boolean;
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

/** Trích nội dung từ tài liệu (docx/md/txt/csv) để làm nguồn sinh slide. */
export async function extractDoc(file: File): Promise<{ title: string; text: string }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch(`${P}/extract-doc`, { method: "POST", body: form });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

/** Trích nội dung từ link web. */
export async function extractUrl(url: string): Promise<{ title: string; text: string }> {
  const res = await fetch(`${P}/extract-url`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

/** URL slide mẫu của style (preview.html) qua proxy. */
export function stylePreviewUrl(styleKey: string): string {
  return `${P}/styles/${encodeURIComponent(styleKey)}/preview`;
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

/** Sinh theo luồng TEMPLATE: điền nội dung vào seed pages, giữ nguyên thiết kế mẫu. */
export async function startTemplateGenerate(sessionId: string, userMessage: string): Promise<{ runId: string }> {
  const res = await fetch(`${P}/sessions/${sessionId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userMessage, type: "deck", template: true }),
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

/* ── Phase 2: chỉnh sửa ─────────────────────────────────────────────────── */

export interface ChatMessage {
  id?: string;
  role: string;          // user | assistant | system
  content: string;
  type?: string;
}

/** Chat-edit 1 trang: AI sửa HTML trang theo yêu cầu (type:page, chatType:page). */
export async function editPage(sessionId: string, pageId: string, instruction: string): Promise<{ runId?: string }> {
  const res = await fetch(`${P}/sessions/${sessionId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userMessage: instruction, type: "page",
      chatType: "page", chatPageId: pageId, selectedPageId: pageId,
    }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

export async function getPageMessages(sessionId: string, pageId: string): Promise<ChatMessage[]> {
  return invoke<ChatMessage[]>("session:getMessages", { sessionId, chatType: "page", pageId });
}

export async function addPage(sessionId: string, userMessage: string, insertAfterPageNumber: number): Promise<{ runId?: string }> {
  return invoke("generate:addPage", { sessionId, userMessage, insertAfterPageNumber });
}

export async function deletePage(sessionId: string, pageId: string): Promise<void> {
  await invoke("session:deletePages", { sessionId, pageIds: [pageId] });
}

export async function reorderPages(sessionId: string, orderedPageIds: string[]): Promise<void> {
  await invoke("session:reorderPages", { sessionId, orderedPageIds });
}

export type SpeechScope = "all" | "single";
export type SpeechStyle = "formal" | "conversational" | "storytelling";

export async function generateSpeech(sessionId: string, scope: SpeechScope, currentPageId: string, style: SpeechStyle): Promise<void> {
  await invoke("speech:generateScript", { sessionId, scope, currentPageId, style, length: "medium" });
}

export async function getSpeech(sessionId: string): Promise<any> {
  return invoke("speech:getScript", { sessionId });
}

/** Lưu deck hiện tại thành template tái dùng. */
export async function saveAsTemplate(sessionId: string, name: string): Promise<{ id: string }> {
  return invoke("templates:createFromSession", { sessionId, name });
}

/* ── Phase 3: history / template / animation ──────────────────────────── */

export interface HistoryVersion {
  id: string;
  operationId: string;
  title: string;
  description: string;
  kind: string;
  createdAt: number;
  isCurrent: boolean;
  isRestorable: boolean;
}

export async function listVersions(sessionId: string): Promise<HistoryVersion[]> {
  return invoke<HistoryVersion[]>("history:listVersions", { sessionId, limit: 50 });
}

export async function rollbackToVersion(sessionId: string, versionId: string): Promise<void> {
  await invoke("history:rollbackToVersion", { sessionId, versionId });
}

export interface TemplateItem {
  id: string;
  name: string;
  description?: string;
  pageCount?: number;
  styleKey?: string;
}

export async function listTemplates(): Promise<TemplateItem[]> {
  const r = await invoke<{ items?: TemplateItem[] }>("templates:list");
  return r?.items ?? [];
}

export async function createFromTemplate(templateId: string, title: string, pageCount: number): Promise<string> {
  const r = await invoke<{ sessionId: string }>("templates:createSession", { templateId, title, pageCount });
  return r.sessionId;
}

export interface TemplatePreviewPage { pageNumber: number; title: string; url: string; }

/** Danh sách trang (kèm URL preview qua proxy) của 1 template — để hiện thumbnail/gallery. */
export async function templateManifest(id: string): Promise<{ name?: string; pages: TemplatePreviewPage[] }> {
  const r = await fetch(`${P}/templates/${encodeURIComponent(id)}/manifest`).then((x) => x.json());
  const pages: TemplatePreviewPage[] = (r.pages ?? []).map((p: TemplatePreviewPage) => ({ ...p, url: `${P}${p.url}` }));
  return { name: r.name, pages };
}

/** Copy template thành session editable ngay (không gọi LLM) — sửa lại nội dung sau. */
export async function createEditableFromTemplate(templateId: string, title: string): Promise<string> {
  const r = await invoke<{ sessionId: string }>("templates:createEditableSession", { templateId, title });
  return r.sessionId;
}

/** Upload 1 file lên engine, trả path phía server (dùng cho import pptx / upload font). */
export async function uploadToEngine(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch(`${P}/upload`, { method: "POST", body: form });
  const data = await res.json();
  if (!data.path) throw new Error(data.error || "Upload lỗi");
  return data.path;
}

/** Import .pptx: upload → tạo template từ pptx → mở thành session editable. */
export async function importPptxAsSession(file: File): Promise<string> {
  const filePath = await uploadToEngine(file);
  const tpl = await invoke<{ id: string }>("templates:importPptx", { filePath });
  return createEditableFromTemplate(tpl.id, file.name.replace(/\.pptx$/i, ""));
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await invoke("templates:delete", templateId);
}

/* ── Quản lý Font ─────────────────────────────────────────────────────── */
export interface FontsData { googleFonts: FontItem[]; userFonts: FontItem[]; }
export async function getFonts(): Promise<FontsData> { return invoke<FontsData>("fonts:list"); }
export async function uploadFont(family: string, file: File, category = "sans-serif"): Promise<void> {
  const p = await uploadToEngine(file);
  await invoke("fonts:upload", { family, category, role: ["title", "body"], scripts: ["latin"], files: [{ path: p, name: file.name }] });
}
export async function deleteFont(fontId: string): Promise<void> { await invoke("fonts:delete", fontId); }

/* ── Quản lý Style ────────────────────────────────────────────────────── */
export interface StyleDraft { name: string; description?: string; category?: string; styleSkill?: string; styleCase?: string; palette?: unknown; }
/** Phân tích 1 ảnh thiết kế → bản nháp style (dùng vision model). */
export async function parseStyleImage(imageBase64: string, mimeType: string): Promise<StyleDraft> {
  return invoke<StyleDraft>("styles:parseImage", { imageBase64, mimeType });
}
/** Lưu style mới từ bản nháp. */
export async function createStyle(draft: StyleDraft): Promise<{ id: string }> {
  return invoke<{ id: string }>("styles:create", draft);
}
export async function deleteStyle(styleId: string): Promise<void> { await invoke("styles:delete", styleId); }

export type IndexTransition = "none" | "fade" | "slide" | "zoom" | "flip" | "cube";

export async function setIndexTransition(sessionId: string, transition: IndexTransition): Promise<void> {
  await invoke("session:setIndexTransition", { sessionId, transition });
}

export async function getIndexTransition(sessionId: string): Promise<string> {
  const r = await invoke<{ transition?: string }>("session:getIndexTransition", { sessionId });
  return r?.transition ?? "none";
}

/** true nếu session còn run generate/edit đang chạy. */
export async function hasActiveRun(sessionId: string): Promise<boolean> {
  try {
    const r = await invoke<{ hasActiveRun?: boolean; status?: string }>("generate:state", sessionId);
    return !!r?.hasActiveRun || r?.status === "running" || r?.status === "queued";
  } catch { return false; }
}

export type ExportKind = "pptx" | "pdf" | "png";

/** Tải file export (mở tab tải trực tiếp qua proxy). */
export function exportDownloadUrl(sessionId: string, kind: ExportKind): string {
  return `${P}/sessions/${sessionId}/export/${kind}`;
}
