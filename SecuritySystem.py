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

    Lógica general:
    1. Escucha continuamente el puerto serie donde Arduino envía mensajes de sensores.
    2. Cada alerta del Arduino inicia la grabación en la cámara correspondiente.
    3. Cuando Arduino indica que la alarma se desactiva, se detienen todas las grabaciones.
    
    Ejemplo de mensajes Arduino:
        "⚠ ALERTA: Sensor ENTRADA detectado" → Inicia grabación de cámara de entrada
        "alarmaActiva=0" → Detiene todas las grabaciones

    Comandos que Python envía al Arduino:
        "activacion" → Arduino habilita sistema de sensores
        "desactivacion" → Arduino deshabilita sistema y detiene grabaciones
    """

    def __init__(self, arduino_port: str = "COM3", output_dir: str = "Videos"):
        """
        Inicializa el sistema y establece conexión con Arduino.

        Ejemplo de uso:
            system = SecuritySystem(arduino_port="COM3", output_dir="Videos")
        
        Flujo interno:
        - Crea carpeta de videos si no existe.
        - Define mapeo de sensores a cámaras (SENSOR_TO_CAMERA)
        - Inicializa estados de grabación por sensor (False al inicio)
        - Inicializa diccionario de controladores de grabación por cámara
        - Conecta Arduino
        - Detecta cámaras disponibles en el sistema
        """
        self.OUTPUT_DIR = output_dir
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        # Cada sensor se asigna a una cámara (índice de OpenCV)
        self.SENSOR_TO_CAMERA = {
            "ENTRADA": 0,
            "SALIDA": 0,
            "ESTACIONAMIENTO": 0,
            "BODEGA": 0,
        }

        # Estado de grabación por sensor (True = grabando, False = inactivo)
        self.estado_sensores: Dict[str, bool] = {
            sensor: False for sensor in self.SENSOR_TO_CAMERA
        }

        # Controladores activos de grabación (uno por cámara)
        self.active_controllers: Dict[int, VideoDeviceRecordingController] = {}

        # Conexión al Arduino
        self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)  # Espera a que Arduino inicialice
        print(f"✅ Arduino conectado en {arduino_port}")

        self._detect_cameras()

    def _detect_cameras(self):
        """Detecta cámaras disponibles usando VideoDeviceDetection.

        Ejemplo de salida:
            🎥 2 cámaras detectadas
            📹 Índice 0: USB Camera
            📹 Índice 1: Webcam integrada
        """
        has_devices, message = VideoDeviceDetection.has_devices()
        print(f"🎥 {message}")

        if has_devices:
            device_map = VideoDeviceDetection.get_device_map()
            print("Cámaras detectadas:")
            for opencv_idx, device_name in device_map:
                print(f"  📹 Índice {opencv_idx}: {device_name}")
        else:
            print("⚠️ No se detectaron cámaras disponibles")

    def _get_device_name_for_index(self, camera_index: int) -> Optional[str]:
        """Obtiene el nombre físico de la cámara según su índice OpenCV.

        Entrada:
            camera_index = 0
        Salida:
            "USB Camera"  o None si no existe
        """
        device_map = VideoDeviceDetection.get_device_map()
        for opencv_idx, device_name in device_map:
            if opencv_idx == camera_index:
                return device_name
        return None

    def _parse_alert_message(self, message: str) -> Optional[str]:
        """
        Extrae el sensor que activó la alerta desde el mensaje del Arduino.

        Ejemplos:
            "⚠ ALERTA: Sensor ENTRADA detectado" → devuelve "ENTRADA"
            "⚠ ALERTA: Sensor SALIDA detectado" → devuelve "SALIDA"
        """
        if "ENTRADA" in message.upper():
            return "ENTRADA"
        elif "SALIDA" in message.upper():
            return "SALIDA"
        elif "ESTACIONAMIENTO" in message.upper():
            return "ESTACIONAMIENTO"
        elif "BODEGA" in message.upper():
            return "BODEGA"
        return None

    def _start_camera_recording(self, sensor: str, camera_index: int):
        """
        Inicia grabación de video para un sensor específico.

        Lógica paso a paso:
        1. Comprueba si la cámara ya está grabando (para evitar duplicados)
        2. Obtiene nombre físico de la cámara
        3. Genera un nombre de archivo con timestamp
        4. Inicializa VideoDeviceRecorder y VideoDeviceRecordingController
        5. Guarda controlador activo en active_controllers
        6. Marca el sensor como grabando
        """
        if camera_index in self.active_controllers:
            print(f"⚠️ Cámara {camera_index} ya está grabando para otro sensor")
            return

        device_name = self._get_device_name_for_index(camera_index)
        if not device_name:
            print(f"❌ No se encontró dispositivo para índice {camera_index}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{sensor.lower()}_{timestamp}.mp4"

        try:
            recorder = VideoDeviceRecorder(
                video_device=device_name,
                output_filename=filename,
                output_dir=self.OUTPUT_DIR
            )

            controller = VideoDeviceRecordingController(recorder)
            controller.start()  # Inicia hilo de grabación en segundo plano

            self.active_controllers[camera_index] = controller
            self.estado_sensores[sensor] = True

            output_path = os.path.join(self.OUTPUT_DIR, filename)
            print(f"🎥 {sensor} activó cámara {camera_index} ({device_name}) → {output_path}")

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")

    def stop_all_recordings(self):
        """
        Detiene todas las grabaciones activas.

        Flujo:
        1. Itera sobre todas las cámaras activas
        2. Llama a controller.stop() para detener FFmpeg
        3. Elimina el controlador de active_controllers
        4. Resetea estado de todos los sensores a False
        """
        print("🛑 Deteniendo todas las grabaciones...")
        
        for camera_index in list(self.active_controllers.keys()):
            try:
                controller = self.active_controllers[camera_index]
                controller.stop()
                del self.active_controllers[camera_index]
                print(f"🛑 Cámara {camera_index} detenida")
            except Exception as e:
                print(f"❌ Error deteniendo cámara {camera_index}: {e}")

        # Reset estado sensores
        for sensor in self.estado_sensores:
            self.estado_sensores[sensor] = False

        print("✅ Todas las grabaciones detenidas")

    def escuchar_arduino(self):
        """
        Escucha continuamente los mensajes enviados por el Arduino.

        Ejemplos de mensajes y acción:
            "⚠ ALERTA: Sensor ENTRADA detectado" → inicia grabación sensor ENTRADA
            "alarmaActiva=0" → detiene todas las grabaciones

        Lógica:
        - Mientras hay datos en buffer serie:
            - Decodifica línea
            - Detecta tipo de alerta o desactivación
            - Inicia o detiene grabaciones según corresponda
        """
        while True:
            try:
                while self.arduino.in_waiting > 0:
                    linea = self.arduino.readline().decode("utf-8").strip()
                    print(f"📨 Arduino: {linea}")  # Debug

                    # Mensaje de alerta de sensor
                    if linea.startswith("⚠ ALERTA:"):
                        sensor = self._parse_alert_message(linea)
                        if sensor and sensor in self.SENSOR_TO_CAMERA:
                            camera_index = self.SENSOR_TO_CAMERA[sensor]
                            if not self.estado_sensores[sensor]:
                                self._start_camera_recording(sensor, camera_index)

                    # Mensaje de desactivación
                    elif linea == "alarmaActiva=0" or "Sistema DESACTIVADO" in linea:
                        self.stop_all_recordings()
                
                time.sleep(0.01)  # evita saturar CPU
                
            except Exception as e:
                print(f"❌ Error leyendo Arduino: {e}")
                break

    def enviar_a_arduino(self, comando: str):
        """
        Envía comando al Arduino.

        Ejemplos:
            "activacion" → Arduino habilita sensores
            "desactivacion" → Arduino deshabilita sensores
        """
        try:
            self.arduino.write((comando + "\n").encode("utf-8"))
            print(f"➡️ Enviado a Arduino: {comando}")
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")

    def get_status_report(self) -> str:
        """
        Devuelve un reporte legible del estado actual del sistema.

        Ejemplo de salida:
            📊 ESTADO DEL SISTEMA:
               Grabaciones activas: 1
               ENTRADA (cám 0): 🔴 GRABANDO
               SALIDA (cám 0): ⚪ INACTIVO
        """
        report = "\n📊 ESTADO DEL SISTEMA:\n"
        report += f"   Grabaciones activas: {len(self.active_controllers)}\n"

        for sensor, grabando in self.estado_sensores.items():
            cam_idx = self.SENSOR_TO_CAMERA[sensor]
            status = "🔴 GRABANDO" if grabando else "⚪ INACTIVO"
            report += f"   {sensor} (cám {cam_idx}): {status}\n"

        return report

    def close(self):
        """Detiene todas las grabaciones y cierra el Arduino."""
        self.stop_all_recordings()
        if hasattr(self, 'arduino'):
            self.arduino.close()
            print("✅ Arduino desconectado")


def main():
    """
    Función principal que inicia el sistema de monitoreo.

    Flujo paso a paso:
    1. Crea instancia de SecuritySystem
    2. Muestra estado inicial
    3. Lanza hilo que escucha Arduino
    4. Espera comandos de usuario por consola:
        - "activacion" → habilita sensores
        - "desactivacion" → deshabilita sensores y detiene grabaciones
        - "status" → muestra estado actual
        - "quit" → cierra el sistema
    """
    system = SecuritySystem(arduino_port="COM3", output_dir="Videos")
    print(system.get_status_report())

    # Hilo para escuchar Arduino
    arduino_thread = threading.Thread(target=system.escuchar_arduino, daemon=True)
    arduino_thread.start()

    print("\n🎧 Escuchando Arduino en tiempo real...")
    print("💡 Comandos disponibles:")
    print("   • 'activacion' - Habilitar sistema de sensores")
    print("   • 'desactivacion' - Deshabilitar y detener grabaciones")
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
            elif cmd in ["activacion", "desactivacion"]:
                system.enviar_a_arduino(cmd)
                if cmd == "desactivacion":
                    # Detenemos también localmente por si Arduino no responde
                    system.stop_all_recordings()
            else:
                print("⚠️ Comando no reconocido. Use: activacion, desactivacion, status, quit")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        print("🧹 Cerrando sistema...")
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()
