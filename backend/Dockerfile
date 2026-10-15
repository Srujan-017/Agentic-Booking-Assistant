FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Seed the vector store only if chroma_db is empty (it's a named volume in
# docker-compose, so this only runs once, on the first container start).
CMD ["sh", "-c", "if [ -z \"$(ls -A /app/chroma_db 2>/dev/null)\" ]; then python -m app.rag.ingest; fi; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
