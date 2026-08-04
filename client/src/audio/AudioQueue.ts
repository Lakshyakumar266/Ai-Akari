/**
 * AudioQueue
 *
 * Serialises incoming audio chunk decode+schedule calls so they never race.
 *
 * Problem without this:
 *   Browser receives chunk 1 and chunk 2 almost simultaneously.
 *   Both call audioPlayer.play() concurrently.
 *   decodeAudioData for chunk 2 may finish before chunk 1.
 *   Chunk 2 gets scheduled first → wrong order → overlap/gap.
 *
 * Solution:
 *   Each push() appends to a promise chain.
 *   Chunk N+1 only starts decoding after chunk N has been scheduled.
 *   Order is guaranteed regardless of chunk size or decode speed.
 */

import { audioPlayer, AudioPlayer } from "./AudioPlayer";

export class AudioQueue {
  private _chain: Promise<void> = Promise.resolve();

  private readonly player: AudioPlayer;

  constructor(player: AudioPlayer) {
    this.player = player;
  }

  /**
   * Enqueue an audio chunk for decode + scheduled playback.
   * Returns immediately — the chunk plays when its turn arrives.
   */
  push(chunk: ArrayBuffer): void {
    // Capture the buffer reference now; don't close over a mutable variable.
    const frozen = chunk;

    this._chain = this._chain
      .then(() => this.player.play(frozen))
      .catch((err) => {
        console.error("[AudioQueue] Chunk error:", err);
        // Don't break the chain — continue with next chunk.
      });
  }

  /**
   * Discard all pending chunks and stop playback immediately.
   * Use when an INTERRUPT packet arrives.
   */
  flush(): void {
    // Reset the chain so future pushes aren't waiting on dead promises.
    this._chain = Promise.resolve();

    this.player.stop();
  }
}

export const audioQueue = new AudioQueue(audioPlayer);
