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
    <></>
  );
};
