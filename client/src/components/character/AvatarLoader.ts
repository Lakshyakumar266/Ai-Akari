import * as THREE from "three";
import {
  type GLTF,
  GLTFLoader,
} from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRM, VRMLoaderPlugin } from "@pixiv/three-vrm";
import { DefaultPoseController } from "./DefaultPoseController";

export interface LoadedAvatar {
  vrm: VRM;
  mixer: THREE.AnimationMixer;
}

export async function loadAvatar(url: string): Promise<LoadedAvatar> {
  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));

  let gltfAsset: GLTF;
  try {
    gltfAsset = (await loader.loadAsync(url)) as GLTF;
  } catch (primaryErr) {
    if (url === "/characters/default.vrm") {
      try {
        gltfAsset = (await loader.loadAsync("/character.vrm")) as GLTF;
      } catch {
        throw primaryErr;
      }
    } else {
      throw primaryErr;
    }
  }

  const vrm = gltfAsset.userData.vrm as VRM | undefined;
  if (!vrm) {
    throw new Error(`Asset loaded from "${url}" lacks valid VRM metadata.`);
  }

  // Align avatar facing camera
  vrm.scene.rotation.y = Math.PI;
  vrm.scene.position.set(0, 0, 0);

  try {
    new DefaultPoseController().apply(vrm);
  } catch (poseErr) {
    console.warn("[AvatarLoader] Default pose application skipped:", poseErr);
  }

  const mixer = new THREE.AnimationMixer(vrm.scene);
  return { vrm, mixer };
}

/**
 * Avatar Model Loader
 * Instantiates GLTF/VRM 3D assets with VRMLoaderPlugin, establishes base transforms,
 * and initializes animation mixers.
 */
