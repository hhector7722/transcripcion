# Supabase – Base de datos de audios

## Tabla `audios` (máximo 5 registros)

- Cada vez que se inserta un audio nuevo, si ya hay 5, se **elimina el más antiguo** automáticamente.
- Diseño: `id`, `filename`, `storage_path`, `transcription_text`, `file_size_bytes`, `created_at`.
- RLS activado: solo usuarios `authenticated` pueden leer/insertar/borrar. Si tu app no usa auth, puedes crear una policy para `anon` en el SQL.

## Cómo aplicar la migración en Supabase

1. Entra en tu proyecto: [Supabase Dashboard](https://supabase.com/dashboard) → tu proyecto.
2. **SQL Editor** → New query.
3. Copia y pega todo el contenido de:
   `supabase/migrations/20250312000000_create_audios_rolling.sql`
4. Run.

Si usas Supabase CLI en el proyecto:

```bash
supabase link --project-ref TU_PROJECT_REF
supabase db push
```

## Variables de entorno (para la app)

En tu app (por ejemplo `app.py` o `.env`) necesitarás:

- `SUPABASE_URL`: URL del proyecto.
- `SUPABASE_SERVICE_ROLE_KEY` o `SUPABASE_ANON_KEY`: clave para las peticiones.

No subas las keys al repo; usa `.env` y ten `.env` en `.gitignore`.
