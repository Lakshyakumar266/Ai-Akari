import { avatarEvents } from "./EventBus";
import type { AvatarEvent } from "./types";

const WS_URL = "ws://127.0.0.1:8765";

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

    this.socket.onopen = () => {
      console.log("[AvatarSocket] Connected");
    };

    this.socket.onmessage = (message) => {
      console.log("[RAW]", message.data);
      try {
        const event = JSON.parse(
          message.data
        ) as AvatarEvent;

        console.log("[PARSED]", event);

        if (event.type === "speech") {
          console.log(
            "[CLIENT] Speech event @",
            performance.now().toFixed(3),
            event
          );
        }

        avatarEvents.emit(event);
      } catch (err) {
        console.error(
          "[AvatarSocket] Invalid packet",
          err
        );
      }
    };

    this.socket.onerror = (err) => {
      console.error(
        "[AvatarSocket] Socket error",
        err
      );
    };

    this.socket.onclose = () => {
      console.warn(
        "[AvatarSocket] Disconnected"
      );

      this.socket = null;

      if (!this.manuallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  disconnect() {
    this.manuallyClosed = true;

    if (this.reconnectTimer !== null) {
      window.clearTimeout(
        this.reconnectTimer
      );
    }

    this.socket?.close();
  }

  send(data: unknown) {
    if (
      !this.socket ||
      this.socket.readyState !==
      WebSocket.OPEN
    ) {
      return;
    }

    this.socket.send(
      JSON.stringify(data)
    );
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== null)
      return;

    console.log(
      "[AvatarSocket] Reconnecting in 2 seconds..."
    );

    this.reconnectTimer =
      window.setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 2000);
  }

  get connected() {
    return (
      this.socket?.readyState ===
      WebSocket.OPEN
    );
  }
}

export const avatarSocket =
  new AvatarSocket();