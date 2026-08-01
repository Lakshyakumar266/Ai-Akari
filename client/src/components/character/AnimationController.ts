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

import {
  ANIMATIONS,
  type AnimationName,
} from "./types";
import { PoseController } from "./PoseController";

export class AnimationController {
  private readonly vrm: VRM;
  private readonly mixer: THREE.AnimationMixer;
  private readonly pose: PoseController;
  private readonly loader = new GLTFLoader();

  private readonly actions = new Map<AnimationName, THREE.AnimationAction>();
  private readonly loading = new Set<AnimationName>();

  private current: THREE.AnimationAction | null = null;
  private next: THREE.AnimationAction | null = null;
  private readonly fadeDuration = 0.25;

  constructor(vrm: VRM, mixer: THREE.AnimationMixer, pose: PoseController) {
    this.vrm = vrm;
    this.mixer = mixer;
    this.pose = pose;

    this.loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
  }

  get currentAction(): THREE.AnimationAction | null {
    return this.current;
  }

  getCurrentAction(): THREE.AnimationAction | null {
    return this.current;
  }

  isPlaying(): boolean {
    return this.current !== null;
  }

  hasLoaded(name: AnimationName): boolean {
    return this.actions.has(name);
  }

  update(delta: number): void {
    this.mixer.update(delta);

    if (this.next) {
      this.current?.stop();
      this.current = this.next;
      this.next = null;
    }
  }

  async preload(name: AnimationName): Promise<void> {
    await this.load(name);
  }

  async preloadAll(): Promise<void> {
    const names = Object.keys(ANIMATIONS) as AnimationName[];
    for (const name of names) {
      await this.load(name);
    }
  }

  private async load(name: AnimationName): Promise<THREE.AnimationAction | null> {
    const cached = this.actions.get(name);
    if (cached) return cached;

    if (this.loading.has(name)) return null;
    this.loading.add(name);

    try {
      const gltf = (await this.loader.loadAsync(ANIMATIONS[name])) as GLTF;
      const animation = gltf.userData.vrmAnimations?.[0] as VRMAnimation | undefined;

      if (!animation) {
        console.warn(`[AnimationController] "${name}" contains no VRM animation.`);
        return null;
      }

      const clip = createVRMAnimationClip(animation, this.vrm);
      const action = this.mixer.clipAction(clip);

      action.enabled = true;
      action.loop = THREE.LoopRepeat;
      action.clampWhenFinished = false;
      action.setEffectiveWeight(1);

      this.actions.set(name, action);
      console.log("[AnimationController] Loaded animation:", name);
      return action;
    } finally {
      this.loading.delete(name);
    }
  }

  async play(name: AnimationName, instant = false): Promise<void> {
    const action = await this.load(name);
    if (!action || action === this.current) return;

    this.pose.clear();

    if (instant || !this.current) {
      this.current?.stop();
      action.reset();
      action.enabled = true;
      action.setEffectiveWeight(1);
      action.play();
      this.current = action;
      return;
    }

    this.current.crossFadeTo(action, this.fadeDuration, true);
    action.reset();
    action.enabled = true;
    action.play();
    this.next = action;
  }

  stop(): void {
    if (!this.current) {
      this.pose.relaxed();
      return;
    }

    const active = this.current;
    active.fadeOut(this.fadeDuration);
    this.current = null;

    setTimeout(() => {
      active.stop();
      this.pose.relaxed();
    }, this.fadeDuration * 1000);
  }

  stopImmediately(): void {
    this.current?.stop();
    this.current = null;
    this.pose.relaxed();
  }

  dispose(): void {
    this.stopImmediately();
    this.actions.clear();
  }
}

/**
 * VRM Skeletal Animation Controller
 * Handles loading, caching, cross-fading, and playback of .vrma animation tracks onto Three.js VRM rigs.
 */