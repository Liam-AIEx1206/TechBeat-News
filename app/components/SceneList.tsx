"use client";

import { SceneCard } from "./SceneCard";
import type { Scene, ScenePlan } from "@/types/scene";

interface Props {
  scenePlan: ScenePlan;
  onChange: (plan: ScenePlan) => void;
}

function emptyScene(index: number): Scene {
  return {
    id: `scene-${Date.now()}-${index}`,
    index,
    title: "Phân cảnh mới",
    narration: "",
    visualDescription: "",
    duration: 8,
  };
}

function reindex(scenes: Scene[]): Scene[] {
  return scenes.map((s, i) => ({ ...s, index: i }));
}

function totalOf(scenes: Scene[]): number {
  return scenes.reduce((sum, s) => sum + s.duration, 0);
}

export function SceneList({ scenePlan, onChange }: Props) {
  function commit(scenes: Scene[]) {
    const reindexed = reindex(scenes);
    onChange({ ...scenePlan, scenes: reindexed, totalDuration: totalOf(reindexed) });
  }

  function updateScene(index: number, updated: Scene) {
    const next = scenePlan.scenes.map((s, i) => (i === index ? updated : s));
    commit(next);
  }

  function deleteScene(index: number) {
    commit(scenePlan.scenes.filter((_, i) => i !== index));
  }

  function move(index: number, dir: -1 | 1) {
    const target = index + dir;
    if (target < 0 || target >= scenePlan.scenes.length) return;
    const next = [...scenePlan.scenes];
    [next[index], next[target]] = [next[target], next[index]];
    commit(next);
  }

  function addScene() {
    const next = [...scenePlan.scenes, emptyScene(scenePlan.scenes.length)];
    commit(next);
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {scenePlan.scenes.map((scene, i) => (
          <div key={scene.id} className="fade-up" style={{ animationDelay: `${i * 60}ms` }}>
            <SceneCard
              scene={scene}
              onUpdate={(updated) => updateScene(i, updated)}
              onDelete={() => deleteScene(i)}
              onMoveUp={() => move(i, -1)}
              onMoveDown={() => move(i, 1)}
              isFirst={i === 0}
              isLast={i === scenePlan.scenes.length - 1}
            />
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <button
          onClick={addScene}
          className="text-sm px-5 py-3 rounded-2xl border-2 border-dashed border-orange-300 text-orange-700 hover:bg-orange-50 hover:border-orange-500 font-bold transition-all flex items-center gap-2"
        >
          <span className="text-lg">+</span>
          <span>Thêm phân cảnh</span>
        </button>
      </div>
    </div>
  );
}
