# AiAkari Client

An interactive 3D web interface that renders **Akari Watanabe** (*More Than a Married Couple, But Not Lovers*) as a VRM avatar, built with React, Vite, [Three.js](https://threejs.org/), and [@pixiv/three-vrm](https://github.com/pixiv/three-vrm).

The scene executes in real time: the avatar autonomously blinks and breathes, directs her gaze toward the camera, and smoothly blends `.vrma` animations and facial expressions—all configurable live through an interactive debug panel.

## Architecture & Controls

Every behavior is governed by modular controller classes invoked on each frame tick:

| Subsystem              | Responsibility                                  |
|------------------------|-------------------------------------------------|
| `AnimationController`  | Lazily loads and caches `.vrma` clips, handles cross-fading |
| `BlinkController`      | Stochastic procedural blinking                  |
| `BreathingController`  | Subtle rhythmic chest rotation                  |
| `LookAtController`     | Directs eye and head gaze toward the active camera |
| `LipSyncController`    | Synchronizes mouth morph targets via audio FFT and viseme mapping |
| `EmotionController`    | Interpolates facial sentiment presets           |
| `PoseController`       | Enforces relaxed, attention, or manual arm poses |

## Core Features

- **VRM 3D Avatar Engine** loaded via `@pixiv/three-vrm` with normalized humanoid rigging.
- **Autonomous Lifelike Motions** — stochastic eye blinking, breathing oscillations, and continuous camera gaze tracking.
- **Animation Track Library** — `.vrma` animation playback (`Blush`, `Clapping`, `Jump`, `LookAround`, `Relax`, `Sad`, `Sleepy`, `Surprised`, `Thinking`) with smooth cross-fading.
- **Facial Blend-Shape System** — `Neutral`, `Happy`, `Sad`, `Angry`, `Relaxed`, and `Surprised` presets.
- **Procedural Posing** — natural resting stance with configurable shoulder and arm drape.
- **Post-Processing & Rendering** — ACES filmic tone mapping and subtle bloom via `@react-three/postprocessing`.
- **Free Camera Controls** — full orbit, pan, and zoom around the avatar.

## Environment Requirements

- [Bun](https://bun.sh/) 1.x or [Node.js](https://nodejs.org/) (npm / pnpm)
- Modern web browser with WebGL2 support

## Getting Started

```bash
# Install dependencies
bun install

# Launch development server
bun run dev
```

Visit the local development server at `http://localhost:5173`.

## Available Scripts

| Command             | Purpose                              |
|---------------------|--------------------------------------|
| `bun run dev`       | Start Vite local development server with HMR |
| `bun run build`     | Validate types (`tsc`) and compile production bundle |
| `bun run lint`      | Execute oxlint diagnostics           |
| `bun run preview`   | Serve built production artifacts     |

## Project Structure

```
client/
├── public/
│   ├── character.vrm         # Default Akari VRM model
│   ├── favicon.svg
│   └── animations/           # .vrma motion clips
└── src/
    ├── App.tsx               # Primary canvas viewport & navigation host
    ├── components/
    │   ├── scene.tsx         # Lighting, environment map, bloom post-processing
    │   ├── loader.tsx        # Fallback loading indicator
    │   └── character/
    │       ├── Character.tsx # Avatar lifecycle & render loop coordinator
    │       ├── AvatarLoader.ts
    │       ├── AvatarContext.ts
    │       ├── types.ts      # Animation, emotion, and character manifests
    │       └── *Controller.ts# Procedural animation controllers
```

## Technology Stack

React 19, TypeScript, Vite 8, Three.js, `@pixiv/three-vrm` + `@pixiv/three-vrm-animation`, `@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`, Tailwind CSS 4, Leva, oxlint.
