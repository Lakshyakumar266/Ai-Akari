import {
    Environment,
} from "@react-three/drei";
import Character from "./character";
import {
    EffectComposer,
    Bloom,
} from "@react-three/postprocessing";

export default function Scene() {
    return (
        <>
            {/* Background */}
            <color attach="background" args={["#F7F7F5"]} />

            <Environment
                preset="studio"
                environmentIntensity={0.45}
            />

            {/* Soft global illumination */}
            <ambientLight intensity={0.65} />

            {/* Main light */}
            <directionalLight
                position={[2.5, 4, 4]}
                intensity={1.15}
            />

            {/* Fill */}
            <directionalLight
                position={[-3, 2, 2]}
                intensity={0.45}
            />

            {/* Rim */}
            <directionalLight
                position={[0, 4, -4]}
                intensity={0.35}
            />
                <Character />

            <EffectComposer>
                <Bloom
                    intensity={0.18}
                    luminanceThreshold={0.75}
                    luminanceSmoothing={0.9}
                />
            </EffectComposer>

        </>
    );
}