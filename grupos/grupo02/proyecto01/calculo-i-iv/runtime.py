"""Un proceso efímero por solicitud, concurrencia acotada y cancelación real."""

import asyncio
import json
import os
import sys
from pathlib import Path

WORKER = Path(__file__).with_name("worker.py")
_gate = asyncio.Lock()
TIMEOUT_SECONDS = 20


async def execute(action, payload, timeout=TIMEOUT_SECONDS):
    if _gate.locked():
        return {
            "estado": "error",
            "codigo": "ocupado",
            "mensaje": "Hay un cálculo en curso; reintente al terminar.",
        }
    async with _gate:
        process = None
        try:
            raw = json.dumps(
                {"action": action, "payload": payload}, ensure_ascii=False
            ).encode()
            if len(raw) > 24000:
                return {
                    "estado": "error",
                    "codigo": "entrada",
                    "mensaje": "La solicitud supera 24 KB.",
                }
            env = os.environ.copy()
            env.update(
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="1",
                MPLBACKEND="Agg",
                MPLCONFIGDIR="/tmp/mpl-g02",
            )
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(WORKER),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
                cwd=str(WORKER.parent),
            )
            out, _ = await asyncio.wait_for(process.communicate(raw), timeout)
            if process.returncode != 0 or len(out) > 1_000_000:
                return {
                    "estado": "error",
                    "codigo": "recursos",
                    "mensaje": "El cálculo excedió recursos o no pudo completarse.",
                }
            return json.loads(out)
        except asyncio.TimeoutError:
            return {
                "estado": "error",
                "codigo": "tiempo",
                "mensaje": "Cálculo cancelado al alcanzar el límite de tiempo.",
            }
        except (OSError, ValueError):
            return {
                "estado": "error",
                "codigo": "interno",
                "mensaje": "No fue posible ejecutar el cálculo.",
            }
        finally:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
