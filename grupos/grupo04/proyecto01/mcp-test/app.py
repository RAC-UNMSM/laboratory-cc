"""Arranca el servidor MCP local y su Cloudflare Tunnel.

Uso desde esta carpeta:
    python app.py

Variables opcionales:
    CLOUDFLARED_EXE    Ruta al ejecutable cloudflared.exe (o host.exe).
    CLOUDFLARED_CONFIG Ruta al config.yml de Cloudflare.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SERVER_FILE = BASE_DIR / "server.py"
VENV_PYTHON = BASE_DIR / ".ENTORNO" / "Scripts" / "python.exe"
DEFAULT_CONFIG = BASE_DIR / "config.yml"


def find_cloudflared() -> str | None:
    configured = os.environ.get("CLOUDFLARED_EXE")
    if configured:
        return configured if Path(configured).is_file() else None

    on_path = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if on_path:
        return on_path

    for candidate in (BASE_DIR / "cloudflared.exe", BASE_DIR / "host.exe"):
        if candidate.is_file():
            return str(candidate)
    return None


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def tunnel_public_base(config_path: Path) -> str | None:
    """Obtiene el primer hostname HTTPS declarado en config.yml."""
    try:
        contents = config_path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    match = re.search(r"^\s*-\s*hostname:\s*([^\s#]+)", contents, re.MULTILINE)
    return f"https://{match.group(1)}" if match else None


def main() -> int:
    if not SERVER_FILE.is_file():
        print(f"ERROR: no se encuentra el servidor MCP: {SERVER_FILE}")
        return 1

    python = VENV_PYTHON if VENV_PYTHON.is_file() else Path(sys.executable)
    config = Path(os.environ.get("CLOUDFLARED_CONFIG", str(DEFAULT_CONFIG)))
    cloudflared = find_cloudflared()

    if not config.is_file():
        print(f"ERROR: no se encuentra la configuración de Cloudflare: {config}")
        print("Define CLOUDFLARED_CONFIG con la ruta correcta a config.yml.")
        return 1
    os.environ.setdefault("MCP_REPORTS_DIR", str(BASE_DIR / "reports"))
    if not os.environ.get("MCP_PUBLIC_BASE_URL"):
        detected_base = tunnel_public_base(config)
        if detected_base:
            os.environ["MCP_PUBLIC_BASE_URL"] = detected_base

    if not cloudflared:
        print("ERROR: no encuentro cloudflared.exe ni host.exe.")
        print("Instala cloudflared o define CLOUDFLARED_EXE con la ruta completa al ejecutable.")
        return 1

    print(f"Python del entorno: {python}")
    print(f"Configuración del túnel: {config}")
    print("MCP local: http://127.0.0.1:8000/mcp")
    print(f"Base pública de informes: {os.environ.get('MCP_PUBLIC_BASE_URL', 'http://127.0.0.1:8000')}")
    print("La regla ingress de config.yml debe dirigir el hostname a http://127.0.0.1:8000.")
    print("Iniciando MCP y Cloudflare Tunnel. Pulsa Ctrl+C para detener ambos.\n", flush=True)

    mcp = tunnel = None
    try:
        mcp = subprocess.Popen([str(python), str(SERVER_FILE)], cwd=BASE_DIR)
        time.sleep(2)
        if mcp.poll() is not None:
            print(f"ERROR: server.py terminó al iniciar (código {mcp.returncode}).")
            return int(mcp.returncode or 1)

        tunnel = subprocess.Popen(
            [cloudflared, "tunnel", "--config", str(config), "run"],
            cwd=BASE_DIR,
        )

        while True:
            if mcp.poll() is not None:
                print(f"El servidor MCP terminó (código {mcp.returncode}).")
                return int(mcp.returncode or 1)
            if tunnel.poll() is not None:
                print(f"Cloudflare Tunnel terminó (código {tunnel.returncode}).")
                return int(tunnel.returncode or 1)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo MCP y Cloudflare Tunnel...")
        return 0
    finally:
        stop_process(tunnel)
        stop_process(mcp)


if __name__ == "__main__":
    raise SystemExit(main())



