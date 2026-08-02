import type { AvatarEvent } from "./types";

type EventType = AvatarEvent["type"];

type EventMap = {
  [K in EventType]: Extract<AvatarEvent, { type: K }>;
};

type EventCallback<K extends EventType = EventType> = (event: EventMap[K]) => void;

export class EventBus {
  private readonly listeners = new Map<EventType, Set<(event: AvatarEvent) => void>>();

  emit(event: AvatarEvent): void {
    const handlers = this.listeners.get(event.type);
    console.log("[EventBus]", event);
    if (!handlers || handlers.size === 0) return;

    handlers.forEach((handler) => handler(event));
  }

  subscribe<K extends EventType>(
    type: K,
    listener: EventCallback<K>
  ): () => void {
    let handlerSet = this.listeners.get(type);

    if (!handlerSet) {
      handlerSet = new Set();
      this.listeners.set(type, handlerSet);
    }

    const castListener = listener as (event: AvatarEvent) => void;
    handlerSet.add(castListener);

    return () => {
      handlerSet?.delete(castListener);
    };
  }

  clear(): void {
    this.listeners.clear();
  }
}

export const avatarEvents = new EventBus();

/**
 * EventBus Architecture
 * Provides strongly-typed publish/subscribe event routing for inbound avatar state changes,
 * emotional expressions, animation triggers, and speech telemetry.
 */