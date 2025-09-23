import serial
import time
import os
from datetime import datetime
import threading
from typing import Dict, Optional
from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.VideoDeviceRecorder import VideoDeviceRecorder
from recording.VideoDeviceRecordingController import VideoDeviceRecordingController


class SecuritySystem:
    """
    Sistema integrado de grabación de video con sensores Arduino + FFmpeg.

    Este sistema:
    - Escucha el puerto serie del Arduino.
    - Recibe mensajes de activación/desactivación de sensores (formato "SENSOR:nombre:estado").
    - Inicia o detiene grabaciones de cámaras usando FFmpeg.
    - Mantiene un estado global de sensores y grabaciones.
    - Permite enviar comandos al Arduino (ej: "activado", "desactivado").

    Parámetros configurables en la inicialización:
    - arduino_port (str): Puerto COM donde está conectado Arduino. Ej: "COM3" en Windows o "/dev/ttyUSB0" en Linux.
    - output_dir (str): Directorio base donde se guardarán los videos generados.

    Extensiones posibles:
    - Asignar diferentes índices de cámara a cada sensor (en SENSOR_TO_CAMERA).
    - Cambiar el formato del nombre de archivo (ej: añadir nombre de cámara, fecha más detallada, etc.).
    - Modificar la lógica de cuándo detener grabaciones (ej: por duración fija, por comando externo).
    """

    def __init__(self, arduino_port: str = "COM3", output_dir: str = "Videos"):
        """
        inicializa el sistema y establece conexión con Arduino.

        Args:
            arduino_port (str): Puerto serie a usar (depende de tu SO y cómo se detecta Arduino).
            output_dir (str): Carpeta donde se guardarán los videos de salida.
        """
        # Directorio donde se guardarán los videos grabados
        self.OUTPUT_DIR = output_dir
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        # Mapeo entre sensores y cámaras físicas (índices de OpenCV).
        # Ejemplo: si sensor "entrada" está vinculado a la cámara con índice 1, se cambia aquí.
        self.SENSOR_TO_CAMERA = {
            "estacionamiento": 0,
            "entrada": 0,
            "salida": 0,
            "bodega": 0,
        }

        # Diccionario que mantiene el estado actual de cada sensor (None = inactivo aún, "1" = activado, "0" = desactivado)
        self.estado_sensores = {sensor: None for sensor in self.SENSOR_TO_CAMERA}

        # Diccionario con grabaciones activas, indexadas por cámara (cada cámara puede tener un controller de FFmpeg)
        self.active_controllers: Dict[int, VideoDeviceRecordingController] = {}

        # Abrir puerto serie con Arduino
        # Baud rate 9600 (debe coincidir con el código del Arduino).
        self.arduino = serial.Serial(arduino_port, 9600, timeout=1)

        # Pequeña espera obligatoria para que el microcontrolador arranque
        time.sleep(2)
        print(f"✅ Arduino conectado en {arduino_port}")

        # Detectar qué cámaras existen físicamente en el sistema
        self._detect_cameras()

    def _detect_cameras(self):
        """
        Detecta cámaras disponibles usando VideoDeviceDetection.

        - Llama a la clase VideoDeviceDetection que ejecuta FFmpeg en modo lista.
        - Imprime en consola qué dispositivos están presentes y qué índices les corresponden.
        - Esto ayuda a configurar SENSOR_TO_CAMERA correctamente.
        """
        has_devices, message = VideoDeviceDetection.has_devices()
        print(f"🎥 {message}")

        if has_devices:
            devices = VideoDeviceDetection.get_devices()
            device_map = VideoDeviceDetection.get_device_map()

            print("Cámaras detectadas:")
            for opencv_idx, device_name in device_map:
                print(f"  📹 Índice {opencv_idx}: {device_name}")
        else:
            print("⚠️ No se detectaron cámaras disponibles")

    def _get_device_name_for_index(self, camera_index: int) -> Optional[str]:
        """
        Obtiene el nombre del dispositivo físico asociado a un índice de cámara OpenCV.

        Args:
            camera_index (int): Índice (ej: 0, 1, 2...).

        Returns:
            str | None: Nombre del dispositivo ("USB Camera XYZ") o None si no existe.
        """
        device_map = VideoDeviceDetection.get_device_map()
        for opencv_idx, device_name in device_map:
            if opencv_idx == camera_index:
                return device_name
        return None

    def procesar_evento(self, sensor: str, estado: str):
        """
        Procesa un evento recibido desde Arduino.

        Flujo:
        - Si el sensor está registrado en SENSOR_TO_CAMERA → se obtiene el índice de cámara asociado.
        - Si el estado es "1" (activado) y el sensor no estaba ya en "1" → se inicia grabación.
        - Si el estado es "0" → actualmente no detiene (se podría ampliar aquí).

        Args:
            sensor (str): Nombre del sensor ("entrada", "salida", etc.).
            estado (str): Estado recibido ("1" = activado, "0" = desactivado).
        """
        if sensor in self.SENSOR_TO_CAMERA:
            cam_index = self.SENSOR_TO_CAMERA[sensor]

            if estado == "1" and self.estado_sensores[sensor] != "1":
                self.estado_sensores[sensor] = "1"
                self._start_camera_recording(sensor, cam_index)

    def _start_camera_recording(self, sensor: str, camera_index: int):
        """
        Lanza la grabación de una cámara.

        - Revisa si ya existe una grabación en esa cámara → si es así, ignora.
        - Obtiene el nombre del dispositivo físico asociado al índice.
        - Crea un archivo .mp4 con timestamp y nombre del sensor.
        - Inicializa VideoDeviceRecorder.
        - Crea un VideoDeviceRecordingController para gestionar esa grabación en segundo plano.

        Args:
            sensor (str): Nombre del sensor que activó la cámara.
            camera_index (int): Índice de cámara en OpenCV.
        """
        if camera_index in self.active_controllers:
            print(f"⚠️ Cámara {camera_index} ya está grabando, ignorando nueva activación de {sensor}")
            return

        device_name = self._get_device_name_for_index(camera_index)
        if not device_name:
            print(f"❌ No se pudo encontrar dispositivo para índice {camera_index}")
            return

        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{sensor}_{timestamp}.mp4"

        try:
            # Inicializa el recorder (configurado para grabar desde el dispositivo)
            recorder = VideoDeviceRecorder(
                video_device=device_name,
                output_filename=filename,
                output_dir=self.OUTPUT_DIR
            )

            # Controller = hilo que mantiene la grabación en ejecución
            controller = VideoDeviceRecordingController(recorder)
            controller.start()

            # Guardamos la referencia de la cámara activa
            self.active_controllers[camera_index] = controller

            output_path = os.path.join(self.OUTPUT_DIR, filename)
            print(f"🎥 {sensor} activó cámara {camera_index} ({device_name}) → {output_path}")

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")
            self.estado_sensores[sensor] = None

    def stop_camera_recording(self, camera_index: int):
        """
        Detiene la grabación de una cámara específica.

        Args:
            camera_index (int): Índice de cámara a detener.
        """
        if camera_index in self.active_controllers:
            try:
                controller = self.active_controllers[camera_index]
                controller.stop()  # Finaliza FFmpeg
                del self.active_controllers[camera_index]
                print(f"🛑 Cámara {camera_index} detenida")
            except Exception as e:
                print(f"❌ Error deteniendo cámara {camera_index}: {e}")

    def stop_all_recordings(self):
        """
        Detiene todas las grabaciones que están activas en el sistema.

        - Recorre active_controllers y detiene cada una.
        - Marca todos los sensores como "0".
        """
        print("🛑 Deteniendo todas las grabaciones...")
        for camera_index in list(self.active_controllers.keys()):
            self.stop_camera_recording(camera_index)

        for sensor in self.estado_sensores:
            self.estado_sensores[sensor] = "0"

        print("✅ Todas las grabaciones detenidas")

    def escuchar_arduino(self):
        """
        Bucle principal que escucha continuamente datos del puerto serie.

        Flujo:
        - Revisa si hay datos en el buffer serial (arduino.in_waiting).
        - Lee línea por línea, las decodifica a UTF-8.
        - Si empieza con "SENSOR:" → intenta separar en formato SENSOR:nombre:estado.
        - Llama a procesar_evento(sensor, estado).
        - Hace una pequeña pausa (0.01s) para no saturar la CPU.
        """
        while True:
            try:
                while self.arduino.in_waiting > 0:
                    linea = self.arduino.readline().decode("utf-8").strip()
                    if linea.startswith("SENSOR:"):
                        try:
                            _, sensor, estado = linea.split(":")
                            self.procesar_evento(sensor, estado)
                        except ValueError:
                            print(f"⚠️ Línea malformada: {linea}")
                time.sleep(0.01)
            except Exception as e:
                print(f"❌ Error leyendo Arduino: {e}")
                break

    def enviar_a_arduino(self, msg: str):
        """
        Envía un mensaje al Arduino por el puerto serie.

        Args:
            msg (str): Texto a enviar. Ej: "activado" o "desactivado".

        Nota:
        - Debe coincidir con los comandos que reconoce el sketch de Arduino.
        - Se le añade automáticamente un salto de línea al final.
        """
        try:
            self.arduino.write((msg + "\n").encode("utf-8"))
            print(f"➡️ Enviado a Arduino: {msg}")
        except Exception as e:
            print(f"❌ Error enviando a Arduino: {e}")

    def get_status_report(self) -> str:
        """
        Genera un reporte del estado actual del sistema.

        Incluye:
        - Cantidad de grabaciones activas.
        - Estado de cada sensor (si está grabando o no).

        Returns:
            str: Texto formateado con información.
        """
        report = "\n📊 ESTADO DEL SISTEMA:\n"
        report += f"   Grabaciones activas: {len(self.active_controllers)}\n"

        for sensor, estado in self.estado_sensores.items():
            cam_idx = self.SENSOR_TO_CAMERA[sensor]
            status = "🔴 GRABANDO" if cam_idx in self.active_controllers else "⚪ INACTIVO"
            report += f"   {sensor} (cám {cam_idx}): {status}\n"

        return report

    def close(self):
        """
        Limpia recursos del sistema antes de cerrar.

        - Detiene todas las grabaciones.
        - Cierra conexión con Arduino.
        """
        self.stop_all_recordings()
        if hasattr(self, 'arduino'):
            self.arduino.close()
            print("✅ Arduino desconectado")


def main():
    """
    Función principal que lanza el sistema de monitoreo y grabación.

    Flujo:
    1. Inicializa SecuritySystem.
    2. Muestra estado inicial.
    3. Lanza un hilo secundario que escucha continuamente al Arduino.
    4. Mantiene un bucle de comandos en la consola:

       Comandos soportados:
       - "activado" → envía mensaje al Arduino para habilitar sensores.
       - "desactivado" → envía mensaje al Arduino y detiene grabaciones.
       - "status" → imprime el estado actual.
       - "quit" → termina el programa.

    """
    system = SecuritySystem(arduino_port="COM3", output_dir="Videos")

    print(system.get_status_report())

    # Hilo separado para escuchar Arduino en paralelo al input()
    arduino_thread = threading.Thread(target=system.escuchar_arduino, daemon=True)
    arduino_thread.start()

    print("\n🎧 Escuchando Arduino en tiempo real...")
    print("💡 Comandos disponibles:")
    print("   • 'activado' - Habilitar sistema de sensores")
    print("   • 'desactivado' - Deshabilitar y detener todas las grabaciones")
    print("   • 'status' - Mostrar estado actual")
    print("   • 'quit' - Salir del programa")
    print("-" * 60)

    try:
        while True:
            cmd = input("Comando → ").strip().lower()

            if cmd == "quit":
                break
            elif cmd == "status":
                print(system.get_status_report())
            elif cmd in ["activado", "desactivado"]:
                system.enviar_a_arduino(cmd)
                if cmd == "desactivado":
                    system.stop_all_recordings()
            else:
                print("⚠️ Comando no reconocido. Use: activado, desactivado, status, quit")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        print("🧹 Cerrando sistema...")
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()
