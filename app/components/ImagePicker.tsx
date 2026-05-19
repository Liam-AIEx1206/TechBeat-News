"use client";

import { useEffect, useRef, useState } from "react";

interface ImageResult {
  image: string;
  thumbnail: string;
  title: string;
  source: string;
  url: string;
  width?: number;
  height?: number;
}

interface Props {
  open: boolean;
  initialQuery: string;
  onClose: () => void;
  onPick: (url: string) => void;
}

export function ImagePicker({ open, initialQuery, onClose, onPick }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<ImageResult[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    if (open) {
      setQuery(initialQuery);
      setResults([]);
      setError("");
      // auto-search on open
      if (initialQuery.trim()) {
        runSearch(initialQuery);
      }
    }
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialQuery]);

  async function runSearch(q: string) {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API}/image-search?q=${encodeURIComponent(q)}&limit=18`,
        { signal: ac.signal },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResults(data.results ?? []);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Tìm ảnh thất bại");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/60 backdrop-blur-sm fade-up">
      <div className="glass-strong rounded-3xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-orange-200/40 flex items-center gap-3 flex-wrap">
          <div className="flex-1 min-w-[240px]">
            <p className="text-[10px] font-black text-orange-700 uppercase tracking-widest mb-0.5">
              Chọn ảnh minh họa · DuckDuckGo
            </p>
            <h3 className="text-base font-bold text-stone-900">Tìm ảnh phù hợp với phân cảnh</h3>
          </div>
          <button
            onClick={onClose}
            className="text-sm px-3 py-1.5 rounded-xl border border-stone-200 text-stone-600 hover:bg-stone-50 font-medium"
          >
            Đóng
          </button>
        </div>

        <div className="px-6 py-3 border-b border-orange-200/40 flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") runSearch(query);
            }}
            placeholder="Từ khóa tìm ảnh..."
            className="flex-1 text-sm bg-white/70 border border-orange-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:border-orange-400"
          />
          <button
            onClick={() => runSearch(query)}
            disabled={loading || !query.trim()}
            className="btn-glow text-sm px-4 py-2 rounded-xl text-white font-bold disabled:opacity-50"
          >
            {loading ? "Đang tìm..." : "Tìm"}
          </button>
        </div>

        <div className="flex-1 overflow-auto p-5">
          {error && (
            <div className="mb-3 px-4 py-3 bg-red-50/80 border border-red-200 rounded-xl text-sm text-red-700">
              ⚠ {error}
            </div>
          )}

          {loading && results.length === 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="aspect-square rounded-xl bg-orange-100/50 animate-pulse"
                />
              ))}
            </div>
          )}

          {!loading && results.length === 0 && !error && (
            <div className="text-center py-16 text-sm text-stone-400">
              Nhập từ khóa rồi bấm Tìm
            </div>
          )}

          {results.length > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {results.map((r, i) => (
                <button
                  key={r.image + i}
                  onClick={() => {
                    onPick(r.image);
                    onClose();
                  }}
                  className="group relative aspect-square rounded-xl overflow-hidden ring-1 ring-stone-200/60 hover:ring-2 hover:ring-orange-500 hover:scale-[1.03] transition-all bg-stone-100"
                  title={r.title}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={r.thumbnail}
                    alt={r.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    referrerPolicy="no-referrer"
                  />
                  <div className="absolute inset-x-0 bottom-0 px-2 py-1.5 bg-gradient-to-t from-stone-900/80 to-transparent text-[10px] text-white opacity-0 group-hover:opacity-100 transition-opacity truncate">
                    {r.source || r.title}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-orange-200/40 text-[11px] text-stone-500">
          Click vào ảnh để chọn. Ảnh sẽ tự động tải về và chèn vào video khi bấm Dựng.
        </div>
      </div>
    </div>
  );
}
