/**
 * LipSyncController
 *
 * Drives VRM mouth expressions directly from live audio analysis.
 *
 * Architecture:
 *
 *   AudioBufferSourceNode → GainNode → AnalyserNode
 *                                           ↓
 *                                    RMS (per frame)
 *                                           ↓
 *                                    Mouth weight [0..1]
 *                                           ↓
 *                                      VRM "aa" expression
 *
 * There is exactly one clock: AudioContext.currentTime.
 * No viseme timelines, no server-generated schedules, no delay calibration.
 * The mouth moves because the audio is playing — not because a timer says so.
 *
 * Future upgrade (FFT-based vowel mapping):
 *   Replace the single "aa" drive with per-band frequency analysis:
 *   Low band  → aa
 *   Mid band  → ee / ih
 *   High band → ou / oh
 */

import type { VRM } from "@pixiv/three-vrm";
import { audioAnalyser } from "../../audio/AudioAnalyser";

// ─── Tuning constants ────────────────────────────────────────────────────────
/**
 * Damping factor for RMS smoothing (0 = instant, 1 = never responds).
 * Higher values = smoother but more lag. 0.25–0.35 works well for speech.
 */
const DAMPING = 0.3;

/**
 * RMS below this threshold is treated as silence.
 * Prevents micro-jitter from background noise opening the mouth.
 */
const MIN_RMS = 0.008;

/**
 * RMS at which the mouth reaches maximum openness.
 * Typical speech peaks around 0.10–0.15 depending on voice/volume.
 */
const MAX_RMS = 0.12;
// ─────────────────────────────────────────────────────────────────────────────

/** All mouth-shape expressions — reset to 0 before each frame. */
const MOUTH_VISEMES = ["aa", "ih", "ou", "ee", "oh"] as const;
type Viseme = typeof MOUTH_VISEMES[number];

export class LipSyncController {
  /** Current mouth open weight [0..1]. Exposed for debug/blending. */
  private _weight = 0;

  /**
   * Called every Three.js frame (via useFrame in Character.tsx).
   *
   * Reads live audio samples from AudioAnalyser, computes smoothed RMS,
   * maps it to a mouth-open weight, and applies it to the VRM expression.
   *
   * @param _delta  Three.js frame delta (not used — audio clock drives timing)
   * @param vrm     The loaded VRM instance
   */
  update(_delta: number, vrm: VRM) {
    const manager = vrm.expressionManager;
    if (!manager) return;

    // Sample the analyser and get smoothed RMS for this frame.
    // audioAnalyser reads from the AnalyserNode in AudioPlayer's live graph.
    const rms = audioAnalyser.update(DAMPING);

    // Map RMS → mouth weight [0, 1]
    // Below MIN_RMS = silence (mouth closed)
    // Above MAX_RMS = saturated open (mouth fully open)
    const target =
      rms < MIN_RMS
        ? 0
        : Math.min((rms - MIN_RMS) / (MAX_RMS - MIN_RMS), 1.0);

    this._weight = target;

    // Clear all mouth shapes before applying the new weight.
    for (const viseme of MOUTH_VISEMES) {
      manager.setValue(viseme, 0);
    }

    // Phase 4 (current): drive "aa" as a jaw-open proxy.
    // Phase 5 (future): use FFT frequency bands to blend AA/EE/OH/IH/OU.
    if (this._weight > 0) {
      manager.setValue("aa" satisfies Viseme, this._weight);
    }
  }

  /**
   * Immediately close the mouth and reset smoothing state.
   * Called on speech interrupt or avatar stop.
   */
  stop(vrm?: VRM) {
    this._weight = 0;
    audioAnalyser.reset();

    const manager = vrm?.expressionManager;
    if (!manager) return;

    for (const viseme of MOUTH_VISEMES) {
      manager.setValue(viseme, 0);
    }
  }

  /** True when audio signal is above the silence threshold. */
  isSpeaking(): boolean {
    return this._weight > 0.01;
  }

  /** Current mouth open weight (0 = closed, 1 = fully open). */
  get weight(): number {
    return this._weight;
  }
}