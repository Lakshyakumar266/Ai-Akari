import { MathUtils } from "three";
import { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";

const { degToRad } = MathUtils;

export type PoseName =
  | "relaxed"
  | "attention"
  | "crossedArms"
  | "handsBehindBack";

const ARM_BONES: readonly VRMHumanBoneName[] = [
  VRMHumanBoneName.LeftUpperArm,
  VRMHumanBoneName.RightUpperArm,
  VRMHumanBoneName.LeftLowerArm,
  VRMHumanBoneName.RightLowerArm,
  VRMHumanBoneName.LeftHand,
  VRMHumanBoneName.RightHand,
];

export class PoseController {
  private readonly vrm: VRM;

  constructor(vrm: VRM) {
    this.vrm = vrm;
  }

  private bone(name: VRMHumanBoneName) {
    return this.vrm.humanoid?.getNormalizedBoneNode(name) ?? null;
  }

  private clearArms(): void {
    for (const boneName of ARM_BONES) {
      const boneNode = this.bone(boneName);
      if (boneNode) {
        boneNode.rotation.set(0, 0, 0);
      }
    }
    this.vrm.update(0);
  }

  clear(): void {
    this.clearArms();
  }

  relaxed(armX = 5, armY = 8, armZ = 72): void {
    this.clearArms();

    const leftUpper = this.bone(VRMHumanBoneName.LeftUpperArm);
    const rightUpper = this.bone(VRMHumanBoneName.RightUpperArm);

    if (leftUpper) {
      leftUpper.rotation.set(degToRad(armX), degToRad(-armY), degToRad(armZ));
    }

    if (rightUpper) {
      rightUpper.rotation.set(degToRad(armX), degToRad(armY), degToRad(-armZ));
    }

    this.vrm.update(0);
  }

  attention(): void {
    this.clearArms();

    const chest = this.bone(VRMHumanBoneName.Chest);
    if (chest) {
      chest.rotation.x = degToRad(-4);
    }

    this.vrm.update(0);
  }

  crossedArms(): void {
    this.clearArms();

    const leftUpper = this.bone(VRMHumanBoneName.LeftUpperArm);
    const rightUpper = this.bone(VRMHumanBoneName.RightUpperArm);

    if (leftUpper) {
      leftUpper.rotation.set(0, degToRad(30), degToRad(50));
    }

    if (rightUpper) {
      rightUpper.rotation.set(0, degToRad(-30), degToRad(-50));
    }

    this.vrm.update(0);
  }

  handsBehindBack(): void {
    this.clearArms();

    const leftUpper = this.bone(VRMHumanBoneName.LeftUpperArm);
    const rightUpper = this.bone(VRMHumanBoneName.RightUpperArm);

    if (leftUpper) {
      leftUpper.rotation.x = degToRad(-28);
    }

    if (rightUpper) {
      rightUpper.rotation.x = degToRad(-28);
    }

    this.vrm.update(0);
  }

  setPose(name: PoseName): void {
    switch (name) {
      case "relaxed":
        return this.relaxed();
      case "attention":
        return this.attention();
      case "crossedArms":
        return this.crossedArms();
      case "handsBehindBack":
        return this.handsBehindBack();
    }
  }
}

/**
 * Skeletal Pose Controller
 * Manages static arm, shoulder, and torso orientations across predefined postural stances.
 */