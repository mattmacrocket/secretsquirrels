FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/controlplane

COPY apps/controlplane-api/requirements.txt ./apps/controlplane-api/requirements.txt
RUN pip install --no-cache-dir -r ./apps/controlplane-api/requirements.txt

COPY adapters ./adapters
COPY config ./config
COPY scripts ./scripts
COPY harness ./harness
COPY apps/controlplane-api ./apps/controlplane-api

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /opt/controlplane

USER appuser
WORKDIR /opt/controlplane/apps/controlplane-api

EXPOSE 8199
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8199"]
