import React from "react";
import ChatInput from "../ChatInput";
import "./ChatScreen.css";

export interface ChatScreenProps {
  character: string;
  onBackToOverview?: () => void;
}

export const ChatScreen: React.FC<ChatScreenProps> = ({ character }) => {
  return (
    <div className="chat-screen-root" aria-label="Interactive Chat Screen">
      <ChatInput character={character} />
    </div>
  );
};

/**
 * Chat Screen Viewport
 * Hosts the primary interactive conversation surface and floating glassmorphic input controls.
 */
