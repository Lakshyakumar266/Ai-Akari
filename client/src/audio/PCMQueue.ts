import type { PCMPlayer } from "./PCMPlayer";

const INT16_TO_FLOAT32_SCALE = 1.0 / 32768.0;

export class PCMQueue {
  private readonly player: PCMPlayer;
  private queue: ArrayBuffer[] = [];
  private isProcessing = false;

  constructor(player: PCMPlayer) {
    this.player = player;
  }

  push(chunk: ArrayBuffer): void {
    this.queue.push(chunk);
    this.process();
  }

  flush(): void {
    this.queue = [];
    this.isProcessing = false;
    this.player.clear();
  }

  private process(): void {
    if (this.isProcessing) return;
    this.isProcessing = true;

    while (this.queue.length > 0) {
      const chunk = this.queue.shift();
      if (!chunk || chunk.byteLength < 2) continue;

      // Transform raw Int16 Little-Endian binary into normalized [-1.0, 1.0] Float32 samples
      const int16View = new Int16Array(chunk);
      const float32Samples = new Float32Array(int16View.length);

      for (let i = 0; i < int16View.length; i++) {
        float32Samples[i] = int16View[i] * INT16_TO_FLOAT32_SCALE;
      }

      this.player.postSamples(float32Samples);
    }

    this.isProcessing = false;
  }
}

/**
 * PCMQueue Architecture
 * Receives raw WebSocket Int16 LE binary PCM chunks from network,
 * converts them to Float32, and posts them to PCMPlayer & AudioWorklet.
 */
