LIPSYNC_START_DELAY_MS = 1000

# Emotion synchronization mode:
# "synced" -> Facial expression synchronizes with audio playback and holds until speech finishes
# "stream" -> Legacy behavior: dispatches emotion during token streaming
# "off"    -> Disables emotion tags (stays Neutral)
EMOTION_SYNC_MODE = "stream"