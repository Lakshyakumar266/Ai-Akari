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
import { PoseController } from "./PoseController";

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

    const pose = useControls("Pose", {
      armX: {
        value: 5,
        min: -90,
        max: 90,
        step: 1,
      },
    
      armY: {
        value: 8,
        min: -90,
        max: 90,
        step: 1,
      },
    
      armZ: {
        value: 72,
        min: -90,
        max: 90,
        step: 1,
      },
    });

  const cameraTarget = useRef(
    new THREE.Vector3()
  );

  //
  // Leva
  //

  const animationOptions = [
    "None",
    ...Object.keys(ANIMATIONS),
  ] as const;

  const { animation } = useControls(
    "Animation",
    {
      animation: {
        value: "None",
        options: animationOptions,
      },
    }
  );

  const { emotion } = useControls(
    "Emotion",
    {
      emotion: {
        value: "Neutral" satisfies EmotionName,
        options: Object.keys(EMOTIONS),
      },
    }
  );

  //
  // Load Avatar
  //

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const { vrm, mixer } =
        await loadAvatar(DEFAULT_VRM_URL);

      if (cancelled) return;

      //
      // Default Pose
      //

      const pose = new PoseController(vrm);

      pose.relaxed();

      //
      // Controllers
      //

      const controllers = {
        pose,

        animation:
          new AnimationController(
            vrm,
            mixer,
            pose
          ),

        blink: new BlinkController(),

        breathing:
          new BreathingController(),

        lookAt:
          new LookAtController(),

        lipSync:
          new LipSyncController(),

        emotion:
          new EmotionController(),
      };

      setAvatar({
        vrm,
        mixer,
        controllers,
      });
    }

    init();

    return () => {
      cancelled = true;
    };
  }, []);

  //
  // Emotion
  //

  useEffect(() => {
    if (!avatar) return;

    avatar.controllers.emotion.setEmotion(
      emotion as EmotionName
    );
  }, [avatar, emotion]);

  //
  // Animation
  //

  useEffect(() => {
    if (!avatar) return;

    if (animation === "None") {
      avatar.controllers.animation.stop();

      return;
    }

    avatar.controllers.animation.play(
      animation as AnimationName
    );
  }, [avatar, animation]);

  //
  // Frame Loop
  //

  useFrame((state, delta) => {
    if (!avatar) return;

    const {
      vrm,
      controllers,
    } = avatar;

    //
    // Body
    //

    controllers.animation.update(delta);

    //
    // Face
    //

    controllers.blink.update(
      delta,
      vrm
    );

    controllers.emotion.update(
      delta,
      vrm
    );

    controllers.lipSync.update(delta,vrm);

    //
    // Idle
    //

    controllers.breathing.update(
      delta,
      vrm
    );

    //
    // LookAt
    //

    cameraTarget.current.setFromMatrixPosition(
      state.camera.matrixWorld
    );

    controllers.lookAt.setTarget(
      cameraTarget.current
    );

    controllers.lookAt.update(vrm);

    //
    // Update VRM
    //

    vrm.update(delta);

    //
    // Pose 
    //
    if (!controllers.animation.isPlaying()) {
      controllers.pose.relaxed(
        pose.armX,
        pose.armY,
        pose.armZ
      );
    }
  });


  if (!avatar) return null;

  return (
    <AvatarContext.Provider
      value={avatar}
    >
      <primitive
        object={avatar.vrm.scene}
      />
    </AvatarContext.Provider>
  );
}