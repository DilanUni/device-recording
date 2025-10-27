import serial
import time
import os
import cv2 as cv
import json
from datetime import datetime
import threading
from typing import Dict, Optional, List, Tuple
from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.RecordingManager import RecordingManager


class CameraConfigManager:
    """
    Gestiona la configuración de asignación de cámaras a zonas.
    """
    
    def __init__(self, config_file: str = "camera_config.json"):
        self.config_file = config_file
        self.zones = ["ENTRADA", "SALIDA", "ESTACIONAMIENTO", "BODEGA"]
    
    def load_config(self) -> Optional[Dict[str, int]]:
        """
        Carga la configuración desde el archivo JSON.
        Retorna None si no existe o es inválida.
        """
        if not os.path.exists(self.config_file):
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validar estructura
            if not isinstance(config, dict) or 'sensor_to_camera' not in config:
                print("⚠️ Archivo de configuración inválido")
                return None
            
            sensor_to_camera = config['sensor_to_camera']
            
            # Validar que todas las zonas estén presentes
            if not all(zone in sensor_to_camera for zone in self.zones):
                print("⚠️ Configuración incompleta - faltan zonas")
                return None
            
            return sensor_to_camera
        
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            return None
    
    def save_config(self, sensor_to_camera: Dict[str, int], device_map: List[Tuple[int, str]]) -> bool:
        """
        Guarda la configuración en el archivo JSON.
        """
        try:
            # Crear estructura completa con metadata
            config = {
                "sensor_to_camera": sensor_to_camera,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "available_devices": [
                        {"index": idx, "name": name} for idx, name in device_map
                    ]
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configuración guardada en {self.config_file}")
            return True
        
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            return False
    
    def validate_config_with_devices(self, sensor_to_camera: Dict[str, int], 
                                    device_map: List[Tuple[int, str]]) -> bool:
        """
        Valida que la configuración sea compatible con los dispositivos actuales.
        """
        available_indices = {idx for idx, _ in device_map}
        configured_indices = set(sensor_to_camera.values())
        
        # Verificar que todos los índices configurados existan
        missing_indices = configured_indices - available_indices
        
        if missing_indices:
            print(f"⚠️ Cámaras configuradas no disponibles: {missing_indices}")
            return False
        
        return True
    
    def assign_cameras_interactive(self, device_map: List[Tuple[int, str]]) -> Dict[str, int]:
        """
        Permite al usuario asignar cámaras a zonas de forma interactiva.
        """
        if not device_map:
            print("❌ No hay cámaras disponibles")
            return {}
        
        print("\n" + "="*60)
        print("🎥 CONFIGURACIÓN DE CÁMARAS POR ZONA")
        print("="*60)
        print("\nCámaras detectadas:")
        for idx, name in device_map:
            print(f"  [{idx}] {name}")
        
        sensor_to_camera: Dict[str, int] = {}
        available_indices = {idx for idx, _ in device_map}
        
        print("\n💡 Asigne una cámara a cada zona:")
        print("   (Puede usar el mismo índice para múltiples zonas)\n")
        
        for zone in self.zones:
            while True:
                try:
                    user_input = input(f"  {zone} → Índice de cámara: ").strip()
                    
                    if not user_input:
                        print("     ⚠️ Debe ingresar un valor")
                        continue
                    
                    cam_idx = int(user_input)
                    
                    if cam_idx not in available_indices:
                        print(f"     ⚠️ Índice inválido. Use: {sorted(available_indices)}")
                        continue
                    
                    sensor_to_camera[zone] = cam_idx
                    cam_name = next(name for idx, name in device_map if idx == cam_idx)
                    print(f"     ✓ {zone} asignado a cámara {cam_idx} ({cam_name})")
                    break
                
                except ValueError:
                    print("     ⚠️ Debe ingresar un número válido")
                except KeyboardInterrupt:
                    print("\n\n⏹️ Configuración cancelada")
                    return {}
        
        # Resumen final
        print("\n" + "="*60)
        print("📋 RESUMEN DE ASIGNACIÓN:")
        print("="*60)
        for zone, cam_idx in sensor_to_camera.items():
            cam_name = next(name for idx, name in device_map if idx == cam_idx)
            print(f"  {zone:20} → [{cam_idx}] {cam_name}")
        print("="*60 + "\n")
        
        return sensor_to_camera


class SecuritySystem:
    """
    Sistema integrado de grabación de video con sensores Arduino + RecordingManager.
    """

    def __init__(self, arduino_port: str = "COM3", output_dir: str = "Videos", 
                 config_file: str = "camera_config.json"):
        self.OUTPUT_DIR = output_dir
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        # Gestor de configuración
        self.config_manager = CameraConfigManager(config_file)
        
        # Asignación de cámaras a sensores (se cargará o configurará)
        self.SENSOR_TO_CAMERA: Dict[str, int] = {}

        # Estado de grabación por sensor
        self.estado_sensores: Dict[str, bool] = {}

        # Capturas de video activas por sensor
        self.active_captures: Dict[str, cv.VideoCapture] = {}

        # Recording Manager
        self.recording_manager = RecordingManager(
            output_dir=self.OUTPUT_DIR,
            fps=30.0
        )

        # Hilos de captura por sensor
        self.capture_threads: Dict[str, threading.Thread] = {}
        self.should_stop_capture: Dict[str, bool] = {}

        # Detectar cámaras y configurar
        device_map = self._detect_cameras()
        self._setup_camera_config(device_map)
        
        # Inicializar estado de sensores
        self.estado_sensores = {sensor: False for sensor in self.SENSOR_TO_CAMERA}

        # Conexión al Arduino
        self.arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)
        print(f"✅ Arduino conectado en {arduino_port}")

    def _detect_cameras(self) -> List[Tuple[int, str]]:
        """Detecta cámaras disponibles usando VideoDeviceDetection."""
        has_devices, message = VideoDeviceDetection.has_devices()
        print(f"\n🎥 {message}")

        device_map = []
        if has_devices:
            device_map = VideoDeviceDetection.get_device_map()
            print("Cámaras detectadas:")
            for opencv_idx, device_name in device_map:
                print(f"  📹 [{opencv_idx}] {device_name}")
        else:
            print("⚠️ No se detectaron cámaras disponibles")
        
        return device_map
    
    def _setup_camera_config(self, device_map: List[Tuple[int, str]]) -> None:
        """
        Configura la asignación de cámaras a zonas.
        Intenta cargar desde JSON, si no es válido, solicita configuración interactiva.
        """
        if not device_map:
            print("❌ No se pueden configurar cámaras sin dispositivos disponibles")
            self.SENSOR_TO_CAMERA = {}
            return
        
        # Intentar cargar configuración existente
        loaded_config = self.config_manager.load_config()
        
        if loaded_config:
            print(f"\n📄 Configuración encontrada en {self.config_manager.config_file}")
            
            # Validar que la configuración sea compatible con dispositivos actuales
            if self.config_manager.validate_config_with_devices(loaded_config, device_map):
                self.SENSOR_TO_CAMERA = loaded_config
                print("✅ Configuración cargada y validada correctamente\n")
                self._print_current_config(device_map)
                return
            else:
                print("⚠️ La configuración no es compatible con los dispositivos actuales")
                print("   Se requiere reconfiguración\n")
        else:
            print("\n📝 No se encontró configuración previa\n")
        
        # Solicitar configuración interactiva
        while True:
            print("¿Desea configurar las cámaras ahora? (s/n): ", end="")
            response = input().strip().lower()
            
            if response == 's':
                new_config = self.config_manager.assign_cameras_interactive(device_map)
                
                if new_config:
                    self.SENSOR_TO_CAMERA = new_config
                    
                    # Guardar configuración
                    print("¿Desea guardar esta configuración? (s/n): ", end="")
                    save_response = input().strip().lower()
                    
                    if save_response == 's':
                        self.config_manager.save_config(new_config, device_map)
                    
                    return
                else:
                    print("⚠️ Configuración vacía o cancelada")
            
            elif response == 'n':
                print("⚠️ Sistema sin configuración - no podrá grabar")
                self.SENSOR_TO_CAMERA = {}
                return
            
            else:
                print("⚠️ Respuesta inválida. Use 's' o 'n'")
    
    def _print_current_config(self, device_map: List[Tuple[int, str]]) -> None:
        """Imprime la configuración actual de cámaras."""
        print("📋 Configuración actual:")
        for zone, cam_idx in self.SENSOR_TO_CAMERA.items():
            cam_name = next((name for idx, name in device_map if idx == cam_idx), "Desconocida")
            print(f"   {zone:20} → [{cam_idx}] {cam_name}")
        print()

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

    def _capture_and_record(self, sensor: str, camera_index: int):
        """
        Hilo que captura frames y los escribe usando RecordingManager.
        """
        cap = cv.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"❌ No se pudo abrir cámara {camera_index} para {sensor}")
            return

        self.active_captures[sensor] = cap
        
        # Leer primer frame para iniciar grabación
        ret, frame = cap.read()
        if not ret:
            print(f"❌ No se pudo leer frame inicial para {sensor}")
            cap.release()
            return

        # Iniciar grabación con RecordingManager
        if not self.recording_manager.start_recording(sensor, frame, "camera"):
            print(f"❌ No se pudo iniciar grabación para {sensor}")
            cap.release()
            return

        print(f"✅ Captura y grabación iniciada para {sensor}")

        # Loop de captura
        while not self.should_stop_capture.get(sensor, False):
            ret, frame = cap.read()
            if not ret:
                print(f"⚠️ Error leyendo frame de {sensor}")
                time.sleep(0.1)
                continue

            # Escribir frame con RecordingManager
            self.recording_manager.write_frame(sensor, frame)
            
            time.sleep(0.01)  # ~100 FPS max

        # Cleanup
        cap.release()
        if sensor in self.active_captures:
            del self.active_captures[sensor]
        
        print(f"🛑 Captura finalizada para {sensor}")

    def _start_camera_recording(self, sensor: str, camera_index: int):
        """
        Inicia grabación de video para un sensor específico.
        """
        # Verificar si este sensor ya está grabando
        if sensor in self.capture_threads and self.capture_threads[sensor].is_alive():
            print(f"⚠️ Sensor {sensor} ya tiene una grabación activa")
            return

        device_name = self._get_device_name_for_index(camera_index)
        if not device_name:
            print(f"❌ No se encontró dispositivo para índice {camera_index}")
            return

        try:
            print(f"🎬 Iniciando grabación para {sensor}...")
            
            # Flag para detener captura
            self.should_stop_capture[sensor] = False
            
            # Iniciar hilo de captura
            thread = threading.Thread(
                target=self._capture_and_record,
                args=(sensor, camera_index),
                daemon=True
            )
            thread.start()
            
            self.capture_threads[sensor] = thread
            self.estado_sensores[sensor] = True

            print(f"✅ {sensor} activó cámara {camera_index} ({device_name})")
            print(f"📁 Guardando en: {self.OUTPUT_DIR}")

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")
            import traceback
            traceback.print_exc()

    def stop_all_recordings(self):
        """
        Detiene todas las grabaciones activas.
        """
        if not self.capture_threads:
            print("ℹ️ No hay grabaciones activas para detener")
            return
            
        print("🛑 Deteniendo todas las grabaciones...")
        
        # Señalar a todos los hilos que deben detenerse
        for sensor in list(self.capture_threads.keys()):
            self.should_stop_capture[sensor] = True
        
        # Esperar a que terminen (timeout de 2 segundos por hilo)
        for sensor, thread in list(self.capture_threads.items()):
            try:
                thread.join(timeout=2.0)
                self.estado_sensores[sensor] = False
            except Exception as e:
                print(f"❌ Error esperando hilo de {sensor}: {e}")
        
        # Detener grabaciones en RecordingManager
        self.recording_manager.stop_all()
        
        # Limpiar estructuras
        self.capture_threads.clear()
        self.should_stop_capture.clear()
        
        # Liberar capturas restantes
        for sensor, cap in list(self.active_captures.items()):
            try:
                cap.release()
            except:
                pass
        self.active_captures.clear()

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
                    
                    if linea:
                        print(f"📨 Arduino: {linea}")

                        # Mensaje de alerta de sensor
                        if "ALERTA:" in linea:
                            sensor = self._parse_alert_message(linea)
                            if sensor and sensor in self.SENSOR_TO_CAMERA:
                                camera_index = self.SENSOR_TO_CAMERA[sensor]
                                print(f"🚨 Alerta detectada: {sensor} → Cámara {camera_index}")
                                self._start_camera_recording(sensor, camera_index)
                            else:
                                print(f"⚠️ Sensor no reconocido o no configurado: {linea}")

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
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")

    def get_status_report(self) -> str:
        """
        Devuelve un reporte legible del estado actual del sistema.
        """
        report = "\n📊 ESTADO DEL SISTEMA:\n"
        active_recordings = self.recording_manager.get_recording_count()
        report += f"   Grabaciones activas: {active_recordings}\n"

        for sensor, grabando in self.estado_sensores.items():
            cam_idx = self.SENSOR_TO_CAMERA.get(sensor, -1)
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
    print("="*60)
    print("🔒 SISTEMA DE SEGURIDAD CON ARDUINO")
    print("="*60)
    
    system = SecuritySystem(arduino_port="COM3", output_dir="Videos")
    
    if not system.SENSOR_TO_CAMERA:
        print("\n❌ Sistema sin configuración de cámaras. Saliendo...")
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
                print("⚠️ Comando no reconocido. Use: activacion, desactivacion, status, quit")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()