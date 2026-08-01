import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import Scene from "./components/scene";
import { Leva } from "leva";


export default function App() {
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
    </>
  );
}