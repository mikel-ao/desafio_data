FROM python:3.11-slim

WORKDIR /app

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY main.py .

# Crear directorio para la BD SQLite
RUN mkdir -p /data

# Variable de entorno para la ruta de la BD
ENV DB_PATH=/data/weights.db

# Puerto
EXPOSE 8000

# Arrancar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
