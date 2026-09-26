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
  tool_calling_supported?: boolean;
}

export interface LlmProviderOption {
  id: string;
  name: string;
  description: string;
  default_model: string;
  tool_calling_supported?: boolean;
  models: LlmModelOption[];
}

export interface AvailableToolInfo {
  id: string;
  name: string;
  description: string;
  enabled?: boolean;
}

export interface ConfigEvent {
  type: "config";
  chat_input_enabled: boolean;
  llm_provider?: string;
  llm_model?: string;
  available_llm_providers?: LlmProviderOption[];
  tool_calling_enabled?: boolean;
  tool_calling_supported?: boolean;
  max_tool_calls?: number;
  available_tools?: AvailableToolInfo[];
}

export interface TranscriptionEvent {
  type: "transcription";
  text: string;
  is_final: boolean;
}

export interface TurnEndEvent {
  type: "turn_end";
}

export interface ToolStartEvent {
  type: "tool_start";
  tool: string;
}

export interface ToolEndEvent {
  type: "tool_end";
  tool: string;
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
  | TurnEndEvent
  | ToolStartEvent
  | ToolEndEvent;