import os
import json
from datetime import datetime
from typing import Dict, Optional, List, Tuple


class CameraConfigManager:
    """
    Gestiona la configuración de asignación de cámaras a zonas.
    """
    
    def __init__(self, config_file: str = "camera_config.json"):
        self.config_file = config_file
        self.zones = ["ENTRADA", "SALIDA", "ESTACIONAMIENTO", "BODEGA"]
    
    def load_config(self) -> Optional[Dict[str, int]]:
        """Carga la configuración desde el archivo JSON."""
        if not os.path.exists(self.config_file):
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, dict) or 'sensor_to_camera' not in config:
                print("⚠️ Archivo de configuración inválido")
                return None
            
            sensor_to_camera = config['sensor_to_camera']
            
            if not all(zone in sensor_to_camera for zone in self.zones):
                print("⚠️ Configuración incompleta - faltan zonas")
                return None
            
            return sensor_to_camera
        
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            return None
    
    def save_config(self, sensor_to_camera: Dict[str, int], 
                   device_map: List[Tuple[int, str]]) -> bool:
        """Guarda la configuración en el archivo JSON."""
        try:
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
        """Valida que la configuración sea compatible con dispositivos actuales."""
        available_indices = {idx for idx, _ in device_map}
        configured_indices = set(sensor_to_camera.values())
        missing_indices = configured_indices - available_indices
        
        if missing_indices:
            print(f"⚠️ Cámaras configuradas no disponibles: {missing_indices}")
            return False
        
        return True
    
    def assign_cameras_interactive(self, device_map: List[Tuple[int, str]]) -> Dict[str, int]:
        """Permite al usuario asignar cámaras a zonas de forma interactiva."""
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
        
        print("\n" + "="*60)
        print("📋 RESUMEN DE ASIGNACIÓN:")
        print("="*60)
        for zone, cam_idx in sensor_to_camera.items():
            cam_name = next(name for idx, name in device_map if idx == cam_idx)
            print(f"  {zone:20} → [{cam_idx}] {cam_name}")
        print("="*60 + "\n")
        
        return sensor_to_camera