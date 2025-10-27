import serial
import time
from typing import Optional, Callable


class ArduinoListener:
    """
    Gestiona la comunicación con Arduino.
    """
    
    def __init__(self, port: str = "COM3", baudrate: int = 9600):
        self.arduino = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)
        print(f"✅ Arduino conectado en {port}")
    
    def parse_alert_message(self, message: str) -> Optional[str]:
        """Extrae el sensor que activó la alerta desde el mensaje."""
        message_upper = message.upper()
        sensors = ["ENTRADA", "SALIDA", "ESTACIONAMIENTO", "BODEGA"]
        
        for sensor in sensors:
            if sensor in message_upper:
                return sensor
        return None
    
    def listen(self, on_alert: Callable[[str], None], 
              on_deactivation: Callable[[], None]):
        """
        Escucha continuamente los mensajes del Arduino.
        
        Args:
            on_alert: Función a llamar cuando se detecta alerta (recibe sensor)
            on_deactivation: Función a llamar cuando se desactiva el sistema
        """
        print("👂 Iniciando escucha de Arduino...")
        
        while True:
            try:
                if self.arduino.in_waiting > 0:
                    linea = self.arduino.readline().decode("utf-8", errors='ignore').strip()
                    
                    if linea:
                        print(f"📨 Arduino: {linea}")

                        if "ALERTA:" in linea:
                            sensor = self.parse_alert_message(linea)
                            if sensor:
                                on_alert(sensor)
                            else:
                                print(f"⚠️ Sensor no reconocido: {linea}")

                        elif "alarmaActiva=0" in linea or "DESACTIVADO" in linea:
                            print("🔴 Desactivación detectada")
                            on_deactivation()
                
                time.sleep(0.01)
                
            except serial.SerialException as e:
                print(f"❌ Error de conexión serial: {e}")
                break
            except Exception as e:
                print(f"❌ Error leyendo Arduino: {e}")
                import traceback
                traceback.print_exc()
    
    def send_command(self, comando: str):
        """Envía comando al Arduino."""
        try:
            self.arduino.write((comando + "\n").encode("utf-8"))
            print(f"➡️ Enviado a Arduino: {comando}")
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")
    
    def close(self):
        """Cierra la conexión con Arduino."""
        if hasattr(self, 'arduino') and self.arduino.is_open:
            self.arduino.close()
            print("✅ Arduino desconectado")