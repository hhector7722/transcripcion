# Estado del proyecto – Transcripciones

## Firebase (audios en la nube para móvil) ✅

- **Storage**: los audios subidos se guardan en Firebase Storage (carpeta `audios/`).
- **Firestore**: colección `audios` con metadata (filename, storage_path, transcription_text, file_size_bytes, created_at).
- **Rotación**: se mantienen solo los **5 más recientes**. Al subir el 6º se elimina el más antiguo (doc en Firestore + archivo en Storage).
- **Endpoints**:
  - `POST /api/upload`: sube a local y, si Firebase está configurado, también a Storage + Firestore (y aplica rotación).
  - `GET /api/audios`: lista los 5 audios en Firebase con URL firmada (1h) para descarga/escucha en móvil.
- **Config**: `.env` con `FIREBASE_CREDENTIALS_JSON` o `GOOGLE_APPLICATION_CREDENTIALS` y `FIREBASE_STORAGE_BUCKET`. Ver `.env.example`.

## Pendiente

- Actualizar `transcription_text` en Firestore cuando el transcriptor termine (opcional: PATCH o hook desde transcriptor_auto.py).
