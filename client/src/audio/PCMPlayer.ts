/**
 * PCMPlayer
 *
 * Connects AudioWorkletNode to GainNode -> AnalyserNode -> Destination.
 * Handles zero-copy transferring of Float32 sample blocks to the AudioWorklet thread.
 */

import { createWorkletModuleUrl } from "./PCMProcessor";

export class PCMPlayer {
  private readonly context: AudioContext;
  private readonly gainNode: GainNode;

  private workletNode: AudioWorkletNode | null = null;
  private initPromise: Promise<void> | null = null;

  constructor(context: AudioContext, gainNode: GainNode) {
    this.context = context;
    this.gainNode = gainNode;
  }

  async init(): Promise<void> {
    if (this.workletNode) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      try {
        const url = createWorkletModuleUrl();
        await this.context.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);

        this.workletNode = new AudioWorkletNode(this.context, "pcm-processor", {
          numberOfInputs: 0,
          numberOfOutputs: 1,
          outputChannelCount: [1],
        });

        // Audio graph: Worklet -> GainNode -> AnalyserNode -> Destination
        this.workletNode.connect(this.gainNode);
        console.log(`[PCMPlayer] Worklet initialized successfully at ${this.context.sampleRate} Hz`);
      } catch (err) {
        console.error("[PCMPlayer] Failed to load AudioWorklet:", err);
      }
    })();

    return this.initPromise;
  }

  postSamples(samples: Float32Array): void {
    if (!this.workletNode) {
      this.init().then(() => {
        if (this.workletNode) {
          this.workletNode.port.postMessage(
            { type: "push", samples: samples },
            [samples.buffer]
          );
        }
      });
      return;
    }

    this.workletNode.port.postMessage(
      { type: "push", samples: samples },
      [samples.buffer]
    );
  }

  clear(): void {
    if (this.workletNode) {
      this.workletNode.port.postMessage({ type: "clear" });
    }
  }
}
