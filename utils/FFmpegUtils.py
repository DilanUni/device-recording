import subprocess
import re
from typing import List, Tuple

class FFmpegUtils:
    """
    Utility class for FFmpeg operations including device detection on Windows.
    Focuses only on video devices for security system.
    """
    FFMPEG_PATH: str = r".\FFMPEG\ffmpeg.exe"

    @staticmethod
    def detect_video_devices() -> List[str]:
        """
        Detects all available webcams on Windows using FFmpeg.
        Returns list of video device names. Empty list if no devices found.
        """
        cmd: List[str] = [
            FFmpegUtils.FFMPEG_PATH,
            "-list_devices", "true",
            "-f", "dshow",
            "-i", "dummy"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stderr
        except subprocess.TimeoutExpired:
            print("FFmpeg device detection timed out")
            return []
        except FileNotFoundError:
            print(f"FFmpeg not found at path: {FFmpegUtils.FFMPEG_PATH}")
            return []
        except Exception as e:
            print(f"Error running FFmpeg: {e}")
            return []

        return FFmpegUtils._extract_video_devices(output)

    @staticmethod
    def _extract_video_devices(output: str) -> List[str]:
        """
        Extracts video device names from FFmpeg output.
        Returns empty list if no video devices are found.
        """
        video_pattern = r'\[dshow @ [0-9a-f]+\]  \"(.+?)\".*\(video\)'
        matches = re.findall(video_pattern, output)
        
        if not matches:
            # Alternative pattern
            alt_pattern = r'\"(.+?)\".*\(video\)'
            matches = re.findall(alt_pattern, output)
        
        return matches

    @staticmethod
    def video_devices_available() -> Tuple[bool, str]:
        """
        Checks if at least one video device is available.
        Returns (success, message) tuple.
        """
        video_devices = FFmpegUtils.detect_video_devices()
        
        if not video_devices:
            return False, "Error: No webcams detected. Please connect at least one webcam and try again."
        
        return True, f"Found {len(video_devices)} video device(s)"