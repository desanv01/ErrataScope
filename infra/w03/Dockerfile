FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-service.lock /tmp/requirements-service.lock
COPY requirements-ingestion.lock /tmp/requirements-ingestion.lock
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: \
    -r /tmp/requirements-service.lock \
    && pip install --no-cache-dir --require-hashes --only-binary=:all: \
    -r /tmp/requirements-ingestion.lock \
    && python -c "import fastapi, sqlalchemy, alembic, psycopg, rq, jwt, cryptography, pdfplumber, pdfminer, pypdfium2, PIL; print('dependencies ok')"

COPY erratascope_domain /app/erratascope_domain
COPY erratascope_service /app/erratascope_service
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY tests /app/tests
COPY tests_w03 /app/tests_w03
COPY tests_w04 /app/tests_w04
COPY fixtures /app/fixtures

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /var/lib/erratascope/artifacts /var/lib/erratascope/test-artifacts \
       /var/lib/erratascope/app-artifacts /.local/w02 \
    && chown -R appuser:appuser /app /var/lib/erratascope /.local/w02
USER appuser

ENV PYTHONPATH=/app
EXPOSE 8000
