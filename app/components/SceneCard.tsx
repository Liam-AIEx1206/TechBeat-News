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

export function SceneCard({
  scene,
  onUpdate,
  onDelete,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Scene>(scene);
  const [pickerOpen, setPickerOpen] = useState(false);

  function save() {
    onUpdate(draft);
    setEditing(false);
  }

  function cancel() {
    setDraft(scene);
    setEditing(false);
  }

  const pickerQuery = scene.imageQuery?.trim() || scene.title;

  if (editing) {
    return (
      <div className="glass-strong rounded-2xl p-5 space-y-3 ring-2 ring-orange-400/40">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black text-white bg-gradient-to-br from-orange-500 to-orange-600 px-2.5 py-1 rounded-full uppercase tracking-wider">
            Phân cảnh {scene.index + 1}
          </span>
          <input
            className="flex-1 text-sm font-bold bg-transparent border-b-2 border-orange-300 focus:outline-none focus:border-orange-500 py-1"
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            placeholder="Tiêu đề phân cảnh"
          />
        </div>

        <div>
          <label className="text-[10px] font-bold text-stone-500 uppercase tracking-wider mb-1 block">
            Lời dẫn (narration)
          </label>
          <textarea
            rows={3}
            className="w-full text-sm bg-white/70 border border-orange-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:border-orange-400 resize-none"
            value={draft.narration}
            onChange={(e) => setDraft({ ...draft, narration: e.target.value })}
          />
        </div>

        <div>
          <label className="text-[10px] font-bold text-stone-500 uppercase tracking-wider mb-1 block">
            Mô tả hình ảnh
          </label>
          <textarea
            rows={2}
            className="w-full text-sm bg-white/70 border border-orange-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:border-orange-400 resize-none"
            value={draft.visualDescription}
            onChange={(e) => setDraft({ ...draft, visualDescription: e.target.value })}
          />
        </div>

        <div>
          <label className="text-[10px] font-bold text-stone-500 uppercase tracking-wider mb-1 block">
            Từ khóa tìm ảnh (image query)
          </label>
          <input
            className="w-full text-sm bg-white/70 border border-orange-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:border-orange-400"
            value={draft.imageQuery ?? ""}
            onChange={(e) => setDraft({ ...draft, imageQuery: e.target.value })}
            placeholder="VD: AI chip nvidia datacenter"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-[10px] font-bold text-stone-500 uppercase tracking-wider">Thời lượng</label>
            <input
              type="number"
              min={3}
              max={60}
              className="w-16 text-sm bg-white border border-orange-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-orange-500/40 text-center font-semibold"
              value={draft.duration}
              onChange={(e) => setDraft({ ...draft, duration: Number(e.target.value) })}
            />
            <span className="text-xs text-stone-500">giây</span>
          </div>
          <div className="flex-1" />
          <button
            onClick={cancel}
            className="text-sm px-3 py-1.5 rounded-xl border border-stone-200 text-stone-600 hover:bg-stone-50 font-medium transition-colors"
          >
            Huỷ
          </button>
          <button
            onClick={save}
            className="btn-glow text-sm px-4 py-1.5 rounded-xl text-white font-bold"
          >
            Lưu
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="glass rounded-2xl p-4 group hover:shadow-lg hover:shadow-orange-500/20 transition-all duration-300">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-black text-base shadow-md shadow-orange-500/30">
            {scene.index + 1}
          </div>

          <button
            onClick={() => setPickerOpen(true)}
            className="relative flex-shrink-0 w-24 h-24 rounded-xl overflow-hidden ring-1 ring-orange-200/60 hover:ring-2 hover:ring-orange-500 transition-all bg-gradient-to-br from-orange-100 to-amber-100 group/img"
            title={scene.imageUrl ? "Thay ảnh khác" : "Chọn ảnh minh họa"}
          >
            {scene.imageUrl ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={scene.imageUrl}
                  alt={scene.title}
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                />
                <div className="absolute inset-0 bg-stone-900/50 opacity-0 group-hover/img:opacity-100 flex items-center justify-center transition-opacity">
                  <span className="text-[10px] font-bold text-white bg-orange-600 px-2 py-1 rounded-full">
                    Đổi ảnh
                  </span>
                </div>
              </>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center gap-1 text-orange-700">
                <span className="text-2xl">🖼️</span>
                <span className="text-[9px] font-bold uppercase tracking-wider">
                  Chọn ảnh
                </span>
              </div>
            )}
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="text-sm font-bold text-stone-900 leading-tight line-clamp-2">
                {scene.title}
              </h3>
              <span className="flex-shrink-0 text-[10px] font-bold text-orange-700 bg-orange-100/80 px-2 py-0.5 rounded-full uppercase tracking-wider">
                {scene.duration}s
              </span>
            </div>
            <p className="text-xs text-stone-700 mb-2 leading-relaxed line-clamp-3">
              {scene.narration}
            </p>
            <p className="text-[11px] text-stone-400 italic line-clamp-2 leading-snug">
              <span className="font-semibold text-orange-600/70 not-italic">Visual:</span>{" "}
              {scene.visualDescription}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-1.5 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
          {onMoveUp && (
            <button
              onClick={onMoveUp}
              disabled={isFirst}
              className="text-[11px] font-semibold w-7 h-7 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Lên"
            >
              ↑
            </button>
          )}
          {onMoveDown && (
            <button
              onClick={onMoveDown}
              disabled={isLast}
              className="text-[11px] font-semibold w-7 h-7 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Xuống"
            >
              ↓
            </button>
          )}
          <button
            onClick={() => setPickerOpen(true)}
            className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors"
          >
            🖼 Ảnh
          </button>
          <button
            onClick={() => { setDraft(scene); setEditing(true); }}
            className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors"
          >
            ✎ Sửa
          </button>
          <button
            onClick={onDelete}
            className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-red-100 text-red-500 hover:bg-red-50 transition-colors"
          >
            ✕ Xoá
          </button>
        </div>
      </div>

      <ImagePicker
        open={pickerOpen}
        initialQuery={pickerQuery}
        onClose={() => setPickerOpen(false)}
        onPick={(url) => onUpdate({ ...scene, imageUrl: url })}
      />
    </>
  );
}
