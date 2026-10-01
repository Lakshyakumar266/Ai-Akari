import { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import { loadAvatar } from "./AvatarLoader";
import { AnimationController } from "./AnimationController";
import { BlinkController } from "./BlinkController";
import { BreathingController } from "./BreathingController";
import { LookAtController } from "./LookAtController";
import { LipSyncController } from "./LipSyncController";
import { EmotionController } from "./EmotionController";
import { PoseController } from "./PoseController";
import { useCharacterControls } from "./characterControlsStore";
import {
  AvatarContext,
  type AvatarContextValue,
} from "./AvatarContext";
import {
  getCharacterConfig,
  type AnimationName,
  type EmotionName,
} from "./types";

interface CharacterProps {
  characterId?: string;
}

export default function Character({ characterId = "akari" }: CharacterProps) {
  const [avatar, setAvatar] = useState<AvatarContextValue | null>(null);
  const { animation, emotion, pose } = useCharacterControls();
  const cameraTarget = useRef(new THREE.Vector3());

  const characterConfig = getCharacterConfig(characterId);
  const vrmUrl = characterConfig.vrmUrl;
  const position = characterConfig.position ?? [0, 0, 0];
  const scale = characterConfig.scale ?? 1;

  // Initialize and load 3D character instance
  useEffect(() => {
    let isCancelled = false;
    let activeAvatar: AvatarContextValue | null = null;

    async function init() {
      try {
        const { vrm, mixer } = await loadAvatar(vrmUrl);

        if (isCancelled) {
          disposeAvatarResources(vrm, mixer);
          return;
        }

        vrm.scene.position.set(0, 0, 0);
        vrm.scene.scale.set(1, 1, 1);

        const poseCtrl = new PoseController(vrm);
        try {
          poseCtrl.relaxed();
        } catch {
          // Fallback if specific humanoid bones are absent
        }

        const controllers = {
          pose: poseCtrl,
          animation: new AnimationController(vrm, mixer, poseCtrl),
          blink: new BlinkController(),
          breathing: new BreathingController(),
          lookAt: new LookAtController(),
          lipSync: new LipSyncController(),
          emotion: new EmotionController(),
        };

        activeAvatar = { vrm, mixer, controllers };
        setAvatar(activeAvatar);
      } catch (err) {
        console.error(`[Character] Failed to initialize avatar for ${characterId}:`, err);
      }
    }

    init();

    return () => {
      isCancelled = true;
      if (activeAvatar) {
        try {
          activeAvatar.controllers.lipSync.dispose();
          activeAvatar.controllers.emotion.dispose();
          activeAvatar.controllers.animation.dispose();
          disposeAvatarResources(activeAvatar.vrm, activeAvatar.mixer);
        } catch (cleanupErr) {
          console.warn("[Character] Cleanup error:", cleanupErr);
        }
      }
      setAvatar(null);
    };
  }, [vrmUrl, characterId]);

  // Sync sentiment expression changes
  useEffect(() => {
    if (!avatar) return;
    avatar.controllers.emotion.setEmotion(emotion as EmotionName);
  }, [avatar, emotion]);

  // Sync animation triggers
  useEffect(() => {
    if (!avatar) return;

    if (animation === "None") {
      avatar.controllers.animation.stop();
      return;
    }

    avatar.controllers.animation.play(animation as AnimationName);
  }, [avatar, animation]);

  // Main 60fps render tick loop
  useFrame((state, delta) => {
    if (!avatar) return;
    const { vrm, controllers } = avatar;

    // Body animation
    controllers.animation.update(delta);

    // Facial controllers
    controllers.blink.update(delta, vrm);
    controllers.emotion.update(delta, vrm);
    controllers.lipSync.update(delta, vrm);

    // Breathing and gaze
    controllers.breathing.update(delta, vrm);
    cameraTarget.current.setFromMatrixPosition(state.camera.matrixWorld);
    controllers.lookAt.setTarget(cameraTarget.current);
    controllers.lookAt.update(vrm);

    // Internal VRM spring bones & scene graph update
    vrm.update(delta);

    // Dynamic procedural arm pose when idle
    if (!controllers.animation.isPlaying()) {
      controllers.pose.relaxed(pose.armX, pose.armY, pose.armZ);
    }
  });

  if (!avatar) return null;

  return (
    <AvatarContext.Provider value={avatar}>
      <group position={position} scale={[scale, scale, scale]}>
        <primitive object={avatar.vrm.scene} />
      </group>
    </AvatarContext.Provider>
  );
}

function disposeAvatarResources(vrm: any, mixer?: THREE.AnimationMixer): void {
  try {
    if (mixer) {
      mixer.stopAllAction();
      if (vrm?.scene) {
        mixer.uncacheRoot(vrm.scene);
      }
    }
    const root = vrm?.scene || vrm;
    root?.traverse?.((obj: any) => {
      if (obj.geometry) {
        obj.geometry.dispose();
      }
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach((mat: any) => mat?.dispose?.());
        } else {
          obj.material?.dispose?.();
        }
      }
    });
  } catch (err) {
    console.warn("[Character] Resource deallocation warning:", err);
  }
}

/**
 * Character Component
 * R3F component coordinating 3D VRM lifecycle, per-frame procedural lifelike animations,
 * look-at tracking, lip-sync FFT integration, and dynamic model swapping.
 */