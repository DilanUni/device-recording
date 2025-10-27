import cv2 as cv
import numpy as np
import datetime
import os
from typing import Dict, Optional, Set
from utils.system_log import SystemLog


class RecordingManager:
    """
    Manages video recording for multiple sources (cameras and video files).
    Uses OpenCV VideoWriter for simplicity and reliability.
    """
    
    def __init__(self, output_dir: str = "videos/recordings", fps: float = 30.0):
        """
        Initialize the recording manager.
        
        Args:
            output_dir: Directory where recordings will be saved
            fps: Frames per second for recordings
        """
        self.output_dir = output_dir
        self.fps = fps
        self.logger = SystemLog(self.__class__.__name__)
        
        # Active writers: {source_name: VideoWriter}
        self.writers: Dict[str, cv.VideoWriter] = {}
        
        # Recording configuration: {source_name: bool} - True to record, False to skip
        self.recording_config: Dict[str, bool] = {}
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger.info("RecordingManager initialized")
    
    def configure_source(self, source_name: str, should_record: bool) -> None:
        """
        Configure whether a specific source should be recorded.
        
        Args:
            source_name: Name of the video source
            should_record: True to enable recording, False to disable
        """
        self.recording_config[source_name] = should_record
        status = "ENABLED" if should_record else "DISABLED"
        self.logger.info(f"Recording for '{source_name}': {status}")
    
    def start_recording(self, source_name: str, frame: np.ndarray, 
                       source_type: str = "unknown") -> bool:
        """
        Start recording for a specific source.
        
        Args:
            source_name: Name of the source
            frame: Initial frame to get dimensions
            source_type: Type of source ("camera", "video", "unknown")
            
        Returns:
            True if recording started successfully
        """
        # Check if already recording
        if source_name in self.writers:
            self.logger.warning(f"'{source_name}' is already being recorded")
            return False
        
        # Check if this source is configured to be recorded
        if source_name in self.recording_config and not self.recording_config[source_name]:
            self.logger.info(f"'{source_name}' is disabled in recording config")
            return False
        
        try:
            h, w = frame.shape[:2]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename based on source type
            safe_name = source_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            filename = f"{safe_name}_{timestamp}.mp4"
            output_path = os.path.join(self.output_dir, filename)
            
            # Create VideoWriter
            fourcc = cv.VideoWriter_fourcc(*'mp4v')
            writer = cv.VideoWriter(output_path, fourcc, self.fps, (w, h))
            
            if not writer.isOpened():
                self.logger.error(f"Failed to create VideoWriter for '{source_name}'")
                return False
            
            self.writers[source_name] = writer
            self.logger.info(f"✓ Recording started: '{source_name}' → {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting recording for '{source_name}': {e}")
            return False
    
    def write_frame(self, source_name: str, frame: np.ndarray) -> None:
        """
        Write a frame to the recording if active.
        
        Args:
            source_name: Name of the source
            frame: Frame to write
        """
        if source_name in self.writers:
            try:
                self.writers[source_name].write(frame)
            except Exception as e:
                self.logger.error(f"Error writing frame for '{source_name}': {e}")
    
    def stop_recording(self, source_name: str) -> bool:
        """
        Stop recording for a specific source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            True if stopped successfully
        """
        if source_name not in self.writers:
            return False
        
        try:
            self.writers[source_name].release()
            del self.writers[source_name]
            self.logger.info(f"✓ Recording stopped: '{source_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping recording for '{source_name}': {e}")
            return False
    
    def stop_all(self) -> None:
        """Stop all active recordings."""
        if not self.writers:
            return
        
        self.logger.info(f"Stopping {len(self.writers)} recording(s)...")
        
        for source_name in list(self.writers.keys()):
            self.stop_recording(source_name)
        
        self.logger.info("All recordings stopped")
    
    def is_recording(self, source_name: str) -> bool:
        """Check if a specific source is being recorded."""
        return source_name in self.writers
    
    def get_active_recordings(self) -> Set[str]:
        """Get set of all sources currently being recorded."""
        return set(self.writers.keys())
    
    def get_recording_count(self) -> int:
        """Get number of active recordings."""
        return len(self.writers)
    
    def toggle_recording(self, source_name: str, frame: Optional[np.ndarray] = None,
                        source_type: str = "unknown") -> bool:
        """
        Toggle recording on/off for a specific source.
        
        Args:
            source_name: Name of the source
            frame: Frame (required if starting recording)
            source_type: Type of source
            
        Returns:
            True if now recording, False if stopped
        """
        if self.is_recording(source_name):
            self.stop_recording(source_name)
            return False
        else:
            if frame is not None:
                return self.start_recording(source_name, frame, source_type)
            else:
                self.logger.warning(f"Cannot start recording '{source_name}': no frame provided")
                return False