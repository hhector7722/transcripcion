# Configurar Firebase para audios (móvil)

1. **Crear proyecto** en [Firebase Console](https://console.firebase.google.com/).
2. **Activar Storage y Firestore** (modo producción; luego puedes ajustar reglas).
3. **Cuenta de servicio**:  
   Project settings → Service accounts → **Generate new private key** → descarga el JSON.
4. **Variables de entorno** (en `.env`, que no se sube al repo):
   - `FIREBASE_CREDENTIALS_JSON`: contenido completo del JSON entre comillas, o
   - `GOOGLE_APPLICATION_CREDENTIALS`: ruta al archivo `.json`.
   - `FIREBASE_STORAGE_BUCKET`: nombre del bucket (ej. `tu-proyecto-id.appspot.com`).
5. **Instalar dependencias**: `pip install -r requirements.txt` (incluye `firebase-admin`).
6. **Probar**: subir un audio con `POST /api/upload` y listar con `GET /api/audios`. En la respuesta verás `url` (firmada, 1h) para reproducir en móvil.

## Uso desde móvil

- **Subir**: `POST /api/upload` con `multipart/form-data`, campo `file` (audio).
- **Listar**: `GET /api/audios` → array de `{ id, filename, url, transcription_text, file_size_bytes, created_at }`. Usar `url` para descargar/reproducir el audio.

Las URLs firmadas expiran en 1 hora; para listas largas o uso prolongado puedes implementar un endpoint que devuelva una nueva URL firmada por `id`.
