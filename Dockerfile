# Usamos una imagen ligera de Python 3.9
FROM python:3.9-slim

# 1. Instalar dependencias del sistema necesarias para OpenCV
# (OpenCV necesita librerías gráficas aunque no tenga pantalla)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Configurar directorio de trabajo
WORKDIR /app

# 3. Copiar requirements e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todo el código fuente
COPY src/ ./src/

# 5. Crear carpetas necesarias para que no falle al arrancar
RUN mkdir -p uploads

# 6. Exponer el puerto 8000
EXPOSE 8000

# 7. Comando para arrancar la aplicación
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]