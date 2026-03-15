# FUNCTION_INVOCATION_FAILED en Vercel – Causa y solución

## 1. Qué se cambió en el código (fix)

- **Detectar Vercel** y usar un filesystem escribible: en Vercel el sistema de archivos es **solo lectura** excepto `/tmp`. La app intentaba crear carpetas (`input_audios`, `output_text`, etc.) en el directorio del proyecto y escribir ahí, lo que en serverless falla.
- **Cambios en `app.py`**:
  - Si `VERCEL=1`: se usa `BASE_DIR = "/tmp/transcripciones"` para rutas escribibles; las carpetas de trabajo son `BASE_DIR/input_audios`, `BASE_DIR/output_text`, `BASE_DIR/procesados`.
  - Si no es Vercel: se sigue usando el directorio del proyecto como hasta ahora.
  - `os.makedirs(...)` se envuelve en `try/except OSError` para que, si algo falla (por ejemplo en un entorno muy restringido), la app no se caiga al cargar.
  - En `list_transcriptions` se comprueba `os.path.exists(INPUT_DIR)` y `os.path.exists(OUTPUT_DIR)` antes de hacer `os.listdir`, para no lanzar excepciones si las carpetas no existen.
  - La ruta de `static` se resuelve con el directorio del script para que el dashboard siga sirviéndose bien en el despliegue.
  - La ruta `/` comprueba si existe `index.html` antes de devolver `FileResponse`; si no existe (p. ej. `static` no desplegado), devuelve un JSON para no romper.

Con esto, la función de Vercel ya no debería fallar por escritura en disco ni por falta de comprobaciones de existencia de directorios.

---

## 2. Por qué ocurría el error (causa raíz)

- **Qué hace Vercel**: ejecuta tu app como una **función serverless**: arranca el proceso, importa el módulo (p. ej. `app.py`) y atiende la petición. El entorno es efímero y el disco **solo permite escritura en `/tmp`**.
- **Qué hacía tu código**:
  - Al **importar** `app.py` se ejecutaba en el nivel de módulo:
    - `os.makedirs(INPUT_DIR, exist_ok=True)` (y lo mismo para otras carpetas) con rutas como `input_audios`, `output_text`, etc. (relativas al proyecto).
  - En Vercel ese directorio de trabajo suele ser **solo lectura**. Crear carpetas o archivos ahí lanza `OSError`/`PermissionError`.
- **Qué pasaba**: esa excepción ocurría **durante la carga del módulo**, antes de que FastAPI llegara a atender la petición. El runtime de la función veía que el proceso había fallado y respondía con **FUNCTION_INVOCATION_FAILED** (500).

Condiciones que lo disparaban:

- Despliegue en Vercel (entorno de solo lectura fuera de `/tmp`).
- Código que escribe o crea directorios en el arranque, asumiendo un filesystem “normal” de servidor.

La idea errónea: tratar el entorno de Vercel como un servidor con disco persistente y escribible en cualquier ruta.

---

## 3. Concepto: por qué existe este error y modelo mental

- **Por qué existe**: En serverless no hay “una máquina” que mantenga estado en disco entre invocaciones. El sistema limita la escritura a `/tmp` para aislar funciones y evitar que una rompa el entorno de otras. Si tu código asume que puede escribir en el directorio del proyecto, el runtime no puede garantizar eso y acabas con fallos de invocación.
- **Modelo mental**:
  - **Local / VPS**: el proceso vive mucho tiempo y el disco del proyecto suele ser escribible.
  - **Serverless (Vercel, Lambda, etc.)**: cada invocación puede ser un proceso nuevo, el filesystem es efímero y escribible solo donde la plataforma lo permita (en Vercel, `/tmp`). Todo lo que sea “estado” o “archivos subidos” debe ir a almacenamiento externo (Firebase, S3, BD, etc.) si quieres que persista.
- **Encaje en el diseño**: Las plataformas serverless exponen límites (disco, tiempo, memoria) para poder escalar y cobrar por uso. Tu código debe cumplir esos límites; si no, la invocación falla y la plataforma devuelve un 500 (en Vercel, FUNCTION_INVOCATION_FAILED).

---

## 4. Señales de alerta y patrones parecidos

- **Qué vigilar**:
  - Código que crea carpetas o escribe archivos **al importar** (nivel de módulo), no dentro de un endpoint.
  - Rutas de archivos **relativas** o **sin comprobar** si el directorio existe antes de `os.listdir` o `open(..., "w")`.
  - Asumir que el “directorio actual” o el directorio del proyecto es escribible.
- **Errores parecidos**:
  - Timeout o out-of-memory en la primera petición (cold start con muchas importaciones o inicialización pesada).
  - `ModuleNotFoundError` o fallos al importar si en el bundle falta algo o el path está mal.
- **Olores**: inicialización costosa o que toca disco/red en el nivel de módulo; falta de comprobación de `os.path.exists` antes de operaciones sobre rutas que pueden no existir en serverless.

---

## 5. Alternativas y trade-offs

- **Usar solo `/tmp` en serverless (lo aplicado)**  
  Ventaja: mismo código sirve en local y en Vercel. Desventaja: en Vercel los archivos en `/tmp` no persisten entre invocaciones; para transcripciones/audios que deban persistir, hay que subirlos a Firebase (o similar).

- **No escribir en disco en producción**  
  Subir el audio directamente a Firebase Storage desde el endpoint y guardar metadata en Firestore; no usar `input_audios`/`output_text` en Vercel. Ventaja: sin dependencia del disco. Desventaja: hay que adaptar la lógica para que “listar transcripciones” venga de Firestore/API, no de carpetas locales.

- **No usar Vercel para esta app**  
  Desplegar en un VPS o en un contenedor (Docker) con disco persistente. Ventaja: comportamiento igual que en local. Desventaja: más gestión y posiblemente más coste.

La opción implementada (usar `/tmp` en Vercel + comprobaciones y `try/except`) corrige el FUNCTION_INVOCATION_FAILED y mantiene la app funcionando tanto en local como en Vercel, usando Firebase para persistencia cuando lo tengas configurado.
