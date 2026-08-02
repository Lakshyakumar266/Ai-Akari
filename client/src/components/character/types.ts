export const ANIMATIONS = {
  Idle: "/animations/Idle.vrma",
  Blush: "/animations/Blush.vrma",
  Clapping: "/animations/Clapping.vrma",
  Jump: "/animations/Jump.vrma",
  LookAround: "/animations/LookAround.vrma",
  Relax: "/animations/Relax.vrma",
  Sad: "/animations/Sad.vrma",
  Sleepy: "/animations/Sleepy.vrma",
  Surprised: "/animations/Surprised.vrma",
  Thinking: "/animations/Thinking.vrma",
} as const;

export type AnimationName = keyof typeof ANIMATIONS;

export type AnimationControlOption = "None" | AnimationName;

export const EMOTIONS = {
  Neutral: {},
  Happy: { happy: 1 },
  Sad: { sad: 1 },
  Angry: { angry: 1 },
  Relaxed: { relaxed: 1 },
  Surprised: { surprised: 1 },
} as const satisfies Record<
  string,
  Record<string, number>
>;

export type EmotionName = keyof typeof EMOTIONS;

export const VISEME_EXPRESSIONS = [
  "aa",
  "ih",
  "ou",
  "ee",
  "oh",
] as const;

export type VisemeName = (typeof VISEME_EXPRESSIONS)[number];

export const DEFAULT_VRM_URL = "/character.vrm";
