from threading import Event, Thread
from typing import Optional
from .VideoDeviceRecorder import VideoDeviceRecorder


class VideoDeviceRecordingController:
    """
    Controls the lifecycle of a single VideoDeviceRecorder in a separate thread.
    Allows starting and stopping recording safely, without blocking the main thread.
    """

    def __init__(self, recorder: VideoDeviceRecorder):
        self.recorder = recorder
        self.stop_event = Event()
        self.recording_thread: Optional[Thread] = None
        self.last_error: Optional[Exception] = None

    def _run(self):
        """Internal method executed inside the recording thread."""
        try:
            if self.recorder.start_recording():
                # Wait until stop() is called
                self.stop_event.wait()
                self.recorder.stop_recording()
        except Exception as e:
            self.last_error = e
            print(f"[RecordingController] Recording error: {e}")

    def start(self):
        """Start recording in a separate thread."""
        if self.recording_thread and self.recording_thread.is_alive():
            print("[RecordingController] Recording already in progress")
            return

        self.stop_event.clear()
        self.last_error = None
        self.recording_thread = Thread(target=self._run, daemon=True)
        self.recording_thread.start()

    def stop(self):
        """Stop recording and wait for thread to finish."""
        self.stop_event.set()
        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)

    def is_recording(self) -> bool:
        """Check if recording is active."""
        return (
            self.recording_thread is not None
            and self.recording_thread.is_alive()
            and self.recorder.is_recording_active()
        )
