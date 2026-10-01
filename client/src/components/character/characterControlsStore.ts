import { useSyncExternalStore } from "react";
import type {
  AnimationControlOption,
  EmotionName,
} from "./types";

export interface CharacterPose {
  armX: number;
  armY: number;
  armZ: number;
}

export interface CharacterControlsState {
  animation: AnimationControlOption;
  emotion: EmotionName;
  pose: CharacterPose;
}

export const DEFAULT_POSE: CharacterPose = {
  armX: 5,
  armY: 8,
  armZ: 72,
};

const DEFAULT_STATE: CharacterControlsState = {
  animation: "Idle",
  emotion: "Neutral",
  pose: { ...DEFAULT_POSE },
};

type StoreListener = () => void;

class CharacterControlsStore {
  private state: CharacterControlsState = { ...DEFAULT_STATE };
  private readonly listeners: Set<StoreListener> = new Set();

  getState = (): CharacterControlsState => this.state;

  subscribe = (listener: StoreListener): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private notify(): void {
    this.listeners.forEach((listener) => listener());
  }

  setAnimation(animation: AnimationControlOption): void {
    if (this.state.animation === animation) return;
    this.state = { ...this.state, animation };
    this.notify();
  }

  setEmotion(emotion: EmotionName): void {
    if (this.state.emotion === emotion) return;
    this.state = { ...this.state, emotion };
    this.notify();
  }

  setPose(poseUpdate: Partial<CharacterPose>): void {
    this.state = {
      ...this.state,
      pose: { ...this.state.pose, ...poseUpdate },
    };
    this.notify();
  }

  setArmX(val: number): void {
    this.setPose({ armX: val });
  }

  setArmY(val: number): void {
    this.setPose({ armY: val });
  }

  setArmZ(val: number): void {
    this.setPose({ armZ: val });
  }

  resetPose(): void {
    this.state = {
      ...this.state,
      pose: { ...DEFAULT_POSE },
    };
    this.notify();
  }

  resetAll(): void {
    this.state = {
      animation: "Idle",
      emotion: "Neutral",
      pose: { ...DEFAULT_POSE },
    };
    this.notify();
  }
}

export const characterControlsStore = new CharacterControlsStore();

export function useCharacterControls() {
  const currentState = useSyncExternalStore(
    characterControlsStore.subscribe,
    characterControlsStore.getState,
    characterControlsStore.getState
  );

  return {
    ...currentState,
    setAnimation: (anim: AnimationControlOption) => characterControlsStore.setAnimation(anim),
    setEmotion: (emo: EmotionName) => characterControlsStore.setEmotion(emo),
    setPose: (pose: Partial<CharacterPose>) => characterControlsStore.setPose(pose),
    setArmX: (val: number) => characterControlsStore.setArmX(val),
    setArmY: (val: number) => characterControlsStore.setArmY(val),
    setArmZ: (val: number) => characterControlsStore.setArmZ(val),
    resetPose: () => characterControlsStore.resetPose(),
    resetAll: () => characterControlsStore.resetAll(),
  };
}

/**
 * Character Controls Store
 * React external store managing active body animations, manual bone rotations, and facial sentiments.
 */
