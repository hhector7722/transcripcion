import os
import time
import shutil
import re
import logging
import torch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel

# --- CONFIGURACIÓN ---
INPUT_DIR = "input_audios"
OUTPUT_DIR = "output_text"
PROCESSED_DIR = "procesados"
MODEL_SIZE = "small"

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """Sanitiza el nombre del archivo eliminando caracteres especiales y espacios."""
    name, ext = os.path.splitext(filename)
    # Reemplazar espacios por guiones bajos y eliminar caracteres no alfanuméricos
    sanitized_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    return f"{sanitized_name}{ext}"

class Transcriptor:
    def __init__(self):
        # Detección de Hardware
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.cpu_threads = 4
        
        logger.info(f"Iniciando Transcriptor en {self.device.upper()} (compute_type={self.compute_type})")
        
        # Carga del modelo
        self.model = WhisperModel(
            MODEL_SIZE, 
            device=self.device, 
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads
        )

    def process_audio(self, file_path):
        try:
            filename = os.path.basename(file_path)
            # 1. Sanitización
            sanitized_name = sanitize_filename(filename)
            temp_path = os.path.join(INPUT_DIR, sanitized_name)
            
            if filename != sanitized_name:
                logger.info(f"Renombrando {filename} a {sanitized_name}")
                os.rename(file_path, temp_path)
                file_path = temp_path
            
            # 2. Transcripción
            logger.info(f"Procesando: {sanitized_name}")
            segments, info = self.model.transcribe(file_path, beam_size=5)
            
            logger.info(f"Idioma detectado: {info.language} (probabilidad: {info.language_probability:.2f})")
            
            full_text = []
            for segment in segments:
                full_text.append(segment.text)
            
            # 3. Guardar Resultado
            txt_filename = os.path.splitext(sanitized_name)[0] + ".txt"
            output_path = os.path.join(OUTPUT_DIR, txt_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(full_text))
            
            # 4. Mover a Procesados
            final_processed_path = os.path.join(PROCESSED_DIR, sanitized_name)
            shutil.move(file_path, final_processed_path)
            
            logger.info(f"Finalizado: {txt_filename} guardado y audio movido a {PROCESSED_DIR}")

        except Exception as e:
            logger.error(f"Error procesando {file_path}: {e}")

class AudioHandler(FileSystemEventHandler):
    def __init__(self, transcriptor):
        self.transcriptor = transcriptor

    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path.lower().endswith('.ogg'):
            logger.info(f"Nuevo archivo detectado: {event.src_path}")
            # Esperar un poco para asegurar que la escritura ha terminado (basice handle for WhatsApp copy)
            time.sleep(1)
            self.transcriptor.process_audio(event.src_path)

if __name__ == "__main__":
    # Asegurar que los directorios existen
    for d in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

    transcriptor = Transcriptor()
    event_handler = AudioHandler(transcriptor)
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIR, recursive=False)
    
    logger.info(f"Servicio activo. Vigilando carpeta: {INPUT_DIR}")
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
