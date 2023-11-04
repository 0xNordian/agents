import asyncio
import livekit.rtc as rtc
from livekit.processors.vad import VAD, VADProcessor
from livekit import agents
from typing import AsyncIterator

SAMPLE_RATE = 48000
NUM_CHANNELS = 1


async def vad_agent(ctx: agents.JobContext):

    source = rtc.AudioSource(SAMPLE_RATE, NUM_CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track("echo", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await ctx.room.local_participant.publish_track(track, options)

    async def process_track(track: rtc.Track):
        audio_stream = rtc.AudioStream(track)
        vad_processor = VADProcessor(
            left_padding_ms=200, silence_threshold_ms=250)

        vad_results = vad_processor.start(audio_stream)

        async for processor_event in vad_results:
            if processor_event.type == agents.ProcessorEventType.ERROR:
                continue
            event = processor_event.data
            print(f"VAD Event: {event.type}")
            if event.type == agents.VoiceActivityDetectionProcessorEventType.STARTED:
                print("VAD - Voice Started")
            elif event.type == agents.VoiceActivityDetectionProcessorEventType.FINISHED:
                asyncio.create_task(ctx.room.local_participant.publish_data(
                    f"Voice Detected For: {len(event.frames) * 10.0 / 1000.0} seconds"))
                for frame in event.frames:
                    resampled = frame.remix_and_resample(
                        SAMPLE_RATE, NUM_CHANNELS)
                    await source.capture_frame(resampled)
                print(
                    f"VAD - Voice Finished. Frame Count: {len(event.frames)}")

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind != rtc.TrackKind.KIND_AUDIO or track.name == "echo":
            return
        asyncio.create_task(process_track(track))