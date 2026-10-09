# ─────────────────────────────────────────────────────────────────────────────
# grupo06-frenet-lagrange — Servidor MCP (streamable-http) para la red Docker lab_net
#
#   docker build -t grupo06-frenet-lagrange .
#   docker compose up -d                         (ver docker-compose.yml)
#
# El contenedor escucha en 0.0.0.0:8000 (ruta /mcp) y guarda TODO en SeaweedFS por API S3:
# no escribe resultados en su propio disco, así que se puede reiniciar o replicar sin perder nada.
# ─────────────────────────────────────────────────────────────────────────────

# ── Etapa 1: dependencias en un entorno virtual ─────────────────────────────
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Etapa 2: imagen final, mínima y sin root ────────────────────────────────
FROM python:3.12-slim
LABEL org.opencontainers.image.title="grupo06-frenet-lagrange" \
      org.opencontainers.image.description="Servidor MCP (streamable-http): Lagrange, Hessiana y Frenet con SymPy exacto; almacenamiento en SeaweedFS (S3)"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    # ── transporte MCP ──
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_HTTP_PATH=/mcp \
    MCP_STATELESS=1 \
    # ── almacenamiento (SeaweedFS S3) ──
    MCP_MATH_STORAGE=s3 \
    MCP_GRUPO=grupo06 \
    SEAWEEDFS_S3_URL=http://seaweedfs:8333 \
    IMG_BUCKET=frenet-lagrange-imgs \
    PUBLIC_IMG_BASE_URL=https://rac-unmsm.vekthos.org/img/frenet-lagrange \
    # ── cálculo ──
    MCP_MATH_PROCESOS=1 \
    MCP_MATH_WORKERS=2 \
    MCP_MATH_TIMEOUT=120 \
    MCP_MATH_LOG=INFO

COPY --from=deps /opt/venv /opt/venv
RUN useradd --create-home --uid 1000 mcp
WORKDIR /app
COPY --chown=mcp:mcp core/ core/
COPY --chown=mcp:mcp methods/ methods/
COPY --chown=mcp:mcp templates/ templates/
COPY --chown=mcp:mcp server.py storage.py cli.py ./

USER mcp
EXPOSE 8000

# Falla el build si algo no importa (sin abrir conexiones: MCP_MATH_STORAGE=local solo para esta prueba)
RUN MCP_MATH_STORAGE=local MCP_MATH_RESULTADOS=/tmp/prueba python -c "import server" >/dev/null

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=4).status == 200 else 1)"

ENTRYPOINT ["python", "server.py"]
