/**
 * AudioAnalyser
 *
 * Reads live audio samples from the Web Audio AnalyserNode and
 * computes a smoothed RMS value that drives VRM mouth expressions.
 *
 * Usage (called once per Three.js frame from LipSyncController):
 *
 *   const rms = audioAnalyser.update();  // 0.0 = silence, ~0.15 = loud speech
 *
 * The analyser sits directly in the AudioPlayer's playback graph, so
 * the RMS reflects exactly what is being sent to the speakers.
 * No synchronization with a separate clock is required.
 */

import { audioPlayer } from "./AudioPlayer";

export class AudioAnalyser {
  private readonly _node: AnalyserNode;
  private readonly _buffer: Float32Array<ArrayBuffer>;
  private _smoothed = 0;

  constructor(node: AnalyserNode) {
    this._node = node;
    this._buffer = new Float32Array(node.fftSize) as Float32Array<ArrayBuffer>;
  }

  /**
   * Sample the analyser, compute RMS, and apply exponential smoothing.
   * Call exactly once per animation frame.
   *
   * @param damping  Controls smoothness.
   *                 0 = mouth jumps instantly to raw signal (jittery)
   *                 1 = mouth never moves
   *                 0.2–0.4 = good range for speech
   */
  update(damping = 0.3): number {
    // Read current time-domain samples (amplitude values)
    this._node.getFloatTimeDomainData(this._buffer);

    // Root Mean Square = measure of signal energy
    let sumSq = 0;
    const n = this._buffer.length;

    for (let i = 0; i < n; i++) {
      sumSq += this._buffer[i] * this._buffer[i];
    }

    const rms = Math.sqrt(sumSq / n);

    // Exponential moving average smoothing
    this._smoothed += (rms - this._smoothed) * damping;

    return this._smoothed;
  }

  /** The last smoothed RMS value (0.0 – ~0.3 for speech). */
  get smoothed(): number {
    return this._smoothed;
  }

  /** Reset to silence (call on speech interrupt). */
  reset() {
    this._smoothed = 0;
  }
}

// Singleton — shares the AnalyserNode from the global AudioPlayer.
export const audioAnalyser = new AudioAnalyser(audioPlayer.analyser);
