/**
 * AudioQueue
 *
 * Decouples network packet receiving from audio decoding & playback scheduling.
 *
 * Pipeline:
 *   Binary Packet (WebSocket)
 *           ↓
 *      rawQueue (ArrayBuffer[])
 *           ↓
 *     Decode Loop (decodeAudioData)
 *           ↓
 *    decodedQueue (AudioBuffer[])
 *           ↓
 *    Playback Scheduler (AudioContext.currentTime)
 *           ↓
 *       AudioPlayer
 */

import { audioPlayer, AudioPlayer } from "./AudioPlayer";

export class AudioQueue {
  private readonly player: AudioPlayer;

  private rawQueue: ArrayBuffer[] = [];
  private decodedQueue: AudioBuffer[] = [];

  private isDecoding = false;
  private bufferedDuration = 0;
  private isStreamingPlayback = false;

  /** Minimum pre-buffer (seconds) required before starting initial playback of a stream */
  private readonly PRE_BUFFER_TARGET_SEC = 0.15; // 150ms

  constructor(player: AudioPlayer) {
    this.player = player;
  }

  /**
   * Enqueue a raw binary audio chunk received over WebSocket.
   * Does NOT block the network callback.
   */
  push(chunk: ArrayBuffer): void {
    this.rawQueue.push(chunk);
    this.processQueue();
  }

  /**
   * Discard all pending audio & stop playback immediately (e.g. on INTERRUPT).
   */
  flush(): void {
    this.rawQueue = [];
    this.decodedQueue = [];
    this.bufferedDuration = 0;
    this.isDecoding = false;
    this.isStreamingPlayback = false;

    this.player.stop();
  }

  private async processQueue(): Promise<void> {
    if (this.isDecoding) return;
    this.isDecoding = true;

    while (this.rawQueue.length > 0) {
      const chunk = this.rawQueue.shift();
      if (!chunk) continue;

      const audioBuffer = await this.player.decodeAudio(chunk);
      if (audioBuffer) {
        this.decodedQueue.push(audioBuffer);
        this.bufferedDuration += audioBuffer.duration;
      }

      this.schedulePlayback();
    }

    this.isDecoding = false;

    // Run scheduling once more in case items remained in decodedQueue
    this.schedulePlayback();
  }

  private schedulePlayback(): void {
    // If we haven't started playing this stream yet, wait until we accumulate ~150ms of audio
    // or until the network raw queue has finished delivering chunks.
    if (!this.isStreamingPlayback) {
      if (this.bufferedDuration >= this.PRE_BUFFER_TARGET_SEC || (this.rawQueue.length === 0 && this.decodedQueue.length > 0)) {
        this.isStreamingPlayback = true;
      } else {
        // Still filling initial buffer
        return;
      }
    }

    // Drain decoded queue into AudioPlayer scheduler
    while (this.decodedQueue.length > 0) {
      const buffer = this.decodedQueue.shift();
      if (buffer) {
        this.bufferedDuration -= buffer.duration;
        this.player.scheduleBuffer(buffer);
      }
    }

    if (this.bufferedDuration <= 0 && this.rawQueue.length === 0) {
      this.isStreamingPlayback = false;
    }
  }
}

export const audioQueue = new AudioQueue(audioPlayer);
