import React, { useState, useEffect } from "react";
import { IconBroadcast, IconMicrophone, IconVolume } from "@tabler/icons-react";
import { avatarEvents } from "../../networking/EventBus";
import "./StreamScreen.css";

interface StreamScreenProps {
  character: string;
}

export const StreamScreen: React.FC<StreamScreenProps> = ({ character }) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [statusText, setStatusText] = useState("Listening to microphone...");
  const displayName = character.charAt(0).toUpperCase() + character.slice(1);

  useEffect(() => {
    const unsubSpeechStart = avatarEvents.subscribe("speech_start", () => {
      setIsSpeaking(true);
      setStatusText(`${displayName} is speaking...`);
    });

    const unsubSpeechEnd = avatarEvents.subscribe("speech_end", () => {
      setIsSpeaking(false);
      setStatusText("Listening to microphone...");
    });

    const unsubTurnEnd = avatarEvents.subscribe("turn_end", () => {
      setIsSpeaking(false);
      setStatusText("Listening to microphone...");
    });

    const unsubTranscript = avatarEvents.subscribe("transcript", (event: any) => {
      if (event.text) {
        setStatusText(`You: "${event.text}"`);
      }
    });

    return () => {
      unsubSpeechStart();
      unsubSpeechEnd();
      unsubTurnEnd();
      unsubTranscript();
    };
  }, [displayName]);

  return (
    <div className="stream-screen-root" aria-label="OpenSpace Stream Screen">
      {/* Bottom floating status indicator */}
      <div className="stream-floating-panel">
        <div className={`stream-indicator-dot ${isSpeaking ? "speaking" : "listening"}`} />
        {isSpeaking ? (
          <IconVolume size={16} stroke={1.8} style={{ color: "var(--accent-indicator)" }} />
        ) : (
          <IconMicrophone size={16} stroke={1.8} style={{ color: "var(--color-success)" }} />
        )}
        <div className="stream-status-content">
          <span className="stream-panel-title">Stream Mode</span>
          <span className="stream-divider">·</span>
          <span className="stream-status-detail">{statusText}</span>
        </div>
        <div className="stream-badge">
          <IconBroadcast size={13} stroke={1.8} />
          <span>Server Mic Loop</span>
        </div>
      </div>
    </div>
  );
};
