"use client";

import { useState, useRef, DragEvent } from "react";

interface Props {
  onExtracted: (content: { title: string; text: string; source: string }) => void;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
  setError: (v: string) => void;
}

export function InputPanel({ onExtracted, isLoading, setIsLoading, setError }: Props) {
  const [url, setUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function extractUrl() {
    if (!url.trim()) return;
    setIsLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/extract/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Trích xuất thất bại");
      }
      const data = await res.json();
      onExtracted(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể trích xuất URL");
    } finally {
      setIsLoading(false);
    }
  }

  async function extractFile(file: File) {
    setIsLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/extract/file`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Trích xuất thất bại");
      }
      const data = await res.json();
      onExtracted(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể trích xuất file");
    } finally {
      setIsLoading(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) extractFile(file);
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="text-[11px] font-bold text-orange-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <span>🔗</span> Dán URL bài viết
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && extractUrl()}
            placeholder="https://example.com/article"
            disabled={isLoading}
            className="flex-1 px-4 py-3 rounded-xl bg-white/80 border border-orange-200/60 text-sm placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:border-orange-400 disabled:opacity-50 transition-all"
          />
          <button
            onClick={extractUrl}
            disabled={isLoading || !url.trim()}
            className="btn-glow px-5 py-3 rounded-xl text-white text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isLoading ? "..." : "Trích xuất"}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 text-stone-400 text-xs">
        <span className="flex-1 border-t border-orange-200/60" />
        <span className="font-medium">hoặc tải lên file</span>
        <span className="flex-1 border-t border-orange-200/60" />
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !isLoading && fileRef.current?.click()}
        className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
          dragging
            ? "border-orange-500 bg-orange-50/80 scale-[1.01]"
            : "border-orange-300/60 bg-white/40 hover:border-orange-400 hover:bg-orange-50/50"
        } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.pptx,.xlsx,.odt,.odp"
          className="hidden"
          disabled={isLoading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) extractFile(file);
            e.target.value = "";
          }}
        />
        <div className="text-4xl mb-3">📄</div>
        <p className="text-sm font-bold text-stone-800 mb-1">
          Kéo file vào đây hoặc click để chọn
        </p>
        <p className="text-xs text-stone-500">
          Hỗ trợ <span className="font-semibold text-orange-700">PDF</span> (OCR),{" "}
          <span className="font-semibold text-orange-700">DOCX</span>,{" "}
          <span className="font-semibold text-orange-700">PPTX</span>
        </p>
      </div>
    </div>
  );
}
