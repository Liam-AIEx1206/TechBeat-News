"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { ArrowLeft, Upload, Trash2, Image as ImageIcon, Loader2 } from "lucide-react";
import {
  getFonts, uploadFont, deleteFont, listStyles, parseStyleImage, createStyle, deleteStyle,
  stylePreviewUrl, type FontItem, type StyleItem,
} from "@/lib/slideEngine";

/** Trang thư viện: quản lý Font (upload/xoá) + Style (tạo từ ảnh, xoá custom). */
export function SlideLibrary() {
  const [tab, setTab] = useState<"style" | "font">("style");
  return (
    <div style={{ minHeight: "100vh", background: "var(--black)", color: "var(--white)" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 24px", borderBottom: "1px solid var(--gray-2)" }}>
        <a href="/slide" style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--gray-5)", textDecoration: "none", fontSize: 13 }}>
          <ArrowLeft size={16} /> Về tạo slide
        </a>
        <div style={{ fontSize: 16, fontWeight: 800 }}>Thư viện</div>
        <div style={{ display: "flex", gap: 8, marginLeft: 12 }}>
          {(["style", "font"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "6px 14px", borderRadius: 99, fontSize: 12, fontWeight: 700, cursor: "pointer",
              background: tab === t ? "var(--accent)" : "rgba(255,255,255,0.04)",
              color: tab === t ? "#000" : "var(--gray-5)", border: "1px solid var(--gray-3)",
            }}>{t === "style" ? "Phong cách" : "Font chữ"}</button>
          ))}
        </div>
      </header>
      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px clamp(16px,4vw,40px)" }}>
        {tab === "style" ? <StyleManager /> : <FontManager />}
      </main>
    </div>
  );
}

/* ── Style ───────────────────────────────────────────────────────────── */
function StyleManager() {
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [busy, setBusy] = useState("");
  const [draft, setDraft] = useState<{ name: string; description?: string; styleSkill?: string; category?: string; styleCase?: string } | null>(null);

  async function load() { setStyles(await listStyles().catch(() => [])); }
  useEffect(() => { load(); }, []);

  async function handleImage(file: File) {
    setBusy("parse");
    try {
      const b64 = await fileToBase64(file);
      const d = await parseStyleImage(b64, file.type || "image/png");
      setDraft({ name: d.name || "Style mới", description: d.description, styleSkill: d.styleSkill, category: d.category, styleCase: d.styleCase });
    } catch (e) { alert(e instanceof Error ? e.message : "Phân tích ảnh lỗi"); }
    finally { setBusy(""); }
  }
  async function saveDraft() {
    if (!draft) return;
    setBusy("save");
    try { await createStyle(draft); setDraft(null); await load(); }
    catch (e) { alert(e instanceof Error ? e.message : "Lưu style lỗi"); }
    finally { setBusy(""); }
  }
  async function remove(s: StyleItem) {
    if (!confirm(`Xoá phong cách "${s.name?.en || s.label}"?`)) return;
    setBusy(s.id);
    try { await deleteStyle(s.id); await load(); }
    catch (e) { alert(e instanceof Error ? e.message : "Xoá lỗi"); }
    finally { setBusy(""); }
  }

  const custom = styles.filter((s) => s.source === "user");
  const builtin = styles.filter((s) => s.source !== "user");

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800 }}>Tạo phong cách từ ảnh</h2>
          <div style={{ fontSize: 12, color: "var(--gray-5)", marginTop: 2 }}>Tải 1 ảnh thiết kế/mockup → AI trích màu, font, bố cục thành style dùng được.</div>
        </div>
        <label className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
          {busy === "parse" ? <Loader2 size={14} className="spin" /> : <ImageIcon size={14} />}
          {busy === "parse" ? "Đang phân tích…" : "Tải ảnh"}
          <input type="file" accept="image/*" hidden disabled={!!busy}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImage(f); }} />
        </label>
      </div>

      {draft && (
        <div style={{ background: "rgba(249,115,22,0.08)", border: "1px solid var(--accent)", borderRadius: 12, padding: 16, marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)", marginBottom: 8 }}>BẢN NHÁP STYLE — kiểm tra rồi lưu</div>
          <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            style={fieldInput} placeholder="Tên style" />
          <textarea value={draft.styleSkill || ""} onChange={(e) => setDraft({ ...draft, styleSkill: e.target.value })} rows={5}
            style={{ ...fieldInput, marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 12 }} placeholder="Design spec (SKILL.md)" />
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button onClick={saveDraft} disabled={busy === "save"} className="btn-primary" style={{ fontSize: 12 }}>{busy === "save" ? "Đang lưu…" : "Lưu style"}</button>
            <button onClick={() => setDraft(null)} className="btn-ghost" style={{ fontSize: 12 }}>Huỷ</button>
          </div>
        </div>
      )}

      {custom.length > 0 && (
        <>
          <div style={{ ...sectionLabel }}>Style của bạn ({custom.length})</div>
          <div style={grid}>{custom.map((s) => <StyleCardMini key={s.id} s={s} onDelete={() => remove(s)} deleting={busy === s.id} />)}</div>
        </>
      )}
      <div style={{ ...sectionLabel, marginTop: custom.length ? 24 : 0 }}>Style có sẵn ({builtin.length})</div>
      <div style={grid}>{builtin.map((s) => <StyleCardMini key={s.id} s={s} />)}</div>
    </div>
  );
}

function StyleCardMini({ s, onDelete, deleting }: { s: StyleItem; onDelete?: () => void; deleting?: boolean }) {
  return (
    <div style={{ borderRadius: 12, overflow: "hidden", border: "1px solid var(--gray-3)", background: "rgba(255,255,255,0.03)", position: "relative" }}>
      <div style={{ aspectRatio: "16/9", background: "#0b0b12", overflow: "hidden", position: "relative" }}>
        <iframe src={stylePreviewUrl(s.styleKey)} title={s.label} scrolling="no" style={{ position: "absolute", top: 0, left: 0, width: 1600, height: 900, border: "none", transform: "scale(0.166)", transformOrigin: "top left" }} />
      </div>
      <div style={{ padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name?.en || s.label}</span>
        {onDelete && <button onClick={onDelete} disabled={deleting} title="Xoá" style={{ flexShrink: 0, background: "transparent", border: "none", color: "#ef4444", cursor: "pointer" }}><Trash2 size={14} /></button>}
      </div>
    </div>
  );
}

/* ── Font ────────────────────────────────────────────────────────────── */
function FontManager() {
  const [google, setGoogle] = useState<FontItem[]>([]);
  const [user, setUser] = useState<FontItem[]>([]);
  const [family, setFamily] = useState("");
  const [busy, setBusy] = useState("");

  async function load() { const d = await getFonts().catch(() => ({ googleFonts: [], userFonts: [] })); setGoogle(d.googleFonts || []); setUser(d.userFonts || []); }
  useEffect(() => { load(); }, []);

  async function handleFile(file: File) {
    if (!family.trim()) { alert("Nhập tên font (family) trước."); return; }
    setBusy("up");
    try { await uploadFont(family.trim(), file); setFamily(""); await load(); }
    catch (e) { alert(e instanceof Error ? e.message : "Upload font lỗi"); }
    finally { setBusy(""); }
  }
  async function remove(f: FontItem) {
    if (!confirm(`Xoá font "${f.family}"?`)) return;
    setBusy(f.id);
    try { await deleteFont(f.id); await load(); }
    catch (e) { alert(e instanceof Error ? e.message : "Xoá lỗi"); }
    finally { setBusy(""); }
  }

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 4 }}>Font chữ</h2>
      <div style={{ fontSize: 12, color: "var(--gray-5)", marginBottom: 16 }}>Tải font .woff2/.ttf/.otf của bạn để dùng khi tạo slide.</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        <input value={family} onChange={(e) => setFamily(e.target.value)} placeholder="Tên font (VD: My Brand Sans)" style={{ ...fieldInput, width: 280, marginTop: 0 }} />
        <label className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
          {busy === "up" ? <Loader2 size={14} className="spin" /> : <Upload size={14} />}
          {busy === "up" ? "Đang tải…" : "Tải font"}
          <input type="file" accept=".woff2,.ttf,.otf,.woff" hidden disabled={!!busy}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
        </label>
      </div>

      {user.length > 0 && <>
        <div style={sectionLabel}>Font của bạn ({user.length})</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 24 }}>
          {user.map((f) => (
            <div key={f.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)", border: "1px solid var(--gray-2)" }}>
              <span style={{ fontSize: 14 }}>{f.family}</span>
              <button onClick={() => remove(f)} disabled={busy === f.id} style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer" }}><Trash2 size={15} /></button>
            </div>
          ))}
        </div>
      </>}
      <div style={sectionLabel}>Google Fonts có sẵn ({google.length})</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 8 }}>
        {google.map((f) => <div key={f.id} style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)", border: "1px solid var(--gray-2)", fontSize: 13 }}>{f.family}</div>)}
      </div>
    </div>
  );
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

const fieldInput: CSSProperties = { width: "100%", background: "rgba(255,255,255,0.04)", border: "1px solid var(--gray-3)", borderRadius: 8, color: "var(--white)", fontSize: 13, padding: "10px 12px", fontFamily: "inherit" };
const sectionLabel: CSSProperties = { fontSize: 11, fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 10 };
const grid: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 12 };
