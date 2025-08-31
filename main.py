import datetime
from video_utils.FFmpegUtils import FFmpegUtils
from video_utils.Recording import Recorder

video_device, audio_device = FFmpegUtils.detect_devices()
print("Video device:", video_device)
print("Audio device:", audio_device)

output_file = f"videos/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

recorder = Recorder(
    video_device=video_device,
    audio_device=audio_device,
    output_file=output_file,
    duration=5,
    # codec_name="H.265_HEVC",
    # resolution="1360x768"
)

recorder.record()