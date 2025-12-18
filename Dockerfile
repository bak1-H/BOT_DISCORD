FROM python:3.11-slim

# Instalar ffmpeg y dependencias del sistema
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Ejecutar el bot
CMD ["python", "bot.py"]
