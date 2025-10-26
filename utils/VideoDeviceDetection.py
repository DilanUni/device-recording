import subprocess
import re
import os
import cv2
from typing import List, Tuple, Final
from functools import lru_cache

try:
    from utils.system_log import SystemLog
except ModuleNotFoundError:
    from system_log import SystemLog

class VideoDeviceDetection:
    """
    Video device detection and management using FFmpeg + OpenCV.
    Logging is used for status reporting instead of print().
    """

    DIR: Final[str] = os.path.dirname(os.path.abspath(__file__))
    ROOT_ROOT: Final[str] = os.path.dirname(DIR) 
    FFMPEG_PATH: Final[str] = os.path.join(ROOT_ROOT, "FFMPEG", "ffmpeg.exe")

    # Regex pattern for extracting device names from FFmpeg output
    _DEVICE_PATTERN: Final[re.Pattern] = re.compile(r'\"(.+?)\".*\(video\)')

    # Command template to list video devices with FFmpeg
    _DEVICE_CMD_TEMPLATE: Final[List[str]] = [
        FFMPEG_PATH,
        "-list_devices", "true",
        "-f", "dshow",
        "-i", "dummy"
    ]

    # Logger de clase
    log: Final[SystemLog] = SystemLog(__name__)

    @classmethod
    @lru_cache(maxsize=1)
    def get_devices(cls) -> List[str]:
        """
        Get the list of video device names detected by FFmpeg.
        Returns a cached result to avoid repeated subprocess calls.
        """
        try:
            result = subprocess.run(
                cls._DEVICE_CMD_TEMPLATE,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            cls.log.debug("FFmpeg device detection subprocess executed successfully")
            return cls._parse_output(result.stderr)

        except subprocess.TimeoutExpired:
            cls.log.error("Timeout: FFmpeg device detection exceeded 10 seconds")
            return []
        except FileNotFoundError:
            cls.log.error(f"FFmpeg executable not found at: {cls.FFMPEG_PATH}")
            return []
        except subprocess.SubprocessError as e:
            cls.log.error(f"Subprocess error during device detection: {e}")
            return []
        except Exception as e:
            cls.log.error(f"Unexpected error during device detection: {e}")
            return []

    @staticmethod
    def _parse_output(output: str) -> List[str]:
        """
        Parse FFmpeg stderr output to extract device names.
        """
        if not output:
            return []
        try:
            return VideoDeviceDetection._DEVICE_PATTERN.findall(output)
        except re.error as e:
            VideoDeviceDetection.log.error(f"Regex pattern matching failed: {e}")
            return []

    @classmethod
    @lru_cache(maxsize=1)
    def get_device_map(cls) -> List[Tuple[int, str]]:
        """
        Map OpenCV device indices to FFmpeg-reported device names.
        If no devices are detected, returns an empty list and shows a warning.
        """
        device_names = cls.get_devices()
        device_map: List[Tuple[int, str]] = []

        if not device_names:
            cls.log.warning("No video devices detected. Skipping OpenCV test loop.")
            return []

        cls.log.info(f"Testing {len(device_names)} device indices with OpenCV...")

        for opencv_idx, device_name in enumerate(device_names):
            cap = cv2.VideoCapture(opencv_idx)
            if not cap.isOpened():
                cap.release()
                continue

            ret, _ = cap.read()
            cap.release()
            if ret:
                device_map.append((opencv_idx, device_name))
                cls.log.info(f"Found working camera at index {opencv_idx}: '{device_name}'")

        if not device_map:
            cls.log.warning("No working cameras available through OpenCV.")
        else:
            cls.log.info(f"Camera detection completed. Found {len(device_map)} working cameras.")

        return device_map

    @classmethod
    def has_devices(cls) -> Tuple[bool, str]:
        """
        Check if there are any video devices available.
        """
        devices = cls.get_devices()
        device_count = len(devices)
        if device_count == 0:
            cls.log.warning("No video devices detected.")
            return False, "No video devices detected."
        cls.log.info(f"Found {device_count} video device(s).")
        return True, f"Found {device_count} video device(s)."

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the cached device list so the next call rescans hardware.
        """
        cls.get_devices.cache_clear()
        cls.log.info("Video device cache cleared - next detection will rescan hardware")


if __name__ == "__main__":
    log = SystemLog("VideoDeviceDetectionTest")

    log.info("=== Video Device Detection Test ===")

    log.info("Step 1: Checking if devices exist...")
    has_dev, msg = VideoDeviceDetection.has_devices()
    log.info(f"Result: {msg}")

    if has_dev:
        log.info("Step 2: Listing all detected devices (FFmpeg)...")
        devices = VideoDeviceDetection.get_devices()
        for idx, dev in enumerate(devices):
            log.info(f"  {idx}: {dev}")

        log.info("Step 3: Mapping OpenCV indices to device names...")
        device_map = VideoDeviceDetection.get_device_map()
        for idx, dev_name in device_map:
            log.info(f"  OpenCV Index {idx} -> {dev_name}")
