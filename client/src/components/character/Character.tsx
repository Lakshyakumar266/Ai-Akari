import { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { useControls } from "leva";
import * as THREE from "three";

import { loadAvatar } from "./AvatarLoader";
import { AnimationController } from "./AnimationController";
import { BlinkController } from "./BlinkController";
import { BreathingController } from "./BreathingController";
import { LookAtController } from "./LookAtController";
import { LipSyncController } from "./LipSyncController";
import { EmotionController } from "./EmotionController";
import {
  AvatarContext,
  type AvatarContextValue,
} from "./AvatarContext";
import {
  ANIMATIONS,
  DEFAULT_VRM_URL,
  EMOTIONS,
  type AnimationName,
  type EmotionName,
} from "./types";

export default function Character() {
  const [avatar, setAvatar] =
    useState<AvatarContextValue | null>(null);

  const lookAtTarget = useRef(new THREE.Vector3());

  const animationOptions = [
    "None",
    ...Object.keys(ANIMATIONS),
  ] as const;

  const { animation } = useControls("Animation", {
    animation: {
      value: "None",
      options: animationOptions,
    },
  });

  const { emotion } = useControls("Emotion", {
    emotion: {
      value: "Neutral" satisfies EmotionName,
      options: Object.keys(EMOTIONS),
    },
  });

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const { vrm, mixer } = await loadAvatar(
        DEFAULT_VRM_URL
      );

      if (cancelled) return;

      const controllers = {
        animation: new AnimationController(vrm, mixer),
        blink: new BlinkController(),
        breathing: new BreathingController(),
        lookAt: new LookAtController(),
        lipSync: new LipSyncController(),
        emotion: new EmotionController(),
      };

      setAvatar({ vrm, mixer, controllers });
    }

    init();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!avatar) return;

    avatar.controllers.emotion.setEmotion(
      emotion as EmotionName
    );
  }, [emotion, avatar]);

  useEffect(() => {
    if (!avatar) return;

    const { animation: animCtrl } = avatar.controllers;

    if (animation === "None") {
      animCtrl.stop();
      return;
    }

    animCtrl.play(animation as AnimationName);
  }, [animation, avatar]);

  useFrame((state, delta) => {
    if (!avatar) return;

    const { vrm, controllers } = avatar;

    controllers.animation.update(delta);
    controllers.blink.update(delta, vrm);
    controllers.breathing.update(delta, vrm);
    controllers.emotion.update(delta, vrm);
    controllers.lipSync.update(vrm);

    lookAtTarget.current.setFromMatrixPosition(
      state.camera.matrixWorld
    );
    controllers.lookAt.setTarget(lookAtTarget.current);
    controllers.lookAt.update(vrm);

    vrm.update(delta);
  });

  if (!avatar) return null;

  return (
    <AvatarContext.Provider value={avatar}>
      <primitive
        object={avatar.vrm.scene}
        position={[0, 0, 0]}
      />
    </AvatarContext.Provider>
  );
}
