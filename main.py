from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.VideoDeviceRecorder import VideoDeviceRecorder
from recording.RecordingController import RecordingController
from recording.VideoFileRecorder import VideoFileRecorder
import datetime

def record_cameras(selected_devices: list[str]) -> None:
    controllers: list[RecordingController] = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for idx, device in enumerate(selected_devices, start=1):
        output_file = f"Videos/Cameras/{idx}_{timestamp}.mp4"
        recorder = VideoDeviceRecorder(video_device=device, output_file=output_file)
        controllers.append(RecordingController(recorder))

    # Start recordings
    for ctrl in controllers:
        ctrl.start()
    print(f"Recording started for devices: {selected_devices}")

    # Status check
    for ctrl in controllers:
        print(f"Camera '{ctrl.recorder.video_device}' -> recording: {ctrl.is_recording()}")

    input("Press Enter to stop recordings...")

    # Stop recordings
    for ctrl in controllers:
        ctrl.stop()
    print("All recordings stopped.")


def create_video_clips() -> None:
    input_file = "Videos/VideoFiles/video.mp4"
    output_dir = "Videos/VideoFiles/Clips"
    recorder = VideoFileRecorder(input_file=input_file, output_dir=output_dir)

    clip1 = recorder.create_clip(10, 20)
    clip2 = recorder.create_clip(30, 45)
    clip3 = recorder.create_clip(50, 60)

    print("Clips started:", clip1, clip2, clip3)


def main() -> None:
    # ----- Camera recording example -----
    has_devices, message = VideoDeviceDetection.has_devices()
    print(message)

    if has_devices:
        devices = VideoDeviceDetection.list_devices()
        print(f"Detected video devices: {devices}")

        if devices:
            print("\n--- Recording only the first camera ---")
            record_cameras([devices[0]])

            """
            if len(devices) >= 2:
                print("\n--- Recording first and second cameras ---")
                record_cameras(devices[:2])

            print("\n--- Recording all cameras ---")
            record_cameras(devices)
            """

    print("\n--- Creating video clips ---")
    create_video_clips()

if __name__ == "__main__":
    main()
