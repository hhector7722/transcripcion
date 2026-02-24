import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import uvicorn

app = FastAPI(title="Transcriptor Dashboard")

# Configuración de rutas
INPUT_DIR = "input_audios"
OUTPUT_DIR = "output_text"
PROCESSED_DIR = "procesados"
STATIC_DIR = "static"

# Asegurar directorios
for d in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, STATIC_DIR]:
    os.makedirs(d, exist_ok=True)

# Servir archivos estáticos (HTML/CSS/JS)
app.mount("/view", StaticFiles(directory=STATIC_DIR, html=True), name="static")

@app.get("/api/transcriptions")
async def list_transcriptions():
    """Lista todos los archivos de texto generados."""
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    files = []
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".txt"):
            path = os.path.join(OUTPUT_DIR, f)
            stats = os.stat(path)
            files.append({
                "name": f,
                "id": f,
                "created_at": stats.st_mtime,
                "size": stats.st_size,
                "status": "completed"
            })
    # Obtener archivos en proceso
    for f in os.listdir(INPUT_DIR):
        if f.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a')):
            path = os.path.join(INPUT_DIR, f)
            stats = os.stat(path)
            files.append({
                "name": f,
                "id": f,
                "created_at": stats.st_mtime,
                "size": stats.st_size,
                "status": "processing"
            })
            
    # Ordenar por fecha de creación descendente
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return files

@app.get("/api/transcription/{filename}")
async def get_transcription(filename: str):
    """Obtiene el contenido de una transcripción específica."""
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Buscar el audio original en procesados
        audio_name = filename.replace(".txt", ".ogg")
        has_audio = os.path.exists(os.path.join(PROCESSED_DIR, audio_name))
        
        return {
            "name": filename,
            "content": content,
            "audio_url": f"/api/audio/{audio_name}" if has_audio else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Sirve el archivo de audio procesado."""
    path = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio no encontrado")
    return FileResponse(path)

@app.delete("/api/transcription/{filename}")
async def delete_transcription(filename: str):
    """Elimina una transcripción y su audio asociado (si existe)."""
    # Archivo de texto
    txt_path = os.path.join(OUTPUT_DIR, filename)
    
    # Intentar eliminar el texto
    if os.path.exists(txt_path):
        try:
            os.remove(txt_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al eliminar texto: {str(e)}")
            
    # Intentar eliminar el audio procesado asociado
    audio_name = filename.replace(".txt", ".ogg")
    audio_path = os.path.join(PROCESSED_DIR, audio_name)
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception:
            pass # No fallar si el audio no se puede borrar
            
    return {"status": "success", "message": "Transcripción eliminada"}

@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Sube un archivo a la carpeta de entrada para ser procesado."""
    if not file.filename.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a')):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")
    
    file_path = os.path.join(INPUT_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"filename": file.filename, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def redirect_to_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    print("Servidor GUI iniciado en http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
