# Usamos una imagen oficial de Python
FROM python:3.10-slim

# Instalamos dependencias del sistema necesarias para psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos los requerimientos primero para aprovechar la caché de Docker
COPY fudo_etl/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el contenido del proyecto.
COPY . .

# Configuramos el PYTHONPATH para que Python encuentre la carpeta 'clients'
ENV PYTHONPATH=/app

# El comando de inicio siempre es el mismo, la genericidad la da la variable CLIENT_NAME
CMD ["python", "fudo_etl/main.py"]