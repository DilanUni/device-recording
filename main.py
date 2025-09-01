from utils.FFmpegUtils import FFmpegUtils
from recording.VideoRecorder import VideoRecorder
from recording.RecordingController import RecordingController

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

    controllers = []
    for idx, device in enumerate(video_devices, start=1):
        output_file: str = f"videos/camera{idx}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        recorder: VideoRecorder = VideoRecorder(video_device=device, output_file=output_file)
        controller: RecordingController = RecordingController(recorder)
        controllers.append(controller)

    # Iniciar grabación de todas las cámaras simultáneamente
    for ctrl in controllers:
        ctrl.start()
    print("Recording started for all cameras")

    for ctrl in controllers:
        print(f"Camera {ctrl.recorder.video_device} recording: {ctrl.is_recording()}")

    input("Press Enter to stop all recordings...")

    for ctrl in controllers:
        ctrl.stop()
    print("All recordings stopped")

if __name__ == "__main__":
    import datetime
    main()
