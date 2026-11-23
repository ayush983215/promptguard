# API service. Build:  docker build -t promptguard .
# Run:   docker run -p 8000:8000 -e PG_ADMIN_TOKEN=change-me -v pg-data:/data -e PG_DB=/data/audit.db promptguard
FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pguard ./pguard
COPY policy.yaml .
USER app
EXPOSE 8000
CMD ["uvicorn", "pguard.api:app", "--host", "0.0.0.0", "--port", "8000"]
