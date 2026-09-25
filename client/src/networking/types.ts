export type Viseme =
  | "aa"
  | "ih"
  | "ou"
  | "ee"
  | "oh"
  | "sil";

export interface VisemeFrame {
  t: number;
  viseme: Viseme;
  weight: number;
}

export interface SpeechTimeline {
  id: string;
  created_at: number;
  start_at: number;
  text: string;
  duration: number;
  frames: VisemeFrame[];
}

export interface TranscriptEvent {
  type: "transcript";
  text: string;
}

export interface SpeechEvent {
  delay_ms: number;
  type: "speech";
  timeline: SpeechTimeline;
}


export interface EmotionEvent {
  type: "emotion";
  emotion: string;
}

export interface AnimationEvent {
  type: "animation";
  animation: string;
}

export interface ThinkingStartEvent {
  type: "thinking_start";
}

export interface ThinkingEndEvent {
  type: "thinking_end";
}

export interface SpeechStartEvent {
  type: "speech_start";
}

export interface SpeechEndEvent {
  type: "speech_end";
}

export interface SubtitleEvent {
  type: "subtitle";
  text: string;
}

export interface SpeechSegmentEvent {
  type: "speech_segment";
  text: string;
  audio: string;
  is_last: boolean;
  segment_index: number;
  total_segments: number;
  emotion?: string;
}

export interface LlmModelOption {
  id: string;
  name: string;
}

export interface LlmProviderOption {
  id: string;
  name: string;
  description: string;
  default_model: string;
  models: LlmModelOption[];
}

export interface ConfigEvent {
  type: "config";
  chat_input_enabled: boolean;
  llm_provider?: string;
  llm_model?: string;
  available_llm_providers?: LlmProviderOption[];
}

export interface TranscriptionEvent {
  type: "transcription";
  text: string;
  is_final: boolean;
}

export interface TurnEndEvent {
  type: "turn_end";
}

export type AvatarEvent =
  | TranscriptEvent
  | SpeechEvent
  | EmotionEvent
  | AnimationEvent
  | ThinkingStartEvent
  | ThinkingEndEvent
  | SpeechStartEvent
  | SpeechEndEvent
  | SubtitleEvent
  | SpeechSegmentEvent
  | ConfigEvent
  | TranscriptionEvent
  | TurnEndEvent;