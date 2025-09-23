import datetime
import time
from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.VideoDeviceRecorder import VideoDeviceRecorder
from recording.VideoDeviceRecordingController import VideoDeviceRecordingController
from recording.VideoFileRecorder import VideoFileRecorder

def record_cameras(selected_devices: list[str]) -> list[VideoDeviceRecordingController]:
    """Start recording cameras and return controllers."""
    controllers: list[VideoDeviceRecordingController] = []
    for device in selected_devices:
        recorder = VideoDeviceRecorder(video_device=device)
        controller = VideoDeviceRecordingController(recorder)
        controller.start()
        controllers.append(controller)
        print(f"Recording started for camera: {device}")
    return controllers

def main():
    has_devices, message = VideoDeviceDetection.has_devices()
    print(message)
    devices = VideoDeviceDetection.list_devices() if has_devices else []
    if devices:
        print(f"Detected cameras: {devices}")

        camera_controllers = record_cameras(devices[:2])
        """"
    input_video = "Videos/VideoFiles/video.mp4"
    file_recorder = VideoFileRecorder(input_file=input_video, output_dir="Videos/VideoFiles/Clips")
    
    clip1 = file_recorder.create_clip(5, 10)   # 5s a 10s
    clip2 = file_recorder.create_clip(15, 25)  # 15s a 25s
    print(f"Clips started: {clip1}, {clip2}")

    
    file_recorder.wait_for_all_clips()
    print("All video clips completed.")
"""
    input("Press Enter to stop camera recordings...")
    for ctrl in camera_controllers:
        ctrl.stop()
    print("All camera recordings stopped.")
    
if __name__ == "__main__":
    main()
