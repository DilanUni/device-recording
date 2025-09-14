import subprocess
import threading
import datetime
import os
from typing import Final, List
from utils.DetectGPU import DetectGPU
from utils.VideoDeviceDetection import VideoDeviceDetection
from utils.VideoLogger import VideoLogger

class VideoFileRecorder:
    """
    Handles creation of video clips from a video file concurrently.
    Each clip runs independently in its own thread, using GPU if available.
    Logs all events with VideoLogger.
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

        # Initialize logger
        self.video_logger = VideoLogger()

        # Guardar hilos activos de clips
        self._active_threads: List[threading.Thread] = []

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
        self.video_logger.log_event(
            source=self.input_file,
            output_file=output_file,
            codec=self.codec,
            event="START",
            timestamp=datetime.datetime.now(),
            status="IN_PROGRESS",
            extra={"clip_start": start_time, "clip_end": end_time}
        )

        try:
            cmd = self._build_ffmpeg_command(start_time, end_time, output_file)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            status = "SUCCESS" if process.returncode == 0 else "FAILED"
            self.video_logger.log_event(
                source=self.input_file,
                output_file=output_file,
                codec=self.codec,
                event="STOP",
                timestamp=datetime.datetime.now(),
                duration=end_time - start_time,
                status=status,
                extra={"ffmpeg_stderr": stderr}
            )
        except Exception as e:
            self.video_logger.log_event(
                source=self.input_file,
                output_file=output_file,
                codec=self.codec,
                event="ERROR",
                timestamp=datetime.datetime.now(),
                status="FAILED",
                extra={"exception": str(e)}
            )

    def create_clip(self, start_time: float, end_time: float) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_file = os.path.join(self.output_dir, f"clip_{timestamp}.mp4")
        thread = threading.Thread(target=self._run_clip, args=(start_time, end_time, output_file), daemon=True)
        thread.start()
        self._active_threads.append(thread)
        return output_file

    def wait_for_all_clips(self) -> None:
        """
        Espera a que todos los clips que se iniciaron terminen su procesamiento.
        """
        for thread in self._active_threads:
            thread.join()
        self._active_threads.clear()
