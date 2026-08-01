# Anime Wifu Client

A 3D web viewer that renders **Akari Watanabe** (*More Than a Married Couple, But Not Lovers*) as a VRM model, built with React, Vite, [Three.js](https://threejs.org/), and [@pixiv/three-vrm](https://github.com/pixiv/three-vrm).

The scene runs in real time: the character blinks and breathes on her own, tracks the camera with her eyes, and can play `.vrma` animations or shift between facial expressions — all controllable live through a [Leva](https://github.com/pmndrs/leva) debug panel.

## Features

- **VRM avatar** loaded from `public/character.vrm` via `@pixiv/three-vrm`
- **Idle motion controllers** — blinking, breathing, and camera look-at run automatically every frame
- **9 playable animations** — `Blush`, `Clapping`, `Jump`, `LookAround`, `Relax`, `Sad`, `Sleepy`, `Surprised`, `Thinking` (`.vrma` files in `public/animations/`), with cross-fading between clips
- **6 facial expressions** — `Neutral`, `Happy`, `Sad`, `Angry`, `Relaxed`, `Surprised`, smoothly blended via the VRM expression manager
- **Pose control** — relaxed standing pose with adjustable arm rotation (Leva "Pose" panel)
- **Post-processing** — Bloom via `@react-three/postprocessing`, ACES filmic tone mapping
- **OrbitControls** for a free camera around the character

## Requirements

- [Bun](https://bun.sh/) 1.x (or npm)
- A modern browser with WebGL support

## Setup

```bash
bun install
bun run dev
```

Open the printed URL (default `http://localhost:5173`).

## Scripts

| Command             | Description                          |
|---------------------|--------------------------------------|
| `bun run dev`       | Start the Vite dev server with HMR   |
| `bun run build`     | Type-check with `tsc` and build      |
| `bun run lint`      | Lint with oxlint                     |
| `bun run preview`   | Preview the production build         |

## Using the debug panel

The Leva panel on the right exposes three tabs:

- **Animation** — pick an animation to play, or `None` to return to the relaxed pose
- **Emotion** — switch the facial expression; transitions are smoothed
- **Pose** — tune the shoulder/arm angles of the relaxed pose

You can also drag to orbit, right-drag to pan, and scroll to zoom (distance is clamped to `1.2–3`).

## Project layout

```
client/
├── public/
│   ├── character.vrm         # The Akari VRM model
│   ├── favicon.svg
│   └── animations/           # .vrma animation clips
└── src/
    ├── App.tsx               # Canvas, camera, OrbitControls, Leva
    ├── components/
    │   ├── scene.tsx         # Lights, environment, bloom, <Character />
    │   ├── loader.tsx        # "Loading Character..." fallback
    │   └── character/
    │       ├── Character.tsx # Avatar load + per-frame controller update
    │       ├── AvatarLoader.ts
    │       ├── AvatarContext.ts
    │       ├── types.ts      # ANIMATIONS, EMOTIONS, visemes, DEFAULT_VRM_URL
    │       └── *Controller.ts# animation, blink, breathing, emotion,
    │                        #   lip-sync, look-at, pose
```

## Controls architecture

Every behavior is a small controller class updated each frame from `Character.tsx`:

| Controller             | Responsibility                                  |
|------------------------|-------------------------------------------------|
| `AnimationController`  | Loads/lazily caches `.vrma` clips, cross-fades   |
| `BlinkController`      | Randomized periodic blinking                     |
| `BreathingController`  | Subtle chest rotation                            |
| `LookAtController`     | Tracks the camera position                       |
| `LipSyncController`    | Maps viseme weights to expression values         |
| `EmotionController`    | Lerps expression presets towards a target        |
| `PoseController`       | Relaxed / attention / procedural arm poses       |

## Tech stack

React 19, TypeScript, Vite 8, Three.js, `@pixiv/three-vrm` + `@pixiv/three-vrm-animation`, `@react-three/fiber`, `@react-three/drei`, `@react-three/postprocessing`, Tailwind CSS 4, Leva, oxlint.
