## Logs

### timestamp
Momento exacto en que se registró el evento.
* *Ejemplo: "```2025-09-14T17:25:19.137116```"*

### event
Tipo de evento de la grabación. Puede ser:
* "START" → Inicio de la grabación de un clip o cámara.
* "STOP" → Fin de la grabación.
* "ERROR" → Hubo un fallo al intentar iniciar o detener la grabación.
* "WARNING" → Advertencia sobre un intento inválido (por ejemplo, intentar iniciar mientras ya se graba).

* *Ejemplo: "```START```"*

### source
Fuente del video que se está grabando.
Para cámaras en vivo: el nombre de la cámara puede ser por ejemplo ("```GENERAL WEBCAM```")

Para archivos de video: la ruta completa del archivo original ("```Videos/VideoFiles/video.mp4```")

### output_file
Ruta y nombre del archivo generado por la grabación.
* *Ejemplo: "```videos/cameras/general_webcam_20250914_172519.mp4```"*

### codec
Codec de video usado para la grabación.
Valores típicos según la GPU:
* "```hevc_amf```" → AMD H.265
* "```hevc_nvenc```" → NVIDIA H.265
* "```libx265```" → CPU H.265

* *Ejemplo: "```hevc_amf```"*

### resolution
Resolución de salida del video. Solo tiene valor si se conoce la resolución (normalmente para cámaras en vivo).
Por defecto está en "```1280x720```"

### duration
Duración del clip en segundos.
* Solo se rellena cuando el evento es "STOP".

* *Ejemplo: ```8.427376```*

### status
Estado del evento registrado.

Valores posibles:
* "```IN_PROGRESS```" → Grabación en curso (eventos START).
* "```SUCCESS```" → Grabación completada correctamente (eventos STOP).
* "```FAILED```" → Error en la grabación (eventos ERROR).
* "```ALREADY_RECORDING```" / "```NOT_RECORDING```" → Advertencias (eventos WARNING).

* *Ejemplo: "```SUCCESS```"*

### extra
Información adicional según el contexto del evento:

* Para clips de archivos: clip_start y clip_end (segundos del segmento grabado).
* Para errores: exception con el mensaje de error.
* Para STOP: ffmpeg_stderr con la salida de FFmpeg para depuración.
* Para cámaras: normalmente vacío {}.

* *Ejemplo:* ```"extra": {"clip_start": 5, "clip_end": 10}```