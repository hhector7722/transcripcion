# Estado del proyecto – Transcripciones

## Base de datos (Supabase)

- **Tabla `audios`**: creada por migración en `supabase/migrations/`.
  - Mantiene solo los **5 audios más recientes**: al insertar el 6º se borra el más antiguo (trigger).
  - Campos: `id`, `filename`, `storage_path`, `transcription_text`, `file_size_bytes`, `created_at`.
  - RLS activado (políticas para `authenticated`).
- **Cómo aplicar**: ejecutar el SQL de la migración en Supabase → SQL Editor, o `supabase db push` si usas CLI.

## Pendiente

- Conectar la app (FastAPI/transcriptor) con Supabase para guardar/consultar audios en esta tabla.
- Configurar `SUPABASE_URL` y clave en `.env` (sin subir keys al repo).
