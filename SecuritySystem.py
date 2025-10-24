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
        """Inicializa el sistema y establece conexión con Arduino."""
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

        # Control para evitar múltiples detecciones del mismo sensor
        self.ultimo_mensaje_sensor: Dict[str, float] = {
            sensor: 0.0 for sensor in self.SENSOR_TO_CAMERA
        }
        self.debounce_time = 2.0  # segundos entre detecciones del mismo sensor

        # Conexión al Arduino
        print(f"🔌 Conectando a Arduino en {arduino_port}...")
        try:
            self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
            time.sleep(2)  # Espera a que Arduino inicialice
            
            # Limpiar buffer de entrada
            self.arduino.reset_input_buffer()
            
            print(f"✅ Arduino conectado en {arduino_port}")
        except serial.SerialException as e:
            print(f"❌ Error conectando Arduino: {e}")
            raise

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
        Mejorado para ser más robusto con variaciones en el mensaje.
        """
        message_upper = message.upper()
        
        # Buscar cada sensor en el mensaje
        if "ENTRADA" in message_upper:
            return "ENTRADA"
        elif "SALIDA" in message_upper:
            return "SALIDA"
        elif "ESTACIONAMIENTO" in message_upper:
            return "ESTACIONAMIENTO"
        elif "BODEGA" in message_upper:
            return "BODEGA"
        
        return None

    def _should_process_sensor(self, sensor: str) -> bool:
        """
        Verifica si debe procesarse una nueva detección del sensor.
        Implementa debounce para evitar múltiples grabaciones del mismo evento.
        """
        current_time = time.time()
        last_detection = self.ultimo_mensaje_sensor[sensor]
        
        # Si ya está grabando Y pasó poco tiempo, ignorar
        if self.estado_sensores[sensor]:
            time_since_last = current_time - last_detection
            if time_since_last < self.debounce_time:
                return False
        
        return True

    def _start_camera_recording(self, sensor: str, camera_index: int):
        """
        Inicia grabación de video para un sensor específico.
        Mejorado con mejor manejo de errores y logging.
        """
        # Verificar debounce
        if not self._should_process_sensor(sensor):
            print(f"⏭️ Ignorando detección duplicada de {sensor} (debounce activo)")
            return

        # Actualizar timestamp de última detección
        self.ultimo_mensaje_sensor[sensor] = time.time()

        if camera_index in self.active_controllers:
            print(f"⚠️ Cámara {camera_index} ya está grabando para otro sensor")
            return

        device_name = self._get_device_name_for_index(camera_index)
        if not device_name:
            print(f"❌ No se encontró dispositivo para índice {camera_index}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{sensor.lower()}_{timestamp}.mp4"

        print(f"🎬 Iniciando grabación para sensor {sensor}...")
        
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
            print(f"✅ {sensor} activó cámara {camera_index} ({device_name})")
            print(f"   📁 Archivo: {output_path}")

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")
            import traceback
            traceback.print_exc()

    def stop_all_recordings(self):
        """Detiene todas las grabaciones activas."""
        if not self.active_controllers:
            print("ℹ️ No hay grabaciones activas para detener")
            return

        print("🛑 Deteniendo todas las grabaciones...")
        
        for camera_index in list(self.active_controllers.keys()):
            try:
                controller = self.active_controllers[camera_index]
                controller.stop()
                del self.active_controllers[camera_index]
                print(f"✅ Cámara {camera_index} detenida")
            except Exception as e:
                print(f"❌ Error deteniendo cámara {camera_index}: {e}")

        # Reset estado sensores
        for sensor in self.estado_sensores:
            self.estado_sensores[sensor] = False

        print("✅ Todas las grabaciones detenidas")

    def escuchar_arduino(self):
        """
        Escucha continuamente los mensajes enviados por el Arduino.
        Mejorado con mejor manejo de errores y logging más detallado.
        """
        print("🎧 Iniciando escucha de Arduino...")
        buffer = ""  # Buffer para manejar mensajes parciales
        
        while True:
            try:
                if self.arduino.in_waiting > 0:
                    # Leer datos disponibles
                    try:
                        chunk = self.arduino.read(self.arduino.in_waiting).decode("utf-8", errors='ignore')
                        buffer += chunk
                    except UnicodeDecodeError:
                        print("⚠️ Error decodificando datos del Arduino")
                        continue

                    # Procesar líneas completas
                    while '\n' in buffer:
                        linea, buffer = buffer.split('\n', 1)
                        linea = linea.strip()
                        
                        if not linea:
                            continue
                        
                        print(f"📨 Arduino: {linea}")
                        
                        # Detectar alerta de sensor
                        if "ALERTA" in linea.upper() and "SENSOR" in linea.upper():
                            sensor = self._parse_alert_message(linea)
                            if sensor and sensor in self.SENSOR_TO_CAMERA:
                                camera_index = self.SENSOR_TO_CAMERA[sensor]
                                print(f"🚨 Sensor {sensor} detectado → Cámara {camera_index}")
                                self._start_camera_recording(sensor, camera_index)
                            else:
                                print(f"⚠️ Sensor no reconocido en mensaje: {linea}")
                        
                        # Detectar desactivación
                        elif "alarmaActiva=0" in linea or "DESACTIVADO" in linea.upper():
                            print("🛑 Señal de desactivación recibida desde Arduino")
                            self.stop_all_recordings()
                
                time.sleep(0.01)  # Pequeña pausa para no saturar CPU
                
            except serial.SerialException as e:
                print(f"❌ Error de conexión serial: {e}")
                print("🔌 Intentando reconectar...")
                time.sleep(2)
                try:
                    self.arduino.close()
                    self.arduino.open()
                    print("✅ Reconexión exitosa")
                except:
                    print("❌ No se pudo reconectar. Terminando escucha.")
                    break
                    
            except Exception as e:
                print(f"❌ Error inesperado en escucha: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

    def enviar_a_arduino(self, comando: str):
        """Envía comando al Arduino."""
        try:
            self.arduino.write((comando + "\n").encode("utf-8"))
            print(f"➡️ Enviado a Arduino: {comando}")
            time.sleep(0.1)  # Pequeña pausa para que Arduino procese
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")

    def get_status_report(self) -> str:
        """Devuelve un reporte legible del estado actual del sistema."""
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
    """Función principal que inicia el sistema de monitoreo."""
    try:
        system = SecuritySystem(arduino_port="COM3", output_dir="Videos")
    except Exception as e:
        print(f"❌ Error iniciando sistema: {e}")
        return

    print(system.get_status_report())

    # Hilo para escuchar Arduino
    arduino_thread = threading.Thread(target=system.escuchar_arduino, daemon=True)
    arduino_thread.start()

    print("\n🎧 Escuchando Arduino en tiempo real...")
    print("💡 Comandos disponibles:")
    print("   • 'activacion' - Habilitar sistema de sensores")
    print("   • 'desactivacion' - Deshabilitar y detener grabaciones")
    print("   • 'status' - Mostrar estado actual")
    print("   • 'stop' - Detener todas las grabaciones manualmente")
    print("   • 'quit' - Salir del programa")
    print("-" * 60)

    try:
        while True:
            cmd = input("Comando → ").strip().lower()

            if cmd == "quit":
                break
            elif cmd == "status":
                print(system.get_status_report())
            elif cmd == "stop":
                system.stop_all_recordings()
            elif cmd in ["activacion", "desactivacion"]:
                system.enviar_a_arduino(cmd)
                if cmd == "desactivacion":
                    # Detenemos también localmente por si Arduino no responde
                    system.stop_all_recordings()
            else:
                print("⚠️ Comando no reconocido. Use: activacion, desactivacion, status, stop, quit")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()