import * as THREE from "three";
import {
  type GLTF,
  GLTFLoader,
} from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRM, VRMLoaderPlugin } from "@pixiv/three-vrm";

export type LoadedAvatar = {
  vrm: VRM;
  mixer: THREE.AnimationMixer;
};

export async function loadAvatar(
  url: string
): Promise<LoadedAvatar> {
  const vrmLoader = new GLTFLoader();

  vrmLoader.register(
    (parser) => new VRMLoaderPlugin(parser)
  );

  const vrmGltf = (await vrmLoader.loadAsync(url)) as GLTF;
  const vrm = vrmGltf.userData.vrm as VRM;

  vrm.scene.rotation.y = Math.PI;
  vrm.scene.position.set(0, 0, 0);

  const mixer = new THREE.AnimationMixer(vrm.scene);

  return { vrm, mixer };
}
