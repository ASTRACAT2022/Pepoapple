FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY app /app/app
COPY sql /app/sql
COPY scripts /app/scripts

RUN pip install --no-cache-dir \
  fastapi \
  uvicorn[standard] \
  sqlalchemy \
  'psycopg[binary]' \
  pydantic-settings \
  python-multipart \
  python-jose[cryptography] \
  passlib \
  redis \
  strawberry-graphql[fastapi] \
  httpx

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
