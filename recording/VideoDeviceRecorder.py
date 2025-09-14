import subprocess
import datetime
import os
import re
from typing import Final, List, Optional
from utils.VideoDeviceDetection import VideoDeviceDetection
from utils.DetectGPU import DetectGPU
from utils.VideoLogger import VideoLogger


class VideoDeviceRecorder:
    """
    Handles video recording using FFmpeg for a single video device.
    This class does not manage threading or multiple simultaneous recorders.
    Use RecordingController to run multiple instances concurrently.
    """

    CODECS: Final[dict[str, str]] = {
        "nvidia": "hevc_nvenc",  # NVIDIA H.265
        "amd": "hevc_amf",       # AMD H.265
        "cpu": "libx265"         # CPU H.265
    }

    def __init__(
        self,
        video_device: str,
        output_file: Optional[str] = None,
        resolution: str = "1280x720",
        ffmpeg_path: str = VideoDeviceDetection.FFMPEG_PATH
    ):
        if not video_device:
            raise ValueError("Video device is required for recording")

        safe_device_name = re.sub(r'[^a-zA-Z0-9_-]', '_', video_device.strip().lower())

        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_file is None:
            safe_device_name = re.sub(r'[^a-zA-Z0-9_-]', '_', video_device.strip().lower())
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"videos/cameras/{safe_device_name}_{timestamp}.mp4"


        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        self.video_device = video_device
        self.output_file = output_file
        self.resolution = resolution
        self.ffmpeg_path = ffmpeg_path

        # State
        self.is_recording: bool = False
        self.process: Optional[subprocess.Popen] = None
        self._start_time: Optional[datetime.datetime] = None

        # Detect GPU and pick codec
        gpu_vendor = DetectGPU.detect_gpu_vendor()
        self.codec = self.CODECS.get(gpu_vendor, "libx265")

        # Logger
        self.video_logger = VideoLogger()

    def _build_ffmpeg_command(self) -> List[str]:
        """
        Build the FFmpeg command for this recorder.
        """
        base_cmd = [
            self.ffmpeg_path,
            "-f", "dshow",
            "-i", f"video={self.video_device}",
            "-c:v", self.codec,
            "-s", self.resolution,
            "-an",  # Disable audio
            "-y"    # Overwrite
        ]

        common_params = [
            "-tune", "zerolatency",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p"
        ]

        input_optimizations = [
            "-fflags", "+nobuffer+flush_packets",
            "-flags", "low_delay",
            "-avioflags", "direct",
            "-probesize", "32",
            "-analyzeduration", "0"
        ]

        # GPU-specific parameters
        gpu_params: List[str] = []
        if self.codec == "hevc_nvenc":
            gpu_params = [
                "-preset", "p5",
                "-tune", "ll",
                "-rc", "constqp",
                "-qp", "23",
                "-gpu", "0",
                "-delay", "0",
                "-no-scenecut", "1"
            ]
        elif self.codec == "hevc_amf":
            gpu_params = [
                "-usage", "ultralowlatency",
                "-quality", "speed",
                "-preanalysis", "0",
                "-vbaq", "0",
                "-enforce_hrd", "0",
                "-filler_data", "0"
            ]
        elif self.codec == "libx265":
            gpu_params = [
                "-preset", "veryfast",
                "-tune", "zerolatency",
                "-x265-params", "no-scenecut=1:keyint=30:min-keyint=30"
            ]

        # Final command
        if self.codec == "hevc_amf":
            return base_cmd + input_optimizations + gpu_params + [self.output_file]
        else:
            return base_cmd + input_optimizations + common_params + gpu_params + [self.output_file]

    def start_recording(self) -> bool:
        """
        Start recording by launching FFmpeg.
        Returns True if started successfully.
        """
        if self.is_recording:
            self.video_logger.log_event(
                source=self.video_device,
                output_file=self.output_file,
                codec=self.codec,
                event="WARNING",
                status="ALREADY_RECORDING",
                extra={"message": "Recording already in progress"}
            )
            return False

        try:
            cmd = self._build_ffmpeg_command()
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            self.is_recording = True
            self._start_time = datetime.datetime.now()
            self._log_recording_event("START")
            return True
        except Exception as e:
            self.video_logger.log_event(
                source=self.video_device,
                output_file=self.output_file,
                codec=self.codec,
                event="ERROR",
                status="FAILED",
                extra={"exception": str(e)}
            )

            return False

    def stop_recording(self) -> bool:
        """
        Stop the recording gracefully.
        Returns True if stopped successfully.
        """
        if not self.is_recording or not self.process:
            self.video_logger.log_event(
            source=self.video_device,
            output_file=self.output_file,
            codec=self.codec,
            event="WARNING",
            status="NOT_RECORDING",
            extra={"message": "No recording in progress"}
        )
            return False

        try:
            # Send "q" to FFmpeg to stop
            self.process.stdin.write("q\n")
            self.process.stdin.flush()
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # Kill if graceful stop fails
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception as e:
            self.video_logger.log_event(
                source=self.video_device,
                output_file=self.output_file,
                codec=self.codec,
                event="ERROR",
                status="FAILED",
                extra={"exception": str(e)}
            )
            return False
        finally:
            self.is_recording = False
            self.process = None
            self._log_recording_event("STOP")

        return True

    def is_recording_active(self) -> bool:
        """
        Check if recording is currently active.
        """
        return self.is_recording and self.process is not None

    def _log_recording_event(self, event_type: str):
        """
        Logs START or STOP events with structured information.
        """
        duration = None
        status = "IN_PROGRESS" if event_type == "START" else "SUCCESS"
        if event_type == "STOP" and self._start_time:
            duration = (datetime.datetime.now() - self._start_time).total_seconds()

        self.video_logger.log_event(
            source=self.video_device,
            output_file=self.output_file,
            codec=self.codec,
            resolution=self.resolution,
            event=event_type,
            timestamp=datetime.datetime.now(),
            duration=duration,
            status=status
        )
