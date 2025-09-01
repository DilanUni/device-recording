import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Formato: fecha-hora, nivel, mensaje
log_filename = os.path.join(LOG_DIR, f"recording_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # También imprime en consola
    ]
)

logger = logging.getLogger(__name__)
