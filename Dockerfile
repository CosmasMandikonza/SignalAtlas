FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir . && useradd --uid 10001 --create-home observer && mkdir /state && chown observer:observer /state
USER observer
EXPOSE 8000
CMD ["uvicorn", "signalatlas.api:app", "--host", "0.0.0.0", "--port", "8000"]
