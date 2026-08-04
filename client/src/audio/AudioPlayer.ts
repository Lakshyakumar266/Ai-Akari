/**
 * AudioPlayer / AudioEngine
 *
 * Web Audio API Engine powering real-time PCM audio playback via AudioWorklet.
 *
 * Audio Graph:
 *   AudioWorkletNode ("pcm-processor")
 *             ↓
 *          GainNode        ← volume control
 *             ↓
 *        AnalyserNode      ← live RMS samples for VRM LipSync
 *             ↓
 *        Destination
 *
 * All streaming audio is raw Int16 LE PCM streamed to the AudioWorklet.
 * Zero MP3 decoding, zero decodeAudioData(), zero codec boundary artifacts.
 */

import { PCMPlayer } from "./PCMPlayer";
import { PCMQueue } from "./PCMQueue";

export class AudioPlayer {
  private readonly context: AudioContext;
  private readonly _gain: GainNode;
  private readonly _analyser: AnalyserNode;

  private readonly pcmPlayer: PCMPlayer;
  private readonly pcmQueue: PCMQueue;

  constructor() {
    this.context = new AudioContext({ latencyHint: "interactive" });

    this._gain = this.context.createGain();
    this._analyser = this.context.createAnalyser();
    this._analyser.fftSize = 2048;
    this._analyser.smoothingTimeConstant = 0;

    // Connect permanent graph: GainNode -> AnalyserNode -> Destination
    this._gain.connect(this._analyser);
    this._analyser.connect(this.context.destination);

    this.pcmPlayer = new PCMPlayer(this.context, this._gain);
    this.pcmQueue = new PCMQueue(this.pcmPlayer);

    console.log(`[AudioEngine] Initialized at ${this.context.sampleRate} Hz`);
  }

  /**
   * Push incoming raw Int16 PCM ArrayBuffer received from WebSocket.
   */
  push(chunk: ArrayBuffer): void {
    this.ensureRunning();
    this.pcmQueue.push(chunk);
  }

  /**
   * Stop audio and flush all buffers immediately (interrupt).
   */
  stop(): void {
    this.pcmQueue.flush();
    console.log("[AudioEngine] Flushed audio queue.");
  }

  async resume(): Promise<void> {
    this.ensureRunning();
    await this.pcmPlayer.init();
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
    return this.context.currentTime;
  }

  get sampleRate(): number {
    return this.context.sampleRate;
  }
}

export const audioPlayer = new AudioPlayer();
export const audioEngine = audioPlayer;