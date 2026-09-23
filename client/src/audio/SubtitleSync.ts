const SAMPLE_RATE = 44100;
const BYTES_PER_SAMPLE = 2; // Int16 mono
const BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE;

class SubtitleSync {
  private _totalAudioBytes = 0;
  private _audioEnded = false;
  private readonly _listeners = new Set<() => void>();

  get totalBytes(): number {
    return this._totalAudioBytes;
  }

  get totalDuration(): number {
    return this._totalAudioBytes / BYTES_PER_SECOND;
  }

  get isAudioEnded(): boolean {
    return this._audioEnded;
  }

  addBytes(byteCount: number): void {
    this._totalAudioBytes += byteCount;
    this.notify();
  }

  markAudioEnd(): void {
    this._audioEnded = true;
    this.notify();
  }

  reset(): void {
    this._totalAudioBytes = 0;
    this._audioEnded = false;
    this.notify();
  }

  subscribe(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => {
      this._listeners.delete(listener);
    };
  }

  private notify(): void {
    for (const listener of this._listeners) {
      try {
        listener();
      } catch (err) {
        console.error("[SubtitleSync] Listener error:", err);
      }
    }
  }
}

export const subtitleSync = new SubtitleSync();

/**
 * SubtitleSync Architecture
 * Tracks audio chunk bytes and stream status for subtitle synchronization.
 * Fish Audio PCM: 44100 Hz, Int16 mono = 88200 bytes per second.
 */
