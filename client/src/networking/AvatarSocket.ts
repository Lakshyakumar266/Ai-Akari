/**
 * AvatarSocket
 *
 * WebSocket bridge between the Python server and the browser.
 *
 * Protocol:
 *   - JSON text frames  → parsed as AvatarEvent, emitted on avatarEvents bus
 *   - Binary frames     → packet[0] is the packet type:
 *       1 = AUDIO_CHUNK     → enqueued on audioQueue for gapless playback
 *       2 = AUDIO_END       → stream finished (log + optionally emit event)
 *       3 = AUDIO_INTERRUPT → stop all audio immediately
 *
 * LipSync Clock:
 *   _lipSyncCursor mirrors AudioPlayer._nextStartTime.
 *   Both use:  startAt = max(audioCtx.currentTime + 0.05, cursor)
 *              cursor  = startAt + duration
 *   This means each speech event gets a scheduledAt time that exactly
 *   matches when its audio will start playing — even before any binary
 *   chunk has been decoded. TimelinePlayer reads audioPlayer.currentTime
 *   and subtracts scheduledAt to get the true elapsed position.
 */

import { avatarEvents } from "./EventBus";
import type { AvatarEvent } from "./types";
import { audioPlayer } from "../audio/AudioPlayer";
import { audioQueue } from "../audio/AudioQueue";

const WS_URL = "ws://127.0.0.1:8765";

// Binary packet type constants — mirror server/src/bridge/protocol.py BinaryPacket
const PACKET_AUDIO_CHUNK = 1;
const PACKET_AUDIO_END = 2;
const PACKET_AUDIO_INTERRUPT = 3;

// Lookahead seconds — must match AudioPlayer's 0.05 constant exactly.
const SCHEDULE_LOOKAHEAD = 0.05;

class AvatarSocket {
  private socket: WebSocket | null = null;

  private reconnectTimer: number | null = null;

  private manuallyClosed = false;

  /**
   * Tracks when the next speech sentence's audio will start playing.
   * Mirrors AudioPlayer._nextStartTime — advanced by each timeline.duration
   * using the same scheduling formula so lipsync stays in lock-step with audio.
   */
  private _lipSyncCursor = 0;

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

    // Must be set before onmessage fires.
    this.socket.binaryType = "arraybuffer";

    this.socket.onopen = () => {
      console.log("[AvatarSocket] Connected");

      // Resume AudioContext on the first user-gesture-adjacent event.
      // WebSocket open is not a user gesture, but resume() is safe to call here
      // in case the context was suspended before connection.
      audioPlayer.resume().catch(() => {
        // Will be resumed on the first binary packet or click.
      });
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
            // Slice off the type byte, hand raw audio bytes to the queue.
            // AudioQueue serialises decoding so chunks play in order with no gaps.
            const audioBytes = packet.slice(1).buffer;

            audioQueue.push(audioBytes);

            console.log(
              `[Audio] chunk ${packet.length - 1}B | ` +
              `queueEnd=${audioPlayer.scheduledEndTime.toFixed(3)}s`,
            );

            break;
          }

          case PACKET_AUDIO_END: {
            console.log(
              "[AvatarSocket] Audio stream ended | " +
              `audioCtx.currentTime=${audioPlayer.currentTime.toFixed(3)} ` +
              `scheduledEnd=${audioPlayer.scheduledEndTime.toFixed(3)}`,
            );

            break;
          }

          case PACKET_AUDIO_INTERRUPT: {
            console.log("[AvatarSocket] Interrupt received — stopping audio");

            // flush() resets the promise chain AND calls player.stop()
            audioQueue.flush();

            // Reset lipsync cursor so next sentence starts fresh.
            this._lipSyncCursor = 0;

            break;
          }

          default:
            console.warn("[AvatarSocket] Unknown binary packet type:", type);
        }

        return;
      }

      // -----------------------------------------------------------------------
      // JSON path — avatar events (transcript, speech, emotion, animation, ...)
      // -----------------------------------------------------------------------
      console.log("[RAW]", message.data);

      try {
        const event = JSON.parse(message.data) as AvatarEvent;

        console.log("[PARSED]", event);

        if (event.type === "speech") {
          //
          // Compute scheduledAt using the same formula AudioPlayer uses
          // for _nextStartTime. This runs synchronously when the JSON
          // arrives — before any binary chunk has been decoded — so
          // scheduledAt is always correct regardless of decode order.
          //
          const scheduledAt = Math.max(
            audioPlayer.currentTime + SCHEDULE_LOOKAHEAD,
            this._lipSyncCursor,
          );

          // Advance cursor by this sentence's audio duration.
          // AudioPlayer advances by buffer.duration after decode;
          // timeline.duration is the same value from Fish's alignment.
          this._lipSyncCursor = scheduledAt + event.timeline.duration;

          console.log(
            "[LipSync] speech scheduled |",
            `startAt=${scheduledAt.toFixed(3)}s |`,
            `cursor→${this._lipSyncCursor.toFixed(3)}s |`,
            event.timeline.text,
          );

          // Emit with scheduledAt attached — TimelinePlayer will use
          // audioPlayer.currentTime - scheduledAt as its elapsed position.
          avatarEvents.emit({ ...event, scheduledAt });

          return;
        }

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
    if (
      !this.socket ||
      this.socket.readyState !== WebSocket.OPEN
    ) {
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