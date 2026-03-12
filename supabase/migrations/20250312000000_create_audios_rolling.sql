-- ============================================================
-- Tabla audios: máximo 5 registros (se borra el más antiguo al insertar el 6º)
-- Ejecutar en Supabase: SQL Editor o CLI (supabase db push)
-- ============================================================

-- Tabla principal
CREATE TABLE IF NOT EXISTS public.audios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text,
  transcription_text text,
  file_size_bytes bigint,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Índice para ordenar por antigüedad (el trigger borra los más viejos)
CREATE INDEX IF NOT EXISTS idx_audios_created_at ON public.audios (created_at ASC);

-- Comentarios
COMMENT ON TABLE public.audios IS 'Últimos 5 audios procesados; al insertar el 6º se elimina el más antiguo.';

-- ============================================================
-- Función: mantener solo los 5 registros más recientes
-- ============================================================
CREATE OR REPLACE FUNCTION public.audios_keep_only_five()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  to_delete bigint;
BEGIN
  SELECT COUNT(*) - 5 INTO to_delete FROM public.audios;
  IF to_delete > 0 THEN
    DELETE FROM public.audios
    WHERE id IN (
      SELECT id FROM public.audios
      ORDER BY created_at ASC
      LIMIT (to_delete::int)
    );
  END IF;
  RETURN NEW;
END;
$$;

-- Trigger: después de cada INSERT
DROP TRIGGER IF EXISTS trg_audios_keep_only_five ON public.audios;
CREATE TRIGGER trg_audios_keep_only_five
  AFTER INSERT ON public.audios
  FOR EACH ROW
  EXECUTE FUNCTION public.audios_keep_only_five();

-- ============================================================
-- RLS (obligatorio)
-- ============================================================
ALTER TABLE public.audios ENABLE ROW LEVEL SECURITY;

-- Lectura: usuarios autenticados
CREATE POLICY "audios_select_authenticated"
  ON public.audios FOR SELECT
  TO authenticated
  USING (true);

-- Inserción: usuarios autenticados
CREATE POLICY "audios_insert_authenticated"
  ON public.audios FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Eliminación: usuarios autenticados (por si quieres borrar manualmente)
CREATE POLICY "audios_delete_authenticated"
  ON public.audios FOR DELETE
  TO authenticated
  USING (true);

-- Opcional: permitir anónimo si tu app no usa auth (descomenta si aplica)
-- CREATE POLICY "audios_all_anon" ON public.audios FOR ALL TO anon USING (true) WITH CHECK (true);
