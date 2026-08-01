import type { VRM } from "@pixiv/three-vrm";

const BREATH_FREQUENCY = 1.4;
const BREATH_AMPLITUDE = 0.015;

export class BreathingController {
  private phase = 0;

  update(delta: number, vrm: VRM): void {
    this.phase += delta;

    const chestBone = vrm.humanoid?.getNormalizedBoneNode("chest");
    if (!chestBone) return;

    chestBone.rotation.x = Math.sin(this.phase * BREATH_FREQUENCY) * BREATH_AMPLITUDE;
  }
}

/**
 * Procedural Breathing Controller
 * Produces subtle chest oscillation when the VRM rig exposes a normalized chest humanoid bone.
 */
