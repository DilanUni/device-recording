from utils.FFmpegUtils import FFmpegUtils
from recording.VideoRecorder import VideoRecorder
from recording.RecordingController import RecordingController
import datetime


def record_cameras(selected_devices: list[str]):
    """Inicia la grabación de una o varias cámaras pasadas en `selected_devices`."""
    controllers = []
    for idx, device in enumerate(selected_devices, start=1):
        output_file = f"videos/camera{idx}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        recorder = VideoRecorder(video_device=device, output_file=output_file)
        controller = RecordingController(recorder)
        controllers.append(controller)

    # Iniciar grabaciones
    for ctrl in controllers:
        ctrl.start()
    print(f"Recording started for devices: {selected_devices}")

    for ctrl in controllers:
        print(f"Camera {ctrl.recorder.video_device} recording: {ctrl.is_recording()}")

    input("Press Enter to stop recordings...")

    for ctrl in controllers:
        ctrl.stop()
    print("Recordings stopped.")


def main():
    success, message = FFmpegUtils.video_devices_available()
    print(message)

    if not success:
        return

    video_devices = FFmpegUtils.detect_video_devices()
    if not video_devices:
        print("No video devices detected")
        return

    print(f"Detected video devices: {video_devices}")

    print("\n--- Recording only the first camera ---")
    record_cameras([video_devices[0]])
    
"""
    if len(video_devices) >= 2:
        print("\n--- Recording first and second cameras ---")
        record_cameras(video_devices[:2])

    print("\n--- Recording all cameras ---")
    record_cameras(video_devices)

"""

if __name__ == "__main__":
    main()
