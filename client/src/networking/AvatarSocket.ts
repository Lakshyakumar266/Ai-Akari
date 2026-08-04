/**
 * AvatarSocket
 *
 * WebSocket bridge between the Python server and the browser.
 *
 * Protocol:
 *   - Binary frames → packet[0] is the packet type:
 *       1 = AUDIO_CHUNK     → enqueued on audioQueue for gapless playback
 *       2 = AUDIO_END       → stream finished
 *       3 = AUDIO_INTERRUPT → stop all audio immediately
 *
 *   - JSON text frames → AvatarEvent dispatched on avatarEvents bus:
 *       transcript  → subtitle display
 *       emotion     → VRM expression
 *       animation   → body animation
 *       thinking_*  → UI state
 *       speech_*    → UI state
 *       speech      → carries text/timeline (received but not used for lipsync)
 *
 * LipSync:
 *   Audio-reactive. No timing cursors, no scheduledAt, no delay_ms.
 *   LipSyncController reads live RMS from the AnalyserNode every frame.
 */

import { avatarEvents } from "./EventBus";
import type { AvatarEvent } from "./types";
import { audioPlayer } from "../audio/AudioPlayer";
import { audioQueue } from "../audio/AudioQueue";

const WS_URL = "ws://127.0.0.1:8765";

const PACKET_AUDIO_CHUNK = 1;
const PACKET_AUDIO_END = 2;
const PACKET_AUDIO_INTERRUPT = 3;

class AvatarSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private manuallyClosed = false;

  connect() {
    if (
      this.socket &&
      (
        this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING
      )
    ) {
      return;
    }

    console.log("[AvatarSocket] Connecting...");

    this.socket = new WebSocket(WS_URL);
    this.socket.binaryType = "arraybuffer";

    this.socket.onopen = () => {
      console.log("[AvatarSocket] Connected");
      audioPlayer.resume().catch(() => {});
    };

    this.socket.onmessage = (message) => {
      // -----------------------------------------------------------------------
      // Binary path — audio packets
      // -----------------------------------------------------------------------
      if (message.data instanceof ArrayBuffer) {
        const packet = new Uint8Array(message.data);
        const type = packet[0];

        switch (type) {
          case PACKET_AUDIO_CHUNK: {
            const audioBytes = packet.slice(1).buffer;
            audioQueue.push(audioBytes);
            console.log(
              `[Audio] chunk ${packet.length - 1}B | end=${audioPlayer.scheduledEndTime.toFixed(3)}s`,
            );
            break;
          }

          case PACKET_AUDIO_END: {
            console.log(
              `[Audio] stream end | ctx=${audioPlayer.currentTime.toFixed(3)}s`,
            );
            break;
          }

          case PACKET_AUDIO_INTERRUPT: {
            console.log("[Audio] interrupt");
            audioQueue.flush();
            break;
          }

          default:
            console.warn("[AvatarSocket] Unknown binary packet type:", type);
        }

        return;
      }

      // -----------------------------------------------------------------------
      // JSON path — avatar events
      // -----------------------------------------------------------------------
      try {
        const event = JSON.parse(message.data as string) as AvatarEvent;

        console.log("[AvatarSocket]", event.type, event);

        // speech events are still received and emitted (carry sentence text)
        // but LipSyncController no longer uses them — it reads audio directly.
        avatarEvents.emit(event);
      } catch (err) {
        console.error("[AvatarSocket] Invalid packet", err);
      }
    };

    this.socket.onerror = (err) => {
      console.error("[AvatarSocket] Socket error", err);
    };

    this.socket.onclose = () => {
      console.warn("[AvatarSocket] Disconnected");
      this.socket = null;
      if (!this.manuallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  disconnect() {
    this.manuallyClosed = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
  }

  send(data: unknown) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    this.socket.send(JSON.stringify(data));
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== null) return;

    console.log("[AvatarSocket] Reconnecting in 2 seconds...");

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 2000);
  }

  get connected() {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}

export const avatarSocket = new AvatarSocket();