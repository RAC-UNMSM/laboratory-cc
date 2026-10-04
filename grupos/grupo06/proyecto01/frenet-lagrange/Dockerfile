# ─────────────────────────────────────────────────────────────────────────────
# Servidor MCP «Frenet, Lagrange y Puntos Críticos» — imagen para transporte STDIO
#
#   docker build -t mcp-math .
#   docker run -i --rm -v "$PWD/resultados:/data/resultados" mcp-math      ← así lo lanza un cliente MCP
#
# '-i' es imprescindible: el protocolo viaja por stdin/stdout. NO usar '-t' (un TTY
# altera los bytes del JSON-RPC).
# ─────────────────────────────────────────────────────────────────────────────

# ── Etapa 1: compilar dependencias en un entorno virtual ────────────────────
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Etapa 2: imagen final, mínima y sin root ────────────────────────────────
FROM python:3.12-slim
LABEL org.opencontainers.image.title="mcp-math-server" \
      org.opencontainers.image.description="Servidor MCP (STDIO): Lagrange, Hessiana y Frenet con SymPy exacto"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    MCP_MATH_RESULTADOS=/data/resultados \
    MCP_MATH_TIMEOUT=120 \
    MCP_MATH_LOG=INFO

COPY --from=deps /opt/venv /opt/venv
RUN useradd --create-home --uid 1000 mcp && mkdir -p /data/resultados && chown -R mcp:mcp /data
WORKDIR /app
COPY --chown=mcp:mcp core/ core/
COPY --chown=mcp:mcp methods/ methods/
COPY --chown=mcp:mcp templates/ templates/
COPY --chown=mcp:mcp server.py storage.py cli.py ./

USER mcp
VOLUME ["/data/resultados"]

# Comprobación rápida de que todo importa (falla el build si falta algo)
RUN python -c "import server; print('ok')" >/dev/null

ENTRYPOINT ["python", "server.py"]
