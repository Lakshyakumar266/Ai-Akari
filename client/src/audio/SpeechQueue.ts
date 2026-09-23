/**
 * SpeechQueue
 *
 * Manages sentence-level speech segments received from the server.
 * Plays each audio segment through AudioPlayer, and triggers exact callbacks
 * for subtitle synchronization so that subtitles stay on screen while their
 * audio is playing, and only advance when that segment's audio finishes.
 */

import { audioPlayer } from "./AudioPlayer";
import type { SpeechSegmentEvent } from "../networking/types";

type SegmentStartListener = (segment: SpeechSegmentEvent) => void;
type SegmentProgressListener = (currentTime: number, duration: number) => void;
type SegmentEndListener = (segment: SpeechSegmentEvent) => void;
type AllSegmentsEndListener = () => void;

export class SpeechQueue {
  private queue: SpeechSegmentEvent[] = [];
  private isPlaying = false;
  private currentSegment: SpeechSegmentEvent | null = null;

  private onStartListeners = new Set<SegmentStartListener>();
  private onProgressListeners = new Set<SegmentProgressListener>();
  private onEndListeners = new Set<SegmentEndListener>();
  private onAllEndListeners = new Set<AllSegmentsEndListener>();

  enqueue(segment: SpeechSegmentEvent): void {
    this.queue.push(segment);
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  interrupt(): void {
    this.queue = [];
    this.isPlaying = false;
    this.currentSegment = null;
    audioPlayer.stop();
    this.notifyAllEnd();
  }

  get activeSegment(): SpeechSegmentEvent | null {
    return this.currentSegment;
  }

  private playNext(): void {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.currentSegment = null;
      this.notifyAllEnd();
      return;
    }

    const segment = this.queue.shift()!;
    this.isPlaying = true;
    this.currentSegment = segment;
    this.notifyStart(segment);

    audioPlayer.playAudioUrl(
      segment.audio,
      (curr, dur) => {
        this.notifyProgress(curr, dur);
      },
      () => {
        this.notifyEnd(segment);
        if (this.queue.length > 0) {
          this.playNext();
        } else {
          this.isPlaying = false;
          this.currentSegment = null;
          this.notifyAllEnd();
        }
      }
    );
  }

  onSegmentStart(cb: SegmentStartListener): () => void {
    this.onStartListeners.add(cb);
    return () => {
      this.onStartListeners.delete(cb);
    };
  }

  onSegmentProgress(cb: SegmentProgressListener): () => void {
    this.onProgressListeners.add(cb);
    return () => {
      this.onProgressListeners.delete(cb);
    };
  }

  onSegmentEnd(cb: SegmentEndListener): () => void {
    this.onEndListeners.add(cb);
    return () => {
      this.onEndListeners.delete(cb);
    };
  }

  onAllSegmentsEnd(cb: AllSegmentsEndListener): () => void {
    this.onAllEndListeners.add(cb);
    return () => {
      this.onAllEndListeners.delete(cb);
    };
  }

  private notifyStart(seg: SpeechSegmentEvent) {
    for (const cb of this.onStartListeners) {
      try {
        cb(seg);
      } catch (err) {
        console.error("[SpeechQueue] start listener error:", err);
      }
    }
  }

  private notifyProgress(curr: number, dur: number) {
    for (const cb of this.onProgressListeners) {
      try {
        cb(curr, dur);
      } catch (err) {
        console.error("[SpeechQueue] progress listener error:", err);
      }
    }
  }

  private notifyEnd(seg: SpeechSegmentEvent) {
    for (const cb of this.onEndListeners) {
      try {
        cb(seg);
      } catch (err) {
        console.error("[SpeechQueue] end listener error:", err);
      }
    }
  }

  private notifyAllEnd() {
    for (const cb of this.onAllEndListeners) {
      try {
        cb();
      } catch (err) {
        console.error("[SpeechQueue] allEnd listener error:", err);
      }
    }
  }
}

export const speechQueue = new SpeechQueue();
