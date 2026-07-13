FROM python:3.12-slim

WORKDIR /srv/spec-monitor

# Camada de dependências separada para cache de build
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app

# Usuário não-root (spec 12 do LitiSense vale de inspiração aqui também)
RUN useradd --create-home appuser && chown -R appuser /srv/spec-monitor
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
