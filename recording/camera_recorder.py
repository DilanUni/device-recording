import cv2 as cv
import time
import threading
from typing import Dict, Optional
from recording.RecordingManager import RecordingManager


class CameraRecorder:
    """
    Gestiona la captura y grabación de video desde cámaras.
    """
    
    def __init__(self, recording_manager: RecordingManager):
        self.recording_manager = recording_manager
        self.active_captures: Dict[str, cv.VideoCapture] = {}
        self.capture_threads: Dict[str, threading.Thread] = {}
        self.should_stop_capture: Dict[str, bool] = {}
    
    def _capture_and_record(self, sensor: str, camera_index: int):
        """Hilo que captura frames y los escribe usando RecordingManager."""
        cap = cv.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"❌ No se pudo abrir cámara {camera_index} para {sensor}")
            return

        self.active_captures[sensor] = cap
        
        ret, frame = cap.read()
        if not ret:
            print(f"❌ No se pudo leer frame inicial para {sensor}")
            cap.release()
            return

        if not self.recording_manager.start_recording(sensor, frame, "camera"):
            print(f"❌ No se pudo iniciar grabación para {sensor}")
            cap.release()
            return

        print(f"✅ Captura y grabación iniciada para {sensor}")

        while not self.should_stop_capture.get(sensor, False):
            ret, frame = cap.read()
            if not ret:
                print(f"⚠️ Error leyendo frame de {sensor}")
                time.sleep(0.1)
                continue

            self.recording_manager.write_frame(sensor, frame)
            time.sleep(0.01)

        cap.release()
        if sensor in self.active_captures:
            del self.active_captures[sensor]
        
        print(f"🛑 Captura finalizada para {sensor}")
    
    def start_recording(self, sensor: str, camera_index: int, device_name: str) -> bool:
        """Inicia grabación de video para un sensor específico."""
        if sensor in self.capture_threads and self.capture_threads[sensor].is_alive():
            print(f"⚠️ Sensor {sensor} ya tiene una grabación activa")
            return False

        try:
            print(f"🎬 Iniciando grabación para {sensor}...")
            
            self.should_stop_capture[sensor] = False
            
            thread = threading.Thread(
                target=self._capture_and_record,
                args=(sensor, camera_index),
                daemon=True
            )
            thread.start()
            
            self.capture_threads[sensor] = thread
            print(f"✅ {sensor} activó cámara {camera_index} ({device_name})")
            return True

        except Exception as e:
            print(f"❌ Error iniciando grabación para {sensor}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_all_recordings(self):
        """Detiene todas las grabaciones activas."""
        if not self.capture_threads:
            print("ℹ️ No hay grabaciones activas para detener")
            return
            
        print("🛑 Deteniendo todas las grabaciones...")
        
        for sensor in list(self.capture_threads.keys()):
            self.should_stop_capture[sensor] = True
        
        for sensor, thread in list(self.capture_threads.items()):
            try:
                thread.join(timeout=2.0)
            except Exception as e:
                print(f"❌ Error esperando hilo de {sensor}: {e}")
        
        self.recording_manager.stop_all()
        
        self.capture_threads.clear()
        self.should_stop_capture.clear()
        
        for sensor, cap in list(self.active_captures.items()):
            try:
                cap.release()
            except:
                pass
        self.active_captures.clear()

        print("✅ Todas las grabaciones detenidas")
    
    def is_recording(self, sensor: str) -> bool:
        """Verifica si un sensor está grabando."""
        return sensor in self.capture_threads and self.capture_threads[sensor].is_alive()