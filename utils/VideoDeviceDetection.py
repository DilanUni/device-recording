import subprocess
import re
from typing import List, Tuple


class VideoDeviceDetection:
    """
    Detects video capture devices (e.g., webcams) on Windows using FFmpeg.
    This class is limited to video sources only.
    """

    FFMPEG_PATH: str = r".\FFMPEG\ffmpeg.exe"

    @classmethod
    def list_devices(cls) -> List[str]:
        """
        Returns a list of available video devices.
        If no devices are found, returns an empty list.
        """
        cmd = [
            cls.FFMPEG_PATH,
            "-list_devices", "true",
            "-f", "dshow",
            "-i", "dummy"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stderr
        except subprocess.TimeoutExpired:
            print("Timeout: FFmpeg device detection took too long.")
            return []
        except FileNotFoundError:
            print(f"FFmpeg not found at: {cls.FFMPEG_PATH}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []

        return cls._parse_output(output)

    @staticmethod
    def _parse_output(output: str) -> List[str]:
        """
        Extracts video device names from FFmpeg output.
        """
        pattern = r'\"(.+?)\".*\(video\)'
        return re.findall(pattern, output)

    @classmethod
    def has_devices(cls) -> Tuple[bool, str]:
        """
        Checks if there are available video devices.
        Returns (status, message).
        """
        devices = cls.list_devices()
        if not devices:
            return False, "No video devices detected."
        return True, f"Found {len(devices)} video device(s)."
