import subprocess
import re
import os
import cv2
from typing import List, Tuple, Final, Optional
from functools import lru_cache


class VideoDeviceDetection:
    """
    Video device detection and management using FFmpeg.
    
    Provides webcam and video input device detection with caching
    and subprocess handling for Windows DirectShow devices.
    
    This class is specifically designed for video capture devices.
    
    Class Attributes:
        ROOT_DIR (str): Root directory of the project
        FFMPEG_PATH (str): Full path to the FFmpeg executable
        MAX_CAMERA_INDEX (int): Maximum camera index to test
        _DEVICE_PATTERN (re.Pattern): Regex pattern for device parsing
        _DEVICE_CMD_TEMPLATE (List[str]): Command template for device detection
    """
    
    MAX_CAMERA_INDEX: Final[int] = 3  

    # Root project directory (one level above this file)
    ROOT_DIR: Final[str] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FFMPEG_PATH: Final[str] = os.path.join(ROOT_DIR, "FFMPEG", "ffmpeg.exe")
    
    _DEVICE_PATTERN: Final[re.Pattern] = re.compile(r'\"(.+?)\".*\(video\)')
    
    _DEVICE_CMD_TEMPLATE: Final[List[str]] = [
        FFMPEG_PATH,
        "-list_devices", "true",
        "-f", "dshow",
        "-i", "dummy"
    ]
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_devices(cls) -> List[str]:
        """
        Retrieve list of available video capture devices.
        """
        try:
            result = subprocess.run(
                cls._DEVICE_CMD_TEMPLATE,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            return cls._parse_output(result.stderr)
            
        except subprocess.TimeoutExpired:
            print("[ERROR] Timeout: FFmpeg device detection exceeded 10 seconds")
            return []
        except FileNotFoundError:
            print(f"[ERROR] FFmpeg executable not found at: {cls.FFMPEG_PATH}")
            return []
        except subprocess.SubprocessError as e:
            print(f"[ERROR] Subprocess error during device detection: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Unexpected error during device detection: {e}")
            return []
    
    @staticmethod
    def _parse_output(output: str) -> List[str]:
        """
        Extract video device names from FFmpeg stderr output.
        """
        if not output:
            return []
            
        try:
            return VideoDeviceDetection._DEVICE_PATTERN.findall(output)
        except re.error as e:
            print(f"[ERROR] Regex pattern matching failed: {e}")
            return []
    
    @classmethod
    def get_device_map(cls, max_test: Optional[int] = None) -> List[Tuple[int, str]]:
        """
        Map OpenCV device indices to FFmpeg device names.
        """
        if max_test is None:
            max_test = cls.MAX_CAMERA_INDEX
            
        device_names = cls.get_devices()
        device_map: List[Tuple[int, str]] = []
        
        print(f"[INFO] Testing OpenCV camera indices 0-{max_test-1}...")
        
        for opencv_idx in range(max_test):
            cap = cv2.VideoCapture(opencv_idx)
            
            if not cap.isOpened():
                cap.release()
                continue
            
            ret, _ = cap.read()
            cap.release()
            
            if ret:
                device_name = (
                    device_names[len(device_map)] 
                    if len(device_map) < len(device_names)
                    else f"Camera {opencv_idx}"
                )
                device_map.append((opencv_idx, device_name))
                print(f"[INFO] Found working camera at index {opencv_idx}: '{device_name}'")
        
        print(f"[INFO] Camera detection completed. Found {len(device_map)} working cameras.")
        return device_map
    
    @classmethod
    def has_devices(cls) -> Tuple[bool, str]:
        """
        Check availability of video capture devices with detailed status information.
        """
        devices = cls.get_devices()
        device_count = len(devices)
        
        if device_count == 0:
            return False, "No video devices detected."
        
        return True, f"Found {device_count} video device(s)."
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the LRU cache for device detection.
        """
        cls.get_devices.cache_clear()
        print("[INFO] Video device cache cleared - next detection will rescan hardware")


if __name__ == "__main__":
    print("=== Video Device Detection Test ===")
    
    has_devices, status_message = VideoDeviceDetection.has_devices()
    print(f"Device Status: {status_message}")
    
    if not has_devices:
        print("No video devices available for testing.")
        exit(1)
    
    print("\n=== Available Devices ===")
    devices = VideoDeviceDetection.get_devices()
    for i, device_name in enumerate(devices):
        print(f"  {i}: {device_name}")
    
    print(f"\n=== OpenCV Device Mapping (Testing indices 0-{VideoDeviceDetection.MAX_CAMERA_INDEX-1}) ===")
    device_map = VideoDeviceDetection.get_device_map()
    
    if device_map:
        print("\nOpenCV Index -> Device Name:")
        for opencv_idx, device_name in device_map:
            print(f"  cv2.VideoCapture({opencv_idx}) -> '{device_name}'")
    else:
        print("No functional OpenCV devices found.")
    
    print("\n=== Cache Test ===")
    print("First call (cache miss)...")
    devices_1 = VideoDeviceDetection.get_devices()
    print("Second call (cache hit)...")
    devices_2 = VideoDeviceDetection.get_devices()
    print(f"Results identical: {devices_1 == devices_2}")
    
    print("\nClearing cache...")
    VideoDeviceDetection.clear_cache()
    print("Cache cleared successfully.")
