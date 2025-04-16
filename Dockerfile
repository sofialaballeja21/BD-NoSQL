FROM python:3.12-slim-bullseye

WORKDIR /API

COPY API/ .

# Instalar dependencias
RUN pip install -r requeriments.txt

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]

EXPOSE 5000