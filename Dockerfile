# AulaNube Rutas: una imagen para las tres iteraciones (la variable VERSION elige v1, v2 o v3).
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app VERSION=v3
RUN useradd --create-home --uid 10001 rutas && mkdir /datos && chown rutas /datos
WORKDIR /app
COPY rutas ./rutas
USER rutas
EXPOSE 7400
# Al arrancar crea la base de demostración (datos ficticios) si no existe.
CMD ["sh", "-c", "python -m rutas.servidor --version $VERSION --db /datos/rutas.db --puerto 7400"]
