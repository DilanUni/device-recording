import subprocess
import threading
import datetime
import os
from typing import Final, List
from utils.DetectGPU import DetectGPU
from utils.VideoDeviceDetection import VideoDeviceDetection
from utils.logger import logger


class VideoFileRecorder:
    """
    Handles creation of video clips from a video file concurrently.
    Each clip runs independently in its own thread, using GPU if available.
    """

    CODECS: Final[dict[str, str]] = {
        "nvidia": "hevc_nvenc",
        "amd": "hevc_amf",
        "cpu": "libx265"
    }

    def __init__(self, input_file: str, output_dir: str = "clips",
                 ffmpeg_path: str = VideoDeviceDetection.FFMPEG_PATH) -> None:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input video not found: {input_file}")

        self.input_file = input_file
        self.output_dir = output_dir
        self.ffmpeg_path = ffmpeg_path
        os.makedirs(self.output_dir, exist_ok=True)

        gpu_vendor = DetectGPU.detect_gpu_vendor()
        self.codec = self.CODECS.get(gpu_vendor, "libx265")
        print(f"Using codec: {self.codec}")

    def _build_ffmpeg_command(self, start_time: float, end_time: float, output_file: str) -> List[str]:
        duration = end_time - start_time
        if duration <= 0:
            raise ValueError("End time must be greater than start time")

        cmd = [
            self.ffmpeg_path,
            "-ss", str(start_time),
            "-i", self.input_file,
            "-t", str(duration),
            "-c:v", self.codec,
            "-an",
            "-y",
            output_file
        ]

        if self.codec == "hevc_nvenc":
            cmd += ["-preset", "p5", "-rc", "constqp", "-qp", "0"]
        elif self.codec == "hevc_amf":
            cmd += ["-quality", "high", "-usage", "transcoding"]
        elif self.codec == "libx265":
            cmd += ["-preset", "veryfast", "-tune", "zerolatency", "-crf", "18"]

        return cmd

    def _run_clip(self, start_time: float, end_time: float, output_file: str) -> None:
        """
        Internal method that runs FFmpeg for a clip.
        Thread will terminate and release resources when done.
        """
        try:
            cmd = self._build_ffmpeg_command(start_time, end_time, output_file)
            logger.info(f"Starting clip: {output_file}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                logger.info(f"Clip finished: {output_file}")
            else:
                logger.error(f"FFmpeg failed ({process.returncode}) for {output_file}: {stderr}")
        except Exception as e:
            logger.error(f"Error creating clip {output_file}: {e}")

    def create_clip(self, start_time: float, end_time: float) -> str:
        """
        Launches a clip in its own thread. Returns the clip path immediately.
        Thread handles completion and resource cleanup internally.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_file = os.path.join(self.output_dir, f"clip_{timestamp}.mp4")
        thread = threading.Thread(target=self._run_clip, args=(start_time, end_time, output_file), daemon=True)
        thread.start()
        return output_file
