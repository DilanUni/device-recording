import subprocess
import re
from typing import Tuple, Optional, Final, List

class FFmpegUtils:
    """
    Utility class for FFmpeg operations including device detection on Windows.
    """
    FFMPEG_PATH: Final[str] = r".\FFMPEG\ffmpeg.exe"

    @staticmethod
    def detect_devices() -> Tuple[Optional[str], Optional[str]]:
        """
        Detects the first available webcam and microphone on Windows using FFmpeg.
        Returns a tuple (video_device, audio_device).
        """
        cmd: Final[List[str]] = [
            FFmpegUtils.FFMPEG_PATH,
            "-list_devices", "true",
            "-f", "dshow",
            "-i", "dummy"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        video_device = None
        audio_device = None
        
        video_matches: List[str] = re.findall(r'"(.*?)"\s*\(video\)', output)
        if video_matches:
            video_device = video_matches[0]
        
        audio_matches: List[str] = re.findall(r'"(.*?)"\s*\(audio\)', output)
        if audio_matches:
            audio_device = audio_matches[0]
        
        return video_device, audio_device
