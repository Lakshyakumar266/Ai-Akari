import type { VRM } from "@pixiv/three-vrm";

const BLINK_EXPRESSION_KEY = "blink";
const BLINK_SPEED = 12;

export class BlinkController {
  private timer = 0;
  private nextBlinkInterval = 2 + Math.random() * 3;
  private blinkWeight = 0;
  private isBlinking = false;

  update(delta: number, vrm: VRM): void {
    this.timer += delta;

    if (!this.isBlinking && this.timer >= this.nextBlinkInterval) {
      this.isBlinking = true;
      this.timer = 0;
      this.nextBlinkInterval = 2 + Math.random() * 3;
    }

    if (this.isBlinking) {
      this.blinkWeight += delta * BLINK_SPEED;
      if (this.blinkWeight >= 1) {
        this.blinkWeight = 1;
        this.isBlinking = false;
      }
    } else if (this.blinkWeight > 0) {
      this.blinkWeight -= delta * BLINK_SPEED;
      if (this.blinkWeight < 0) {
        this.blinkWeight = 0;
      }
    }

    vrm.expressionManager?.setValue(BLINK_EXPRESSION_KEY, this.blinkWeight);
  }
}

/**
 * Procedural Eye Blinking Controller
 * Simulates lifelike stochastic blinking patterns by modulating the VRM blink morph target.
 */
