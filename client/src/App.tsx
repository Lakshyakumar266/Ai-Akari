import * as THREE from "three";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import Scene from "./components/scene";
import SubtitleOverlay from "./components/SubtitleOverlay";
import { Leva } from "leva";
import { audioPlayer } from "./audio/AudioPlayer";
import { useEffect } from "react";
import { Sidebar } from "./navigation/Sidebar";
import { useNavigation } from "./navigation/useNavigation";
import { ThemeProvider } from "./navigation/ThemeContext";
import { OverviewScreen } from "./components/screens/OverviewScreen";
import { ChatScreen } from "./components/screens/ChatScreen";
import { StreamScreen } from "./components/screens/StreamScreen";
import { GalleryScreen } from "./components/screens/GalleryScreen";
import "./App.css";

function CameraRig({ isOverview }: { isOverview: boolean }) {
  useFrame((state, delta) => {
    const targetX = isOverview ? -0.26 : 0;
    state.camera.position.x = THREE.MathUtils.damp(state.camera.position.x, targetX, 5, delta);
  });
  return null;
}

function AppContent() {
  const { screen, character, navigate } = useNavigation();

  // Unlock Web Audio on first pointer interaction
  useEffect(() => {
    const unlock = () => {
      audioPlayer.resume();
      window.removeEventListener("pointerdown", unlock);
    };

    window.addEventListener("pointerdown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
    };
  }, []);

  return (
    <div className="app-shell">
      {/* ─── 1. Persistent Shared Sidebar ──────────────────────────────────── */}
      <Sidebar
        currentScreen={screen}
        currentCharacter={character}
        onNavigate={(targetScreen) => navigate(targetScreen, character)}
      />

      {/* ─── 2. Main Viewport & 3D Avatar Canvas ────────────────────────────── */}
      <main className="main-viewport">
        <Canvas
          shadows
          dpr={[1, 2]}
          camera={{
            position: [screen === "characters" ? -0.26 : 0, 1.35, 1.25],
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
          <CameraRig isOverview={screen === "characters"} />
          <Scene />

          <OrbitControls
            makeDefault
            target={[screen === "characters" ? -0.26 : 0, 1.32, 0.2]}
            enableDamping
            dampingFactor={0.08}
            rotateSpeed={0.6}
            minDistance={1.2}
            maxDistance={3}
          />
        </Canvas>

        {/* ─── 3. Screen View Layer ────────────────────────────────────────── */}
        {screen === "characters" && (
          <OverviewScreen
            character={character}
            onStartChat={() => navigate("chat", character)}
          />
        )}

        {screen === "chat" && (
          <ChatScreen
            character={character}
            onBackToOverview={() => navigate("characters", character)}
          />
        )}

        {screen === "stream" && (
          <StreamScreen
            character={character}
          />
        )}

        {screen === "galary" && (
          <GalleryScreen
            character={character}
          />
        )}

        {/* Global subtitle overlay with dynamic height based on active screen */}
        <SubtitleOverlay raised={screen === "chat"} />
      </main>

      <Leva collapsed={true} />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}