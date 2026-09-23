/**
 * SubtitleSync
 *
 * Tracks audio bytes received during a speech session to compute
 * elapsed playback time. The SubtitleOverlay reads this to know
 * how far through the text the audio has progressed.
 *
 * Fish Audio PCM: 44100 Hz, Int16 mono = 88200 bytes per second.
 */

const PCM_SAMPLE_RATE = 44100;
const BYTES_PER_SAMPLE = 2; // Int16
const BYTES_PER_SECOND = PCM_SAMPLE_RATE * BYTES_PER_SAMPLE;

class SubtitleSync {
  private _totalBytes = 0;

  /** Call this whenever an AUDIO_CHUNK packet arrives. */
  addBytes(byteCount: number): void {
    this._totalBytes += byteCount;
  }

  /** Reset at the start of each new speech session. */
  reset(): void {
    this._totalBytes = 0;
  }

  /** Elapsed audio time in seconds based on PCM bytes received. */
  get elapsedSeconds(): number {
    return this._totalBytes / BYTES_PER_SECOND;
  }

  /** Total PCM bytes received so far. */
  get totalBytes(): number {
    return this._totalBytes;
  }
}

export const subtitleSync = new SubtitleSync();
