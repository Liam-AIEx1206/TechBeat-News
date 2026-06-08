"use client";

import { useState } from "react";
import type { Scene } from "@/types/scene";
import { ImagePicker } from "./ImagePicker";

interface Props {
  scene: Scene;
  onUpdate: (updated: Scene) => void;
  onDelete: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export function SceneCard({ scene, onUpdate, onDelete, onMoveUp, onMoveDown, isFirst, isLast }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft]     = useState<Scene>(scene);
  const [pickerOpen, setPickerOpen] = useState(false);

  function save()   { onUpdate(draft); setEditing(false); }
  function cancel() { setDraft(scene); setEditing(false); }

  const pickerQuery = scene.imageQuery?.trim() || scene.title;

  if (editing) {
    return (
      <div className="scene-card" style={{ borderColor: "rgba(249,115,22,0.4)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <span className="badge badge-accent">Scene {scene.index + 1}</span>
          <input className="input-dark" style={{ flex: 1, fontSize: 13, fontWeight: 700, padding: "8px 14px" }}
            value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            placeholder="Tiêu đề phân cảnh" />
        </div>

        {[
          { label: "Lời dẫn (narration)", key: "narration" as const, rows: 3 },
          { label: "Mô tả hình ảnh", key: "visualDescription" as const, rows: 2 },
        ].map(({ label, key, rows }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <div className="field-label" style={{ marginBottom: 8 }}>{label}</div>
            <textarea rows={rows} className="input-dark" style={{ resize: "none", fontSize: 13 }}
              value={draft[key]} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
          </div>
        ))}

        <div style={{ marginBottom: 12 }}>
          <div className="field-label" style={{ marginBottom: 8 }}>Từ khóa tìm ảnh</div>
          <input className="input-dark" style={{ fontSize: 13 }}
            value={draft.imageQuery ?? ""}
            onChange={(e) => setDraft({ ...draft, imageQuery: e.target.value })}
            placeholder="VD: AI chip nvidia datacenter" />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 11, color: "var(--gray-5)", fontStyle: "italic" }}>
            Thời lượng sẽ tính tự động theo audio sau khi build
          </div>
          <div style={{ flex: 1 }} />
          <button onClick={cancel} className="btn-ghost" style={{ fontSize: 12 }}>Huỷ</button>
          <button onClick={save} className="btn-primary" style={{ fontSize: 12, padding: "8px 18px" }}>
            <span>Lưu</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="scene-card group">
        <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
          {/* Index */}
          <div style={{
            flexShrink: 0, width: 36, height: 36, borderRadius: "var(--r-sm)",
            background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 13, fontWeight: 900, color: "var(--black)",
          }}>
            {scene.index + 1}
          </div>

          {/* Thumbnail */}
          <button onClick={() => setPickerOpen(true)}
            style={{
              flexShrink: 0, width: 72, height: 72, borderRadius: "var(--r-sm)",
              background: "var(--gray-2)", border: "1px solid var(--gray-3)",
              overflow: "hidden", position: "relative", transition: "border-color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(249,115,22,0.5)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--gray-3)")}
            title={scene.imageUrl ? "Thay ảnh" : "Chọn ảnh"}>
            {scene.imageUrl ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={scene.imageUrl} alt={scene.title} style={{ width: "100%", height: "100%", objectFit: "cover" }} referrerPolicy="no-referrer" />
                <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", opacity: 0, transition: "opacity 0.2s" }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = "0")}>
                  <span style={{ fontSize: 9, fontWeight: 800, color: "var(--white)", background: "var(--accent)", padding: "3px 8px", borderRadius: 99 }}>Đổi</span>
                </div>
              </>
            ) : (
              <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--gray-4)" }}>
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <span style={{ fontSize: 8, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--gray-4)" }}>Ảnh</span>
              </div>
            )}
          </button>

          {/* Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ marginBottom: 6 }}>
              <h3 style={{ fontSize: 13, fontWeight: 800, lineHeight: 1.3, color: "var(--white)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {scene.title}
              </h3>
            </div>
            <p style={{ fontSize: 12, color: "var(--gray-5)", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", marginBottom: 4 }}>
              {scene.narration}
            </p>
            <p style={{ fontSize: 11, color: "var(--gray-4)", display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              <span style={{ color: "rgba(249,115,22,0.5)", fontWeight: 700 }}>Visual: </span>
              {scene.visualDescription}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 6, marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--gray-3)" }}>
          {onMoveUp && <button onClick={onMoveUp} disabled={isFirst} className="btn-ghost" style={{ fontSize: 11, padding: "5px 10px", opacity: isFirst ? 0.3 : 1 }}>↑</button>}
          {onMoveDown && <button onClick={onMoveDown} disabled={isLast} className="btn-ghost" style={{ fontSize: 11, padding: "5px 10px", opacity: isLast ? 0.3 : 1 }}>↓</button>}
          <button onClick={() => setPickerOpen(true)} className="btn-ghost" style={{ fontSize: 11, padding: "5px 12px", display: "inline-flex", alignItems: "center", gap: 4 }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            Ảnh
          </button>
          <button onClick={() => { setDraft(scene); setEditing(true); }} className="btn-ghost" style={{ fontSize: 11, padding: "5px 12px", display: "inline-flex", alignItems: "center", gap: 4 }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            Sửa
          </button>
          <button onClick={onDelete} style={{ fontSize: 11, padding: "5px 12px", borderRadius: "var(--r)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--red)", background: "transparent", fontWeight: 700, transition: "background 0.2s", display: "inline-flex", alignItems: "center", gap: 4 }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(239,68,68,0.08)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Xoá
          </button>
        </div>
      </div>

      <ImagePicker open={pickerOpen} initialQuery={pickerQuery}
        onClose={() => setPickerOpen(false)}
        onPick={(url) => onUpdate({ ...scene, imageUrl: url })} />
    </>
  );
}
