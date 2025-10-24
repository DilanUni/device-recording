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
    """

    def __init__(self, arduino_port: str = "COM3", output_dir: str = "Videos"):
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

        # Controladores activos de grabación por SENSOR (no por cámara)
        self.active_controllers: Dict[str, VideoDeviceRecordingController] = {}

        # Conexión al Arduino
        self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)
        print(f"✅ Arduino conectado en {arduino_port}")

        self._detect_cameras()

    def _detect_cameras(self):
        """Detecta cámaras disponibles usando VideoDeviceDetection."""
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
        """Obtiene el nombre físico de la cámara según su índice OpenCV."""
        device_map = VideoDeviceDetection.get_device_map()
        for opencv_idx, device_name in device_map:
            if opencv_idx == camera_index:
                return device_name
        return None

    def _parse_alert_message(self, message: str) -> Optional[str]:
        """
        Extrae el sensor que activó la alerta desde el mensaje del Arduino.
        """
        message_upper = message.upper()
        if "ENTRADA" in message_upper:
            return "ENTRADA"
        elif "SALIDA" in message_upper:
            return "SALIDA"
        elif "ESTACIONAMIENTO" in message_upper:
            return "ESTACIONAMIENTO"
        elif "BODEGA" in message_upper:
            return "BODEGA"
        return None

    def _start_camera_recording(self, sensor: str, camera_index: int):
        """
        Inicia grabación de video para un sensor específico.
        """
        # Verificar si este sensor ya está grabando
        if sensor in self.active_controllers:
            print(f"⚠️ Sensor {sensor} ya tiene una grabación activa")
            return

        device_name = self._get_device_name_for_index(camera_index)
        if not device_name:
            print(f"❌ No se encontró dispositivo para índice {camera_index}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{sensor.lower()}_{timestamp}.mp4"

        try:
            print(f"🎬 Intentando iniciar grabación para {sensor}...")
            
            recorder = VideoDeviceRecorder(
                video_device=device_name,
                output_filename=filename,
                output_dir=self.OUTPUT_DIR
            )

            controller = VideoDeviceRecordingController(recorder)
            controller.start()

            # Guardamos el controlador por SENSOR, no por cámara
            self.active_controllers[sensor] = controller
            self.estado_sensores[sensor] = True

            output_path = os.path.join(self.OUTPUT_DIR, filename)
            print(f"✅ {sensor} activó cámara {camera_index} ({device_name})")
            print(f"📁 Archivo: {output_path}")

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")
            import traceback
            traceback.print_exc()

    def stop_all_recordings(self):
        """
        Detiene todas las grabaciones activas.
        """
        if not self.active_controllers:
            print("ℹ️ No hay grabaciones activas para detener")
            return
            
        print("🛑 Deteniendo todas las grabaciones...")
        
        for sensor in list(self.active_controllers.keys()):
            try:
                controller = self.active_controllers[sensor]
                controller.stop()
                del self.active_controllers[sensor]
                self.estado_sensores[sensor] = False
                print(f"🛑 Grabación de {sensor} detenida")
            except Exception as e:
                print(f"❌ Error deteniendo {sensor}: {e}")

        print("✅ Todas las grabaciones detenidas")

    def escuchar_arduino(self):
        """
        Escucha continuamente los mensajes enviados por el Arduino.
        """
        print("👂 Iniciando escucha de Arduino...")
        
        while True:
            try:
                if self.arduino.in_waiting > 0:
                    linea = self.arduino.readline().decode("utf-8", errors='ignore').strip()
                    
                    if linea:  # Solo procesar líneas no vacías
                        print(f"📨 Arduino: {linea}")

                        # Mensaje de alerta de sensor
                        if "ALERTA:" in linea:
                            sensor = self._parse_alert_message(linea)
                            if sensor and sensor in self.SENSOR_TO_CAMERA:
                                camera_index = self.SENSOR_TO_CAMERA[sensor]
                                print(f"🚨 Alerta detectada: {sensor} → Cámara {camera_index}")
                                # Siempre intentar iniciar (el método ya verifica duplicados)
                                self._start_camera_recording(sensor, camera_index)
                            else:
                                print(f"⚠️ Sensor no reconocido en mensaje: {linea}")

                        # Mensaje de desactivación
                        elif "alarmaActiva=0" in linea or "DESACTIVADO" in linea:
                            print("🔴 Desactivación detectada")
                            self.stop_all_recordings()
                
                time.sleep(0.01)
                
            except serial.SerialException as e:
                print(f"❌ Error de conexión serial: {e}")
                break
            except Exception as e:
                print(f"❌ Error leyendo Arduino: {e}")
                import traceback
                traceback.print_exc()

    def enviar_a_arduino(self, comando: str):
        """
        Envía comando al Arduino.
        """
        try:
            self.arduino.write((comando + "\n").encode("utf-8"))
            print(f"➡️ Enviado a Arduino: {comando}")
            time.sleep(0.1)  # Pequeña pausa para que Arduino procese
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")

    def get_status_report(self) -> str:
        """
        Devuelve un reporte legible del estado actual del sistema.
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
        print("🧹 Cerrando sistema...")
        self.stop_all_recordings()
        if hasattr(self, 'arduino') and self.arduino.is_open:
            self.arduino.close()
            print("✅ Arduino desconectado")


def main():
    """
    Función principal que inicia el sistema de monitoreo.
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
            elif cmd in ["activado", "desactivado"]:
                system.enviar_a_arduino(cmd)
                if cmd == "desactivado":
                    # Detenemos también localmente por si Arduino no responde

                    system.stop_all_recordings()
            else:
                print("⚠️ Comando no reconocido. Use: activacion, desactivacion, status, quit")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()