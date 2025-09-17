import serial
import threading

from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.VideoDeviceRecorder import VideoDeviceRecorder
from recording.VideoDeviceRecordingController import VideoDeviceRecordingController

PUERTO: str = "COM3"
BAUDIOS: int = 9600
CAMERA_CONTROLLERS: list[VideoDeviceRecordingController] = []
arduino: serial.Serial = serial.Serial(PUERTO, BAUDIOS, timeout=1)

# Estado de grabación (True = grabando, False = detenido)
is_recording: bool = False


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


def stop_cameras():
    """Stop all active recordings."""
    global CAMERA_CONTROLLERS, is_recording
    if CAMERA_CONTROLLERS:
        for ctrl in CAMERA_CONTROLLERS:
            ctrl.stop()
        CAMERA_CONTROLLERS = []
        print("All camera recordings stopped.")
    is_recording = False


def toggle_recording():
    """Alterna entre grabar y detener."""
    global is_recording, CAMERA_CONTROLLERS

    if not is_recording:
        has_devices, message = VideoDeviceDetection.has_devices()
        print(message)
        devices: list[str] = VideoDeviceDetection.list_devices() if has_devices else []
        if devices:
            CAMERA_CONTROLLERS = record_cameras(devices[:1])
            is_recording = True
    else:
        stop_cameras()


def escuchar_arduino():
    """Hilo para leer mensajes que envía el Arduino"""
    while True:
        if arduino.in_waiting > 0:
            mensaje = arduino.readline().decode('utf-8', errors='ignore').strip()
            if not mensaje:
                continue

            print(f"[Arduino] {mensaje}")

            if mensaje.startswith("alarmaActiva=1"):
                toggle_recording()

            elif mensaje == "⚠ Sistema DESACTIVADO":
                stop_cameras()


# Lanzamos hilo para escuchar al Arduino
hilo = threading.Thread(target=escuchar_arduino, daemon=True)
hilo.start()

print("Conexión establecida ")
print("'activacion' o 'desactivacion' para controlar el sistema.")
print("'salir' para cerrar.")

# Bucle principal para mandar comandos manuales
while True:
    comando = input(">> ").strip()
    if comando.lower() == "salir":
        stop_cameras()
        break
    if comando:
        arduino.write((comando + "\n").encode('utf-8'))

arduino.close()
print("Conexión cerrada ")
