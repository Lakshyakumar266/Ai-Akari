import type { VRM } from "@pixiv/three-vrm";

import { EMOTIONS, type EmotionName } from "./types";

const ALL_EXPRESSION_KEYS = [
  ...new Set(
    Object.values(EMOTIONS).flatMap((preset) =>
      Object.keys(preset)
    )
  ),
];

export class EmotionController {
  private current: EmotionName = "Neutral";
  private readonly lerpSpeed = 4;

  setEmotion(name: EmotionName) {
    this.current = name;
  }

  update(delta: number, vrm: VRM) {
    const manager = vrm.expressionManager;
    if (!manager) return;

    const target = EMOTIONS[this.current];
    const step = Math.min(1, delta * this.lerpSpeed);

    for (const name of ALL_EXPRESSION_KEYS) {
      const desired =
        target[name as keyof typeof target] ?? 0;
      const current = manager.getValue(name) ?? 0;
      const next =
        current + (desired - current) * step;

      manager.setValue(name, next);
    }
  }
}
