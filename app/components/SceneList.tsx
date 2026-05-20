"use client";

import { SceneCard } from "./SceneCard";
import type { Scene, ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onChange: (plan: ScenePlan) => void;
}

function emptyScene(index: number): Scene {
  return { id: `scene-${Date.now()}-${index}`, index, title: "Phân cảnh mới", narration: "", visualDescription: "", duration: 8 };
}
function reindex(scenes: Scene[]): Scene[] { return scenes.map((s, i) => ({ ...s, index: i })); }
function totalOf(scenes: Scene[]): number  { return scenes.reduce((sum, s) => sum + s.duration, 0); }

export function SceneList({ scenePlan, onChange }: Props) {
  function commit(scenes: Scene[]) {
    const r = reindex(scenes);
    onChange({ ...scenePlan, scenes: r, totalDuration: totalOf(r) });
  }

  return (
    <div>
      {/* Stats bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 24, paddingBottom: 20, borderBottom: "1px solid var(--gray-3)" }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 4 }}>Phân cảnh</div>
          <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--white)" }}>{scenePlan.scenes.length}</div>
        </div>
        <div style={{ width: 1, height: 40, background: "var(--gray-3)" }} />
        <div>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 4 }}>Thời lượng</div>
          <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--accent)" }}>{scenePlan.totalDuration}s</div>
        </div>
        <div style={{ width: 1, height: 40, background: "var(--gray-3)" }} />
        <div>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gray-5)", marginBottom: 4 }}>Độ phân giải</div>
          <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--white)" }}>1080p</div>
        </div>
      </div>

      {/* Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 12, marginBottom: 20 }}>
        {scenePlan.scenes.map((scene, i) => (
          <div key={scene.id} className="fade-up" style={{ animationDelay: `${i * 40}ms` }}>
            <SceneCard
              scene={scene}
              onUpdate={(u) => commit(scenePlan.scenes.map((s, j) => j === i ? u : s))}
              onDelete={() => commit(scenePlan.scenes.filter((_, j) => j !== i))}
              onMoveUp={() => {
                if (i === 0) return;
                const n = [...scenePlan.scenes]; [n[i], n[i-1]] = [n[i-1], n[i]]; commit(n);
              }}
              onMoveDown={() => {
                if (i === scenePlan.scenes.length - 1) return;
                const n = [...scenePlan.scenes]; [n[i], n[i+1]] = [n[i+1], n[i]]; commit(n);
              }}
              isFirst={i === 0}
              isLast={i === scenePlan.scenes.length - 1}
            />
          </div>
        ))}
      </div>

      {/* Add scene */}
      <div style={{ display: "flex", justifyContent: "center" }}>
        <button
          onClick={() => commit([...scenePlan.scenes, emptyScene(scenePlan.scenes.length)])}
          className="btn-ghost"
          style={{ borderStyle: "dashed", borderColor: "rgba(249,115,22,0.25)", color: "var(--accent2)", fontSize: 12, padding: "10px 24px" }}
        >
          <span style={{ fontSize: 16, fontWeight: 900, marginRight: 4 }}>+</span> Thêm phân cảnh
        </button>
      </div>
    </div>
  );
}
