import type { VRM } from "@pixiv/three-vrm";

import type {
  SpeechTimeline,
} from "../../networking/types";

import { TimelinePlayer } from "./TimelinePlayer";
import { TimelineQueue } from "./TimelineQueue";
import type { VisemeName } from "./types";

const VISEMES: VisemeName[] = [
  "aa",
  "ih",
  "ou",
  "ee",
  "oh",
];

export class LipSyncController {
  private readonly queue =
    new TimelineQueue();

  private readonly player =
    new TimelinePlayer();

  /**
   * Enqueue a speech timeline for playback.
   *
   * @param timeline  Viseme frames from the server.
   * @param startAt   AudioContext.currentTime when this sentence's audio plays.
   *                  TimelinePlayer computes elapsed = audioPlayer.currentTime - startAt
   *                  so visemes stay locked to the actual audio sample clock.
   */
  playTimeline(
    timeline: SpeechTimeline,
    startAt: number,
  ) {
    this.queue.enqueue(timeline, startAt);
  }

  stop(vrm?: VRM) {
    this.queue.clear();

    this.player.stop();

    if (vrm) {
      this.resetExpressions(vrm);
    }
  }

  isSpeaking() {
    return (
      this.player.active ||
      !this.queue.empty
    );
  }

  update(
    delta: number,
    vrm: VRM
  ) {
    //
    // Start next sentence automatically.
    // The queue entry carries its own startAt so TimelinePlayer knows
    // when to begin relative to the audio clock.
    //
    if (
      !this.player.active &&
      !this.queue.empty
    ) {
      const next = this.queue.dequeue();

      if (next) {
        this.player.play(next.timeline, next.startAt);
      }
    }

    //
    // Nothing playing
    //
    if (!this.player.active) {
      this.resetExpressions(vrm);
      return;
    }

    //
    // Advance timeline (delta is passed but TimelinePlayer uses AudioContext clock)
    //
    const state = this.player.update(delta);

    //
    // Timeline finished
    //
    if (!state) {
      this.resetExpressions(vrm);
      return;
    }

    //
    // Reset all mouth shapes
    //

    this.resetExpressions(vrm);
    const manager =
      vrm.expressionManager;

    if (!manager) return;

    const {
      current,
      next,
      alpha,
    } = state;

    //
    // current
    //

    if (current.viseme !== "sil") {
      manager.setValue(
        current.viseme,
        current.weight * (1 - alpha)
      );
    }

    //
    // next
    //

    if (
      next &&
      next.viseme !== "sil"
    ) {
      manager.setValue(
        next.viseme,
        next.weight * alpha
      );
    }
  }

  private resetExpressions(
    vrm: VRM
  ) {
    const manager =
      vrm.expressionManager;

    if (!manager) return;

    for (const viseme of VISEMES) {
      manager.setValue(viseme, 0);
    }
  }
}