export { default } from "./Character";
export { useAvatar } from "./AvatarContext";
export type {
  AnimationName,
  AnimationControlOption,
  EmotionName,
  VisemeName,
} from "./types";
export { ANIMATIONS, EMOTIONS } from "./types";
export {
  useCharacterControls,
  characterControlsStore,
  DEFAULT_POSE,
  type CharacterPose,
  type CharacterControlsState,
} from "./characterControlsStore";
