import subprocess
import threading
import time
import datetime
import os
from typing import Final, List, Optional
from utils.VideoDeviceDetection import VideoDeviceDetection
from utils.DetectGPU import DetectGPU
from utils.logger import logger

class VideoDeviceRecorder:
    """
    Handles continuous video recording using FFmpeg for security system (video only).
    Records indefinitely until stopped manually.
    """
    CODECS: Final[dict] = {
        "nvidia": "hevc_nvenc",    # H.265 NVIDIA encoder
        "amd": "hevc_amf",         # H.265 AMD encoder
        "cpu": "libx265"           # H.265 software encoder
    }

    def __init__(
        self,
        video_device: str,
        output_file: str = f"videos/cameras/camera{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
        resolution: str = "1280x720",
        ffmpeg_path: str = VideoDeviceDetection.FFMPEG_PATH
    ):
        if not video_device:
            raise ValueError("Video device is required for recording")
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        self.video_device = video_device
        self.output_file = output_file
        self.resolution = resolution
        self.ffmpeg_path = ffmpeg_path
        self.is_recording = False
        self.process: Optional[subprocess.Popen] = None
        
        # Auto-detect optimal codec based on GPU
        gpu_vendor: str = DetectGPU.detect_gpu_vendor()
        self.codec = self.CODECS.get(gpu_vendor, "libx265")
        print(f"Using codec: {self.codec}")

    def _build_ffmpeg_command(self) -> List[str]:
        """
        Builds the optimized FFmpeg command for high-performance video recording.
        """
        base_cmd = [
            self.ffmpeg_path,
            "-f", "dshow",
            "-i", f"video={self.video_device}",
            "-c:v", self.codec,
            "-s", self.resolution,
            "-an",  # Disable audio recording
            "-y"   # Overwrite output file
        ]
        
        # Common optimizations for all codecs
        common_params = [
            "-tune", "zerolatency",     # Minimize latency
            "-movflags", "+faststart",  # Web optimization
            "-pix_fmt", "yuv420p"       # Most compatible pixel format
        ]
        
        # GPU-specific optimizations
        gpu_params = []
        if self.codec == "hevc_nvenc":  # NVIDIA
            gpu_params = [
                "-preset", "p5",           # Performance preset (p1-p7, p1=fastest)
                "-tune", "ll",             # Low latency
                "-rc", "constqp",          # Constant QP for consistent quality
                "-qp", "23",               # Quality level (0-51, lower=better)
                "-gpu", "0",               # Use first GPU
                "-delay", "0",             # No delay
                "-no-scenecut", "1"        # Disable scene cut detection for performance
            ]
        elif self.codec == "hevc_amf":    # AMD
            gpu_params = [
                "-usage", "ultralowlatency",
                "-quality", "speed",       # Prioritize speed over quality
                "-preanalysis", "0",       # Disable pre-analysis (0=false)
                "-vbaq", "0",              # Disable VBAQ for performance (0=false)
                "-enforce_hrd", "0",       # Disable HRD enforcement (0=false)
                "-filler_data", "0"        # Disable filler data (0=false)
            ]
        elif self.codec == "libx265":     # CPU
            gpu_params = [
                "-preset", "veryfast",     # Faster CPU encoding
                "-tune", "zerolatency",
                "-x265-params", "no-scenecut=1:keyint=30:min-keyint=30"
            ]
        
        # Input optimizations (reduce CPU usage)
        input_optimizations = [
            "-fflags", "+nobuffer+flush_packets",
            "-flags", "low_delay",
            "-avioflags", "direct",
            "-probesize", "32",
            "-analyzeduration", "0"
        ]
        
        # Para AMD, no usar -preset en common_params
        if self.codec == "hevc_amf":
            return base_cmd + input_optimizations + gpu_params + [self.output_file]
        else:
            return base_cmd + input_optimizations + common_params + gpu_params + [self.output_file]
        
    
    def start_recording(self) -> bool:
        """
        Starts continuous video recording in a separate thread.
        Returns True if recording started successfully.
        """
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return False
        
        try:
            cmd = self._build_ffmpeg_command()
            logger.info(f"Starting recording with command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            self.is_recording = True
            self._log_recording_event("START")
            
            self.monitor_thread = threading.Thread(target=self._monitor_process)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False

    def stop_recording(self) -> bool:
        """
        Stops the continuous recording by sending 'q' to FFmpeg.
        Returns True if stopped successfully.
        """
        if not self.is_recording or not self.process:
            logger.warning("No recording in progress to stop")
            return False
        
        try:
            self.process.stdin.write('q\n')
            self.process.stdin.flush()
            self.process.wait(timeout=10)
            self.is_recording = False
            self.process = None
            self._log_recording_event("STOP")
            return True
            
        except subprocess.TimeoutExpired:
            logger.warning("Force terminating recording")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.is_recording = False
            self.process = None
            self._log_recording_event("STOP")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.is_recording = False
            self.process = None
            return False

    def _monitor_process(self) -> None:
        """
        Monitors the FFmpeg process and handles output.
        """
        try:
            # Read stderr output (FFmpeg uses stderr for progress info)
            while self.is_recording and self.process:
                line = self.process.stderr.readline()
                if line:
                    print(f"FFmpeg: {line.strip()}")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error in monitor thread: {e}")

    def is_recording_active(self) -> bool:
        """
        Returns True if recording is currently active.
        """
        return self.is_recording and self.process is not None

    def record_for_duration(self, duration: int) -> bool:
        """
        Records for a specific duration (alternative method for timed recordings).
        Useful for backward compatibility.
        """
        cmd = [
            self.ffmpeg_path,
            "-f", "dshow",
            "-i", f"video={self.video_device}",
            "-c:v", self.codec,
            "-s", self.resolution,
            "-t", str(duration),
            "-an",
            "-y",
            self.output_file
        ]
        
        try:
            print(f"Recording for {duration} seconds...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 15)
            
            if result.stderr:
                print("FFmpeg output:", result.stderr)
            
            if result.returncode == 0:
                print(f"Success! Video saved as: {self.output_file}")
                return True
            else:
                print("Recording failed")
                return False
                
        except subprocess.TimeoutExpired:
            print("Recording completed")
            return True
        except Exception as e:
            print(f"Error during recording: {e}")
            return False
        
    def _log_recording_event(self, event_type: str):
            """
            Logs an event related to recording.
            event_type: "START" or "STOP"
            """
            logger.info(
                f"{event_type} Recording | Device: {self.video_device} | Codec: {self.codec} | File: {self.output_file}"
            )
        