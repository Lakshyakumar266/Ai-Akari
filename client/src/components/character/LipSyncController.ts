import type { VRM } from "@pixiv/three-vrm";

import {
  VISEME_EXPRESSIONS,
  type VisemeName,
} from "./types";

export class LipSyncController {
  private weights: Record<VisemeName, number> = {
    aa: 0,
    ih: 0,
    ou: 0,
    ee: 0,
    oh: 0,
  };

  private enabled = false;

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
    if (!enabled) {
      this.reset();
    }
  }

  setViseme(name: VisemeName, weight: number) {
    if (!(name in this.weights)) return;
    this.weights[name] = Math.max(0, Math.min(1, weight));
  }

  /** Drive visemes from a single loudness value (0–1). */
  setFromVolume(volume: number) {
    const v = Math.max(0, Math.min(1, volume));
    this.setViseme("aa", v * 0.85);
    this.setViseme("oh", v * 0.35);
  }

  reset() {
    for (const key of VISEME_EXPRESSIONS) {
      this.weights[key] = 0;
    }
  }

  update(vrm: VRM) {
    if (!this.enabled) return;

    const manager = vrm.expressionManager;
    if (!manager) return;

    for (const name of VISEME_EXPRESSIONS) {
      manager.setValue(name, this.weights[name]);
    }
  }
}
