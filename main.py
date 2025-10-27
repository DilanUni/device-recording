import os
import threading
from typing import Dict, List, Tuple, Optional
from utils.VideoDeviceDetection import VideoDeviceDetection
from recording.RecordingManager import RecordingManager
from config.camera_config_manager import CameraConfigManager
from recording.camera_recorder import CameraRecorder
from utils.arduino_listener import ArduinoListener


class SecuritySystem:
    """
    Sistema integrado de grabación de video con sensores Arduino.
    """

    def __init__(self, arduino_port: str = "COM3", output_dir: str = "Videos", 
                 config_file: str = "camera_config.json"):
        self.OUTPUT_DIR = output_dir
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        # Componentes
        self.config_manager = CameraConfigManager(config_file)
        self.recording_manager = RecordingManager(output_dir=self.OUTPUT_DIR, fps=30.0)
        self.camera_recorder = CameraRecorder(self.recording_manager)
        self.arduino_listener = ArduinoListener(arduino_port)
        
        # Configuración de cámaras
        self.SENSOR_TO_CAMERA: Dict[str, int] = {}
        self.device_map: List[Tuple[int, str]] = []
        
        # Inicializar
        self._setup_cameras()
    
    def _setup_cameras(self):
        """Detecta y configura cámaras."""
        # Detectar cámaras
        has_devices, message = VideoDeviceDetection.has_devices()
        print(f"\n🎥 {message}")

        if has_devices:
            self.device_map = VideoDeviceDetection.get_device_map()
            print("Cámaras detectadas:")
            for opencv_idx, device_name in self.device_map:
                print(f"  📹 [{opencv_idx}] {device_name}")
        else:
            print("⚠️ No se detectaron cámaras disponibles")
            return
        
        # Configurar asignación
        loaded_config = self.config_manager.load_config()
        
        if loaded_config:
            print(f"\n📄 Configuración encontrada en {self.config_manager.config_file}")
            
            if self.config_manager.validate_config_with_devices(loaded_config, self.device_map):
                self.SENSOR_TO_CAMERA = loaded_config
                print("✅ Configuración cargada y validada correctamente\n")
                self._print_current_config()
                return
            else:
                print("⚠️ La configuración no es compatible con dispositivos actuales\n")
        else:
            print("\n📝 No se encontró configuración previa\n")
        
        # Solicitar nueva configuración
        while True:
            response = input("¿Desea configurar las cámaras ahora? (s/n): ").strip().lower()
            
            if response == 's':
                new_config = self.config_manager.assign_cameras_interactive(self.device_map)
                
                if new_config:
                    self.SENSOR_TO_CAMERA = new_config
                    
                    save_response = input("¿Desea guardar esta configuración? (s/n): ").strip().lower()
                    if save_response == 's':
                        self.config_manager.save_config(new_config, self.device_map)
                    return
            
            elif response == 'n':
                print("⚠️ Sistema sin configuración - no podrá grabar")
                return
    
    def _print_current_config(self):
        """Imprime la configuración actual."""
        print("📋 Configuración actual:")
        for zone, cam_idx in self.SENSOR_TO_CAMERA.items():
            cam_name = next((name for idx, name in self.device_map if idx == cam_idx), "Desconocida")
            print(f"   {zone:20} → [{cam_idx}] {cam_name}")
        print()
    
    def _get_device_name_for_index(self, camera_index: int) -> Optional[str]:
        """Obtiene el nombre de la cámara por índice."""
        for idx, name in self.device_map:
            if idx == camera_index:
                return name
        return None
    
    def _on_sensor_alert(self, sensor: str):
        """Callback cuando Arduino detecta alerta."""
        if sensor not in self.SENSOR_TO_CAMERA:
            print(f"⚠️ Sensor {sensor} no configurado")
            return
        
        camera_index = self.SENSOR_TO_CAMERA[sensor]
        device_name = self._get_device_name_for_index(camera_index)
        
        if not device_name:
            print(f"❌ No se encontró dispositivo para índice {camera_index}")
            return
        
        print(f"🚨 Alerta detectada: {sensor} → Cámara {camera_index}")
        self.camera_recorder.start_recording(sensor, camera_index, device_name)
    
    def _on_system_deactivation(self):
        """Callback cuando Arduino desactiva el sistema."""
        self.camera_recorder.stop_all_recordings()
    
    def start_listening(self):
        """Inicia escucha de Arduino en hilo separado."""
        arduino_thread = threading.Thread(
            target=self.arduino_listener.listen,
            args=(self._on_sensor_alert, self._on_system_deactivation),
            daemon=True
        )
        arduino_thread.start()
        return arduino_thread
    
    def get_status_report(self) -> str:
        """Devuelve reporte del estado actual."""
        report = "\n📊 ESTADO DEL SISTEMA:\n"
        active_recordings = self.recording_manager.get_recording_count()
        report += f"   Grabaciones activas: {active_recordings}\n"

        for sensor in self.SENSOR_TO_CAMERA.keys():
            cam_idx = self.SENSOR_TO_CAMERA[sensor]
            is_recording = self.camera_recorder.is_recording(sensor)
            status = "🔴 GRABANDO" if is_recording else "⚪ INACTIVO"
            report += f"   {sensor} (cám {cam_idx}): {status}\n"

        return report
    
    def close(self):
        """Cierra el sistema."""
        print("🧹 Cerrando sistema...")
        self.camera_recorder.stop_all_recordings()
        self.arduino_listener.close()


def main():
    print("="*60)
    print("🔒 SISTEMA DE SEGURIDAD CON ARDUINO")
    print("="*60)
    
    system = SecuritySystem(arduino_port="COM3", output_dir="Videos")
    
    if not system.SENSOR_TO_CAMERA:
        print("\n❌ Sistema sin configuración de cámaras. Saliendo...")
        return
    
    print(system.get_status_report())
    system.start_listening()

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
                system.arduino_listener.send_command(cmd)
                if cmd == "desactivado":
                    system.camera_recorder.stop_all_recordings()
            else:
                print("⚠️ Comando no reconocido")

    except KeyboardInterrupt:
        print("\n⏹️ Programa interrumpido por usuario")
    finally:
        system.close()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()