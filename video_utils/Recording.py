import subprocess
from typing import Final, Optional
from video_utils.FFmpegUtils import FFmpegUtils
from video_utils.DetectGPU import DetectGPU

class Recorder:
    """
    Handles video recording using FFmpeg.
    """
    CODECS: Final[dict] = {
        "nvidia": "hevc_nvenc",    # H.265 NVIDIA encoder
        "amd": "hevc_amf",         # H.265 AMD encoder
        "cpu": "libx265"           # H.265 software encoder (best for CPU)
    }

    def __init__(
        self,
        video_device: Optional[str],
        audio_device: Optional[str],
        output_file: str,
        duration: int = 5,
        resolution: str = "1280x720",
        ffmpeg_path: str = FFmpegUtils.FFMPEG_PATH
    ):
        
        self.video_device = video_device
        self.audio_device = audio_device
        self.output_file = output_file
        self.duration = duration
        self.resolution = resolution
        self.ffmpeg_path = ffmpeg_path
        
        # Auto-detect optimal codec based on GPU
        gpu_vendor: str = DetectGPU.detect_gpu_vendor()
        self.codec = self.CODECS.get(gpu_vendor, "libx265")
        print(self.codec)

    def record(self):
        if not self.video_device:
            raise ValueError("No video device specified.")
        
        input_devices = f'video={self.video_device}'
        if self.audio_device:
            input_devices += f':audio={self.audio_device}'
        
        cmd = [
            self.ffmpeg_path,
            "-f", "dshow",
            "-i", input_devices,
            "-c:v", self.codec,
            "-s", self.resolution,
            "-t", str(self.duration),
            "-y",  # overwrite if exists
            self.output_file
        ]
        
        print("Executing command:", " ".join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.duration + 10)
            print("Return code:", result.returncode)
            if result.stderr:
                print("FFmpeg output:", result.stderr)
            if result.stdout:
                print("Output:", result.stdout)
            
            if result.returncode == 0:
                print(f"Success! Video saved as: {self.output_file}")
            else:
                print("Recording failed")
        except subprocess.TimeoutExpired:
            print("Recording completed (timeout)")
        except Exception as e:
            print(f"Error: {e}")
