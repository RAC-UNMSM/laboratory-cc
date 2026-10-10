from mcp.server.fastmcp import FastMCP
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import importlib
import json
import re
import sympy as sp
import numpy as np

from resultado import ResultadoMetodo, EstadoMetodo
from reportes import guardar_reporte_html
from validacion import validar_entrada, resultado_error

mcp = FastMCP("sistemas-no-lineales")
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "salida-mathjax"
CONFIG_PATH = PROJECT_DIR / "config" / "proyecto_config.json"

_METODOS_DISPONIBLES = {
    "newton_sistemas": ("metodos.newton_sistemas", "newton_sistemas"),
    "newton_raphson": ("metodos.newton_sistemas", "newton_sistemas"),
    "punto_fijo": ("metodos.punto_fijo", "punto_fijo_varias_variables"),
    "punto_fijo_varias_variables": ("metodos.punto_fijo", "punto_fijo_varias_variables"),
    "cuasi_newton": ("metodos.cuasi_newton", "cuasi_newton_broyden"),
    "cuasi_newton_broyden": ("metodos.cuasi_newton", "cuasi_newton_broyden"),
    "descenso_gradiente": ("metodos.descenso", "descenso_mas_rapido"),
    "descenso_mas_rapido": ("metodos.descenso", "descenso_mas_rapido"),
    "homotopia_continuacion": ("metodos.homotopia", "homotopia_continuacion"),
}


def _compilar_funciones(expresiones: List[str], variables: List[str]):
    simbolos = sp.symbols(' '.join(variables))
    if not isinstance(simbolos, (tuple, list)):
        simbolos = (simbolos,)

    funciones = []
    for expr in expresiones:
        f_sym = sp.sympify(expr)
        f_num = sp.lambdify(simbolos, f_sym, modules=['numpy'])

        def wrapper(x, f_num=f_num):
            return float(f_num(*x))

        funciones.append(wrapper)
    return funciones


def _ejecutar_metodo(
    nombre_metodo: str,
    modulo: str,
    funcion: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float,
    max_iter: int,
) -> Dict[str, Any]:
    errores = validar_entrada(expresiones, variables, x0, tolerancia, max_iter)
    if errores:
        return resultado_error(nombre_metodo, errores).model_dump()

    try:
        funciones = _compilar_funciones(expresiones, variables)
        mod = importlib.import_module(modulo)
        impl = getattr(mod, funcion)
        resultado = impl(funciones, x0, tolerancia, max_iter)
        return resultado.model_dump()
    except ImportError:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[f"Módulo no implementado: {modulo}"],
            message="Método no disponible aún."
        ).model_dump()
    except Exception as e:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[str(e)],
            message="Error al ejecutar el método."
        ).model_dump()


@mcp.tool()
def cuasi_newton_broyden(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando el método de Broyden."""
    return _ejecutar_metodo(
        "cuasi_newton_broyden",
        "metodos.cuasi_newton",
        "cuasi_newton_broyden",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def descenso_mas_rapido(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando descenso más rápido."""
    return _ejecutar_metodo(
        "descenso_mas_rapido",
        "metodos.descenso",
        "descenso_mas_rapido",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def newton_sistemas(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando Newton-Raphson."""
    return _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def punto_fijo_varias_variables(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando punto fijo."""
    return _ejecutar_metodo(
        "punto_fijo_varias_variables",
        "metodos.punto_fijo",
        "punto_fijo_varias_variables",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def homotopia_continuacion(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando homotopía."""
    return _ejecutar_metodo(
        "homotopia_continuacion",
        "metodos.homotopia",
        "homotopia_continuacion",
        expresiones, variables, x0, tolerancia, max_iter
    )


def _configuracion_inicial() -> Dict[str, Any]:
    return {
        "proyecto": "Sistemas No Lineales",
        "grupo": "Grupo 08",
        "rama": "feature-viz-reportes",
        "version": "1.0.0",
        "rutas": {
            "codigo": ".",
            "reportes": "salida-mathjax/",
            "imagenes": "salida-mathjax/imagenes/",
            "tests": "tests/",
        },
        "configuracion_numerica": {"tolerancia": 1e-8, "max_iteraciones": 100},
        "metodos": [
            "punto_fijo_varias_variables",
            "newton_sistemas",
            "cuasi_newton_broyden",
            "descenso_mas_rapido",
            "homotopia_continuacion",
        ],
        "ejercicios": [],
        "dependencias": ["mcp", "numpy", "sympy", "pydantic"],
        "comandos": {
            "servidor": "python server.py",
            "tests": "python -m pytest tests -v",
        },
        "fecha_ultima_actualizacion": None,
    }


def _formatear_vector_tex(vector: List[float]) -> str:
    return r"\begin{bmatrix}" + r"\\".join(f"{valor:.8g}" for valor in vector) + r"\end{bmatrix}"


def _construir_contexto_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float,
    max_iter: int,
    resultado: Dict[str, Any],
) -> Dict[str, Any]:
    simbolos = [sp.Symbol(variable) for variable in variables]
    expresiones_sym = [
        sp.sympify(expresion, locals=dict(zip(variables, simbolos)))
        for expresion in expresiones
    ]
    vector_funciones = r"\begin{bmatrix}" + r"\\".join(
        sp.latex(expresion) for expresion in expresiones_sym
    ) + r"\end{bmatrix}"

    es_punto_fijo = metodo in ("punto_fijo", "punto_fijo_varias_variables")
    if es_punto_fijo:
        ecuacion = r"\mathbf{x}=\mathbf{G}(\mathbf{x})=" + vector_funciones
        nombre_jacobiano = r"J_G(\mathbf{x})"
    else:
        ceros = r"\begin{bmatrix}" + r"\\".join("0" for _ in expresiones) + r"\end{bmatrix}"
        ecuacion = r"F(\mathbf{x})=" + vector_funciones + "=" + ceros
        nombre_jacobiano = r"J_F(\mathbf{x})"

    jacobiano = sp.Matrix(expresiones_sym).jacobian(simbolos)
    matriz_tex = sp.latex(jacobiano)

    funciones = _compilar_funciones(expresiones, variables)
    trayectoria = resultado.get("trajectory") or []
    iteraciones = []
    for indice, punto in enumerate(trayectoria):
        punto_array = np.asarray(punto, dtype=float)
        valores = np.asarray([funcion(punto_array) for funcion in funciones], dtype=float)
        if es_punto_fijo:
            valores = valores - punto_array
        if indice == 0:
            error = None
        else:
            diferencia = punto_array - np.asarray(trayectoria[indice - 1], dtype=float)
            error = float(np.linalg.norm(diferencia, ord=np.inf if es_punto_fijo else 2))
        iteraciones.append(
            {
                "k": indice,
                "x": punto_array.tolist(),
                "error": error,
                "residuo": float(np.linalg.norm(valores)),
            }
        )

    error_final = iteraciones[-1]["error"] if iteraciones else None
    residuo_final = iteraciones[-1]["residuo"] if iteraciones else None
    pasos = [f"Se formula el problema: \\({ecuacion}\\)."]
    if metodo in ("newton_sistemas", "newton_raphson"):
        pasos.extend(
            [
                f"El Jacobiano es \\({nombre_jacobiano}={matriz_tex}\\); el solver lo aproxima mediante diferencias centrales.",
                r"Se resuelve \(J_F(\mathbf{x}_k)\,\Delta\mathbf{x}_k=-F(\mathbf{x}_k)\) y se actualiza \(\mathbf{x}_{k+1}=\mathbf{x}_k+\Delta\mathbf{x}_k\).",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    elif metodo in ("punto_fijo", "punto_fijo_varias_variables"):
        pasos.append(r"Se itera \(\mathbf{x}_{k+1}=\mathbf{G}(\mathbf{x}_k)\).")
        criterio = r"\|\mathbf{x}_{k+1}-\mathbf{x}_k\|_\infty<\varepsilon"
    elif metodo in ("cuasi_newton", "cuasi_newton_broyden"):
        pasos.extend(
            [
                r"Se inicia la aproximación del Jacobiano con \(B_0=I\).",
                r"Se resuelve \(B_k\,\Delta\mathbf{x}_k=-F(\mathbf{x}_k)\) y se actualiza \(B_k\) con la fórmula de rango uno de Broyden.",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    elif metodo in ("descenso_gradiente", "descenso_mas_rapido"):
        pasos.extend(
            [
                r"Se minimiza \(\phi(\mathbf{x})=\frac{1}{2}\|F(\mathbf{x})\|_2^2\).",
                f"El gradiente es \\((\\nabla\\phi=2J_F(\\mathbf{{x}})^T F(\\mathbf{{x}})),\\quad J_F={matriz_tex}\\); se usa búsqueda de línea.",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    else:
        pasos.extend(
            [
                r"Se define la homotopía \(H(\mathbf{x},t)=F(\mathbf{x})-(1-t)F(\mathbf{x}_0)\).",
                r"Se incrementa \(t\) de 0 a 1 y se corrige cada punto mediante Newton.",
            ]
        )
        criterio = r"\|F(\mathbf{x}(1))\|_2<\varepsilon"

    solucion = resultado.get("solution") or []
    valores_solucion = np.asarray([funcion(solucion) for funcion in funciones], dtype=float)
    if es_punto_fijo:
        valores_solucion = valores_solucion - np.asarray(solucion, dtype=float)
    verificacion_vector = valores_solucion.tolist()
    conclusion = (
        f"Estado: {resultado.get('status')}. Solucion aproximada: "
        f"({', '.join(f'{float(valor):.10g}' for valor in solucion)}). "
        f"El metodo registro {resultado.get('iterations', 0)} iteraciones."
    )

    return {
        "enunciado": enunciado,
        "ecuaciones_tex": [ecuacion, f"{nombre_jacobiano}={matriz_tex}"],
        "punto_inicial": x0,
        "tolerancia": tolerancia,
        "max_iteraciones": max_iter,
        "criterio_tex": criterio.replace(r"\varepsilon", f"{tolerancia:g}"),
        "pasos": pasos,
        "iteraciones": iteraciones,
        "error_final": error_final,
        "residuo_final": residuo_final,
        "verificacion_tex": (
            r"\text{Residual en la solucion}=" + _formatear_vector_tex(verificacion_vector)
        ),
        "conclusion": conclusion,
        "grafico": "Trayectoria de las variables, incrustada como SVG en el HTML.",
    }


def _registrar_ejercicio(ejercicio: Dict[str, Any]) -> None:
    if CONFIG_PATH.exists():
        configuracion = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        configuracion = _configuracion_inicial()
    configuracion.setdefault("ejercicios", []).append(ejercicio)
    configuracion["fecha_ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporal = CONFIG_PATH.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(configuracion, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporal.replace(CONFIG_PATH)


def _resolver_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Ejecuta un método, genera su HTML y registra el ejercicio en el JSON."""
    if not enunciado.strip():
        return {"status": "invalid_input", "message": "El enunciado no puede estar vacío."}
    if metodo not in _METODOS_DISPONIBLES:
        return {
            "status": "invalid_input",
            "message": f"Método no disponible: {metodo}.",
            "metodos_disponibles": sorted(_METODOS_DISPONIBLES),
        }

    modulo, funcion = _METODOS_DISPONIBLES[metodo]
    resultado = _ejecutar_metodo(
        metodo,
        modulo,
        funcion,
        expresiones,
        variables,
        x0,
        tolerancia,
        max_iter,
    )
    estado = resultado.get("status")
    estado = getattr(estado, "value", estado)
    resultado["status"] = estado
    if estado == EstadoMetodo.INVALID_INPUT.value:
        return {"resultado": resultado, "status": "invalid_input", "reporte_html": None}

    contexto = _construir_contexto_ejercicio(
        enunciado,
        expresiones,
        variables,
        x0,
        metodo,
        tolerancia,
        max_iter,
        resultado,
    )
    resultado["final_error"] = contexto["error_final"]
    if contexto["residuo_final"] is not None:
        resultado["final_residual"] = contexto["residuo_final"]

    id_base = re.sub(r"[^a-z0-9]+", "-", metodo.lower()).strip("-")
    base_reporte = OUTPUT_DIR / f"reporte_{id_base}.html"
    reporte = guardar_reporte_html(
        resultado,
        base_reporte,
        titulo=f"Resolucion: {metodo}",
        contexto=contexto,
    )
    identificador = reporte.stem.rsplit("_", 1)[-1]
    registro = {
        "id": identificador,
        "enunciado": enunciado,
        "metodo": resultado.get("method", metodo),
        "estado": resultado.get("status"),
        "reporte_html": reporte.relative_to(OUTPUT_DIR.parent).as_posix(),
        "imagenes": [],
        "solucion": resultado.get("solution"),
        "residuo_final": resultado.get("final_residual"),
        "fecha_generacion": datetime.now(timezone.utc).isoformat(),
    }
    _registrar_ejercicio(registro)
    return {
        "status": resultado.get("status"),
        "resultado": resultado,
        "reporte_html": str(reporte.resolve()),
        "configuracion_json": str(CONFIG_PATH.resolve()),
        "id": identificador,
        "mensaje": "Ejercicio resuelto; reporte HTML con LaTeX y trayectoria generado.",
    }


@mcp.tool()
def resolver_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un ejercicio y genera automáticamente un HTML en salida-mathjax.

    Usa esta herramienta cuando el usuario envíe un ejercicio del tema. Primero
    interpreta el enunciado y entrega expresiones, variables, x0 y método en forma
    estructurada. Si el método o el punto inicial faltan en el enunciado, pregunta
    al usuario antes de invocar la herramienta. El reporte incluye formulación TeX,
    pasos del método, tabla de trayectoria, verificación y gráfica SVG; también
    registra el ejercicio en config/proyecto_config.json.
    Métodos aceptados: newton_sistemas, punto_fijo_varias_variables,
    cuasi_newton_broyden, descenso_mas_rapido, homotopia_continuacion.
    """
    return _resolver_ejercicio(
        enunciado,
        expresiones,
        variables,
        x0,
        metodo,
        tolerancia,
        max_iter,
    )


if __name__ == "__main__":
    mcp.run()