import type { SpeechTimeline } from "../../networking/types";

export class TimelineQueue {
  private queue: SpeechTimeline[] = [];

  enqueue(timeline: SpeechTimeline) {
    this.queue.push(timeline);
  }

  dequeue(): SpeechTimeline | null {
    if (this.queue.length === 0) {
      return null;
    }

    return this.queue.shift() ?? null;
  }

  peek(): SpeechTimeline | null {
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