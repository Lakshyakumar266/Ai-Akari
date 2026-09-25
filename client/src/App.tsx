import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import Scene from "./components/scene";
import SubtitleOverlay from "./components/SubtitleOverlay";
import ChatInput from "./components/ChatInput";
import { Leva } from "leva";
import { audioPlayer } from "./audio/AudioPlayer";
import { useEffect, useState } from "react";
import { avatarEvents } from "./networking/EventBus";
import { avatarSocket } from "./networking";


export default function App() {
  const [chatInputEnabled, setChatInputEnabled] = useState(
    () => avatarSocket.lastConfig?.chat_input_enabled ?? false
  );

  useEffect(() => {
    const unlock = () => {

      audioPlayer.resume();

      window.removeEventListener(
        "pointerdown",
        unlock
      );

    };

    window.addEventListener(
      "pointerdown",
      unlock,
    );

  }, []);

  // Listen for server config event (when server-side is ready)
  useEffect(() => {
    if (avatarSocket.lastConfig?.chat_input_enabled !== undefined) {
      setChatInputEnabled(avatarSocket.lastConfig.chat_input_enabled);
    }
    const unsub = avatarEvents.subscribe("config" as any, (event: any) => {
      if (typeof event.chat_input_enabled === "boolean") {
        setChatInputEnabled(event.chat_input_enabled);
      }
    });
    return unsub;
  }, []);

  return (
    <>
      <Leva collapsed={false} />

      <div
        style={{
          width: "100vw",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        <Canvas
          shadows
          dpr={[1, 2]}
          camera={{
            position: [0, 1.35, 1.25],
            fov: 26,
          }}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: "high-performance",
          }}
          onCreated={({ gl }) => {
            gl.outputColorSpace = THREE.SRGBColorSpace;
            gl.toneMapping = THREE.ACESFilmicToneMapping;
            gl.toneMappingExposure = 0.9;
          }}
        >
          <Scene />

          <OrbitControls
            makeDefault
            target={[0, 1.32, 0.2]}
            enableDamping
            dampingFactor={0.08}
            rotateSpeed={0.6}
            minDistance={1.2}
            maxDistance={3}
          />
        </Canvas>
      </div>

      <SubtitleOverlay raised={chatInputEnabled} />

      {chatInputEnabled && <ChatInput />}
    </>
  );
}