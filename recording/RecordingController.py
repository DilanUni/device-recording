from threading import Event, Thread
from typing import Optional
from .VideoRecorder import VideoRecorder

class RecordingController:
    def __init__(self, recorder: VideoRecorder):
        self.recorder = recorder
        self.stop_event = Event()
        self.recording_thread: Optional[Thread] = None

    def _run(self):
        """Internal method for the recording thread"""
        try:
            if self.recorder.start_recording():
                self.stop_event.wait()
                self.recorder.stop_recording()
        except Exception as e:
            print(f"Recording error: {e}")

    def start(self):
        """Start recording in a separate thread"""
        if self.recording_thread and self.recording_thread.is_alive():
            print("Recording already in progress")
            return
        
        self.stop_event.clear()
        self.recording_thread = Thread(target=self._run, daemon=True)
        self.recording_thread.start()

    def stop(self):
        """Stop recording"""
        self.stop_event.set()
        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)

    def is_recording(self) -> bool:
        """Check if recording is active"""
        return self.recorder.is_recording_active()