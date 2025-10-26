from typing import Dict
from utils.VideoDeviceDetection import VideoDeviceDetection

# Define the zones
ZONES = ["ENTRADA", "SALIDA", "ESTACIONAMIENTO", "BODEGA"]

def assign_cameras() -> Dict[str, int]:
    """
    Allows the user to dynamically assign cameras to zones.
    Returns a dictionary SENSOR_TO_CAMERA.
    """
    # Get the map of available devices
    device_map = VideoDeviceDetection.get_device_map()

    if not device_map:
        print("No cameras available.")
        return {}

    print("Detected cameras:")
    for idx, name in device_map:
        print(f"  [{idx}] {name}")

    sensor_to_camera: Dict[str, int] = {}

    for zone in ZONES:
        while True:
            try:
                cam_idx = int(input(f"Select camera index for {zone}: "))
                if cam_idx not in [idx for idx, _ in device_map]:
                    print("Invalid index, try again.")
                    continue
                sensor_to_camera[zone] = cam_idx
                break
            except ValueError:
                print("You must enter a valid number.")

    print("\nCamera assignment complete:")
    for zone, cam_idx in sensor_to_camera.items():
        cam_name = next(name for idx, name in device_map if idx == cam_idx)
        print(f"  {zone} -> {cam_idx} ({cam_name})")

    return sensor_to_camera

if __name__ == "__main__":
    SENSOR_TO_CAMERA = assign_cameras()
