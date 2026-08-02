import type {
    SpeechTimeline,
    VisemeFrame,
  } from "../../networking/types";
  
  export interface ActiveViseme {
    current: VisemeFrame;
    next: VisemeFrame | null;
    alpha: number;
  }
  
  export class TimelinePlayer {
    private timeline: SpeechTimeline | null =
      null;
  
    private elapsed = 0;
  
    private currentIndex = 0;
  
    private playing = false;
  
    play(timeline: SpeechTimeline) {
      this.timeline = timeline;
      this.elapsed = 0;
      this.currentIndex = 0;
      this.playing = true;
    }
  
    stop() {
      this.timeline = null;
      this.elapsed = 0;
      this.currentIndex = 0;
      this.playing = false;
    }
  
    get active() {
      return this.playing;
    }
  
    update(
      delta: number
    ): ActiveViseme | null {
      if (
        !this.playing ||
        !this.timeline
      )
        return null;
  
      this.elapsed += delta;
  
      const frames =
        this.timeline.frames;
  
      while (
        this.currentIndex <
          frames.length - 1 &&
        this.elapsed >=
          frames[this.currentIndex + 1].t
      ) {
        this.currentIndex++;
      }
  
      const current =
        frames[this.currentIndex];
  
      const next =
        frames[
          this.currentIndex + 1
        ] ?? null;
  
      if (
        this.elapsed >=
        this.timeline.duration
      ) {
        this.stop();
  
        return {
          current,
          next: null,
          alpha: 1,
        };
      }
  
      let alpha = 1;
  
      if (next) {
        const length =
          next.t - current.t;
  
        if (length > 0) {
          alpha =
            (this.elapsed -
              current.t) /
            length;
        }
      }
  
      alpha = Math.max(
        0,
        Math.min(alpha, 1)
      );
  
      return {
        current,
        next,
        alpha,
      };
    }
  }