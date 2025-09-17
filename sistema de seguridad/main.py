import serial
import threading

from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.VideoDeviceRecorder import VideoDeviceRecorder
from recording.VideoDeviceRecordingController import VideoDeviceRecordingController

PUERTO: str = "COM3"
BAUDIOS: int = 9600
CAMERA_CONTROLLERS: list[VideoDeviceRecordingController] = []
# Abre la conexión
arduino: serial.Serial = serial.Serial(PUERTO, BAUDIOS, timeout=1)

def escuchar_arduino():
    """Hilo para leer mensajes que envía el Arduino"""
    global CAMERA_CONTROLLERS  # importante para modificar la lista global

    while True:
        if arduino.in_waiting > 0:
            mensaje = arduino.readline().decode('utf-8', errors='ignore').strip()
            if mensaje:
                if mensaje.startswith("alarmaActiva="):
                    estado = mensaje.split("=")[1]
                    print(f"[ESTADO] alarmaActiva = {estado}")

                    # Detectar cámaras disponibles
                    has_devices, message = VideoDeviceDetection.has_devices()
                    print(message)
                    devices: list[str] = VideoDeviceDetection.list_devices() if has_devices else []
                    if devices:
                        print(f"Detected cameras: {devices}")
                        already_recording = any(
                            ctrl.is_recording() for ctrl in CAMERA_CONTROLLERS
                        )

                        if not already_recording and estado == "1":
                            CAMERA_CONTROLLERS = record_cameras(devices[:1])
                        elif already_recording and estado == "0":
                            for ctrl in CAMERA_CONTROLLERS:
                                ctrl.stop()
                            CAMERA_CONTROLLERS = []
                    print(f"[Arduino] {mensaje}")



# Lanzamos hilo para escuchar al Arduino
hilo = threading.Thread(target=escuchar_arduino, daemon=True)
hilo.start()

print("Conexión establecida ")
print("'activacion' o 'desactivacion' para controlar el sistema.")
print("'salir' para cerrar.")

# Bucle principal para mandar comandos
while True:
    comando = input(">> ").strip()
    if comando.lower() == "salir":
        for ctrl in CAMERA_CONTROLLERS:
            ctrl.stop()
        break
    if comando:
        arduino.write((comando + "\n").encode('utf-8'))

arduino.close()
print("Conexión cerrada ")

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