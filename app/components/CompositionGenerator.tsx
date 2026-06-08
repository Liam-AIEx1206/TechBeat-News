"use client";

import { useState, useRef } from "react";
import type { ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onBack: () => void;
}

type Status = "idle" | "generating" | "ready" | "saving" | "saved" | "error";

export function CompositionGenerator({ scenePlan, onBack }: Props) {
  const [status, setStatus] = useState<Status>("idle");
  const [streamBuffer, setStreamBuffer] = useState("");
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");
  const [savedInfo, setSavedInfo] = useState<{ path: string; next: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function generate() {
    setStatus("generating");
    setStreamBuffer("");
    setHtml("");
    setError("");
    setSavedInfo(null);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const endpoint = process.env.NODE_ENV === "development"
        ? `${API}/generate-composition`
        : `/api/proxy/generate-composition`;
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scenePlan),
        signal: abort.signal,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Composition generation failed");
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalHtml = "";

      function processLines(raw: string) {
        const lines = raw.split("\n\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let event: { type: string; text?: string; html?: string; message?: string };
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (event.type === "chunk" && event.text) {
            setStreamBuffer((prev) => prev + event.text);
          } else if (event.type === "done" && event.html) {
            finalHtml = event.html;
          } else if (event.type === "error") {
            throw new Error(event.message ?? "Unknown error");
          }
        }
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buf.trim()) processLines(buf);
          break;
        }
        buf += decoder.decode(value, { stream: true });
        const split = buf.split("\n\n");
        buf = split.pop() ?? "";
        processLines(split.join("\n\n") + "\n\n");
      }

      if (finalHtml) {
        setHtml(finalHtml);
        setStatus("ready");
      } else {
        throw new Error("Không nhận được HTML hoàn chỉnh");
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Generation failed");
      setStatus("error");
    }
  }

  async function save() {
    if (!html) return;
    setStatus("saving");
    setError("");
    try {
      const res = await fetch(`${API}/save-composition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html, sessionId: scenePlan.sessionId }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Save failed");
      }
      const data = await res.json();
      setSavedInfo({ path: data.path, next: data.next });
      setStatus("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
      setStatus("error");
    }
  }

  function download() {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "index.html";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (status === "idle") {
    return (
      <div className="bg-white rounded-2xl border border-orange-100 p-8 shadow-sm shadow-orange-500/5">
        <div className="text-center max-w-md mx-auto">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-orange-500/30">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-stone-900 mb-2">
            Sẵn sàng sinh composition
          </h2>
          <p className="text-sm text-stone-500 mb-6">
            AI sẽ chuyển scene plan thành file HyperFrames HTML hoàn chỉnh — bao gồm GSAP timeline, layout, animation và các điểm gắn audio narration.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={onBack}
              className="px-5 py-2.5 rounded-lg border border-stone-200 text-stone-600 text-sm font-medium hover:bg-stone-50 transition-colors inline-flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg> Back to scenes
            </button>
            <button
              onClick={generate}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 text-white text-sm font-semibold hover:from-orange-600 hover:to-orange-700 transition-all shadow-sm shadow-orange-500/30 inline-flex items-center gap-2"
            >
              Generate Composition <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === "generating") {
    return (
      <div className="bg-white rounded-2xl border border-orange-100 p-8 shadow-sm">
        <div className="text-center mb-6">
          <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-stone-900 mb-1">
            Đang sinh composition HTML...
          </h2>
          <p className="text-xs text-stone-500">
            Gemini đang viết GSAP timeline + layout cho {scenePlan.scenes.length} scene
          </p>
        </div>
        {streamBuffer && (
          <div className="bg-stone-900 text-orange-300 rounded-xl p-4 max-h-96 overflow-auto">
            <pre className="text-xs font-mono whitespace-pre-wrap break-all">
              {streamBuffer.slice(-3000)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {savedInfo && (
        <div className="px-4 py-3 bg-orange-50 border border-orange-200 rounded-xl">
          <p className="text-sm font-semibold text-orange-900 mb-1 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Đã ghi vào my-video/index.html
          </p>
          <p className="text-xs text-stone-600 mb-2 font-mono break-all">{savedInfo.path}</p>
          <p className="text-xs text-stone-700 mb-1">Bước tiếp theo, mở terminal và chạy:</p>
          <code className="block text-xs bg-stone-900 text-orange-300 px-3 py-2 rounded-lg font-mono break-all">
            {savedInfo.next}
          </code>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-orange-100 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-medium text-orange-600 uppercase tracking-wide mb-0.5">
              {status === "saved" ? "Saved & Ready" : "Composition Ready"}
            </p>
            <p className="text-sm font-semibold text-stone-900">{scenePlan.title}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onBack}
              className="text-sm px-3 py-1.5 rounded-lg border border-stone-200 text-stone-600 hover:bg-stone-50 transition-colors inline-flex items-center gap-1.5"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg> Back
            </button>
            <button
              onClick={generate}
              className="text-sm px-3 py-1.5 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors"
            >
              Regenerate
            </button>
            <button
              onClick={download}
              className="text-sm px-3 py-1.5 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50 transition-colors"
            >
              Download .html
            </button>
            <button
              onClick={save}
              disabled={status === "saving"}
              className="text-sm px-4 py-1.5 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 text-white font-medium hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 transition-all shadow-sm shadow-orange-500/30"
            >
              {status === "saving" ? "Saving..." : "Save to my-video/"}
            </button>
          </div>
        </div>

        <div className="rounded-xl overflow-hidden border border-orange-100 bg-stone-50">
          <iframe
            srcDoc={html}
            sandbox="allow-scripts"
            className="w-full bg-black"
            style={{ height: "540px", aspectRatio: "16 / 9" }}
            title="Composition preview"
          />
        </div>
      </div>
    </div>
  );
}
