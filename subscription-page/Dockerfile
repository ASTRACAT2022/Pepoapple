FROM python:3.11-slim

WORKDIR /app
COPY app.py /app/app.py

RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic-settings

EXPOSE 3010
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3010"]
