import serial
import time
import grabacion
import os
from datetime import datetime
import threading

# Configuración
grab = grabacion.Grabacion()
OUTPUT_DIR = "Videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mapeo de sensores a cámaras
SENSOR_TO_CAMERA = {
    "estacionamiento": 0, #estan todos en 0 porque solo tengo una camara xd ya cuando conecte mas camaras asigno a cada sensor una camara
    "entrada": 0,
    "salida": 0,
    "bodega": 0,
}

# Estado actual de grabación por sensor (None al inicio)
estado_sensores = {sensor: None for sensor in SENSOR_TO_CAMERA}

# Conectar Arduino
arduino = serial.Serial("COM3", 9600, timeout=1)
time.sleep(2)  # Esperar a que Arduino arranque

# ---------------- Funciones ----------------

def procesar_evento(sensor: str, estado: str):
    """Inicia grabación cuando sensor se activa; detener solo por 'desactivado'."""
    if sensor in SENSOR_TO_CAMERA:
        cam_index = SENSOR_TO_CAMERA[sensor]

        # Solo iniciar grabación si sensor pasa a 1 y no estaba grabando ya
        if estado == "1" and estado_sensores[sensor] != "1":
            estado_sensores[sensor] = "1"
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(OUTPUT_DIR, f"{sensor}_{timestamp}.mp4")
            grab.start_recording(cam_index, filename=filename)
            print(f"🎥 {sensor} activó cámara {cam_index} → {filename}")

def escuchar_arduino():
    """Lee Arduino continuamente en tiempo real"""
    while True:
        while arduino.in_waiting > 0:
            linea = arduino.readline().decode("utf-8").strip()
            if linea.startswith("SENSOR:"):
                try:
                    _, sensor, estado = linea.split(":")
                    procesar_evento(sensor, estado)
                except ValueError:
                    print(f"⚠️ Línea malformada: {linea}")
        time.sleep(0.01)  # Pequeña pausa para no bloquear CPU

def enviar_a_arduino(msg: str):
    arduino.write((msg + "\n").encode("utf-8"))
    print(f"➡️ Enviado a Arduino: {msg}")

# ---------------- Main ----------------

if __name__ == "__main__":
    # Hilo para leer Arduino en segundo plano
    hilo = threading.Thread(target=escuchar_arduino, daemon=True)
    hilo.start()

    print("Escuchando Arduino en tiempo real... escribe 'activado' o 'desactivado' para el sistema.")

    try:
        while True:
            cmd = input("Comando → ").strip()
            if cmd in ["activado", "desactivado"]:
                enviar_a_arduino(cmd)
                if cmd == "desactivado":
                    # Detener todas las grabaciones activas
                    for sensor, cam_index in SENSOR_TO_CAMERA.items():
                        grab.stop_recording(cam_index)
                        estado_sensores[sensor] = "0"
                        print(f"🛑 Cámara {cam_index} detenida por desactivado")
    except KeyboardInterrupt:
        print("Programa detenido.")
        arduino.close()
