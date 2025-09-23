import cv2
import threading

def detectar_camaras(max_index=5):
    disponibles = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # CAP_DSHOW = más estable en Windows
        if cap.isOpened():
            disponibles.append(i)
            cap.release()
    return disponibles


class Grabacion:
    def __init__(self):
        self.captures = {}
        self.writers = {}

    def start_recording(self, cam_index, filename="output.mp4"):
        if cam_index in self.captures:
            print(f"⚠️ La cámara {cam_index} ya está grabando")
            return

        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara {cam_index}")

        # obtener resolución real de la cámara
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:  # fallback por si no devuelve fps
            fps = 20.0

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # codec más compatible
        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))

        self.captures[cam_index] = cap
        self.writers[cam_index] = out
        print(f"✅ Grabando cámara {cam_index} ({width}x{height} @ {fps}fps) -> {filename}")

        def loop():
            while cam_index in self.captures:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)

        threading.Thread(target=loop, daemon=True).start()

    def stop_recording(self, cam_index):
        if cam_index not in self.captures:
            print(f"⚠️ La cámara {cam_index} no estaba grabando")
            return

        self.captures[cam_index].release()
        self.writers[cam_index].release()
        del self.captures[cam_index]
        del self.writers[cam_index]
        print(f"🛑 Cámara {cam_index} detenida")
