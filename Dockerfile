FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir gemini-webapi fastapi uvicorn[standard] httpx

COPY api_server.py /app/
COPY web /app/web/

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
