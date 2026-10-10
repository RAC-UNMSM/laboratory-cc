"""Servidor MCP del grupo04 para Métodos Numéricos I y II."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.apps import Apps, ResourceCsp
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse

from interpolation import solve_interpolation
from numerical_methods import (
    analyze_error, analyze_float_arithmetic, propagate_error, solve_root,
    solve_nonlinear_system, analyze_conditioning, solve_ode_multistep, solve_pde_2d,
    optimize_constrained, solve_sparse_eigenvalues, integrate_adaptive,
    solve_linear, solve_sparse_linear, fit_data, differentiate, differentiate_data,
    integrate, integrate_data, solve_ode, eigen_solve, optimize, solve_bvp,
    solve_pde, pack_result,
)
from report import generar_reporte_latex, generar_reporte_numerico
from storage import public_origin, resolve_pdf

BASE_DIR = Path(__file__).resolve().parent
SERVER_NAME = "grupo04-mcp-test"
LEGACY_UI_URI = "ui://interpolation/v5/main.html"
NUMERICAL_UI_URI = "ui://numerical-methods/v1/main.html"
LEGACY_UI_FILE = BASE_DIR / "ui" / "interpolation.html"
NUMERICAL_UI_FILE = BASE_DIR / "ui" / "numerical.html"
if not LEGACY_UI_FILE.is_file() or not NUMERICAL_UI_FILE.is_file():
    raise FileNotFoundError("Falta una interfaz HTML en ui/.")

apps = Apps()


def _legacy_report(result: dict[str, Any], report_name: str,
                   level: str = "inicial", include_report: bool = True) -> dict[str, Any]:
    result["level"] = level
    result.setdefault("schema_version", "1.1")
    result.setdefault("problem_type", "interpolacion")
    result.setdefault("status", "success")
    result.setdefault("inputs", {"points": result.get("points", []),
                                  "x_eval": result.get("x_eval"),
                                  "method": result.get("method")})
    result.setdefault("result", {key: result.get(key) for key in
        ("value", "polynomial", "lagrange_value", "newton_value", "difference")})
    result.setdefault("diagnostics", {"absolute_difference": result.get("difference")})
    result.setdefault("steps", ["Se construyó el polinomio interpolante.",
        f"Se evaluó en x={result.get('x_eval')}.",
        f"P(x)={result.get('polynomial')}.", f"Resultado: {result.get('value')}."])
    result.setdefault("tables", [{"name": "Puntos utilizados", "columns": ["x", "y"],
        "rows": [[point.get("x"), point.get("y")] for point in result.get("points", [])]}])
    curve = result.get("curve") or {}
    result.setdefault("charts", ([{"name": "Polinomio interpolante", "series": [
        {"label": "P(x)", "x": curve.get("x", []), "y": curve.get("y", [])}]}]
        if curve.get("x") and curve.get("y") else []))
    result.setdefault("warnings", [])
    if not include_report:
        result["report"] = {"status": "skipped", "message": "PDF omitido por solicitud."}
        result["report_status"] = "skipped"
        result["pdf_url"] = result["pdf_preview_url"] = None
        return result
    try:
        metadata = generar_reporte_latex(result, report_name)
        result["report"] = {k: v for k, v in metadata.items() if k != "pdf"}
        result["report_status"] = "ok"
        result["pdf_url"] = metadata.get("download_url")
        result["pdf_preview_url"] = metadata.get("preview_url")
    except Exception as exc:
        result["report"] = {"status": "error", "error": "No se pudo generar el PDF."}
        result["report_status"] = "error"
        result["report_error"] = str(exc)[:300]
        result["pdf_url"] = result["pdf_preview_url"] = None
    result.pop("pdf_path", None)
    return result


def _publish(result: dict[str, Any], report_name: str,
             include_report: bool = True, level: str = "inicial") -> dict[str, Any]:
    result["level"] = level
    if result.get("status") in {"invalid_input", "resource_limit", "calculation_error"}:
        return result
    if not include_report:
        result["report"] = {"status": "skipped", "message": "PDF omitido por solicitud."}
        return result
    try:
        metadata = generar_reporte_numerico(result, report_name)
        public = {k: v for k, v in metadata.items() if k != "pdf"}
        result["report"] = {"status": "ok", **public}
        result["pdf_url"] = metadata.get("download_url")
        result["pdf_preview_url"] = metadata.get("preview_url")
    except Exception as exc:
        result["report"] = {"status": "error", "error": "El cálculo terminó, pero no se pudo crear el PDF."}
        result["report_error"] = str(exc)[:300]
        result["pdf_url"] = result["pdf_preview_url"] = None
        result.setdefault("warnings", []).append("La resolución está disponible; la generación del informe PDF falló.")
    return result


def _invoke(family: str, method_name: str, report_name: str, function,
            level: str = "inicial", include_report: bool = True, **kwargs):
    level = str(level).lower().strip()
    if level not in {"inicial", "intermedio"}:
        return {"schema_version": "1.1", "level": level, "problem_type": family,
                "method": method_name, "status": "invalid_input",
                "error": {"code": "INVALID_LEVEL", "message": "level debe ser inicial o intermedio."}}
    try:
        result = function(**kwargs)
    except (TypeError, ValueError, ArithmeticError) as exc:
        result = pack_result(family, method_name, kwargs, {}, {"converged": False},
                             warnings=[], status="invalid_input")
        result["error"] = {"code": "INVALID_INPUT", "message": str(exc)[:500]}
        result["level"] = level
        return result
    except Exception as exc:
        result = pack_result(family, method_name, kwargs, {}, {"converged": False},
                             status="calculation_error")
        result["error"] = {"code": "CALCULATION_ERROR",
                            "message": "Ocurrió un error interno al resolver el problema.",
                            "detail": str(exc)[:300]}
        result["level"] = level
        return result
    return _publish(result, report_name, include_report=include_report, level=level)


def _solve_interpolation(points, x_eval, method, report_name="interpolacion",
                         level="inicial", include_report=True):
    if method not in ("lagrange", "newton"):
        raise ValueError("method debe ser lagrange o newton.")
    if level not in {"inicial", "intermedio"}:
        raise ValueError("level debe ser inicial o intermedio.")
    result = solve_interpolation(points, x_eval, method)
    return _legacy_report(result, report_name, level=level, include_report=include_report)


@apps.tool(
    resource_uri=LEGACY_UI_URI,
    name="resolver_interpolacion",
    title="Interpolación Newton/Lagrange"
)
def resolver_interpolacion(points: list[dict[str, float]], x_eval: float,
                           method: str = "lagrange",
                           report_name: str = "interpolacion", level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve una interpolación polinómica con el método solicitado y evalúa el polinomio en x_eval.

    Args:
        points: Lista de puntos como [{"x": número, "y": número}, ...] o pares [x,y]; no repita x.
        x_eval: Abscisa donde evaluar el polinomio.
        method: 'lagrange' o 'newton'; por defecto 'lagrange'.
        report_name: Nombre base opcional para el PDF.
        level: Nivel de explicación, 'inicial' o 'intermedio'.
        include_report: Si es true, genera enlaces de vista previa y descarga del PDF.

    Returns:
        Valores interpolados, polinomio, desarrollo de ambos métodos y estado del reporte."""
    return _solve_interpolation(points, x_eval, method, report_name, level=level, include_report=include_report)


@apps.tool(
    resource_uri=LEGACY_UI_URI,
    name="interpolacion_lagrange",
    title="Interpolación de Lagrange"
)
def interpolacion_lagrange(points: list[dict[str, float]], x_eval: float, level: str = "inicial", include_report: bool = True) -> dict:
    """Calcula y evalúa el polinomio de interpolación de Lagrange.

    Args:
        points: Puntos [{"x": número, "y": número}, ...] o pares [x,y], con x distintos.
        x_eval: Abscisa donde evaluar.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Genera o no un PDF descargable.

    Returns:
        Valor, polinomio, aportes de las bases y datos del reporte."""
    return _solve_interpolation(points, x_eval, "lagrange", level=level, include_report=include_report)


@apps.tool(
    resource_uri=LEGACY_UI_URI,
    name="interpolacion_newton",
    title="Interpolación de Newton"
)
def interpolacion_newton(points: list[dict[str, float]], x_eval: float, level: str = "inicial", include_report: bool = True) -> dict:
    """Calcula y evalúa el polinomio de Newton mediante diferencias divididas.

    Args:
        points: Puntos [{"x": número, "y": número}, ...] o pares [x,y], con x distintos.
        x_eval: Abscisa donde evaluar.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Genera o no un PDF descargable.

    Returns:
        Valor, tabla de diferencias divididas, desarrollo y datos del reporte."""
    return _solve_interpolation(points, x_eval, "newton", level=level, include_report=include_report)


@apps.tool(
    resource_uri=LEGACY_UI_URI,
    name="comparar_interpolacion",
    title="Comparar Newton y Lagrange"
)
def comparar_interpolacion(points: list[dict[str, float]], x_eval: float, level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve los mismos puntos con Lagrange y Newton y compara sus evaluaciones.

    Args:
        points: Puntos [{"x": número, "y": número}, ...] o pares [x,y], con x distintos.
        x_eval: Abscisa común de evaluación.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Genera o no los PDF de cada método.

    Returns:
        Resultados anidados, diferencia absoluta y enlaces de reportes disponibles."""
    lagrange = _solve_interpolation(points, x_eval, "lagrange", "comparacion_lagrange", level=level, include_report=include_report)
    newton = _solve_interpolation(points, x_eval, "newton", "comparacion_newton", level=level, include_report=include_report)
    return {
        "schema_version": "1.1",
        "level": level,
        "problem_type": "interpolacion",
        "status": "success",
        "method": "Comparación Newton y Lagrange",
        "x_eval": x_eval,
        "inputs": {"points": points, "x_eval": x_eval},
        "result": {"lagrange_value": lagrange.get("value"),
                   "newton_value": newton.get("value"),
                   "absolute_difference": abs(lagrange.get("value", 0)-newton.get("value", 0))},
        "diagnostics": {"absolute_difference": abs(lagrange.get("value", 0)-newton.get("value", 0))},
        "steps": ["Se calcularon los polinomios de Lagrange y Newton para los mismos puntos.",
                  "Se compararon las dos evaluaciones en x_eval."],
        "tables": [], "charts": [], "warnings": [],
        "lagrange": lagrange,
        "newton": newton,
        "reports": [
            {"label": "Informe de Lagrange", **(lagrange.get("report") or {})},
            {"label": "Informe de Newton", **(newton.get("report") or {})},
        ],
    }


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="analizar_aritmetica_flotante",
           title="Estudiar redondeo y cancelación")
def analizar_aritmetica_flotante(values: list[float], precision_digits: int = 8, level: str = "inicial", include_report: bool = True) -> dict:
    """Compara acumulación float secuencial, suma compensada y redondeo decimal.

    Args:
        values: Lista finita de números, de 1 a 500 elementos.
        precision_digits: Precisión decimal entre 1 y 50.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Si true, añade un reporte PDF.

    Returns:
        Sumas, referencia decimal, errores y tabla de acumulación."""
    return _invoke("floating_point", "suma y redondeo", "aritmetica_flotante",
                   analyze_float_arithmetic, values=values,
                   precision_digits=precision_digits, level=level, include_report=include_report)

@apps.tool(resource_uri=NUMERICAL_UI_URI, name="analizar_error_numerico",
           title="Analizar error numérico")
def analizar_error_numerico(exact: float, approximation: float, level: str = "inicial", include_report: bool = True) -> dict:
    """Calcula errores absoluto, relativo y porcentual entre referencia y aproximación.

    Args:
        exact: Valor de referencia.
        approximation: Valor aproximado.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Si true, añade un reporte PDF.

    Returns:
        Métricas de error; el relativo no se define si exact es cero."""
    return _invoke("error", "comparación", "error_numerico",
                   analyze_error, exact=exact, approximation=approximation, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="propagar_error_numerico",
           title="Propagar incertidumbre de mediciones")
def propagar_error_numerico(a: float, b: float, error_a: float, error_b: float,
                            operation: str = "add", level: str = "inicial", include_report: bool = True) -> dict:
    """Propaga incertidumbres independientes de primer orden en una operación aritmética.

    Args:
        a, b: Valores de entrada finitos.
        error_a, error_b: Incertidumbres absolutas no negativas.
        operation: add, subtract, multiply o divide.
        level: Nivel de explicación.
        include_report: Si true, añade un reporte PDF.

    Returns:
        Resultado e incertidumbre absoluta y relativa estimada."""
    return _invoke("error_propagation", operation, "propagacion_error",
                   propagate_error, a=a, b=b, error_a=error_a,
                   error_b=error_b, operation=operation, level=level, include_report=include_report)

@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_raiz",
           title="Resolver raíz de ecuación")
def resolver_raiz(expression: str, method: str = "bisection",
                  a: float = 0.0, b: float = 1.0,
                  x0: float = 0.0, x1: float = 1.0,
                  g_expression: str = "",
                  tolerance: float = 1e-10, max_iter: int = 100, level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve f(x)=0 por bisección, falsa posición, punto fijo, Newton o secante.

    Args:
        expression: Función segura en x; admite operaciones y funciones matemáticas comunes.
        method: Método admitido; por defecto bisection.
        a, b: Extremos con cambio de signo para bisección/falsa posición.
        x0, x1: Estimaciones iniciales para métodos iterativos; secante requiere ambos.
        g_expression: Función de iteración requerida por fixed_point.
        tolerance: Tolerancia positiva.
        max_iter: Máximo de iteraciones, hasta 10000.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Raíz, residuo, estado de convergencia, iteraciones y gráfica."""
    return _invoke("roots", method, "raiz", solve_root,
                   expression=expression, method=method, a=a, b=b, x0=x0, x1=x1,
                   g_expression=g_expression or None, tolerance=tolerance, max_iter=max_iter, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_sistema_lineal",
           title="Resolver sistema lineal")
def resolver_sistema_lineal(matrix: list[list[float]], vector: list[float],
                            method: str = "gaussian",
                            tolerance: float = 1e-10, max_iter: int = 1000,
                            preconditioner: str = "none", level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve A·x=b por métodos directos o iterativos densos.

    Args:
        matrix: Matriz cuadrada finita de hasta 250 por 250.
        vector: Vector b de la misma dimensión.
        method: gaussian, lu, jacobi, gauss_seidel, conjugate_gradient, gmres, qr o svd.
        tolerance, max_iter: Criterios de los métodos iterativos.
        preconditioner: none o jacobi para CG/GMRES.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Solución, residuo, convergencia y tablas de iteraciones cuando apliquen."""
    return _invoke("linear_system", method, "sistema_lineal", solve_linear,
                   matrix=matrix, vector=vector, method=method, tolerance=tolerance,
                   max_iter=max_iter, preconditioner=preconditioner, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_sistema_disperso",
           title="Resolver sistema lineal disperso")
def resolver_sistema_disperso(size: int, entries: list[list[float]], vector: list[float],
                              method: str = "cg", tolerance: float = 1e-8,
                              max_iter: int = 2000,
                              preconditioner: str = "none", level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve A·x=b conservando A dispersa a partir de tripletas COO.

    Args:
        size: Orden de la matriz.
        entries: Tripletas [fila,columna,valor], índices base 0.
        vector: Vector b.
        method: cg o gmres.
        tolerance, max_iter: Criterios iterativos.
        preconditioner: none o jacobi.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Solución, residuo y diagnósticos del método iterativo."""
    return _invoke("sparse_linear_system", method, "sistema_disperso",
                   solve_sparse_linear, size=size, entries=entries, vector=vector,
                   method=method, tolerance=tolerance, max_iter=max_iter,
                   preconditioner=preconditioner, level=level, include_report=include_report)

@apps.tool(resource_uri=NUMERICAL_UI_URI, name="ajustar_datos",
           title="Interpolar o ajustar datos")
def ajustar_datos(points: list[dict[str, float]], method: str = "least_squares",
                  degree: int = 1,
                  evaluation_points: list[float] | None = None, level: str = "inicial", include_report: bool = True) -> dict:
    """Interpola o ajusta puntos con mínimos cuadrados, spline o interpolación lineal por tramos.

    Args:
        points: Puntos [{"x": número, "y": número}, ...], con x distintos.
        method: Método de ajuste admitido por fit_data.
        degree: Grado del ajuste polinómico.
        evaluation_points: Abscisas donde evaluar si se solicitan.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Modelo, evaluaciones, residuos, tabla y datos para la gráfica."""
    return _invoke("approximation", method, "ajuste_datos", fit_data,
                   points=points, method=method, degree=degree,
                   evaluation_points=evaluation_points, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="derivar_numericamente",
           title="Derivar numéricamente")
def derivar_numericamente(expression: str, x: float, h: float = 1e-4,
                          method: str = "central", level: str = "inicial", include_report: bool = True) -> dict:
    """Aproxima una derivada de una expresión en un punto.

    Args:
        expression: Función segura en x.
        x: Punto de evaluación.
        h: Paso positivo de diferencias finitas.
        method: central, forward, backward o Richardson, según la implementación.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Derivada aproximada, pasos y diagnósticos del paso."""
    return _invoke("differentiation", method, "derivada", differentiate,
                   expression=expression, x=x, h=h, method=method, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="derivar_tabla_numericamente",
           title="Derivar datos tabulados")
def derivar_tabla_numericamente(points: list[dict[str, float]], method: str = "central", level: str = "inicial", include_report: bool = True) -> dict:
    """Estima derivadas de puntos tabulados, incluso con malla no uniforme cuando esté admitida.

    Args:
        points: Lista de puntos [{"x": número, "y": número}, ...].
        method: Diferencia disponible; por defecto central.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Estimaciones de derivada y tabla de datos derivados."""
    return _invoke("tabular_differentiation", method, "derivada_tabla",
                   differentiate_data, points=points, method=method, level=level, include_report=include_report)

@apps.tool(resource_uri=NUMERICAL_UI_URI, name="integrar_numericamente",
           title="Integrar numéricamente")
def integrar_numericamente(expression: str, a: float, b: float, n: int = 100,
                           method: str = "simpson", level: str = "inicial", include_report: bool = True) -> dict:
    """Aproxima una integral definida de una expresión mediante cuadratura fija.

    Args:
        expression: Integrando seguro en x.
        a, b: Límites de integración, distintos.
        n: Número de subintervalos o nodos según el método.
        method: trapezoid, simpson o gauss_legendre.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Integral, estimación de error cuando disponible, tabla y gráfica."""
    return _invoke("quadrature", method, "integral", integrate,
                   expression=expression, a=a, b=b, n=n, method=method, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="integrar_tabla_numericamente",
           title="Integrar datos tabulados")
def integrar_tabla_numericamente(points: list[dict[str, float]], method: str = "trapezoid", level: str = "inicial", include_report: bool = True) -> dict:
    """Integra valores tabulados con reglas compuestas disponibles.

    Args:
        points: Puntos [{"x": número, "y": número}, ...] ordenables por x.
        method: trapezoid o simpson según los requisitos de la malla.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Integral, aportes por panel y advertencia sobre error estimado."""
    return _invoke("tabular_quadrature", method, "integral_tabla",
                   integrate_data, points=points, method=method, level=level, include_report=include_report)

@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_edo",
           title="Resolver ecuación diferencial ordinaria")
def resolver_edo(equations: list[str], initial_state: list[float],
                 t0: float, t_end: float, step: float = 0.1,
                 method: str = "rk4",
                 state_names: list[str] | None = None,
                 tolerance: float = 1e-8, level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve un problema de valor inicial para un sistema de EDO.

    Args:
        equations: Una expresión dy_i/dt por variable; admite t y nombres de estado.
        initial_state: Valores iniciales en el mismo orden.
        t0, t_end: Extremos del intervalo.
        step: Paso máximo/fijo según el método.
        method: euler, heun, midpoint, rk4, rk45 o bdf.
        state_names: Nombres válidos opcionales de variables de estado.
        tolerance: Tolerancia de RK45/BDF.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Estado final, trayectoria tabulada y diagnósticos de integración."""
    return _invoke("ode", method, "edo", solve_ode,
                   equations=equations, initial_state=initial_state,
                   t0=t0, t_end=t_end, step=step, method=method,
                   state_names=state_names, tolerance=tolerance, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_valores_propios",
           title="Resolver valores propios")
def resolver_valores_propios(matrix: list[list[float]], method: str = "qr",
                             count: int = 1, tolerance: float = 1e-10,
                             max_iter: int = 1000, shift: float = 0.0, level: str = "inicial", include_report: bool = True) -> dict:
    """Calcula valores y vectores propios de una matriz densa.

    Args:
        matrix: Matriz cuadrada finita de hasta 100 por 100.
        method: qr, power o inverse; los iterativos requieren simetría.
        count: Número de pares solicitados para QR.
        tolerance, max_iter: Criterios iterativos.
        shift: Desplazamiento del método inverse.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Pares propios, residuos y tablas de iteración cuando aplique."""
    return _invoke("eigenvalues", method, "valores_propios", eigen_solve,
                   matrix=matrix, method=method, count=count, tolerance=tolerance,
                   max_iter=max_iter, shift=shift, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="optimizar_funcion",
           title="Optimizar función")
def optimizar_funcion(expression: str, initial: list[float],
                      variables: list[str] | None = None,
                      method: str = "bfgs", tolerance: float = 1e-7,
                      max_iter: int = 500, level: str = "inicial", include_report: bool = True) -> dict:
    """Minimiza una función diferenciable sin restricciones desde un punto inicial.

    Args:
        expression: Función segura en las variables declaradas.
        initial: Vector inicial de 1 a 5 valores.
        variables: Nombres opcionales de las variables.
        method: gradient_descent, newton o bfgs.
        tolerance, max_iter: Criterios de parada.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Minimizador, valor objetivo, norma del gradiente y convergencia."""
    return _invoke("optimization", method, "optimizacion", optimize,
                   expression=expression, initial=initial, variables=variables,
                   method=method, tolerance=tolerance, max_iter=max_iter, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_problema_frontera",
           title="Resolver problema de frontera 1D")
def resolver_problema_frontera(rhs_expression: str, a: float, b: float,
                               alpha: float, beta: float, n: int = 40,
                               method: str = "shooting", level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve un problema de frontera 1D para y''=f con valores en ambos extremos.

    Args:
        rhs_expression: f(x) para finite_difference o f(x,y,yp) para shooting.
        a, b: Límites con a<b.
        alpha, beta: Valores de y(a) e y(b).
        n: Número de subintervalos, de 3 a 300.
        method: shooting o finite_difference.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Perfil aproximado, residuo de frontera y tabla/gráfica."""
    return _invoke("boundary_value", method, "problema_frontera", solve_bvp,
                   rhs_expression=rhs_expression, a=a, b=b, alpha=alpha,
                   beta=beta, n=n, method=method, level=level, include_report=include_report)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_pde",
           title="Resolver PDE modelo 1D")
def resolver_pde(problem_type: str, length: float, nx: int, nt: int,
                 diffusivity: float = 1.0, speed: float = 1.0,
                 initial_values: list[float] | None = None,
                 initial_expression: str = "sin(pi*x)",
                 boundary_left: float = 0.0, boundary_right: float = 0.0,
                 dt: float | None = None, level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve modelos PDE 1D de calor, onda o Laplace con diferencias finitas.

    Args:
        problem_type: heat, wave o laplace.
        length, nx, nt: Longitud, subintervalos espaciales y pasos temporales.
        diffusivity, speed: Parámetros físicos para calor/onda.
        initial_values: Perfil inicial de nx+1 valores; alternativamente initial_expression.
        boundary_left, boundary_right: Valores de frontera.
        dt: Paso temporal opcional.
        level: Nivel de presentación; include_report: habilita el PDF.

    Returns:
        Solución de malla, perfil final, diagnósticos de estabilidad y mapa/gráfica."""
    return _invoke("pde", problem_type, "pde_1d", solve_pde,
                   problem_type=problem_type, length=length, nx=nx, nt=nt,
                   diffusivity=diffusivity, speed=speed,
                   initial_values=initial_values,
                   initial_expression=initial_expression,
                   boundary_left=boundary_left, boundary_right=boundary_right, dt=dt, level=level, include_report=include_report)



@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_sistema_no_lineal",
           title="Resolver sistema no lineal")
def resolver_sistema_no_lineal(equations: list[str], variables: list[str],
                               initial: list[float], tolerance: float = 1e-8,
                               max_iter: int = 100, damping: bool = True,
                               level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve un sistema F(x)=0 con Newton multivariable y Jacobiano numérico.

    Args:
        equations: Una expresión residual por variable.
        variables: Identificadores únicos en el orden de las incógnitas.
        initial: Estimación inicial del mismo tamaño.
        tolerance: Norma de residuo requerida.
        max_iter: Límite entre 1 y 500.
        damping: Usa búsqueda amortiguada para reducir el residuo.
        level: Nivel 'inicial' o 'intermedio'.
        include_report: Genera el PDF si es true.

    Returns:
        Solución, residuo, historial de Newton, convergencia e informe opcional."""
    return _invoke("nonlinear_system", "Newton multivariable", "sistema_no_lineal",
                   solve_nonlinear_system, level=level, include_report=include_report,
                   equations=equations, variables=variables, initial=initial,
                   tolerance=tolerance, max_iter=max_iter, damping=damping)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="analizar_condicionamiento",
           title="Analizar condicionamiento y sensibilidad")
def analizar_condicionamiento(matrix: list[list[float]], vector: list[float] | None = None,
                              perturbation: list[float] | None = None,
                              norm: str = "2", level: str = "inicial",
                              include_report: bool = True) -> dict:
    """Calcula el número de condición de A y mide sensibilidad de Ax=b ante Δb opcional.

    Args:
        matrix: Matriz cuadrada finita.
        vector: Vector b opcional para resolver el sistema.
        perturbation: Δb opcional del mismo tamaño que b.
        norm: Norma '1', '2' o 'inf'.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        κ(A), solución si b existe y cambio observado si también se da Δb."""
    return _invoke("conditioning", "Número de condición", "condicionamiento",
                   analyze_conditioning, level=level, include_report=include_report,
                   matrix=matrix, vector=vector, perturbation=perturbation, norm=norm)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_edo_multipaso",
           title="Resolver EDO con Adams multipaso")
def resolver_edo_multipaso(equations: list[str], initial_state: list[float],
                           t0: float, t_end: float, step: float = 0.1,
                           method: str = "ab4", state_names: list[str] | None = None,
                           level: str = "inicial", include_report: bool = True) -> dict:
    """Integra sistemas de EDO con Adams-Bashforth 2/4 o predictor-corrector ABM4.

    Args:
        equations: Una derivada por variable de estado.
        initial_state: Estado inicial en t0.
        t0, t_end: Intervalo creciente de integración.
        step: Paso fijo positivo.
        method: ab2, ab4 o abm4.
        state_names: Nombres de estados opcionales.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        Trayectoria, estado final y pasos de arranque RK4; no estima error global."""
    return _invoke("ode_multistep", method, "edo_multipaso", solve_ode_multistep,
                   level=level, include_report=include_report, equations=equations,
                   initial_state=initial_state, t0=t0, t_end=t_end, step=step,
                   method=method, state_names=state_names)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_pde_2d",
           title="Resolver Laplace o Poisson 2D")
def resolver_pde_2d(problem_type: str, length_x: float, length_y: float,
                    nx: int, ny: int, source_expression: str = "0",
                    boundary_left: list[float] | None = None,
                    boundary_right: list[float] | None = None,
                    boundary_bottom: list[float] | None = None,
                    boundary_top: list[float] | None = None,
                    method: str = "sor", omega: float = 1.5,
                    tolerance: float = 1e-6, max_iter: int = 3000,
                    level: str = "inicial", include_report: bool = True) -> dict:
    """Resuelve Laplace o Poisson en rectángulo con diferencias finitas y fronteras Dirichlet.

    Args:
        problem_type: laplace o poisson; para Poisson se resuelve Δu=f.
        length_x, length_y: Dimensiones positivas del dominio.
        nx, ny: Subintervalos, de 4 a 50 por dirección.
        source_expression: f(x,y), requerida para Poisson y cero para Laplace.
        boundary_left/right: Valores en ny+1 puntos por lado.
        boundary_bottom/top: Valores en nx+1 puntos por lado; esquinas deben coincidir.
        method: sor o gauss_seidel.
        omega: Factor SOR entre 0 y 2.
        tolerance, max_iter: Criterio de residuo y límite de iteraciones.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        Malla u(x,y), residuo, convergencia, tabla y mapa de calor."""
    return _invoke("pde_2d", problem_type, "pde_2d", solve_pde_2d,
                   level=level, include_report=include_report,
                   problem_type=problem_type, length_x=length_x, length_y=length_y,
                   nx=nx, ny=ny, source_expression=source_expression,
                   boundary_left=boundary_left, boundary_right=boundary_right,
                   boundary_bottom=boundary_bottom, boundary_top=boundary_top,
                   method=method, omega=omega, tolerance=tolerance, max_iter=max_iter)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="optimizar_funcion_restringida",
           title="Optimizar función con restricciones")
def optimizar_funcion_restringida(expression: str, initial: list[float],
                                  variables: list[str] | None = None,
                                  bounds: list[list[float | None]] | None = None,
                                  equality_constraints: list[str] | None = None,
                                  inequality_constraints: list[str] | None = None,
                                  tolerance: float = 1e-7, max_iter: int = 500,
                                  level: str = "inicial", include_report: bool = True) -> dict:
    """Minimiza una función con SLSQP, restricciones de igualdad y desigualdades g(x)>=0.

    Args:
        expression: Función objetivo segura.
        initial: Estimación inicial de 1 a 5 variables.
        variables: Identificadores opcionales en el orden de initial.
        bounds: Pares [mínimo,máximo] por variable; un extremo puede ser null.
        equality_constraints: Expresiones que deben valer cero.
        inequality_constraints: Expresiones que deben ser no negativas.
        tolerance, max_iter: Criterios de parada.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        Minimizador, objetivo, valores de restricciones y estado de factibilidad."""
    return _invoke("constrained_optimization", "SLSQP", "optimizacion_restringida",
                   optimize_constrained, level=level, include_report=include_report,
                   expression=expression, initial=initial, variables=variables,
                   bounds=bounds, equality_constraints=equality_constraints,
                   inequality_constraints=inequality_constraints,
                   tolerance=tolerance, max_iter=max_iter)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="resolver_valores_propios_dispersos",
           title="Resolver valores propios de matriz dispersa")
def resolver_valores_propios_dispersos(size: int, entries: list[list[float]],
                                       count: int = 1, which: str = "LM",
                                       tolerance: float = 1e-8, max_iter: int = 1000,
                                       level: str = "inicial", include_report: bool = True) -> dict:
    """Calcula pares propios de matriz real simétrica COO sin convertirla a densa.

    Args:
        size: Orden entre 2 y 10000.
        entries: Tripletas [fila,columna,valor] con índices base 0; matrix debe ser simétrica.
        count: Cantidad entre 1 y min(20,size-1).
        which: LM, SM, LA o SA según ARPACK.
        tolerance, max_iter: Criterios del método Lanczos/ARPACK.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        Valores, vectores propios, residuos y cantidad de entradas no nulas."""
    return _invoke("sparse_eigenvalues", "Lanczos / ARPACK", "valores_propios_dispersos",
                   solve_sparse_eigenvalues, level=level, include_report=include_report,
                   size=size, entries=entries, count=count, which=which,
                   tolerance=tolerance, max_iter=max_iter)


@apps.tool(resource_uri=NUMERICAL_UI_URI, name="integrar_adaptativamente",
           title="Integrar con cuadratura adaptativa")
def integrar_adaptativamente(expression: str, a: float, b: float,
                             absolute_tolerance: float = 1e-9,
                             relative_tolerance: float = 1e-9,
                             max_subintervals: int = 200,
                             level: str = "inicial", include_report: bool = True) -> dict:
    """Integra una función con cuadratura adaptativa Gauss-Kronrod y estimación de error.

    Args:
        expression: Integrando seguro en x.
        a, b: Límites distintos, incluso en orden inverso.
        absolute_tolerance, relative_tolerance: Tolerancias positivas.
        max_subintervals: Límite de subdivisiones entre 1 y 500.
        level: Nivel de presentación; include_report genera PDF opcional.

    Returns:
        Integral, error estimado, evaluaciones y tabla de subintervalos adaptativos."""
    return _invoke("adaptive_quadrature", "Gauss-Kronrod adaptativa", "integral_adaptativa",
                   integrate_adaptive, level=level, include_report=include_report,
                   expression=expression, a=a, b=b,
                   absolute_tolerance=absolute_tolerance,
                   relative_tolerance=relative_tolerance,
                   max_subintervals=max_subintervals)


apps.add_html_resource(
    LEGACY_UI_URI, LEGACY_UI_FILE.read_text(encoding="utf-8"),
    name="interpolation-ui-v5", title="Interpolación Newton y Lagrange",
    prefers_border=True, csp=ResourceCsp(frame_domains=[public_origin()]))

apps.add_html_resource(
    NUMERICAL_UI_URI, NUMERICAL_UI_FILE.read_text(encoding="utf-8"),
    name="numerical-methods-ui-v1", title="Resolución de métodos numéricos",
    prefers_border=True, csp=ResourceCsp(frame_domains=[public_origin()]))

mcp = MCPServer(SERVER_NAME, extensions=[apps])


@mcp.custom_route("/reports/{filename}/preview", methods=["GET"], include_in_schema=False)
async def preview_report(request: Request):
    path = resolve_pdf(request.path_params["filename"])
    if path is None:
        return PlainTextResponse("PDF no encontrado.", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=path.name,
                        content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff"})


@mcp.custom_route("/reports/{filename}/download", methods=["GET"], include_in_schema=False)
async def download_report(request: Request):
    path = resolve_pdf(request.path_params["filename"])
    if path is None:
        return PlainTextResponse("PDF no encontrado.", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=path.name,
                        content_disposition_type="attachment",
                        headers={"X-Content-Type-Options": "nosniff"})


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
