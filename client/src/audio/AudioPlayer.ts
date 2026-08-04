/**
 * AudioPlayer
 *
 * Decodes and schedules audio chunks for gapless playback using the Web Audio API.
 *
 * Design:
 *   - A single AudioContext is the source of truth for time.
 *   - Each incoming chunk is decoded, then scheduled to start precisely
 *     when the previous chunk ends (_nextStartTime).
 *   - Sample rate is NOT hardcoded — the AudioContext uses its default
 *     (auto-matched by the OS) and WAV headers are decoded natively by
 *     decodeAudioData, which handles any sample rate automatically.
 *   - stop() clears the schedule so an interrupt takes effect immediately.
 */

export class AudioPlayer {
  private readonly context: AudioContext;

  /**
   * AudioContext time (seconds) at which the next buffered chunk should start.
   * Advances by each decoded buffer's duration.
   */
  private _nextStartTime = 0;

  /**
   * All currently active BufferSource nodes.
   * Tracked so stop() can disconnect them all.
   */
  private _activeSources: AudioBufferSourceNode[] = [];

  constructor() {
    this.context = new AudioContext({
      // "playback" prioritises low-latency-accurate scheduling over
      // interactive latency — best for streaming audio queues.
      latencyHint: "playback",
    });
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Decode one audio chunk and schedule it to play
   * immediately after the previous chunk ends.
   *
   * Returns a Promise that resolves when the chunk has been *scheduled*
   * (not when it finishes playing). AudioQueue chains these promises to
   * prevent race conditions when chunks arrive faster than decode speed.
   */
  async play(audio: ArrayBuffer): Promise<void> {
    // Resume context if browser suspended it (autoplay policy).
    await this._ensureRunning();

    let buffer: AudioBuffer;

    try {
      buffer = await this.context.decodeAudioData(audio.slice(0));
    } catch (err) {
      // If this fires, the audio format is not supported by the browser.
      // Switch fish_stream.py to "mp3" or "opus" format.
      console.error("[AudioPlayer] decodeAudioData FAILED — format unsupported?", err);
      return;
    }

    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);

    // Schedule: clamp to "now + tiny lookahead" to avoid scheduling in the past.
    const startAt = Math.max(
      this.context.currentTime + 0.05,
      this._nextStartTime,
    );

    source.start(startAt);

    // Advance the cursor by exactly one buffer duration for gapless continuity.
    this._nextStartTime = startAt + buffer.duration;

    // Track source so stop() can clean up.
    this._activeSources.push(source);

    source.onended = () => {
      this._activeSources = this._activeSources.filter((s) => s !== source);
    };

    console.debug(
      `[AudioPlayer] scheduled +${buffer.duration.toFixed(3)}s @ ${startAt.toFixed(3)} | queue end: ${this._nextStartTime.toFixed(3)}`,
    );
  }

  /**
   * Immediately stop all queued / playing audio and reset the schedule.
   * Call this when an INTERRUPT packet arrives.
   */
  stop() {
    for (const source of this._activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Already stopped — ignore.
      }
    }

    this._activeSources = [];
    this._nextStartTime = 0;

    console.log("[AudioPlayer] Stopped — queue cleared");
  }

  /**
   * Resume a suspended AudioContext.
   * Must be called inside a user-gesture handler at least once.
   */
  async resume() {
    await this._ensureRunning();
  }

  // ---------------------------------------------------------------------------
  // Clock exposure
  // ---------------------------------------------------------------------------

  /**
   * The AudioContext's live clock.
   * Use this for any timing that must stay in sync with audio playback.
   */
  get currentTime(): number {
    return this.context.currentTime;
  }

  /**
   * The AudioContext time (seconds) when the last scheduled chunk ends.
   *
   * LipSyncController can use this to know when speech audio will finish,
   * allowing it to switch from delta-accumulation to AudioContext-clock timing.
   */
  get scheduledEndTime(): number {
    return this._nextStartTime;
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  private async _ensureRunning() {
    if (this.context.state === "suspended") {
      await this.context.resume();
    }
  }
}

// Global singleton — shared by AvatarSocket and LipSyncController.
export const audioPlayer = new AudioPlayer();