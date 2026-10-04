"""
core/motor.py — Orquesta UN cálculo completo: verificar → resolver → graficar → reportar.

Esta función es la que el servidor ejecuta en un proceso aparte (para poder cortar a tiempo
los cálculos simbólicos que se eternizan). Por eso:

* recibe y devuelve solo datos serializables (dict / str), nunca objetos SymPy;
* nunca lanza excepciones hacia afuera: devuelve ``{"ok": False, "error": {...}}`` con un
  código, un mensaje y una sugerencia que el LLM puede explicar al usuario;
* no escribe en stdout (el canal STDIO de MCP es sagrado): el inicializador del proceso
  redirige stdout → stderr.

Flujo:
    solicitud (dict) ──Pydantic──▶ Solicitud*  ──verificador──▶ InformeVerificacion
         ──methods.*.resolver──▶ objeto exacto ──a_dict──▶ resultado.json
         ──visualizacion──▶ datos de gráficos / PNG ──reporte (Jinja2)──▶ reporte.html
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from core.utils_math import ErrorEntrada
from core.validacion import SolicitudFrenet, SolicitudHessiana, SolicitudLagrange
from core.verificador import ErrorVerificacion, verificar

__all__ = ["ejecutar", "inicializar_proceso", "MODELOS", "compactar"]

Metodo = Literal["lagrange", "hessiana", "frenet"]
MODELOS: dict[str, type[BaseModel]] = {"lagrange": SolicitudLagrange, "hessiana": SolicitudHessiana,
                                       "frenet": SolicitudFrenet}
log = logging.getLogger("mcp_math.motor")


def inicializar_proceso() -> None:
    """Se ejecuta al arrancar cada proceso de cálculo: protege STDIO y precarga los módulos pesados."""
    sys.stdout = sys.stderr
    os.environ.setdefault("MPLBACKEND", "Agg")
    from core import reporte, visualizacion  # precarga sympy, numpy, matplotlib y Jinja2
    del reporte, visualizacion


def _resolver(metodo: Metodo, s: Any) -> Any:
    if metodo == "lagrange":
        from methods import metodo_lagrange as ML
        return ML.resolver(s.funcion, s.restricciones, s.variables, s.metodo)
    if metodo == "hessiana":
        from methods import metodo_hessiana as MH
        return MH.resolver(s.funcion, s.variables, s.metodo)
    from methods import metodo_frenet as MF
    return MF.resolver(s.curva, s.t0, s.parametro, s.constantes or None)


def _error(tipo: str, codigo: str, mensaje: str, sugerencia: str = "") -> dict[str, Any]:
    return {"ok": False, "error": {"tipo": tipo, "codigo": codigo, "mensaje": mensaje, "sugerencia": sugerencia}}


def ejecutar(metodo: Metodo, solicitud: dict[str, Any], carpeta: str | None) -> dict[str, Any]:
    """Cálculo completo. ``carpeta``: dónde guardar reporte.html / grafico.png (None = no guardar)."""
    t_ini = time.perf_counter()
    # ── Capa 1 (otra vez, por si se llama sin pasar por el servidor) ───────
    try:
        s = MODELOS[metodo].model_validate(solicitud)
    except ValidationError as e:
        return _error("estructura", "SOLICITUD_INVALIDA", "; ".join(err["msg"] for err in e.errors()))
    # ── Capa 2: sentido matemático ─────────────────────────────────────────
    try:
        informe = verificar(metodo, s)
    except ErrorVerificacion as e:
        return {"ok": False, "error": e.como_dict()}
    # ── Cálculo exacto ─────────────────────────────────────────────────────
    from core import reporte, visualizacion
    try:
        objeto = _resolver(metodo, s)
        resultado = reporte.a_dict(metodo, objeto)
    except (ErrorEntrada, ValueError, NotImplementedError) as e:
        return _error("calculo", "NO_RESOLUBLE", str(e), "Revisa el planteamiento o prueba otro 'metodo' de resolución.")
    except Exception as e:  # noqa: BLE001
        log.error("Fallo inesperado:\n%s", traceback.format_exc())
        return _error("interno", "ERROR_INTERNO", f"{type(e).__name__}: {e}",
                      "Es un error del servidor; prueba una forma equivalente de la expresión.")
    t_calc = time.perf_counter() - t_ini

    # ── Gráficos y reportes (si fallan, el cálculo sigue siendo válido) ────
    avisos = list(informe.avisos)
    archivos: dict[str, str] = {}
    datos: dict | None = None
    salida = s.salida
    rango = getattr(s, "rango", None)
    try:
        datos = visualizacion.datos_grafico(metodo, objeto, rango=list(rango) if rango else None)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"No se pudieron generar los datos del gráfico: {e}")
    if carpeta:
        dir_ = Path(carpeta)
        if salida.generar_html and datos is not None:
            try:
                archivos["html"] = reporte.guardar_html(metodo, objeto, dir_ / "reporte.html", datos=datos,
                                                        resultado=resultado, offline=salida.offline)
            except Exception as e:  # noqa: BLE001
                avisos.append(f"No se pudo generar el HTML: {e}")
        if salida.generar_png and datos is not None:
            try:
                archivos["png"] = visualizacion.generar_png(metodo, objeto, str(dir_ / "grafico.png"), datos=datos)
            except Exception as e:  # noqa: BLE001
                avisos.append(f"No se pudo generar el PNG: {e}")

    out: dict[str, Any] = {
        "ok": True,
        "metodo": metodo,
        "resumen": reporte.resumen_breve(metodo, resultado),
        "verificacion_previa": {**informe.como_dict(), "avisos": avisos},
        "resultado": resultado,
        "archivos": archivos,
        "tiempo_s": {"calculo": round(t_calc, 3), "total": round(time.perf_counter() - t_ini, 3)},
        "solicitud": s.model_dump(mode="json"),
    }
    if salida.incluir_datos_grafico and datos is not None:
        out["datos_grafico"] = datos
    return out


# ════════════════════════════════════════════════════════════════════════════
# Compactación para el LLM
# ════════════════════════════════════════════════════════════════════════════
_CLAVES_PESADAS = ("latex", "pasos", "procedimiento", "matriz_latex", "lhs", "rhs")


def compactar(obj: Any, profundidad: int = 0, max_lista: int = 30) -> Any:
    """Quita del resultado lo que solo sirve para la página web (LaTeX, pasos) y recorta listas
    largas. El LLM recibe lo esencial; el JSON completo queda guardado en disco."""
    if isinstance(obj, dict):
        return {k: compactar(v, profundidad + 1, max_lista) for k, v in obj.items()
                if not any(k == c or k.endswith("_" + c) for c in _CLAVES_PESADAS) and k != "grafico"}
    if isinstance(obj, list):
        recorte = [compactar(v, profundidad + 1, max_lista) for v in obj[:max_lista]]
        if len(obj) > max_lista:
            recorte.append(f"... ({len(obj) - max_lista} elementos más en resultado.json)")
        return recorte
    return obj
