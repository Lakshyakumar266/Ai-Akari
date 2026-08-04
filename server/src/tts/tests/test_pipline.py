from src.tts.streaming_speech_pipeline import (
    StreamingSpeechPipeline,
)


def tokens():

    yield "Hello"
    yield " there."
    yield " I"
    yield " am"
    yield " Akari."
    yield " Nice"
    yield " to"
    yield " meet"
    yield " you!"


pipeline = StreamingSpeechPipeline()

reply = pipeline.speak(
    tokens()
)

print()
print(reply)