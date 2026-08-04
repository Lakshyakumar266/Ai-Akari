import type {
  SpeechTimeline,
  VisemeFrame,
} from "../../networking/types";

import { audioPlayer } from "../../audio/AudioPlayer";

export interface ActiveViseme {
  current: VisemeFrame;
  next: VisemeFrame | null;
  alpha: number;
}

export class TimelinePlayer {
  private timeline: SpeechTimeline | null = null;

  private currentIndex = 0;

  private playing = false;

  /**
   * AudioContext.currentTime when this timeline's audio was scheduled to start.
   * elapsed = audioPlayer.currentTime - _startAt
   */
  private _startAt = 0;

  play(timeline: SpeechTimeline, startAt: number) {
    this.timeline = timeline;
    this._startAt = startAt;
    this.currentIndex = 0;
    this.playing = true;
  }

  stop() {
    this.timeline = null;
    this._startAt = 0;
    this.currentIndex = 0;
    this.playing = false;
  }

  get active() {
    return this.playing;
  }

  /**
   * delta is still accepted for API compatibility with the Three.js frame loop,
   * but TimelinePlayer derives elapsed from AudioContext.currentTime so that
   * viseme timing is locked to the actual audio sample clock.
   */
  update(
    _delta: number,
  ): ActiveViseme | null {
    if (!this.playing || !this.timeline) {
      return null;
    }

    // Elapsed time derived from the audio clock — not from accumulated delta.
    const elapsed = audioPlayer.currentTime - this._startAt;

    // Don't advance before audio starts playing.
    if (elapsed < 0) {
      return null;
    }

    const frames = this.timeline.frames;

    // Advance frame index to match current elapsed time.
    while (
      this.currentIndex < frames.length - 1 &&
      elapsed >= frames[this.currentIndex + 1].t
    ) {
      this.currentIndex++;
    }

    const current = frames[this.currentIndex];
    const next = frames[this.currentIndex + 1] ?? null;

    // Timeline finished.
    if (elapsed >= this.timeline.duration) {
      this.stop();
      return null;
    }

    let alpha = 1;

    if (next) {
      const length = next.t - current.t;

      if (length > 0) {
        alpha = (elapsed - current.t) / length;
      }
    }

    alpha = Math.max(0, Math.min(alpha, 1));

    return {
      current,
      next,
      alpha,
    };
  }
}