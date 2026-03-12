import os
import shutil
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import uvicorn

from firebase_config import init_firebase, get_firestore, get_storage_bucket, is_firebase_configured

app = FastAPI(title="Transcriptor Dashboard")

# Firebase (opcional): al arrancar se inicializa si hay env configurado
init_firebase()
FIREBASE_AUDIOS_COLLECTION = "audios"
FIREBASE_MAX_AUDIOS = 5

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


def _firebase_keep_only_five() -> None:
    """Elimina los audios más antiguos en Firestore y Storage si hay más de FIREBASE_MAX_AUDIOS."""
    if not is_firebase_configured():
        return
    db = get_firestore()
    bucket = get_storage_bucket()
    coll = db.collection(FIREBASE_AUDIOS_COLLECTION)
    docs = list(coll.order_by("created_at").stream())
    to_remove = len(docs) - FIREBASE_MAX_AUDIOS
    if to_remove <= 0:
        return
    for doc in docs[:to_remove]:
        data = doc.to_dict()
        storage_path = data.get("storage_path")
        if storage_path:
            try:
                blob = bucket.blob(storage_path)
                blob.delete()
            except Exception:
                pass
        doc.reference.delete()

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
    """Sube un archivo a la carpeta de entrada para ser procesado. Si Firebase está configurado, también se sube a la nube (máx. 5)."""
    if not file.filename.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a')):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")

    file_path = os.path.join(INPUT_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Firebase: subir a Storage y registrar en Firestore; mantener solo los 5 más recientes
    if is_firebase_configured():
        try:
            bucket = get_storage_bucket()
            db = get_firestore()
            file_size = os.path.getsize(file_path)
            safe_name = f"{int(time.time())}_{file.filename}"
            storage_path = f"audios/{safe_name}"
            blob = bucket.blob(storage_path)
            blob.upload_from_filename(file_path, content_type=file.content_type or "audio/ogg")
            doc_ref = db.collection(FIREBASE_AUDIOS_COLLECTION).add({
                "filename": file.filename,
                "storage_path": storage_path,
                "transcription_text": "",
                "file_size_bytes": file_size,
                "created_at": time.time(),
            })[1]
            _firebase_keep_only_five()
        except Exception as e:
            # No fallar el upload local si Firebase falla
            pass

    return {"filename": file.filename, "status": "queued"}


@app.get("/api/audios")
async def list_firebase_audios():
    """Lista los últimos 5 audios en Firebase (Storage + Firestore). Para móvil: incluye URL firmada de descarga."""
    if not is_firebase_configured():
        return []
    db = get_firestore()
    bucket = get_storage_bucket()
    docs = list(db.collection(FIREBASE_AUDIOS_COLLECTION).order_by("created_at", direction="DESCENDING").stream())
    result = []
    for doc in docs:
        data = doc.to_dict()
        storage_path = data.get("storage_path") or ""
        url = ""
        if storage_path:
            try:
                blob = bucket.blob(storage_path)
                url = blob.generate_signed_url(expiration=3600, method="GET")
            except Exception:
                pass
        result.append({
            "id": doc.id,
            "filename": data.get("filename", ""),
            "url": url,
            "transcription_text": data.get("transcription_text") or "",
            "file_size_bytes": data.get("file_size_bytes"),
            "created_at": data.get("created_at"),
        })
    return result


@app.get("/")
async def redirect_to_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    # Hugging Face Spaces suele usar el 7860, en local usaremos el 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    # En local es más cómodo usar 127.0.0.1 (localhost), pero para producción/Docker debe ser 0.0.0.0
    host = os.environ.get("HOST", "127.0.0.1")
    
    print(f"Servidor GUI iniciado en http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
