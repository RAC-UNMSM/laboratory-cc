"""
cli.py — Uso desde la terminal (sin LLM), con las MISMAS capas que el servidor MCP.

    python cli.py lagrange -f "x*y" -g "x^2 + y^2 = 8" --html lagrange.html
    python cli.py hessiana -f "x^4 + y^4 - 4xy + 1" --png h.png --html h.html --offline
    python cli.py frenet   -r "cos t, sin t, t" --t0 pi/4 --html helice.html
    python cli.py lagrange --demo 1 --html pagina.html          (demos 1..5 / 1..8 / 1..8; 0 = todos)
    python cli.py diagnostico "maximiza xy sobre la circunferencia x^2+y^2=8"

Cada cálculo pasa por: Pydantic (core/validacion) → verificador (core/verificador) →
methods/* → core/visualizacion (PNG + datos) → core/reporte (texto, HTML con Jinja2).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MPLBACKEND", "Agg")

import sympy as sp  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from core import reporte, visualizacion  # noqa: E402
from core.diagnostico import diagnosticar  # noqa: E402
from core.motor import MODELOS  # noqa: E402
from core.utils_math import ErrorEntrada, parsear_seguro  # noqa: E402
from core.verificador import ErrorVerificacion, verificar  # noqa: E402
from methods import metodo_frenet as MF, metodo_hessiana as MH, metodo_lagrange as ML  # noqa: E402


def _con_sufijo(ruta: str, suf: str) -> str:
    if not suf:
        return ruta
    p = Path(ruta)
    return str(p.with_name(p.stem + suf + p.suffix))


def _leer_constantes(lista: list[str] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in lista or []:
        if "=" not in item:
            raise ValueError(f"Constante mal escrita: '{item}'. Usa el formato a=2.")
        k, v = item.split("=", 1)
        out[k.strip()] = float(sp.N(parsear_seguro(v)))
    return out


def _resolver(metodo: str, s: Any) -> Any:
    if metodo == "lagrange":
        return ML.resolver(s.funcion, s.restricciones, s.variables, s.metodo)
    if metodo == "hessiana":
        return MH.resolver(s.funcion, s.variables, s.metodo)
    return MF.resolver(s.curva, s.t0, s.parametro, s.constantes or None)


def _ejecutar(metodo: str, solicitud: dict[str, Any], args: argparse.Namespace, suf: str = "") -> None:
    # Capa 1 (estructura) y capa 2 (sentido matemático): mismos mensajes que verá el LLM.
    s = MODELOS[metodo].model_validate(solicitud)
    informe = verificar(metodo, s)
    for aviso in informe.avisos:
        print(f"[aviso] {aviso}", file=sys.stderr)

    objeto = _resolver(metodo, s)
    print(reporte.texto(metodo, objeto, ascii_=args.ascii, detalle=not args.breve))
    rango = args.rango if args.rango else None
    if metodo == "frenet" and rango:
        rango = list(rango)
    datos = None
    if args.png or args.html or args.datos:
        datos = visualizacion.datos_grafico(metodo, objeto, rango=rango)
    if args.png:
        print("PNG guardado en:", visualizacion.generar_png(metodo, objeto, _con_sufijo(args.png, suf), datos))
    if args.html:
        print("HTML guardado en:", reporte.guardar_html(metodo, objeto, _con_sufijo(args.html, suf), datos=datos,
                                                        offline=args.offline))
    if args.json or args.datos:
        out = reporte.a_dict(metodo, objeto)
        if args.datos:
            out["grafico"] = datos
        texto = json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)
        dest = args.json or args.datos
        if dest == "-":
            print(texto)
        else:
            Path(_con_sufijo(dest, suf)).write_text(texto, encoding="utf-8")
            print("JSON guardado en:", _con_sufijo(dest, suf))


def _salidas(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--png", help="guardar lámina PNG")
    ap.add_argument("--html", help="guardar página web interactiva (LaTeX + gráficos 3D + JSON)")
    ap.add_argument("--offline", action="store_true",
                    help="incrusta Plotly.js en el HTML (funciona sin internet; requiere  pip install plotly)")
    ap.add_argument("--json", help="guardar resultado en JSON ('-' = pantalla)")
    ap.add_argument("--datos", help="como --json pero con los arreglos para graficar")
    ap.add_argument("--ascii", action="store_true", help="fórmulas sin Unicode")
    ap.add_argument("--breve", action="store_true", help="reporte más corto")


def construir_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python cli.py",
                                 description="Frenet, Lagrange y Puntos Críticos — cálculo exacto desde la terminal.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)

    pl = sub.add_parser("lagrange", help="optimización con restricciones de igualdad")
    pl.add_argument("-f", "--funcion", help='función objetivo, p. ej. "x^2 + 3xy"')
    pl.add_argument("-g", "--restriccion", action="append", default=[], help='restricción, p. ej. "x^2 + y^2 = 8" '
                                                                              "(repetible)")
    pl.add_argument("-v", "--vars", nargs="+", help="orden de las variables")
    pl.add_argument("--metodo", default="auto", choices=["auto", "groebner", "solve", "nonlinsolve"])
    pl.add_argument("--rango", nargs=2, type=float, action="append", metavar=("MIN", "MAX"),
                    help="rango por variable para los gráficos (repetible)")
    pl.add_argument("--demo", type=int, help=f"ejemplo 1..{len(ML.DEMOS)} (0 = todos)")
    _salidas(pl)

    ph = sub.add_parser("hessiana", help="puntos críticos sin restricciones y matriz Hessiana")
    ph.add_argument("-f", "--funcion", help='función, p. ej. "x^3 + y^3 - 3xy"')
    ph.add_argument("-v", "--vars", nargs="+", help="orden de las variables")
    ph.add_argument("--metodo", default="auto", choices=["auto", "groebner", "solve", "nonlinsolve"])
    ph.add_argument("--rango", nargs=2, type=float, action="append", metavar=("MIN", "MAX"))
    ph.add_argument("--demo", type=int, help=f"ejemplo 1..{len(MH.DEMOS)} (0 = todos)")
    _salidas(ph)

    pf = sub.add_parser("frenet", help="triedro de Frenet, curvatura y torsión de una curva r(t)")
    pf.add_argument("-r", "--curva", help='curva, p. ej. "cos t, sin t, t"')
    pf.add_argument("--t0", default="0", help="punto donde evaluar (0, 1, pi/4, ...)")
    pf.add_argument("--param", default="t", help="nombre del parámetro")
    pf.add_argument("--const", nargs="+", help="valores de constantes para graficar, p. ej. a=2 b=1")
    pf.add_argument("--rango", nargs=2, type=float, metavar=("TMIN", "TMAX"), help="rango del parámetro")
    pf.add_argument("--demo", type=int, help=f"ejemplo 1..{len(MF.DEMOS)} (0 = todos)")
    _salidas(pf)

    pd = sub.add_parser("diagnostico", help="¿qué método corresponde a este enunciado?")
    pd.add_argument("enunciado", nargs="+", help="texto del problema entre comillas")
    return ap


def _solicitudes(args: argparse.Namespace, ap: argparse.ArgumentParser) -> list[tuple[str, dict[str, Any]]]:
    """(descripción, solicitud) a ejecutar: las demos pedidas o la entrada del usuario."""
    c = args.comando
    if args.demo is not None:
        demos = {"lagrange": ML.DEMOS, "hessiana": MH.DEMOS, "frenet": MF.DEMOS}[c]
        if args.demo != 0 and args.demo not in demos:
            ap.error(f"la demo {args.demo} no existe (hay {len(demos)}).")
        ids = list(demos) if args.demo == 0 else [args.demo]
        out = []
        for i in ids:
            d = demos[i]
            if c == "lagrange":
                f, gs, vs, desc = d
                out.append((f"DEMO {i}: {desc}", {"funcion": f, "restricciones": gs, "variables": vs}))
            elif c == "hessiana":
                f, vs, desc = d
                out.append((f"DEMO {i}: {desc}", {"funcion": f, "variables": vs}))
            else:
                r, t0, ctes, desc = d
                out.append((f"DEMO {i}: {desc}", {"curva": r, "t0": t0, "constantes": ctes or {}}))
        return out
    if c == "lagrange":
        if not args.funcion or not args.restriccion:
            ap.error('indica -f "función" y al menos un -g "restricción" (o usa --demo).')
        return [("", {"funcion": args.funcion, "restricciones": args.restriccion, "variables": args.vars,
                      "metodo": args.metodo})]
    if c == "hessiana":
        if not args.funcion:
            ap.error('indica -f "función" (o usa --demo).')
        return [("", {"funcion": args.funcion, "variables": args.vars, "metodo": args.metodo})]
    if not args.curva:
        ap.error('indica la curva con -r "x(t), y(t), z(t)" (o usa --demo).')
    return [("", {"curva": args.curva, "t0": args.t0, "parametro": args.param,
                  "constantes": _leer_constantes(args.const)})]


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    ap = construir_parser()
    args = ap.parse_args(argv)
    if args.comando == "diagnostico":
        print(json.dumps(diagnosticar(" ".join(args.enunciado)).como_dict(), ensure_ascii=False, indent=2))
        return 0
    try:
        trabajos = _solicitudes(args, ap)
        for desc, sol in trabajos:
            if desc:
                print(f"\n### {desc}")
            _ejecutar(args.comando, sol, args, suf=desc.split(":")[0].replace("DEMO ", "_demo")
                      if desc and len(trabajos) > 1 else "")
    except ValidationError as e:
        for err in e.errors():
            print(f"Error de entrada: {err['msg']}", file=sys.stderr)
        return 1
    except ErrorVerificacion as e:
        print(f"Error de verificación [{e.codigo}]: {e.mensaje}", file=sys.stderr)
        if e.sugerencia:
            print(f"Sugerencia: {e.sugerencia}", file=sys.stderr)
        return 1
    except (ErrorEntrada, ValueError, RuntimeError, NotImplementedError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
