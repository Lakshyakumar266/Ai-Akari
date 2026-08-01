import * as THREE from "three";
import {
  type GLTF,
  GLTFLoader,
} from "three/examples/jsm/loaders/GLTFLoader.js";
import type { VRM } from "@pixiv/three-vrm";
import {
  VRMAnimation,
  VRMAnimationLoaderPlugin,
  createVRMAnimationClip,
} from "@pixiv/three-vrm-animation";

import { ANIMATIONS, type AnimationName } from "./types";

export class AnimationController {
  private loader: GLTFLoader;
  private actions = new Map<
    AnimationName,
    THREE.AnimationAction
  >();
  private loading = new Set<AnimationName>();
  private currentAction: THREE.AnimationAction | null =
    null;
  private vrm: VRM;
  private mixer: THREE.AnimationMixer;

  constructor(vrm: VRM, mixer: THREE.AnimationMixer) {
    this.vrm = vrm;
    this.mixer = mixer;
    this.loader = new GLTFLoader();
    this.loader.register(
      (parser) =>
        new VRMAnimationLoaderPlugin(parser)
    );
  }

  update(delta: number) {
    this.mixer.update(delta);
  }

  async load(
    name: AnimationName
  ): Promise<THREE.AnimationAction | null> {
    const cached = this.actions.get(name);
    if (cached) return cached;

    if (this.loading.has(name)) return null;

    this.loading.add(name);

    try {
      const gltf = (await this.loader.loadAsync(
        ANIMATIONS[name]
      )) as GLTF;

      const vrmAnimation =
        gltf.userData.vrmAnimations?.[0] as VRMAnimation;

      const clip = createVRMAnimationClip(
        vrmAnimation,
        this.vrm
      );

      const action = this.mixer.clipAction(clip);

      action.enabled = true;
      action.loop = THREE.LoopRepeat;
      action.clampWhenFinished = false;

      this.actions.set(name, action);

      return action;
    } finally {
      this.loading.delete(name);
    }
  }

  async play(name: AnimationName, instant = false) {
    const action = await this.load(name);
    if (!action) return;

    if (this.currentAction === action) return;

    if (instant) {
      this.currentAction?.stop();
      action.reset().play();
      this.currentAction = action;
      return;
    }

    this.currentAction?.fadeOut(0.25);

    action
      .reset()
      .setEffectiveWeight(1)
      .setEffectiveTimeScale(1)
      .fadeIn(0.25)
      .play();

    this.currentAction = action;
  }

  stop(fadeDuration = 0.25) {
    this.currentAction?.fadeOut(fadeDuration);
    this.currentAction?.stop();
    this.currentAction = null;
  }
}
