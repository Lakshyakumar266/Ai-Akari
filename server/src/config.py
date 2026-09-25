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
