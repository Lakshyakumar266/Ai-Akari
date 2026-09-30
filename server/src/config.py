import os

LIPSYNC_START_DELAY_MS = 1000

# Subtitle display switch:
# True  -> Subtitles are sent and rendered on screen
# False -> Subtitles are turned off (character speaks without on-screen subtitles)
ENABLE_SUBTITLES = True

# Emotion synchronization mode:
# "synced" -> Facial expression synchronizes per segment with audio playback and holds until speech finishes
# "stream" -> Legacy behavior: dispatches emotion during token streaming
# "off"    -> Disables emotion tags (stays Neutral)
EMOTION_SYNC_MODE = "synced"

# Chat input mode default:
# Note: The active conversation mode is now dynamically controlled by the connected client:
#   - Chat Screen   -> client sends ENABLE_CHAT_INPUT=True  (client-driven text/voice chat)
#   - Stream Screen -> client sends ENABLE_CHAT_INPUT=False (server-side mic & audio streaming)
ENABLE_CHAT_INPUT = True

# Tool Calling / Function Calling Configuration:
# Global switch: True by default for supported models
TOOL_CALLING_ENABLED = True
MAX_TOOL_CALL_ROUNDS = 5
TOOL_EXECUTION_TIMEOUT = float(os.getenv("TOOL_EXECUTION_TIMEOUT", "20.0"))

# LLM Temperature Configuration:
# - CHAT_TEMPERATURE: Used for natural conversational text generation (prevents hallucinations while keeping personality lively)
# - TOOL_TEMPERATURE: Used during tool-calling decisions (ensures deterministic, precise tool calls without hallucinating)
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.7"))
TOOL_TEMPERATURE = float(os.getenv("TOOL_TEMPERATURE", "0.2"))