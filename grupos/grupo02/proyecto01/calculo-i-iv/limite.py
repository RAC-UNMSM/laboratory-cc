"""Tope de tiempo para las tools: cada calculo corre en un proceso hijo."""
from __future__ import annotations

import functools
import multiprocessing
import threading

TIEMPO_MAX_S = 20          # segundos por llamada
CALCULOS_A_LA_VEZ = 2      # el contenedor tiene 512 MB

try:
    _CTX = multiprocessing.get_context("fork")
except ValueError:         # Windows no tiene fork: en la laptop no se aplica el tope
    _CTX = None
_TURNOS = threading.BoundedSemaphore(CALCULOS_A_LA_VEZ)


def _hijo(conexion, fn, args, kwargs):
    try:
        conexion.send(fn(*args, **kwargs))
    except BaseException as exc:  # noqa: BLE001
        conexion.send({"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        conexion.close()


def con_limite(fn):
    """Envuelve una tool: si pasa de TIEMPO_MAX_S se mata el proceso y se responde un error."""
    if _CTX is None:
        return fn

    @functools.wraps(fn)
    def envoltura(*args, **kwargs):
        if not _TURNOS.acquire(timeout=TIEMPO_MAX_S):
            return {"estado": "error", "mensaje": "Servidor ocupado: intenta de nuevo en unos segundos."}
        try:
            lectura, escritura = _CTX.Pipe(duplex=False)
            proceso = _CTX.Process(target=_hijo, args=(escritura, fn, args, kwargs), daemon=True)
            proceso.start()
            escritura.close()
            try:
                if lectura.poll(TIEMPO_MAX_S):
                    return lectura.recv()
            except EOFError:
                return {"estado": "error", "mensaje": "El cálculo se interrumpió (posible falta de memoria)."}
            finally:
                if proceso.is_alive():
                    proceso.kill()
                proceso.join()
                lectura.close()
            return {"estado": "error",
                    "mensaje": f"El cálculo superó {TIEMPO_MAX_S} s y se canceló. "
                               "Simplifica la expresión o divide el problema."}
        finally:
            _TURNOS.release()
    return envoltura
