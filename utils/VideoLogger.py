import logging
import os
from datetime import datetime
import json
from threading import Lock

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class VideoLogger:
    """
    Handles structured logging for video recordings (file or device).
    Generates JSON lines logs for easy DB ingestion.
    """

    _lock = Lock()

    def __init__(self, log_name: str = None):
        self.log_name = log_name or f"recording_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.log_path = os.path.join(LOG_DIR, self.log_name)

        self.logger = logging.getLogger("VideoLogger")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path, encoding="utf-8")
            formatter = logging.Formatter('%(message)s')  # raw JSON
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(
        self,
        source: str,
        output_file: str,
        codec: str,
        resolution: str = None,
        event: str = "INFO",
        timestamp: datetime = None,
        duration: float = None,
        status: str = None,
        extra: dict = None
    ):
        """
        Logs a structured event.
        source: camera or input file
        output_file: destination file
        codec: codec used
        resolution: resolution of video
        event: "START", "STOP", "CLIP", "ERROR", etc.
        timestamp: datetime of event
        duration: duration in seconds (if applicable)
        status: "SUCCESS", "FAILED", "IN_PROGRESS"
        extra: any additional info
        """
        timestamp = timestamp or datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "event": event,
            "source": source,
            "output_file": output_file,
            "codec": codec,
            "resolution": resolution,
            "duration": duration,
            "status": status,
            "extra": extra or {}
        }

        with self._lock:
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))
