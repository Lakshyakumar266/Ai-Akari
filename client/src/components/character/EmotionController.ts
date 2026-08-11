import type { VRM } from "@pixiv/three-vrm";
import { avatarEvents } from "../../networking/EventBus";
import type { EmotionEvent } from "../../networking/types";
import { EMOTIONS, type EmotionName } from "./types";

const MOUTH_VISEMES = new Set(["aa", "ih", "ou", "ee", "oh"]);

const ALL_EXPRESSION_KEYS = Array.from(
  new Set(Object.values(EMOTIONS).flatMap((preset) => Object.keys(preset)))
);

const VALID_EMOTION_MAP: Record<string, EmotionName> = {
  // Primary 6 VRM emotions
  neutral: "Neutral",
  happy: "Happy",
  sad: "Sad",
  angry: "Angry",
  relaxed: "Relaxed",
  surprised: "Surprised",

  // Contextual aliases
  blush: "Happy",
  flustered: "Happy",
  smirk: "Happy",
  teasing: "Happy",
  joy: "Happy",
  annoyed: "Angry",
  mad: "Angry",
  furious: "Angry",
  pouting: "Angry",
  shocked: "Surprised",
  confused: "Surprised",
  gasp: "Surprised",
  unhappy: "Sad",
  crying: "Sad",
  sulky: "Sad",
  calm: "Relaxed",
  sleepy: "Relaxed",
};

export class EmotionController {
  private current: EmotionName = "Neutral";
  private readonly lerpSpeed = 4;
  private unsubscribers: Array<() => void> = [];

  constructor() {
    const unsubEmotion = avatarEvents.subscribe("emotion", (event: EmotionEvent) => {
      if (event.emotion) {
        this.setEmotionByName(event.emotion);
      }
    });

    const unsubSpeechEnd = avatarEvents.subscribe("speech_end", () => {
      console.log("[EmotionController] Speech ended -> resetting facial expression to Neutral");
      this.setEmotionByName("Neutral");
    });

    this.unsubscribers.push(unsubEmotion, unsubSpeechEnd);
  }

  setEmotion(name: EmotionName): void {
    this.current = name;
  }

  setEmotionByName(rawName: string): void {
    const key = rawName.trim().toLowerCase();
    const mapped = VALID_EMOTION_MAP[key] ?? "Neutral";
    console.log(`[EmotionController] Setting emotion to ${mapped} (raw: ${rawName})`);
    this.current = mapped;
  }

  update(delta: number, vrm: VRM): void {
    const manager = vrm.expressionManager;
    if (!manager) return;

    const targetPreset = EMOTIONS[this.current] ?? EMOTIONS.Neutral;
    const step = Math.min(1, delta * this.lerpSpeed);

    for (const name of ALL_EXPRESSION_KEYS) {
      if (MOUTH_VISEMES.has(name)) continue;

      const desired = targetPreset[name as keyof typeof targetPreset] ?? 0;
      const current = manager.getValue(name) ?? 0;
      const next = current + (desired - current) * step;

      manager.setValue(name, next);
    }
  }

  dispose(): void {
    this.unsubscribers.forEach((unsub) => unsub());
    this.unsubscribers = [];
  }
}

/**
 * Facial Emotion Controller
 * Translates character sentiment tags and dialog events into smooth blend-shape transitions.
 */
