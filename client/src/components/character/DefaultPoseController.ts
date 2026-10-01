import { MathUtils } from "three";
import { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";

const { degToRad } = MathUtils;

export class DefaultPoseController {
  apply(vrm: VRM): void {
    const humanoid = vrm.humanoid;
    if (!humanoid) return;

    const leftUpperArm = humanoid.getNormalizedBoneNode(VRMHumanBoneName.LeftUpperArm);
    const rightUpperArm = humanoid.getNormalizedBoneNode(VRMHumanBoneName.RightUpperArm);
    const leftLowerArm = humanoid.getNormalizedBoneNode(VRMHumanBoneName.LeftLowerArm);
    const rightLowerArm = humanoid.getNormalizedBoneNode(VRMHumanBoneName.RightLowerArm);

    // Natural shoulder and arm drape
    if (leftUpperArm) {
      leftUpperArm.rotation.set(degToRad(4), degToRad(-4), degToRad(18));
    }

    if (rightUpperArm) {
      rightUpperArm.rotation.set(degToRad(4), degToRad(4), degToRad(-18));
    }

    // Subtle natural elbow bend
    if (leftLowerArm) {
      leftLowerArm.rotation.z = degToRad(6);
    }

    if (rightLowerArm) {
      rightLowerArm.rotation.z = degToRad(-6);
    }

    vrm.update(0);
  }
}

/**
 * Default Pose Controller
 * Imposes a natural anatomical rest pose with slightly bent elbows and relaxed shoulders.
 */