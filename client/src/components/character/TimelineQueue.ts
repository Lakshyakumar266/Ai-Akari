import type { SpeechTimeline } from "../../networking/types";

interface QueueEntry {
  timeline: SpeechTimeline;
  /** AudioContext.currentTime when this timeline's audio starts playing. */
  startAt: number;
}

export class TimelineQueue {
  private queue: QueueEntry[] = [];

  enqueue(timeline: SpeechTimeline, startAt: number) {
    this.queue.push({ timeline, startAt });
  }

  dequeue(): QueueEntry | null {
    if (this.queue.length === 0) {
      return null;
    }

    return this.queue.shift() ?? null;
  }

  peek(): QueueEntry | null {
    return this.queue[0] ?? null;
  }

  clear() {
    this.queue.length = 0;
  }

  get size() {
    return this.queue.length;
  }

  get empty() {
    return this.queue.length === 0;
  }
}