FROM python:3.10-slim

# Instalar dependencias del sistema necesarias para ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de dependencias
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto que usará FastAPI
EXPOSE 7860

# Comando para ejecutar la aplicación
ENV PORT=7860
ENV HOST=0.0.0.0
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
