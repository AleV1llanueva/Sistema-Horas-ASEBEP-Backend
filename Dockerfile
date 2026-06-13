# 1. Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# 2. Configurar el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar la lista de dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todo el código del repositorio del backend hacia el contenedor
COPY . .

# 5. Exponer el puerto interno en el que corre Uvicorn
EXPOSE 8000

# 6. Comando para arrancar tu API de FastAPI en producción
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
