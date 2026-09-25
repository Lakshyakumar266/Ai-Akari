import React from "react";
import { IconBroadcast, IconMicrophone } from "@tabler/icons-react";
import "./StreamScreen.css";

interface StreamScreenProps {
  character: string;
}

export const StreamScreen: React.FC<StreamScreenProps> = ({ character }) => {
  const displayName = character.charAt(0).toUpperCase() + character.slice(1);

  return (
    <div className="stream-screen-root" aria-label="OpenSpace Stream Screen">
      {/* Bottom status floating pill */}
      <div className="stream-floating-panel">
        <IconBroadcast size={18} stroke={1.8} style={{ color: "var(--accent-indicator)" }} />
        <div>
          <span className="stream-panel-title">Server-Driven Audio Active</span>
          <span style={{ margin: "0 8px", opacity: 0.4 }}>|</span>
          <span>Speak directly to your microphone to converse with {displayName}</span>
        </div>
        <IconMicrophone size={16} stroke={1.6} style={{ color: "var(--color-success)" }} />
      </div>
    </div>
  );
};
