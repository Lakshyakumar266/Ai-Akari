import * as THREE from "three";
import type { VRM } from "@pixiv/three-vrm";

export class LookAtController {
  private isEnabled = true;
  private readonly lookTarget = new THREE.Vector3();

  update(vrm: VRM): void {
    if (!this.isEnabled || !vrm.lookAt) return;
    vrm.lookAt.lookAt(this.lookTarget);
  }

  setTarget(position: THREE.Vector3): void {
    this.lookTarget.copy(position);
  }

  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }
}

/**
 * Gaze & LookAt Controller
 * Directs the avatar's eye and head gaze toward specified 3D camera coordinates.
 */
