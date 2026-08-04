/**
 * AudioPlayer
 *
 * Web Audio API engine. Maintains the permanent audio graph:
 *   AudioBufferSourceNode -> GainNode -> AnalyserNode -> Destination
 *
 * Implements an exact AudioContext time scheduler:
 *   startTime = Math.max(nextPlaybackTime, currentTime + 0.02)
 *   source.start(startTime)
 *   nextPlaybackTime = startTime + buffer.duration
 */

export class AudioPlayer {
  private readonly context: AudioContext;
  private readonly _gain: GainNode;
  private readonly _analyser: AnalyserNode;

  private nextPlaybackTime = 0;
  private activeSources: AudioBufferSourceNode[] = [];
  private logCount = 0;

  constructor() {
    this.context = new AudioContext({ latencyHint: "interactive" });

    this._gain = this.context.createGain();
    this._analyser = this.context.createAnalyser();
    this._analyser.fftSize = 2048;
    this._analyser.smoothingTimeConstant = 0;

    // Connect graph: gain -> analyser -> destination
    this._gain.connect(this._analyser);
    this._analyser.connect(this.context.destination);

    console.log(`[AudioPlayer] Initialized AudioContext at ${this.context.sampleRate} Hz`);
  }

  /**
   * Schedule an AudioBuffer for continuous playback.
   */
  scheduleBuffer(buffer: AudioBuffer): void {
    this.ensureRunning();

    const now = this.context.currentTime;

    // Prevent accumulated drift if playback underran or queue was empty
    if (now > this.nextPlaybackTime) {
      this.nextPlaybackTime = now;
    }

    const startTime = Math.max(
      this.nextPlaybackTime,
      now + 0.02
    );

    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this._gain);

    source.start(startTime);
    this.nextPlaybackTime = startTime + buffer.duration;

    this.activeSources.push(source);

    source.onended = () => {
      this.activeSources = this.activeSources.filter((s) => s !== source);
      source.disconnect();
    };

    if (this.logCount < 10) {
      console.log(
        `[AudioScheduler] buf#${this.logCount} | ` +
        `dur=${buffer.duration.toFixed(3)}s | ` +
        `start=${startTime.toFixed(3)}s | ` +
        `next=${this.nextPlaybackTime.toFixed(3)}s | ` +
        `now=${now.toFixed(3)}s | ` +
        `bufSampleRate=${buffer.sampleRate} (ctxSampleRate=${this.context.sampleRate})`
      );
      this.logCount++;
    }
  }

  /**
   * Decode raw ArrayBuffer into AudioBuffer using AudioContext.
   */
  async decodeAudio(data: ArrayBuffer): Promise<AudioBuffer | null> {
    try {
      return await this.context.decodeAudioData(data.slice(0));
    } catch (err) {
      console.error("[AudioPlayer] decodeAudioData failed for chunk:", err);
      return null;
    }
  }

  /**
   * Stop all playing & scheduled sources immediately.
   */
  stop(): void {
    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Ignored
      }
    }
    this.activeSources = [];
    this.nextPlaybackTime = 0;
    this.logCount = 0;
    console.log("[AudioPlayer] Stopped all audio playback.");
  }

  async resume(): Promise<void> {
    this.ensureRunning();
  }

  private ensureRunning(): void {
    if (this.context.state === "suspended") {
      this.context.resume().catch(() => {});
    }
  }

  get analyser(): AnalyserNode {
    return this._analyser;
  }

  get currentTime(): number {
    return this.context.currentTime;
  }

  get scheduledEndTime(): number {
    return this.nextPlaybackTime;
  }

  get sampleRate(): number {
    return this.context.sampleRate;
  }
}

export const audioPlayer = new AudioPlayer();